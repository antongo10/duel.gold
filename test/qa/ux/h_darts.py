from hand import *
import time
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'darts','darts')
    tap_start(page)
    cv = page.locator('[data-test=stage] canvas, .g-darts canvas, canvas').first
    box = cv.bounding_box(); print('canvas', box)
    cx, cy = box['x']+box['width']/2, box['y']+box['height']/2
    cdp = page.context.new_cdp_session(page)
    def touch(type_, x, y):
        pts = [] if type_=='touchEnd' else [{'x':x,'y':y}]
        cdp.send('Input.dispatchTouchEvent', {'type':type_, 'touchPoints':pts})
    totals=[]
    for d in range(9):
        page.wait_for_function("(()=>{const c=DGApp.ctx();return !c || c.test.state().phase==='aim'})()", timeout=15000)
        if page.evaluate("!DGApp.ctx()"): break
        # aim at T20 : 20 is up. treble ring ~ 0.6 radius
        tx, ty = cx, cy - box['width']*0.27
        touch('touchStart', tx, ty); page.wait_for_timeout(700); touch('touchEnd', tx, ty)
        page.wait_for_timeout(900)
        s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
        if s: totals.append((s['dart'], s['total'], s['thrown'][-1] if s['thrown'] else None))
        if d==2: shot(page,'hand-darts-visit-360')
    for t in totals: print(t)
    wait_result(page, 30000); page.wait_for_timeout(300)
    shot(page,'hand-darts-result-360'); shot(page,'hand-darts-result-360-full', True)
    print(page.evaluate("DGApp.last()"), errs(page))
