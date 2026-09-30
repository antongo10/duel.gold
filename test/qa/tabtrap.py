from qalib import *
with new_page_ctx(1280, height=700) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    page.click('#settingsBtn'); page.wait_for_selector('#resetBtn')
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:500})")
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
    g0 = st(page)['gold']
    n = 0
    while page.evaluate("document.activeElement.id") != 'resetBtn' and n < 200:
        page.keyboard.press('Tab'); n += 1
    print('tabs to reach Reset behind overlay:', n, page.evaluate("document.activeElement.id"))
    page.keyboard.press('Enter'); page.wait_for_selector('#confirmYes'); shot(page, 'tab-reset-behind-overlay')
    page.click('#confirmYes'); page.wait_for_timeout(300)
    print('after reset: gold', st(page)['gold'], 'age gate shown', page.locator('[data-test=age-gate]').count(), 'match phase', cur(page) and cur(page)['phase'])
    if page.locator('#ageAdult').count(): page.click('#ageAdult')
    T(page, "t.solve()"); wait_result(page, 30)
    s = st(page); print('after finishing the match: gold', s['gold'], 'last', last(page), 'history', len(s['history']))
    print(errs(page))
