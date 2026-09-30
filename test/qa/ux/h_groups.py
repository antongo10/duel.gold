from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'groups','word groups')
    tap_start(page)
    sol = page.evaluate("DGApp.ctx().test.solution()")
    def pick(words):
        d=page.locator('[data-test=wg-clear]')
        if d.is_enabled(): d.tap(); page.wait_for_timeout(60)
        for w in words:
            page.locator('[data-test=wg-grid] button', has_text=w).first.tap(); page.wait_for_timeout(60)
        page.tap('[data-test=wg-submit]'); page.wait_for_timeout(900)
    pick(sol[0]['words'][:3]+[sol[1]['words'][0]])
    for i,g in enumerate(sol):
        pick(g['words'])
        if i==1: shot(page,'hand-groups-mid-360')
    wait_result(page, 30000); page.wait_for_timeout(300)
    shot(page,'hand-groups-result-360')
    print('groups', page.evaluate("DGApp.last()"), errs(page))
