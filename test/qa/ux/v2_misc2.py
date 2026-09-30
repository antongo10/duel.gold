from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.startMatch({game:'city',format:'1v1',stake:100})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(600)
    page.evaluate("c=DGApp.ctx(); c.test.autoBuild(0.9); c.test.finish(false)")
    seen=[]
    for i in range(40):
        ph=page.evaluate("DGApp.current().phase"); st=page.inner_text('#ovStatus'); f=page.evaluate("(()=>{const b=document.querySelector('#ovForfeit');return !b.hidden && !b.disabled})()")
        seen.append((round(i*0.2,1),ph,st[:14],f))
        if ph=='result': break
        page.wait_for_timeout(200)
    print([s for s in seen if 'Final' in s[2]])
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.set({limits:{loss:150,remind:0,coolUntil:0,pending:null}})")
    page.evaluate("DGApp.go('home')")
    for s in [100,50]:
        page.evaluate(f"DGApp.startMatch({{game:'sudoku',format:'1v1',stake:{s}}})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(200)
        if s==50: shot(page,'v2-limit-result-360'); print('rematch', page.evaluate("[document.querySelector('#resRematch').disabled, document.querySelector('#resRematch').textContent]"))
        page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    page.evaluate("window.scrollTo(0,0)"); shot(page,'v2-limit-home-360')
    print('pressed', page.evaluate("[...document.querySelectorAll('[data-stake][aria-pressed=true]')].map(b=>b.textContent)"), 'msgs', page.evaluate("[document.querySelector('#dnBlock')&&document.querySelector('#dnBlock').textContent, document.querySelector('#dnNote').textContent]"))
