from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.startMatch({game:'city',format:'1v1',stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(600)
    page.evaluate("c=DGApp.ctx(); c.test.autoBuild(0.9); c.test.finish(false)")
    vis=[]
    for i in range(30):
        ph=page.evaluate("DGApp.current().phase"); f=page.evaluate("(()=>{const b=document.querySelector('#ovForfeit');return !b.hidden && !b.disabled})()")
        vis.append((ph,f));
        if ph=='result': break
        page.wait_for_timeout(250)
    print('forfeit active while game shows final:', [v for v in vis if v[1]][-3:], 'status', page.inner_text('#ovStatus'))
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.set({limits:{loss:150,remind:0,coolUntil:0,pending:null}})")
    page.evaluate("DGApp.go('home')"); page.wait_for_timeout(200)
    page.tap('#dnS-100'); page.wait_for_timeout(100)
    page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(200)
    shot(page,'v2-limit-result-360')
    print('rematch disabled', page.evaluate("document.querySelector('#resRematch') && document.querySelector('#resRematch').disabled"), page.evaluate("[...document.querySelectorAll('.result .dg-note')].map(n=>n.textContent).slice(-1)"))
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:50})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(200); page.evaluate("DGApp.close()"); page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0,0)")
    shot(page,'v2-limit-home-360')
    print('pressed stake', page.evaluate("[...document.querySelectorAll('[data-stake][aria-pressed=true]')].map(b=>b.textContent)"), 'find disabled', page.evaluate("document.querySelector('#dnFind').disabled"))
    print('messages', page.evaluate("[document.querySelector('#dnBlock')&&document.querySelector('#dnBlock').textContent, document.querySelector('#dnNote').textContent]"))
