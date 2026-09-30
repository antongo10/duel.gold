from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.set({limits:{loss:150,remind:0,coolUntil:0,pending:null}})")
    for s in [100,50]:
        page.evaluate(f"DGApp.startMatch({{game:'sudoku',format:'1v1',stake:{s}}})"); page.wait_for_selector('[data-test=start]:not([disabled])'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(300)
        if s==100: page.evaluate("DGApp.close()"); page.wait_for_timeout(200)
    print('today', page.evaluate("DGApp.state().today.net"), 'rematch', page.evaluate("[document.querySelector('#resRematch').disabled, document.querySelector('#resRematch').textContent]"))
    page.click('#resRematch'); page.wait_for_timeout(500)
    print('after click phase', page.evaluate("DGApp.current() && DGApp.current().phase"), 'gold', page.evaluate("DGApp.state().gold"), 'toasts', page.evaluate("[...document.querySelectorAll('.toast')].map(t=>t.textContent)"))
    shot(page,'v2-limit-rematch-360')
