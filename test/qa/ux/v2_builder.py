from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    # Base
    start_via_ui(page,'base','base duel'); page.wait_for_selector('[data-test=start]:not([disabled])'); tap_start(page)
    shot(page,'v2-base-build-360'); shot(page,'v2-base-build-360-full',True)
    print('base score pre-wave', page.evaluate("DGApp.ctx().test.state().score"), page.inner_text('[data-test=score]') if page.query_selector('[data-test=score]') else '')
    cv = page.locator('[data-test=map] canvas'); 
    page.locator('[data-test=tool-arrow]').tap()
    box=cv.bounding_box()
    for (x,y) in [(9,4),(10,6)]:
        for _ in range(2): page.touchscreen.tap(box['x']+(x+0.5)*box['width']/12, box['y']+(y+0.5)*box['height']/9); page.wait_for_timeout(120)
    page.locator('[data-test=go]').tap(); page.wait_for_timeout(2500)
    shot(page,'v2-base-wave-360')
    vis = page.evaluate("""(()=>{const vh=innerHeight;const m=document.querySelector('[data-test=map] canvas').getBoundingClientRect();const b=document.querySelector('[data-test=tool-bomb]').getBoundingClientRect();return {map:[Math.round(m.top),Math.round(m.bottom)],bomb:[Math.round(b.top),Math.round(b.bottom)],vh}})()""")
    print('wave layout', vis)
    page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    # Restaurant
    start_via_ui(page,'restaurant','restaurant'); page.wait_for_selector('[data-test=start]:not([disabled])'); tap_start(page)
    shot(page,'v2-rest-plan-360'); shot(page,'v2-rest-plan-360-full',True)
    print('rest root h', page.evaluate("document.querySelector('#gameRoot').getBoundingClientRect().height"))
    page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    # City
    start_via_ui(page,'city','city duel'); page.wait_for_selector('[data-test=start]:not([disabled])'); tap_start(page)
    st=page.evaluate("DGApp.ctx().test.state()"); free=[i for i,t in enumerate(st['tiles']) if t==0]
    msgs=[]
    for t,i in [('power',free[0]),('water',free[1]),('res',free[2]),('res',free[3]),('res',free[4]),('com',free[5]),('park',free[6])]:
        page.locator(f'[data-tool={t}]').tap(); page.locator(f'[data-test=tile-{i}]').tap(); page.wait_for_timeout(80)
        m=page.inner_text('[data-test=msg]'); msgs.append(m[:40])
        if 'again' in m.lower(): page.locator(f'[data-test=tile-{i}]').tap(); page.wait_for_timeout(80)
    print('city msgs', msgs)
    hud = page.evaluate("DGApp.ctx().test.score()"); hudpop = page.evaluate("DGApp.ctx().test.state().eval")
    print('hud score', hud, {k:hudpop.get(k) for k in ['pop','population','happy','score10'] if k in hudpop})
    page.locator('[data-test=finish]').tap()
    wait_result(page, 40000); page.wait_for_timeout(300)
    shot(page,'v2-city-result-360'); shot(page,'v2-city-result-360-full',True)
    print('city history', page.evaluate("DGApp.state().history[0].s"))
