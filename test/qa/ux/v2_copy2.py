from common import *
import re
with browser_page(360,780,True) as page:
    boot(page)
    for v in ['home','games','profile','settings','social']:
        page.evaluate(f"DGApp.go('{v}')"); page.wait_for_timeout(200)
        txt = page.evaluate("document.querySelector('#app').textContent")
        c={term: len(re.findall(term, txt)) for term in ['Duel points','DUEL POINTS',' DP','Favorites','Favourites','favourites','Cups','colour','color ']}
        print(v, c)
    print('demo tag visible text 360:', page.evaluate("document.querySelector('#demoTag').textContent"))
