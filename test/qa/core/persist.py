"""Persistence and robustness: reload keeps state; corrupt/partial/old-version storage; storage throwing (get/set);
quota errors; bad game registrations and throwing packs via add_init_script."""
import json
from qa_common import *
def rep(name, ok, detail=''): print(('OK  ' if ok else 'BUG ') + name, detail)

def fresh(storage_value=None, extra_init=None, adult=True):
    inits = []
    if storage_value is not None:
        inits.append("try{ if (!sessionStorage.getItem('qa_seeded')) { localStorage.setItem('duelgold.v2', %s); sessionStorage.setItem('qa_seeded','1'); } }catch(e){}" % json.dumps(storage_value))
    if extra_init: inits.append(extra_init)
    return inits

cases = {
  'corrupt JSON': '{"v":2, gold:',
  'wrong type (array)': '[1,2,3]',
  'old version v1': json.dumps({'v': 1, 'gold': 999999}),
  'partial v2': json.dumps({'v': 2, 'gold': 1234}),
  'hostile v2': json.dumps({'v': 2, 'gold': -5, 'dp': 'lots', 'games': {'sudoku': {'r': 'x', 'w': -3}, 'bad': 5}, 'history': [None, 5, {'g': 'x', 'net': 'NaN'}], 'friends': 'nope', 'limits': {'loss': -100, 'coolUntil': 'soon'}, 'today': 7, 'age': 'child', 'favs': [1, 'sudoku'], 'cos': {'owned': 'x'}, 'tours': [], 'ach': None, 'rec': {'w': 'a'}, 'streak': 'x', 'name': {'a': 1}}),
  'huge gold float': json.dumps({'v': 2, 'gold': 1e308, 'dp': 1.5}),
  'name with html': json.dumps({'v': 2, 'name': '<img src=x onerror=window.__xss=1>', 'history': [{'g': 'sudoku', 'gn': '<b onmouseover=1>x</b>', 'f': '1v1', 'o': 'win', 'net': 5, 'vs': '<script>window.__xss=2</script>'}]}),
}
for name, val in cases.items():
    with browser_page(width=1280) as page:
        boot(page, init=fresh(val))
        st = page.evaluate("DGApp.state()")
        tabs_ok = True
        for t in ['home', 'games', 'watch', 'tournaments', 'social', 'profile', 'settings']:
            page.evaluate(f"DGApp.go('{t}')")
            if page.locator(f'#view-{t} #viewRetry').count(): tabs_ok = False
        e = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:10})"); page.evaluate("DGApp.close()")
        types = {k: type(st[k]).__name__ for k in ['gold', 'dp', 'streak', 'name', 'history', 'friends']}
        rep(f'storage {name}', tabs_ok and not errs(page) and not page.evaluate("window.__xss || 0"),
            f"gold={st['gold']} dp={st['dp']} streak={st['streak']!r} name={st['name']!r} types={types} age={st['age']} start={e!r} errs={errs(page)[:2]} xss={page.evaluate('window.__xss || 0')}")

# reload keeps state
with browser_page() as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(20)")
    page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100})")
    page.wait_for_function("DGApp.current().phase==='ready'"); page.evaluate("document.querySelector('#mStart').click()")
    page.wait_for_function("DGApp.current().phase==='play'"); page.evaluate("DGApp.ctx().end({score:1e6})")
    page.wait_for_function("DGApp.current().phase==='result'"); page.evaluate("DGApp.close()")
    page.evaluate("DGApp.set({favs:['sudoku'], club:'owls'})")
    s0 = page.evaluate("DGApp.state()")
    page.reload(); page.wait_for_function("DG.__appReady")
    s1 = page.evaluate("DGApp.state()")
    diff = [k for k in s0 if json.dumps(s0[k], sort_keys=True) != json.dumps(s1[k], sort_keys=True)]
    rep('reload keeps state', not diff and not page.locator('#ageAdult').count(), f'diff keys {diff}')

# storage throwing: getter throws; setItem throws (quota)
for label, init in [('localStorage getter throws', "Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})"),
                    ('setItem throws (quota)', "Storage.prototype.setItem = function(){ throw new DOMException('quota','QuotaExceededError'); }"),
                    ('getItem returns garbage type', "Storage.prototype.getItem = function(){ return {}; }")]:
    with browser_page() as page:
        boot(page, init=[init])
        page.evaluate("DGApp.setSpeed(20)")
        page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100})")
        page.wait_for_function("DGApp.current().phase==='ready'"); page.evaluate("document.querySelector('#mStart').click()")
        page.wait_for_function("DGApp.current().phase==='play'"); page.evaluate("DGApp.ctx().end({score:1e6})")
        page.wait_for_function("DGApp.current().phase==='result'"); page.evaluate("DGApp.close()")
        page.evaluate("DGApp.go('settings')")
        note = page.inner_text('#storageNote')
        rep(f'{label}', page.evaluate("DGApp.state().gold") == 10080 and not errs(page), f'gold {page.evaluate("DGApp.state().gold")} note={note!r} errs={errs(page)[:2]}')

# bad game registrations + throwing pack, registered BEFORE packs load
BAD = r"""
(() => {
  let reg = null;
  Object.defineProperty(window, 'DG', { configurable: true, get(){ return reg; }, set(v){
    reg = v;
    const orig = v.registerGame;
    queueMicrotask(() => {});
    // hook registerGame when sdk assigns it
    let rg = null;
    Object.defineProperty(v, 'registerGame', { configurable: true, get(){ return rg; }, set(fn){
      rg = fn;
      // after sdk defines registerGame, inject bad games immediately (before real packs)
      setTimeout(()=>{}, 0);
      const bads = [
        null,
        {},
        { id: 'qa-nokind', name: 'x', category: 'puzzle', formats: ['1v1'], skill: 1, luck: 1, blurb: 'b', rules: ['r'], play(){} },
        { id: 'qa-norace-bot', name: 'x', category: 'puzzle', kind: 'race', formats: ['1v1'], skill: 1, luck: 1, blurb: 'b', rules: ['r'], play(){} },
        { id: 'qa-badfmt', name: 'x', category: 'puzzle', kind: 'versus', formats: ['ffa'], skill: 1, luck: 1, blurb: 'b', rules: ['r'], play(){} },
        { id: 'sudoku', name: 'Fake Sudoku', category: 'puzzle', kind: 'versus', formats: ['1v1'], skill: 1, luck: 1, blurb: 'b', rules: ['r'], play(){} },
        { id: 'qa-formats-string', name: 'x', category: 'puzzle', kind: 'versus', formats: '1v1', skill: 1, luck: 1, blurb: 'b', rules: ['r'], play(){} },
        { id: 'qa-rules-string', name: 'QA Rules String', category: 'puzzle', kind: 'versus', formats: ['1v1','tournament'], skill: 'high', luck: 99, blurb: 5, rules: 'just one', play(ctx){ throw new Error('play boom'); } },
        { id: 'qa-throw-bot', name: 'QA Throw Bot', category: 'reflex', kind: 'race', formats: ['1v1','2v2','ffa','tournament','mix'], skill: 5, luck: 1, blurb: 'b', rules: ['r'], play(ctx){ ctx.end({score: 1}); }, bot(){ throw new Error('bot boom'); } },
        { id: 'qa-nan-bot', name: 'QA NaN Bot', category: 'reflex', kind: 'race', formats: ['1v1','tournament','mix'], skill: 5, luck: 1, blurb: 'b', rules: ['r'], play(ctx){ ctx.end({score: 1}); }, bot(){ return {score: NaN, timeline: []}; } },
        { id: 'qa-getter', name: 'QA Getter', category: 'reflex', kind: 'race', formats: ['1v1'], skill: 5, luck: 1, blurb: 'b', get rules(){ throw new Error('getter boom'); }, play(){}, bot(){ return {score:1, timeline:[[1,1]]}; } },
        { id: 'qa-fmtscore', name: 'QA FmtScore', category: 'reflex', kind: 'race', formats: ['1v1'], skill: 5, luck: 1, blurb: 'b', rules: ['r'], formatScore(){ throw new Error('fmt boom'); }, play(ctx){ ctx.end({score: 3}); }, bot(){ return {score:1, timeline:[[1,1]]}; } },
      ];
      window.__qaBad = bads.map(b => { try { return !!rg.call(v, b); } catch(e) { return 'threw:' + e.message; } });
      // a whole pack that throws while registering
      try { (function(){ throw new Error('pack exploded'); })(); } catch(e) { v.loadErrors.push({id:'qa-pack', message: e.message}); }
    }});
  }});
})();
"""
with browser_page() as page:
    boot(page, init=[BAD])
    print('   registerGame results:', page.evaluate("window.__qaBad"))
    print('   DG.loadErrors:', page.evaluate("JSON.stringify(DG.loadErrors).slice(0,600)"))
    box = page.evaluate("document.querySelector('#loadErrors').hidden ? '(hidden)' : document.querySelector('#loadErrors').innerText")
    print('   #loadErrors box:', box[:400])
    n = page.evaluate("DG.games.length"); ids = page.evaluate("DG.games.map(g=>g.id)")
    print('   games registered:', n, [i for i in ids if i.startswith('qa')], 'sudoku kind:', page.evaluate("DG.getGame('sudoku').kind"))
    for t in ['home', 'games', 'watch', 'tournaments', 'social', 'profile']:
        page.evaluate(f"DGApp.go('{t}')")
        if page.locator(f'#view-{t} #viewRetry').count(): print('   view broke:', t)
    page.evaluate("DGApp.setSpeed(20)")
    for gid, fmt in [('qa-rules-string', '1v1'), ('qa-throw-bot', 'ffa'), ('qa-throw-bot', 'tournament'), ('qa-nan-bot', '1v1'), ('qa-nan-bot', 'tournament'), ('qa-fmtscore', '1v1'), ('qa-throw-bot', 'mix')]:
        g0 = page.evaluate("DGApp.state().gold")
        e = page.evaluate("(o)=>DGApp.startMatch(o)", {'game': gid, 'format': fmt, 'stake': 100})
        if e: print(f'   {gid}/{fmt}: refused {e!r}'); continue
        try:
            page.wait_for_function("DGApp.current() && ['ready','error','result','between'].includes(DGApp.current().phase)", timeout=8000)
            if page.evaluate("DGApp.current().phase") in ('ready',):
                page.evaluate("document.querySelector('#mStart').click()")
            page.wait_for_function("DGApp.current() && ['error','result'].includes(DGApp.current().phase)", timeout=8000)
        except Exception as ex:
            print(f'   {gid}/{fmt}: STUCK in', page.evaluate("DGApp.current()"))
        ph = page.evaluate("DGApp.current() && DGApp.current().phase"); g1 = page.evaluate("DGApp.state().gold")
        print(f'   {gid}/{fmt}: phase={ph} gold {g0}->{g1} last={page.evaluate("DGApp.last()")}')
        page.evaluate("DGApp.close()")
    print('   console errors (expected logged failures):', len(errs(page)))
