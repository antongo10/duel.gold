from qalib import *
with new_page_ctx(1280) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    page.click('#tab-watch'); b = page.locator('#view-watch [data-watch-go]').nth(2); b.click()
    page.wait_for_timeout(300)
    print('focused:', page.evaluate("[document.activeElement.dataset.watchGo, document.getElementById('ov').contains(document.activeElement)]"))
    for k in ['Space', 'Enter']:
        page.keyboard.press(k); page.wait_for_timeout(200)
    print('toasts:', page.evaluate("[...document.querySelectorAll('.toast')].map(t => t.textContent)"))
    shot(page, 'watch-space-toast')
    print(errs(page))
