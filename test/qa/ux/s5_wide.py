import sys
from common import *
GAMES = ["chess","four","reversi","gomoku","sudoku","mines","queens","tiles2048","memory","reaction","aim","rush","darts","hockey","base","city","restaurant","trivia","groups","durak","liars","auction"]
key=sys.argv[1]; w,h,t=SIZES[key]
with browser_page(w,h,t) as page:
    boot(page)
    for g in GAMES:
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'1v1',stake:100}})")
        page.wait_for_selector('[data-test=start]', timeout=8000); page.wait_for_timeout(150)
        shot(page, f'g-{g}-rules-{key}')
        page.click('[data-test=start]'); page.wait_for_timeout(2200)
        shot(page, f'g-{g}-play-{key}')
        info = page.evaluate("""()=>{const gr=document.querySelector('#gameRoot').getBoundingClientRect();const s=document.querySelector('#ovScroll');return {rootW:Math.round(gr.width),rootH:Math.round(gr.height),scrollH:s.scrollHeight,clientH:s.clientHeight,docW:document.documentElement.scrollWidth}}""")
        print(g, info)
        page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(250)
        if g in ('sudoku','durak'): shot(page, f'g-{g}-result-{key}')
        page.evaluate("DGApp.close()"); page.wait_for_timeout(150)
    print(errs(page))
