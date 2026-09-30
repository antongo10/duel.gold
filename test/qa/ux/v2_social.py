from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    for g in ['durak','liars','auction']:
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'1v1',stake:100}})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(2500)
        shot(page,f'v2-{g}-play-360')
        if g=='liars':
            txt=page.inner_text('#gameRoot'); import re
            print('liars dies?', bool(re.search(r'\bdies\b',txt)), '|', [l for l in txt.split('\n') if 'bid' in l.lower()][:3])
        if g=='auction':
            print('slider', page.evaluate("(()=>{const r=document.querySelector('.g-auction-range');const b=r.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height), getComputedStyle(r).height]})()"))
        page.evaluate("DGApp.ctx().test.autoplay()")
        wait_result(page, 240000); page.wait_for_timeout(300)
        shot(page,f'v2-{g}-result-360')
        print(g, page.evaluate("DGApp.last().outcome"), page.inner_text('[data-test=result] .scoreline').replace('\n',' '))
        page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    # brain/strategy minors
    for g in ['sudoku','mines','gomoku','queens','chess']:
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'1v1',stake:0}})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(1500)
        shot(page,f'v2-{g}-play-360')
        print(g, 'small', small_targets(page,'#gameRoot',36)[:2], 'n', len(small_targets(page,'#gameRoot',36)))
        if g=='sudoku': print('  key hint visible', page.evaluate("[...document.querySelectorAll('#gameRoot *')].some(e=>e.offsetParent && /Keys: 1/.test(e.textContent) && e.children.length==0)"))
        page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
