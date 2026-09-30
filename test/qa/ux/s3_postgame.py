from common import *
import time
with browser_page(360,780,True) as page:
    boot(page)
    for g,js in [('city',"c=DGApp.ctx(); c.test.autoBuild(0.9); c.test.finish(true)"),('base',"c=DGApp.ctx(); c.test.placeAI(0.9); c.test.fastForward()"),('restaurant',"c=DGApp.ctx(); c.test.optimise(0.9); c.test.finish(true)")]:
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'1v1',stake:100}})")
        page.wait_for_selector('[data-test=start]'); page.click('[data-test=start]'); page.wait_for_timeout(800)
        page.evaluate(js)
        t0=time.time()
        # observe phase until result
        vis=None
        while time.time()-t0<60:
            ph = page.evaluate("DGApp.current() && DGApp.current().phase")
            ff = page.evaluate("!document.querySelector('#ovForfeit').hidden")
            if ph=='result': break
            vis=ff
            page.wait_for_timeout(250)
        print(g,'time to platform result',round(time.time()-t0,1),'forfeit visible during game-final', vis)
        page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    # now test forfeiting during city final display
    page.evaluate("DGApp.startMatch({game:'city',format:'1v1',stake:100})")
    page.wait_for_selector('[data-test=start]'); page.click('[data-test=start]'); page.wait_for_timeout(800)
    page.evaluate("c=DGApp.ctx(); c.test.autoBuild(0.9); c.test.finish(false)")
    page.wait_for_timeout(1500)
    shot(page,'city-finalanim-360')
    print('phase', page.evaluate("DGApp.current().phase"))
