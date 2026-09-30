from hand import *
import time, math
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'hockey','air hockey')
    shot(page,'hand-hockey-rules-360')
    tap_start(page)
    cv = page.locator('#gameRoot canvas').first
    box = cv.bounding_box(); print('canvas', box, 'viewport h 780')
    cdp = page.context.new_cdp_session(page)
    def T(type_, x, y):
        cdp.send('Input.dispatchTouchEvent', {'type':type_, 'touchPoints':[] if type_=='touchEnd' else [{'x':x,'y':y}]})
    # track the puck with finger for ~25s
    t0=time.time(); started=False
    while time.time()-t0<25:
        s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
        if not s or s['over']: break
        p=s['puck']
        c=page.evaluate(f"DGApp.ctx().test.physToClient({p['x']},{p['y']})")
        x=c['x']; y=max(c['y']+15, box['y']+box['height']*0.55)
        y=min(y, box['y']+box['height']-10)
        T('touchMove' if started else 'touchStart', x, y); started=True
        page.wait_for_timeout(40)
    T('touchEnd',0,0)
    shot(page,'hand-hockey-mid-360')
    s=page.evaluate("DGApp.ctx() && DGApp.ctx().test.state()")
    print('state', s and {k:s[k] for k in ['score','clock','phase']}, status(page))
    print('page scrollY', page.evaluate("[window.scrollY, document.querySelector('#ovScroll').scrollTop]"))
    page.evaluate("DGApp.ctx().test.setClock(1)")
    wait_result(page, 40000); page.wait_for_timeout(300)
    shot(page,'hand-hockey-result-360')
    print(page.evaluate("DGApp.last()"), errs(page))
