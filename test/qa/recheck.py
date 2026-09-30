from qalib import *
from finish import play_round
with new_page_ctx(1280, height=600) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    # queens: which key scrolls?
    page.evaluate("DGApp.startMatch({game:'queens', format:'1v1', stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]')
    page.wait_for_function("DGApp.ctx() && DGApp.ctx().test"); page.wait_for_timeout(300)
    page.click('#ovInfo')
    for k in ['ArrowDown', 'ArrowDown', 'ArrowDown', 'PageDown', 'Space']:
        page.keyboard.press(k); page.wait_for_timeout(150)
        print('queens', k, 'scrollTop', page.evaluate("document.getElementById('ovScroll').scrollTop"), 'focus', page.evaluate("document.activeElement.dataset.test || document.activeElement.id"))
    page.evaluate("DGApp.close()")
    # stale forfeit dialog: 1v1 and tournament
    page.evaluate("DGApp.setSpeed(2)")
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'tournament', stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
    page.click('#ovForfeit'); page.wait_for_selector('#forfeitYes'); T(page, "t.solve()")
    page.wait_for_function("DGApp.current().tour.round === 1 || DGApp.current().phase==='result'", timeout=30000)
    page.wait_for_timeout(300)
    print('tour after QF: dialog open =', page.locator('[data-test=forfeit-confirm]').count(), 'phase', cur(page)['phase'], cur(page)['tour'])
    page.evaluate("DGApp.close()")
    # mm cancel at speed 1
    g0 = st(page)['gold']
    page.evaluate("DGApp.setSpeed(1)")
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:250})")
    ids = []
    for i in range(8):
        ids.append(page.evaluate("(() => { const b = document.getElementById('mmCancel'); if (!b) return null; b.__tag = b.__tag || Math.random(); return b.__tag; })()")); page.wait_for_timeout(100)
    print('mmCancel element identity over 0.8 s:', len(set(i for i in ids if i)), 'distinct nodes', ids[:3])
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:250})"); page.wait_for_timeout(200)
    try:
        page.click('#mmCancel', timeout=3000); print('mm cancel refund delta', st(page)['gold'] - g0, 'cur', cur(page))
    except Exception as e:
        print('mmCancel click failed', str(e)[:200]); shot(page, 'mmcancel-fail')
    print(errs(page))
