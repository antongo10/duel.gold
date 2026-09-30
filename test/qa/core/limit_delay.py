"""24 h delay on raising/removing a loss limit: applies after 24 h (clock offset, no reload), and stakeError honours it."""
from qa_common import *
with browser_page() as page:
    boot(page)
    page.evaluate("DGApp.go('settings')"); page.click('#loss-1000'); page.click('#loss-0')
    print('pending', page.evaluate("DGApp.state().limits"))
    page.evaluate("DGApp.advanceDays(0.99)"); print('23.8h:', page.evaluate("DGApp.state().limits.loss"), page.evaluate("DGP.lossRoom()"))
    page.evaluate("DGApp.advanceDays(0.02)"); print('24.2h lossRoom:', page.evaluate("DGP.lossRoom()"), 'state:', page.evaluate("DGApp.state().limits"))
    page.evaluate("DGApp.go('settings')"); print('after settings render:', page.evaluate("DGApp.state().limits"))
    # pending survives reload
    page.click('#loss-1000'); page.click('#loss-5000'); p = page.evaluate("DGApp.state().limits")
    page.reload(); page.wait_for_function("DG.__appReady"); print('after reload:', page.evaluate("DGApp.state().limits"), 'was', p)
    print('errs', errs(page))
