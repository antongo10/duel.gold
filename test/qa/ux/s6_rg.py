from common import *
with browser_page(360,780,True) as page:
    boot(page)
    # Set loss limit custom 150 via UI
    page.tap('#settingsBtn'); page.wait_for_timeout(200)
    page.fill('#lossCustom','150'); page.tap('#lossSet'); page.wait_for_timeout(200)
    print('lossMsg', page.inner_text('#lossMsg'), DG:=page.evaluate("DGApp.state().limits"))
    # Home: stake chips > room disabled?
    page.tap('#bn-home'); page.wait_for_timeout(200)
    dis = page.evaluate("[...document.querySelectorAll('[data-stake]')].map(b=>[b.textContent,b.disabled])")
    print('stake chips with limit 150', dis)
    # lose 100 via forfeit match
    page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:100})"); page.wait_for_selector('[data-test=start]'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(200); page.evaluate("DGApp.close()")
    page.wait_for_timeout(200)
    dis = page.evaluate("[...document.querySelectorAll('[data-stake]')].map(b=>[b.textContent,b.disabled])")
    print('after -100', dis)
    page.tap('#dnS-50'); page.wait_for_timeout(100)
    print('note', page.inner_text('#dnNote'), page.evaluate("document.querySelector('#dnFind').disabled"))
    page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:50})"); page.wait_for_selector('[data-test=start]'); page.evaluate("DGApp.forfeit()"); page.wait_for_timeout(200); page.evaluate("DGApp.close()")
    page.wait_for_timeout(300)
    shot(page,'rg-losslimit-home-360'); shot(page,'rg-losslimit-home-360-full', True)
    print('block', page.evaluate("document.querySelector('#dnBlock') && document.querySelector('#dnBlock').textContent"))
    print('startMatch 50 ->', page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:50})"))
    print('today', page.evaluate("DGApp.state().today"))
    # Tournaments page with limit reached
    page.tap('#bn-tournaments'); page.wait_for_timeout(200); shot(page,'rg-losslimit-tours-360')
    print('join weekend disabled', page.evaluate("document.querySelector('#join-weekend').disabled"), page.evaluate("document.querySelector('#join-daily').disabled"))
    # free play still ok
    print('free ->', repr(page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:0})"))); page.wait_for_timeout(300); page.evaluate("DGApp.close()")
    # Rematch button after loss when limit reached?
    # Cool-off
    page.evaluate("DGApp.set({limits:Object.assign(DGApp.state().limits,{loss:0})})")
    page.tap('#settingsBtn'); page.wait_for_timeout(200)
    page.tap('#cool-24h'); page.wait_for_timeout(200); shot(page,'rg-cool-confirm-360')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    print('esc closed confirm', not page.query_selector('[data-test=cool-confirm]'), 'cool', page.evaluate("DGApp.state().limits.coolUntil"))
    page.tap('#cool-24h'); page.tap('#confirmYes'); page.wait_for_timeout(300)
    shot(page,'rg-cool-settings-360'); shot(page,'rg-cool-settings-360-full', True)
    page.tap('#bn-home'); page.wait_for_timeout(200); shot(page,'rg-cool-home-360')
    print('cool block', page.evaluate("document.querySelector('#dnBlock') && document.querySelector('#dnBlock').textContent"))
    print('startMatch 100 ->', page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:100})"))
    page.tap('#bn-tournaments'); page.wait_for_timeout(200); shot(page,'rg-cool-tours-360', True)
    print('daily free join enabled under cool-off', not page.evaluate("document.querySelector('#join-daily').disabled"))
    # quick tournament entry chips
    print('qentry', page.evaluate("[...document.querySelectorAll('[data-qentry]')].map(b=>[b.textContent,b.disabled])"))
    # reminder
    page.evaluate("DGApp.remindNow()"); page.wait_for_timeout(200); shot(page,'toast-reminder-360')
    # reset confirm
    page.tap('#settingsBtn'); page.wait_for_timeout(200); page.tap('#resetBtn'); page.wait_for_timeout(200); shot(page,'modal-reset-360')
    print(errs(page))
with browser_page(360,780,True) as page:
    boot(page, age='minor')
    page.wait_for_timeout(300); shot(page,'minor-home-360'); shot(page,'minor-home-360-full', True)
    print('minor block', page.evaluate("document.querySelector('#dnBlock') && document.querySelector('#dnBlock').textContent"))
    print('minor chips', page.evaluate("[...document.querySelectorAll('[data-stake]')].map(b=>[b.textContent,b.disabled])"))
    page.tap('#bn-tournaments'); page.wait_for_timeout(200); shot(page,'minor-tours-360', True)
    print('minor daily (free, house prize 5000) enabled', not page.evaluate("document.querySelector('#join-daily').disabled"))
    print('minor quick', page.evaluate("[...document.querySelectorAll('[data-qentry]')].map(b=>[b.textContent,b.disabled])"))
    page.tap('#settingsBtn'); page.wait_for_timeout(200); shot(page,'minor-settings-360')
    page.tap('#ageAgain'); page.wait_for_timeout(200); shot(page,'minor-agegate-again-360')
    page.tap('#ageAdult'); page.wait_for_timeout(200)
    print('minor switched to adult trivially:', page.evaluate("DGApp.state().age"))
