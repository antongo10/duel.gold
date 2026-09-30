from common import *
for key,(w,h,t) in SIZES.items():
    with browser_page(w,h,t) as page:
        open_app(page, APP)
        page.wait_for_function("window.DG && DG.__appReady", timeout=15000)
        page.wait_for_timeout(300)
        shot(page, f'agegate-{key}')
        page.click('#ageAdult')
        page.wait_for_timeout(200)
        for v in ['home','games','watch','tournaments','social','profile','settings','fair']:
            page.evaluate(f"DGApp.go('{v}')"); page.wait_for_timeout(250)
            shot(page, f'{v}-{key}')
            shot(page, f'{v}-{key}-full', full=True)
            print(key, v, 'hscroll', hscroll(page))
            if key=='360':
                st = small_targets(page, '#app')
                print('  small', st[:25])
                print('  overflow', overflowing(page, '#main')[:15])
        print('errors', errs(page))
