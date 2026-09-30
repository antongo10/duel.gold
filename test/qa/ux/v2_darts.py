from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'darts','darts')
    page.wait_for_selector('[data-test=start]:not([disabled])'); tap_start(page)
    cv = page.locator('[data-test=canvas]'); box=cv.bounding_box(); print(box)
    cx, cy = box['x']+box['width']/2, box['y']+box['height']/2
    cdp = page.context.new_cdp_session(page)
    T=lambda t,x,y: cdp.send('Input.dispatchTouchEvent', {'type':t,'touchPoints':[] if t=='touchEnd' else [{'x':x,'y':y}]})
    # board radius 225 logical => DB.VIEW; T20 treble at ~ 103mm of 170 radius ; compute from test hook
    res=[]
    for d in range(9):
        page.wait_for_function("(()=>{const c=DGApp.ctx();return !c || c.test.state().phase==='aim'})()", timeout=15000)
        if page.evaluate("!DGApp.ctx()"): break
        tgt = page.evaluate("DGApp.ctx().test.boardToClient(0,103)")  # T20 in mm
        if d>=6: tgt = page.evaluate("DGApp.ctx().test.boardToClient(0,0)")
        fx, fy = tgt['x'], tgt['y']+48
        T('touchStart',fx,fy); page.wait_for_timeout(500)
        if d==0: shot(page,'v2-darts-hold-360')
        T('touchEnd',fx,fy); page.wait_for_timeout(900)
        s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
        if s: res.append(s['thrown'][-1]['label'])
    print('labels (6x T20 aim, 3x bull aim):', res)
    wait_result(page, 30000); page.wait_for_timeout(300); shot(page,'v2-darts-result-360')
