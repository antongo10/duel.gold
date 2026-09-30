from hand import *
import time
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'hockey','air hockey')
    page.wait_for_selector('[data-test=start]:not([disabled])'); tap_start(page)
    cv = page.locator('#gameRoot canvas').first; box=cv.bounding_box(); print('canvas', box)
    cdp = page.context.new_cdp_session(page)
    T=lambda t,x,y: cdp.send('Input.dispatchTouchEvent', {'type':t,'touchPoints':[] if t=='touchEnd' else [{'x':x,'y':y}]})
    fx, fy = box['x']+box['width']/2, box['y']+box['height']-60
    T('touchStart',fx,fy); page.wait_for_timeout(300)
    pad = page.evaluate("(()=>{const s=DGApp.ctx().test.state();return DGApp.ctx().test.physToClient(s.pads[0].x,s.pads[0].y)})()")
    print('finger', (round(fx),round(fy)), 'paddle', pad)
    shot(page,'v2-hockey-finger-360')
    # track puck: finger 48 below puck-ish
    t0=time.time(); started=True
    while time.time()-t0<30:
        s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
        if not s or s['over']: break
        p=s['puck']; c=page.evaluate(f"DGApp.ctx().test.physToClient({p['x']},{p['y']})")
        x=c['x']; y=min(max(c['y']+60, box['y']+box['height']*0.55), box['y']+box['height']-5)
        T('touchMove', x, y); page.wait_for_timeout(35)
    T('touchEnd',0,0)
    s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
    print('after 30s', s and s['score'], s and round(s['clock'],1), page.evaluate("DGApp.current().opps[0].skill"))
    print('page scroll', page.evaluate("[window.scrollY, document.querySelector('#ovScroll').scrollTop]"))
    shot(page,'v2-hockey-mid-360')
