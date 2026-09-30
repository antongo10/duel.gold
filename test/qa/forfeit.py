import json, sys
from qalib import *
from finish import FIN
width = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
touch = width < 500
def rep(*a): print(*a, flush=True)
SNAP = "(() => ({raf: __qa.rafCalls, pend: __qa.raf, iv: __qa.iv, kd: __qa.keydown, audio: __qa.audio, status: document.querySelector('#ovStatus').textContent}))()"
with new_page_ctx(width, touch=touch) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(3)")
    page.wait_for_timeout(500)
    base = page.evaluate(SNAP)
    rep('baseline', base)
    for gid in GAMES:
        g0 = st(page)['gold']; e0 = len(errs(page))
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000)
        page.click('[data-test=start]') if not touch else page.tap('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test", timeout=8000)
        # get the game busy: versus -> autoplay so AI engines run; race -> partial progress
        if GAMES[gid] == 'versus':
            try: T(page, "t.autoplay && t.autoplay(0.9)")
            except Exception: pass
        page.wait_for_timeout(1200)
        page.evaluate("window.__old = DGApp.ctx(); window.__oldState = JSON.stringify(window.__old.test.state ? window.__old.test.state() : null)")
        loc = page.locator('#ovForfeit'); loc.tap() if touch else loc.click()
        page.wait_for_selector('#forfeitYes')
        page.locator('#forfeitYes').tap() if touch else page.click('#forfeitYes')
        wait_result(page, 10)
        L = last(page); s1 = st(page)
        a = page.evaluate(SNAP)
        page.wait_for_timeout(2500)
        b = page.evaluate(SNAP)
        same = page.evaluate("JSON.stringify(window.__old.test.state ? window.__old.test.state() : null) === (() => { try { return JSON.stringify(window.__old.test.state()); } catch(e) { return 'ERR' } })()")
        changed = page.evaluate("(() => { try { return JSON.stringify(window.__old.test.state()) !== window.__oldState; } catch(e) { return 'ERR ' + e.message } })()")
        # game root cleared?
        root_gone = page.evaluate("!document.querySelector('#gameRoot')")
        res = dict(outcome=L['outcome'], payout=L['payout'], gold_ok=s1['gold'] == g0 - 100, hist=s1['history'][0]['o'],
                   raf_after=b['raf'] - a['raf'], pend=b['pend'], iv=b['iv'], kd=b['kd'], audio=b['audio'] - a['audio'], status_change=a['status'] != b['status'],
                   state_changed_after_abort=changed, root_gone=root_gone)
        page.locator('[data-test=back]').click()
        page.wait_for_timeout(300)
        c = page.evaluate(SNAP)
        res['after_close'] = dict(iv=c['iv'], kd=c['kd'], pend=c['pend'])
        # next match starts cleanly
        page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:0})")
        page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000)
        page.click('[data-test=start]') if not touch else page.tap('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test", timeout=8000)
        clean = page.evaluate("document.querySelectorAll('#gameRoot').length === 1 && document.querySelector('#gameRoot').dataset.game === 'sudoku'")
        page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(100); page.evaluate("DGApp.close()")
        res['next_clean'] = clean
        res['errors'] = errs(page)[e0:]
        flag = (res['outcome'] != 'loss' or res['payout'] != 0 or not res['gold_ok'] or res['raf_after'] > 0 or res['status_change'] or res['state_changed_after_abort'] is not False
                or res['after_close']['kd'] != base['kd'] or res['after_close']['iv'] != base['iv'] or res['after_close']['pend'] != 0 or res['errors'] or not clean or res['audio'])
        rep(('FLAG ' if flag else 'ok   ') + gid, json.dumps(res))
    rep('errors', errs(page))
