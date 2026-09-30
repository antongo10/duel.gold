import sys
from common import *
key=sys.argv[1]; w,h,t=SIZES[key]
with browser_page(w,h,t) as page:
    boot(page)
    page.wait_for_timeout(300)
    shot(page,f'v2-home-{key}')
    print('find top', page.evaluate("(()=>{const r=document.querySelector('#dnFind').getBoundingClientRect();return [Math.round(r.top),Math.round(r.bottom)]})()"), 'vh', h)
    print('hscroll', hscroll(page))
    page.evaluate("window.scrollTo(0,1200)"); page.wait_for_timeout(300)
    shot(page,f'v2-home-scrolled-{key}')
    print('header top after scroll', page.evaluate("document.querySelector('#top').getBoundingClientRect().top"))
    for v in ['games','profile','tournaments','settings','social','watch']:
        page.evaluate(f"DGApp.go('{v}')"); page.wait_for_timeout(300)
        shot(page,f'v2-{v}-{key}'); shot(page,f'v2-{v}-{key}-full',True)
        print(v,'hscroll',hscroll(page))
        if key=='360':
            print('  past-vp', [o for o in overflowing(page,'#main') if o[0]=='past-vp'][:5])
            print('  small', small_targets(page,'#main')[:8])
    page.evaluate("DGApp.go('home')"); page.evaluate("window.scrollTo(0,0)")
    print('small home', small_targets(page,'#app')[:10])
    print(errs(page))
