from hand import *
import time
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'city','city duel')
    tap_start(page)
    st=page.evaluate("DGApp.ctx().test.state()"); tiles=st['tiles']
    free=[i for i,t in enumerate(tiles) if t==0]
    for t,i in [('power',free[0]),('water',free[1]),('res',free[2]),('res',free[3]),('res',free[4]),('com',free[5]),('park',free[6])]:
        page.locator(f'[data-tool={t}]').tap(); page.locator(f'[data-test=tile-{i}]').tap(); page.wait_for_timeout(80)
        if 'Tap again' in page.inner_text('[data-test=msg]'): page.locator(f'[data-test=tile-{i}]').tap()
    proj = page.evaluate("DGApp.ctx().test.score()")
    t0=time.time(); page.locator('[data-test=finish]').tap()
    samples=[]
    while time.time()-t0<40:
        ph=page.evaluate("DGApp.current().phase")
        samples.append((round(time.time()-t0,1), status(page), ph))
        if ph=='result': break
        page.wait_for_timeout(1000)
    print('projected', proj); print(samples)
    shot(page,'hand-city-result2-360'); shot(page,'hand-city-result2-360-full', True)
    print(page.evaluate("DGApp.last()"), page.evaluate("DGApp.state().history[0]"))
