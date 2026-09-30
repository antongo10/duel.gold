import sys
from common import *
key=sys.argv[1] if len(sys.argv)>1 else '360'
w,h,t=SIZES[key]
with browser_page(w,h,t) as page:
    boot(page)
    # Duel setup sheet from Games
    page.evaluate("DGApp.go('games')"); page.wait_for_timeout(200)
    page.click('[data-duel="sudoku"]'); page.wait_for_timeout(300)
    shot(page,f'sheet-{key}'); shot(page,f'sheet-{key}-full',True)
    page.click('#shS-custom'); page.fill('#shCustom','5'); page.wait_for_timeout(200); shot(page,f'sheet-custom-err-{key}')
    print('custom 5 note', page.inner_text('#shNote'))
    page.fill('#shCustom','99999'); print('custom big', page.inner_text('#shNote'))
    page.keyboard.press('Escape'); page.wait_for_timeout(200)
    print('sheet closed by esc', not page.query_selector('[data-test=duel-sheet]'))
    # rules panel
    page.click('[data-rules="durak"]'); page.wait_for_timeout(200); shot(page,f'howto-durak-{key}')
    page.keyboard.press('Escape')
    # 2v2 race
    page.evaluate("DGApp.startMatch({game:'rush',format:'2v2',stake:100})")
    page.wait_for_selector('[data-test=start]'); shot(page,f'vs-2v2-{key}'); shot(page,f'vs-2v2-{key}-full',True)
    page.click('[data-test=start]'); page.wait_for_timeout(3000); shot(page,f'play-2v2-{key}')
    page.evaluate("c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},250)")
    page.wait_for_function("DGApp.current().phase==='result'", timeout=90000); page.evaluate("clearInterval(window.__iv)")
    page.wait_for_timeout(300); shot(page,f'res-2v2-{key}'); shot(page,f'res-2v2-{key}-full',True)
    print('2v2', page.evaluate("DGApp.last()"))
    page.evaluate("DGApp.close()")
    # FFA
    page.evaluate("DGApp.startMatch({game:'reaction',format:'ffa',stake:100})")
    page.wait_for_selector('[data-test=start]'); shot(page,f'vs-ffa-{key}')
    page.click('[data-test=start]'); page.wait_for_timeout(1500); shot(page,f'play-ffa-{key}')
    page.evaluate("c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.fire(300)}catch(e){}},150)")
    page.wait_for_function("DGApp.current().phase==='result'", timeout=90000); page.evaluate("clearInterval(window.__iv)")
    page.wait_for_timeout(300); shot(page,f'res-ffa-{key}'); shot(page,f'res-ffa-{key}-full',True)
    print('ffa', page.evaluate("DGApp.last()"))
    page.evaluate("DGApp.close()")
    # Tournament: versus game four
    page.evaluate("DGApp.startMatch({game:'rush',format:'tournament',stake:100})")
    page.wait_for_selector('[data-test=start]'); shot(page,f'tour-qf-{key}'); shot(page,f'tour-qf-{key}-full',True)
    for rnd in range(3):
        if page.evaluate("DGApp.current().phase")=='result': break
        page.wait_for_selector('[data-test=start]')
        page.click('[data-test=start]'); page.wait_for_timeout(500)
        page.evaluate("c=DGApp.ctx(); window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},200)")
        page.wait_for_function("['between','result','ready'].includes(DGApp.current().phase)", timeout=90000); page.evaluate("clearInterval(window.__iv)")
        page.wait_for_timeout(400)
        shot(page,f'tour-after-r{rnd}-{key}'); shot(page,f'tour-after-r{rnd}-{key}-full',True)
    page.wait_for_function("DGApp.current().phase==='result'", timeout=5000)
    shot(page,f'tour-final-{key}-full',True)
    print('tour', page.evaluate("DGApp.last()"))
    page.evaluate("DGApp.close()")
    # Mix
    page.evaluate("DGApp.startMatch({game:'any',format:'mix',stake:100})")
    page.wait_for_selector('[data-test=start]'); shot(page,f'mix-r1-{key}'); shot(page,f'mix-r1-{key}-full',True)
    games = page.evaluate("DGApp.current().games"); print('mix games', games)
    for r in range(3):
        page.wait_for_selector('[data-test=start]'); page.click('[data-test=start]'); page.wait_for_timeout(800)
        if r==0: shot(page,f'mix-play-{key}')
        page.evaluate("DGApp.forfeit()") if False else None
        # generic finisher: speed timers
        gid=games[r]
        js={'sudoku':"c.test.solve()",'mines':"c.test.solve()",'queens':"c.test.solve()",'tiles2048':"c.test.solve()",'groups':"for(let i=0;i<4;i++)c.test.submitGroup(i)",
            'city':"c.test.autoBuild(0.9);c.test.finish(true)",'base':"c.test.placeAI(0.9);c.test.fastForward()",'restaurant':"c.test.optimise(0.9);c.test.finish(true)",
            'reaction':"window.__iv=setInterval(()=>{try{c.test.fire(250)}catch(e){}},150)",'rush':"window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},200)",
            'trivia':"window.__iv=setInterval(()=>{try{c.test.answerCorrect()}catch(e){}},300)",'darts':"window.__iv=setInterval(()=>{try{c.test.throwAt(0,0)}catch(e){}},300)",
            'memory':"window.__iv=setInterval(()=>{try{c.test.solve()}catch(e){}},200)"}.get(gid,"")
        page.evaluate("c=DGApp.ctx();"+js)
        page.wait_for_function(f"DGApp.current().phase!=='play'", timeout=120000); page.evaluate("clearInterval(window.__iv)")
        page.wait_for_timeout(400); shot(page,f'mix-after-r{r}-{key}'); shot(page,f'mix-after-r{r}-{key}-full',True)
    print('mix', page.evaluate("DGApp.last()"))
    page.evaluate("DGApp.close()")
    # Watch spectate + race
    lm = page.evaluate("DGApp.go('watch')")
    page.wait_for_timeout(200)
    page.evaluate("DGApp.setSpeed(3)")
    page.evaluate("DGApp.watchGame('chess')"); page.wait_for_timeout(4000); shot(page,f'watch-spect-chess-{key}')
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.watchGame('durak')"); page.wait_for_timeout(3000); shot(page,f'watch-spect-durak-{key}')
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.watchGame('sudoku')"); page.wait_for_timeout(3000); shot(page,f'watch-race-{key}')
    page.wait_for_selector('[data-test=watch-result]', timeout=120000); shot(page,f'watch-race-end-{key}')
    page.evaluate("DGApp.close()"); page.evaluate("DGApp.setSpeed(1)")
    print(errs(page))
