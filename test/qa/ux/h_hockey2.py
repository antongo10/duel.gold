from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'hockey','air hockey')
    tap_start(page)
    cv = page.locator('#gameRoot canvas').first; box=cv.bounding_box()
    cdp = page.context.new_cdp_session(page)
    T=lambda t,x,y: cdp.send('Input.dispatchTouchEvent', {'type':t,'touchPoints':[] if t=='touchEnd' else [{'x':x,'y':y}]})
    print('pad0', page.evaluate("DGApp.ctx().test.state().pads[0]"), 'ta', page.evaluate("getComputedStyle(document.querySelector('#gameRoot canvas')).touchAction"))
    T('touchStart', box['x']+60, box['y']+box['height']-80)
    for k in range(10):
        T('touchMove', box['x']+60+k*15, box['y']+box['height']-80-k*5); page.wait_for_timeout(50)
    print('pad0 after', page.evaluate("DGApp.ctx().test.state().pads[0]"), page.evaluate("DGApp.ctx().test.physToClient(DGApp.ctx().test.state().pads[0].x,DGApp.ctx().test.state().pads[0].y)"))
    T('touchEnd',0,0)
    # measure how fast AI scores when human idle: wait 20s
    page.wait_for_timeout(20000)
    print('idle 20s score', page.evaluate("DGApp.ctx() && DGApp.ctx().test.state().score"), page.evaluate("DGApp.current().opps[0]"))
