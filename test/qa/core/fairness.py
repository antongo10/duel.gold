"""Fairness / identical content: for every race game, play() content (read back via ctx.test / DOM) must equal the
content the bot uses (pure generator), independent of viewport width, Math.random, wall clock and ctx speed.
Runs in the harness (single game) at two widths, with Math.random / Date.now poisoned differently per run."""
import json, sys
sys.path.insert(0, '/home/claude/duel-gold/test')
from dglib import browser_page, open_harness

POISON = """(() => { let s = %d; Math.random = () => { s = (s * 1103515245 + 12345) %% 2147483648; return s / 2147483648; };
  const d0 = Date.now(); const off = %d; Date.now = () => d0 + off; })();"""

FILES = {'sudoku': 'brain.js', 'mines': 'brain.js', 'queens': 'brain.js', 'tiles2048': 'brain.js', 'memory': 'brain.js',
         'reaction': 'reflex.js', 'aim': 'reflex.js', 'rush': 'reflex.js', 'darts': 'reflex.js',
         'base': 'builder.js', 'city': 'builder.js', 'restaurant': 'builder.js', 'trivia': 'social.js', 'groups': 'social.js'}

# expression that extracts the content the HUMAN faces, after __run
PLAY = {
  'sudoku':    "(() => { const t = __handle.ctx.test; return {sol: t.solution(), given: t.state().values}; })()",
  'mines':     "(() => { const t = __handle.ctx.test; return {mines: t.solution(), open: t.state().open}; })()",
  'queens':    "(() => { const t = __handle.ctx.test; return {sol: t.solution(), reg: [...document.querySelectorAll('[data-region]')].map(e=>+e.dataset.region)}; })()",
  'tiles2048': "(() => { const t = __handle.ctx.test; const seq=[]; seq.push(t.state().board.join(',')); for (const d of [3,0,1,2,3,0,3,0,1,3,0,2]) { t.move(d); seq.push(t.state().board.join(',')); } return seq; })()",
  'memory':    "null",
  'reaction':  "__handle.ctx.test.state().delays",
  'aim':       "__handle.ctx.test.schedule()",
  'rush':      "(() => { const t = __handle.ctx.test, out = []; for (let i=0;i<15;i++){ const c=t.state().current; out.push([c.text, c.options.join('/'), c.correct]); t.answerCorrect(); } return out; })()",
  'darts':     "(() => { const t = __handle.ctx.test; return [t.reticle().x.toFixed(3), t.throwAt(0,103).label]; })()",
  'base':      "__handle.ctx.test.legal('wall').length + '|' + JSON.stringify(__handle.ctx.test.state().gold)",
  'city':      "__handle.ctx.test.state().tiles",
  'restaurant':"__handle.ctx.test.state().proj",
  'trivia':    "__handle.ctx.test.state().ids",
  'groups':    "__handle.ctx.test.solution()",
}
# pure generator the BOT uses (same seed/mode)
GEN = {
  'sudoku':    "(({seed,mode}) => { const P = DG.getGame('sudoku').lab.generate(seed, mode); return {sol: P.solution, given: P.puzzle}; })",
  'mines':     "(({seed,mode}) => { const B = DG.getGame('mines').lab.generate(seed, mode); return {mines: B.mine, start: B.start}; })",
  'queens':    "(({seed,mode}) => { const P = DG.getGame('queens').lab.generate(seed, 0, 6); return {sol: P.sol.map((c,r)=>r*P.N+c), reg: P.reg}; })",
  'tiles2048': "(({seed,mode}) => { const L = DG.getGame('tiles2048').lab; const ds=[3,0,1,2,3,0,3,0,1,3,0,2]; const seq=[L.initial(seed).join(',')]; const played=[]; for (const d of ds){ played.push(d); seq.push(L.sim(seed, played).board.join(',')); } return seq; })",
  'rush':      "(({seed,mode}) => DG.getGame('rush')._content(seed, mode).probs.slice(0,15).map(c => [c.text, c.options.join('/'), c.correct]))",
  'city':      "(({seed,mode}) => DG.getGame('city')._lab.cityMap(seed, mode).tiles)",
  'restaurant':"(({seed,mode}) => { const L = DG.getGame('restaurant')._lab; return L.restSim(L.restDay(seed), L.restDefaultPlan()); })",
}

res = {}
for gid, f in FILES.items():
    for mode in ['full', 'mix']:
        outs = []
        for (w, rs, off, speed) in [(400, 1, 0, 1), (1280, 99, 86400000 * 3, 7)]:
            with browser_page(width=w) as page:
                page.add_init_script(POISON % (rs, off))
                open_harness(page, files=[f], game=gid, mode=mode, seed=481023, skill=0.5, speed=speed)
                page.evaluate("__run()")
                page.wait_for_timeout(250)
                v = page.evaluate(PLAY[gid])
                gen = page.evaluate(GEN[gid] + "({seed:481023, mode:'%s'})" % mode) if gid in GEN else None
                errs = page.evaluate("__errors")
                outs.append((json.dumps(v, sort_keys=True), json.dumps(gen, sort_keys=True) if gen is not None else None, errs))
        same_play = outs[0][0] == outs[1][0]
        vs_gen = None
        if outs[0][1] is not None:
            a = json.loads(outs[0][0]); b = json.loads(outs[0][1])
            if gid == 'sudoku': vs_gen = a['sol'] == b['sol'] and a['given'] == b['given']
            elif gid == 'mines': vs_gen = a['mines'] == b['mines']
            elif gid == 'queens': vs_gen = (a['sol'] == b['sol'] and a['reg'] == b['reg']) if mode == 'mix' or True else None
            else: vs_gen = a == b
        print(f"{gid:10s} {mode:4s} play-identical-across(width,Math.random,Date.now,speed)={same_play}  play==bot-generator={vs_gen}  errs={outs[0][2] + outs[1][2]}")
        if not same_play:
            print('    run1:', outs[0][0][:200]); print('    run2:', outs[1][0][:200])
        if vs_gen is False:
            print('    play:', outs[0][0][:200]); print('    gen :', outs[0][1][:200])
