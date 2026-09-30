from hand import *
import re
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'base','base duel')
    shot(page,'hand-base-rules-360-full', True)
    tap_start(page)
    st = page.evaluate("DGApp.ctx().test.state()")
    cv = page.locator('[data-test=map] canvas')
    box = cv.bounding_box(); print('canvas', box)
    BW,BH = page.evaluate("(()=>{return [12,9]})()")
    # figure grid dims from aspect
    def tapTile(x,y,bw,bh):
        page.touchscreen.tap(box['x']+(x+0.5)*box['width']/bw, box['y']+(y+0.5)*box['height']/bh)
        page.wait_for_timeout(120)
    # find BW/BH from source constants
    print(page.evaluate("DGApp.ctx().test.state().structs"))
    # scroll palette into view and pick Arrow
    page.locator('[data-test=tool-arrow]').tap(); 
    box = cv.bounding_box()
    # tap a few tiles near base (right side). try grid 12x9
    for (x,y) in [(9,4),(10,6),(7,3)]:
        for bw,bh in [(12,9)]:
            tapTile(x,y,bw,bh); msg1=page.inner_text('[data-test=msg]'); tapTile(x,y,bw,bh); msg2=page.inner_text('[data-test=msg]')
            print((x,y), msg1,'|',msg2)
    shot(page,'hand-base-built-360')
    print(page.evaluate("DGApp.ctx().test.state().structs"))
    page.locator('[data-test=go]').tap(); page.wait_for_timeout(2500)
    # firebomb
    page.locator('[data-test=tool-bomb]').tap()
    en = page.evaluate("DGApp.ctx().test.state().enemies")
    print('enemies', en[:3])
    box = cv.bounding_box()
    if en:
        e=en[0]; page.touchscreen.tap(box['x']+e['x']*box['width']/12, box['y']+e['y']*box['height']/9)
    page.wait_for_timeout(300)
    print('bomb msg', page.inner_text('[data-test=msg]'), page.evaluate("DGApp.ctx().test.state().bombs"))
    shot(page,'hand-base-wave-360')
    page.evaluate("window.scrollTo(0,0)")
    print('scroll pos', page.evaluate("document.querySelector('#ovScroll').scrollTop"))
    # let wave play out at speed: wait until window
    page.wait_for_timeout(20000)
    shot(page,'hand-base-later-360')
    print(status(page), page.evaluate("DGApp.ctx() && DGApp.ctx().test.state().phase"))
    print(errs(page))
