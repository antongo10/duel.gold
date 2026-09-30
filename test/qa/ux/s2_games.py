import sys
from common import *
GAMES = ["chess","four","reversi","gomoku","sudoku","mines","queens","tiles2048","memory","reaction","aim","rush","darts","hockey","base","city","restaurant","trivia","groups","durak","liars","auction"]
only = sys.argv[2:] if len(sys.argv)>2 else GAMES
key = sys.argv[1] if len(sys.argv)>1 else '360'
w,h,t = SIZES[key]

FINISH = {
 'sudoku': "c=DGApp.ctx(); c.test.solve()",
 'mines': "c=DGApp.ctx(); c.test.solve()",
 'queens': "c=DGApp.ctx(); c.test.solve()",
 'tiles2048': "c=DGApp.ctx(); c.test.solve()",
 'reaction': "c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.fire(250)}catch(e){}},150)",
 'aim': None,
 'rush': "c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},200)",
 'darts': "c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.throwAt(0,0)}catch(e){}},300)",
 'memory': "c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.solve()}catch(e){}},200)",
 'trivia': "c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},300)", 'groups': "c=DGApp.ctx(); for(let i=0;i<4;i++) c.test.submitGroup(i)",
 'base': "c=DGApp.ctx(); c.test.placeAI(0.9); c.test.fastForward()",
 'city': "c=DGApp.ctx(); c.test.autoBuild(0.9); c.test.finish(true)",
 'restaurant': "c=DGApp.ctx(); c.test.optimise(0.9); c.test.finish(true)",
 'chess': "c=DGApp.ctx(); c.test.autoplay(0.9)", 'four': "c=DGApp.ctx(); c.test.autoplay(0.9)",
 'reversi': "c=DGApp.ctx(); c.test.autoplay(0.9)", 'gomoku': "c=DGApp.ctx(); c.test.autoplay(0.9)",
 'durak': "c=DGApp.ctx(); c.test.autoplay()", 'liars': "c=DGApp.ctx(); c.test.autoplay()", 'auction': "c=DGApp.ctx(); c.test.autoplay()",
 'hockey': "c=DGApp.ctx(); c.test.autoplay(0.9)",
}
with browser_page(w,h,t) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(float(0)||1)".replace('float(0)','0'))
    for g in only:
        page._console.clear()
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'1v1',stake:100}})")
        page.wait_for_timeout(300)
        if g == only[0]: shot(page, f'mm-{key}')
        page.wait_for_selector('[data-test=start]', timeout=8000)
        page.wait_for_timeout(200)
        shot(page, f'g-{g}-rules-{key}')
        shot(page, f'g-{g}-rules-{key}-full', full=True)
        page.click('[data-test=start]')
        page.wait_for_timeout(2500)
        shot(page, f'g-{g}-play-{key}')
        info = page.evaluate("""()=>{const s=document.querySelector('#ovScroll');const gr=document.querySelector('#gameRoot');const r=gr.getBoundingClientRect();return {scrollH:s.scrollHeight, clientH:s.clientHeight, rootW:Math.round(r.width), rootH:Math.round(r.height), docW:document.documentElement.scrollWidth, ovW: document.querySelector('#ov').scrollWidth, ovStageW: document.querySelector('#ovStage').scrollWidth}}""")
        print(g, 'layout', info)
        if key=='360':
            st = small_targets(page, '#ov', 36)
            print('  small targets', st[:12])
        # finish
        js = FINISH.get(g)
        try:
            if js: page.evaluate(js)
        except Exception as e: print('  finish err', e)
        # for timed games, speed up by waiting
        try:
            page.wait_for_selector('[data-test=result], [data-test=error]', timeout=200000)
        except Exception as e:
            print('  TIMEOUT waiting result; status=', page.evaluate("document.querySelector('#ovStatus').textContent"))
            shot(page, f'g-{g}-stuck-{key}')
            page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(300)
        page.wait_for_timeout(400)
        shot(page, f'g-{g}-result-{key}')
        shot(page, f'g-{g}-result-{key}-full', full=True)
        last = page.evaluate("DGApp.last()")
        gold = page.evaluate("DGApp.state().gold")
        print('  last', last, 'gold', gold)
        print('  errors', errs(page))
        page.evaluate("clearInterval(window.__iv)")
        page.evaluate("DGApp.close()")
        page.wait_for_timeout(200)
