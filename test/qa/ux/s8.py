from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.tap('#wCashPill'); page.wait_for_timeout(500)
    shot(page,'cash-anchor-360')
    print('cash top', page.evaluate("document.querySelector('#cash').getBoundingClientRect().top"), 'header h', page.evaluate("document.querySelector('#top').getBoundingClientRect().height"))
    for v in ['home','settings','profile']:
        page.evaluate(f"DGApp.go('{v}')"); page.evaluate("window.scrollTo(0,1e6)"); page.wait_for_timeout(200)
        print(v,'footer bottom', page.evaluate("document.querySelector('.foot').getBoundingClientRect().bottom"), 'nav top', page.evaluate("document.querySelector('#bottomNav').getBoundingClientRect().top"))
    page.evaluate("DGApp.go('home')"); page.evaluate("window.scrollTo(0,0)")
    print('find btn top', page.evaluate("document.querySelector('#dnFind').getBoundingClientRect().top"))
    # memory game real duration check (clock only in input?)
    import re
    page.evaluate("DGApp.startMatch({game:'memory',format:'1v1',stake:0})"); page.wait_for_selector('[data-test=start]'); page.click('[data-test=start]')
    s=[]
    for i in range(6):
        page.wait_for_timeout(2000); s.append(page.evaluate("document.querySelector('#ovStatus').textContent"))
    print('memory status over 12s', s)
