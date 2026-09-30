from qalib import *
with new_page_ctx(360, touch=True) as page:
    boot(page); page.evaluate("DGApp.setSpeed(3)")
    for i in range(3):
        page.evaluate("DGApp.startMatch({game:'durak', format:'1v1', stake:100})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.tap('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
        T(page, "t.autoplay()")
        for j in range(30):
            page.wait_for_timeout(100)
            c = cur(page)
            vis = page.evaluate("(() => { const b = document.getElementById('ovForfeit'); const r = b.getBoundingClientRect(); return [b.hidden, getComputedStyle(b).display, r.width, r.height, r.top]; })()")
            if j % 5 == 0 or c['phase'] != 'play': print(i, j, c['phase'], vis)
            if c['phase'] != 'play': break
        shot(page, f'durak360-{i}')
        print('last', last(page))
        page.evaluate("DGApp.close()")
