from qalib import *
with new_page_ctx(1280) as page:
    boot(page)
    page.evaluate("DGApp.startMatch({game:'cat:knowledge', format:'mix', stake:100})")
    page.wait_for_selector('[data-test=mix]', timeout=10000)
    print(cur(page)['games'], page.inner_text('[data-test=mix]').split('\n')[-6:])
    page.evaluate("DGApp.close()")
    page.click('#tab-home'); page.click('[data-pick="cat:knowledge"]'); page.click('#dnF-mix')
    print('home note:', page.inner_text('#dnNote'))
    print(errs(page))
