from qalib import *
from formats_util import home_start
AE = "(() => { const a = document.activeElement; return a ? (a.id || a.dataset.test || a.tagName) + (document.getElementById('ov').contains(a) ? ' [in ov]' : '') : null })()"
with new_page_ctx(1280, height=600) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    # queens arrows only
    page.evaluate("DGApp.startMatch({game:'queens', format:'1v1', stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]')
    page.wait_for_function("DGApp.ctx() && DGApp.ctx().test"); page.wait_for_timeout(300)
    out = []
    for k in ['ArrowDown'] * 7:
        page.keyboard.press(k); page.wait_for_timeout(60); out.append(page.evaluate("document.getElementById('ovScroll').scrollTop"))
    print('queens arrow-down scrollTop sequence', out, 'cursor', T(page, "t.state().idx"))
    shot(page, 'queens-arrow-scroll')
    page.evaluate("DGApp.close()")
    # launched from Home Duel-now: focus + Space during matchmaking and during play (2048 ignores Space)
    for src in ['tour', 'watch']:
        g0 = st(page)['gold']
        if src == 'home':
            home_start(page, 'tiles2048', '1v1', 100)
        elif src == 'tour':
            page.click('#tab-tournaments'); page.locator('#view-tournaments [data-join]').first.click()
        else:
            page.click('#tab-watch'); page.locator('#view-watch [data-watch-go]').first.click()
        page.wait_for_timeout(200)
        a1 = page.evaluate(AE)
        page.keyboard.press('Space'); page.keyboard.press('Enter'); page.wait_for_timeout(300)
        modals = page.evaluate("[...document.querySelectorAll('.modal')].map(m => m.dataset.test)")
        print(src, 'focus after launch', a1, 'modals after Space/Enter', modals, 'cur', cur(page) and cur(page)['phase'], 'gold', g0, '->', st(page)['gold'])
        page.evaluate("DGApp.close()"); page.wait_for_timeout(100)
        while page.locator('.modal-x').count(): page.locator('.modal-x').first.click()
    # Escape during a game: does it close anything / leave overlay?
    page.evaluate("DGApp.startMatch({game:'chess', format:'1v1', stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]')
    page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
    page.keyboard.press('Escape'); page.wait_for_timeout(200)
    print('Esc in chess -> phase', cur(page)['phase'])
    page.click('#ovForfeit'); page.wait_for_selector('#forfeitNo'); page.keyboard.press('Escape'); page.wait_for_timeout(100)
    print('Esc closes forfeit dialog', page.locator('[data-test=forfeit-confirm]').count() == 0, 'phase', cur(page)['phase'])
    # Tab focus: can Tab reach lobby controls behind overlay?
    behind = []
    for i in range(40):
        page.keyboard.press('Tab')
        r = page.evaluate("(() => { const a = document.activeElement; return [a.id || a.tagName, document.getElementById('ov').contains(a) || document.getElementById('modalRoot').contains(a)]; })()")
        if not r[1] and r[0] != 'BODY': behind.append(r[0])
    print('Tab reached behind overlay:', behind[:12], len(behind))
    print(errs(page))
