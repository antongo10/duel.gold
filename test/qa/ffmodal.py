from qalib import *
with new_page_ctx(1280) as page:
    boot(page); page.evaluate("DGApp.setSpeed(2)")
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
    page.click('#ovForfeit'); page.wait_for_selector('#forfeitYes')
    T(page, "t.solve()"); wait_result(page, 20)
    page.wait_for_timeout(300)
    print('outcome', last(page)['outcome'], 'forfeit dialog still open over result:', page.locator('[data-test=forfeit-confirm]').count())
    shot(page, 'forfeit-dialog-over-result')
    page.click('#forfeitYes'); page.wait_for_timeout(200)
    print('after clicking Forfeit on stale dialog:', last(page)['outcome'], cur(page)['phase'], st(page)['gold'])
    # tournament: dialog open while round ends -> between phase: does stale Forfeit forfeit the NEXT round?
    page.click('[data-test=back]')
    g0 = st(page)['gold']
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'tournament', stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
    page.click('#ovForfeit'); page.wait_for_selector('#forfeitYes')
    T(page, "t.solve()")
    page.wait_for_function("DGApp.current().tour.round === 1 || DGApp.current().phase==='result'", timeout=30000)
    print('QF done, round', cur(page)['tour'], 'dialog open', page.locator('[data-test=forfeit-confirm]').count())
    shot(page, 'forfeit-dialog-tour-between')
    if page.locator('#forfeitYes').count():
        page.click('#forfeitYes'); page.wait_for_timeout(300)
        print('stale Forfeit clicked in round 2 ->', cur(page)['phase'], last(page))
    print(errs(page))
