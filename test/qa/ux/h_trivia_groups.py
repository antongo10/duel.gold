from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'trivia','trivia')
    tap_start(page)
    for q in range(10):
        page.wait_for_function("(()=>{const s=DGApp.ctx()&&DGApp.ctx().test.state();return !s||s.phase==='ask'})()", timeout=20000)
        if page.query_selector('[data-test=result]'): break
        s=page.evaluate("DGApp.ctx().test.state()")
        pick = s['ans'] if q%3 else (s['ans']+1)%4
        page.tap(f'.g-trivia-opt[data-i="{pick}"]'); page.wait_for_timeout(250)
        if q==0: shot(page,'hand-trivia-wrong-360')
        if q==1: shot(page,'hand-trivia-right-360')
    wait_result(page, 30000); page.wait_for_timeout(300)
    shot(page,'hand-trivia-result-360'); shot(page,'hand-trivia-result-360-full', True)
    print('trivia', page.evaluate("DGApp.last()"))
    back(page)
    start_via_ui(page,'groups','word groups')
    tap_start(page)
    sol = page.evaluate("DGApp.ctx().test.solution()")
    print([g['name'] for g in sol])
    # one wrong guess: take 3 from group0 and 1 from group1
    wrong = sol[0]['words'][:3]+[sol[1]['words'][0]]
    def pick(words):
        for w in words:
            el = page.locator('[data-test=wg-grid] button', has_text=w).first
            el.tap(); page.wait_for_timeout(60)
        page.tap('text=Submit'); page.wait_for_timeout(700)
    pick(wrong); shot(page,'hand-groups-wrong-360')
    print('msg', page.inner_text('[data-test=wg-msg]'))
    for g in sol: pick(g['words'])
    shot(page,'hand-groups-after-360')
    wait_result(page, 30000); page.wait_for_timeout(300)
    shot(page,'hand-groups-result-360')
    print('groups', page.evaluate("DGApp.last()"))
