from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.go('tournaments')"); page.wait_for_timeout(200)
    for t in ['daily','weekend','high','world']:
        print(t, '|', page.inner_text(f'[data-tour={t}] .dg-note'))
    txt = page.evaluate("document.body.innerText")
    import re
    for term in ['Duel points','DP','Favorites','Favourites','favourites','Cups','colour','color']:
        print(term, len(re.findall(r'\b'+term+r'\b', txt)))
    page.evaluate("DGApp.go('profile')"); page.wait_for_timeout(200)
    t2=page.evaluate("document.body.innerText")
    print('profile DP count', len(re.findall(r'\bDP\b', t2)), 'Duel points', len(re.findall(r'Duel points', t2)))
    print('locked ach opacity/colors', page.evaluate("(()=>{const li=document.querySelector('.ach li:not(.got)');const b=li.querySelector('b');const n=li.querySelector('.dg-note');return [getComputedStyle(li).opacity,getComputedStyle(b).color,getComputedStyle(n).color]})()"))
    print('demo tag', page.inner_text('#demoTag'), page.evaluate("document.querySelector('#demoTag').getAttribute('title')"))
