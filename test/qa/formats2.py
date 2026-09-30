import json, math, sys
from qalib import *
from finish import play_round, FIN
from formats_util import home_start
def rep(*a): print(*a, flush=True)

with new_page_ctx(1280) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(4)")
    # toast occlusion check
    page.evaluate("DGApp.startMatch({game:'darts', format:'1v1', stake:100})")
    play_round(page); wait_result(page, 60)
    page.evaluate("DGP.toast('Achievement unlocked · Test toast', 'gold', 8000)")
    hit = page.evaluate("""(() => { const b = document.querySelector('[data-test=rematch]'), r = b.getBoundingClientRect(); const out = [];
       for (const [x,y] of [[r.left+5,r.top+r.height/2],[r.left+r.width/2,r.top+r.height/2],[r.right-5,r.bottom-3]]) { const e = document.elementFromPoint(x,y); out.push(b.contains(e) ? 'rematch' : (e.className||e.tagName)); } return {rect:[r.top,r.bottom], toast: document.querySelector('.toast').getBoundingClientRect().top, hit: out, scrollH: document.querySelector('#ovScroll').scrollHeight, clientH: document.querySelector('#ovScroll').clientHeight}; })()""")
    rep('toast-vs-rematch', hit)
    shot(page, 'toast-over-rematch')
    page.click('[data-test=back]')

    # ---- Tournament: versus (four) and race (trivia)
    for gid in ('four', 'trivia'):
        g0 = st(page)['gold']; tp0 = st(page)['tp']
        home_start(page, gid, 'tournament', 100)
        page.wait_for_selector('[data-test=bracket]', timeout=8000)
        rounds = 0
        while True:
            c = cur(page)
            if c['phase'] in ('result', 'error'): break
            try:
                page.wait_for_function("DGApp.current().phase==='result' || !!document.querySelector('[data-test=start]:not([disabled])')", timeout=15000)
            except Exception:
                rep('stuck', cur(page)); shot(page, f'tour-stuck-{gid}'); break
            if cur(page)['phase'] == 'result': break
            play_round(page); rounds += 1
            page.wait_for_function("['between','result','ready'].includes(DGApp.current().phase) && !DGApp.ctx()?.test || DGApp.current().phase==='result' || (DGApp.ctx() && DGApp.ctx().signal.ended)", timeout=120000)
            page.wait_for_timeout(300)
            shot(page, f'tour-{gid}-r{rounds}')
            if rounds > 8: break
        L = last(page); s1 = st(page)
        prize = {0: 0, 1: 54, 2: 180, 3: 432}[L['stage']]
        ok = L['payout'] == prize and s1['gold'] == g0 - 100 + prize and s1['tp'] - tp0 == L['tp']
        rep('tournament', gid, 'rounds played', rounds, 'stage', L['stage'], 'payout', L['payout'], 'expected', prize, 'tp+', s1['tp'] - tp0, 'OK' if ok else 'BAD', 'hist', s1['history'][0])
        rep('   bracket text:', page.inner_text('[data-test=bracket]').replace('\n', ' | ')[:500])
        shot(page, f'tour-{gid}-final')
        page.click('[data-test=back]')

    # ---- Duel Mix via Home mix card
    for k in range(2):
        g0 = st(page)['gold']
        page.click('#tab-home'); page.click('#mixGo'); page.click('#dnS-100'); page.click('#dnFind')
        page.wait_for_selector('[data-test=mix]', timeout=8000)
        games = cur(page)['games']
        played = []
        for i in range(3):
            played.append(play_round(page))
            page.wait_for_function(f"DGApp.current().phase==='result' || (DGApp.current().mix && DGApp.current().mix.rounds.length==={i+1})", timeout=120000)
            if i == 0: shot(page, 'mix-after-r1')
        wait_result(page, 30)
        L = last(page); s1 = st(page)
        exp = {'win': 180, 'draw': 100, 'loss': 0}[L['outcome']]
        cats = page.evaluate(f"{json.dumps(games)}.map(id => DG.getGame(id).category)")
        mixok = all(page.evaluate(f"DG.getGame('{g}').formats.includes('mix') && DG.getGame('{g}').kind==='race'") for g in games)
        rep('mix', games, cats, 'played', played, L['outcome'], L['pts'], 'payout', L['payout'], 'OK' if L['payout'] == exp and s1['gold'] == g0 - 100 + exp and mixok and len(set(games)) == 3 else 'BAD', s1['history'][0]['s'])
        rep('   table:', page.inner_text('[data-test=mix-table]').replace('\n', ' | '))
        shot(page, f'mix-final-{k}')
        page.click('[data-test=back]')
    rep('errors', errs(page))
