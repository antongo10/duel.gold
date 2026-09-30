from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'city','city duel')
    tap_start(page)
    st=page.evaluate("DGApp.ctx().test.state()"); n=st['n']; tiles=st['tiles']
    free=[i for i,t in enumerate(tiles) if t==0]
    tools=[b.get_attribute('data-tool') for b in page.query_selector_all('[data-tool]')]
    print('tools', tools, 'n', n)
    plan=[('power',free[0]),('water',free[1]),('res',free[2]),('res',free[3]),('res',free[4]),('shop',free[5]),('park',free[6])]
    for t,i in plan:
        if t not in tools: continue
        page.locator(f'[data-tool={t}]').tap(); page.wait_for_timeout(100)
        page.locator(f'[data-test=tile-{i}]').tap(); page.wait_for_timeout(120)
        m1=page.inner_text('[data-test=msg]')
        page.locator(f'[data-test=tile-{i}]').tap(); page.wait_for_timeout(120)
        print(t,i,'|',m1,'|',page.inner_text('[data-test=msg]'))
    shot(page,'hand-city-built-360'); shot(page,'hand-city-built-360-full', True)
    print('score', page.evaluate("DGApp.ctx().test.score()"), status(page))
    page.locator('[data-test=finish]').tap(); page.wait_for_timeout(500)
    shot(page,'hand-city-finish-360')
    wait_result(page, 30000); page.wait_for_timeout(300)
    shot(page,'hand-city-result-360')
    print(page.evaluate("DGApp.last()"), errs(page))
