from common import *
with browser_page(1440,900,False) as page:
    boot(page)
    for g in ['base','restaurant','four']:
        f = 'tournament' if g=='four' else '1v1'
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'{f}',stake:100}})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.wait_for_timeout(200)
        if g=='four': shot(page,'v2-tour-qf-1440'); print('ov w', page.evaluate("document.querySelector('#ov').scrollWidth"))
        page.click('[data-test=start]'); page.wait_for_timeout(1500)
        shot(page,f'v2-{g}-play-1440')
        page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(300)
        shot(page,f'v2-{g}-result-1440')
        page.evaluate("DGApp.close()")
    print(errs(page))
