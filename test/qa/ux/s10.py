from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.set({limits:{loss:500,remind:0,coolUntil:Date.now()+86400000}})")
    page.tap('#settingsBtn'); page.wait_for_timeout(200)
    page.tap('#resetBtn'); page.tap('#confirmYes'); page.wait_for_timeout(300)
    shot(page,'rg-reset-bypass-360')
    page.click('#ageAdult'); page.wait_for_timeout(200)
    print('after reset limits', page.evaluate("DGApp.state().limits"), 'staked start ->', repr(page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:500})")))
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.go('tournaments')"); page.wait_for_timeout(200)
    print(page.inner_text('[data-tour=weekend] .dg-note'))
