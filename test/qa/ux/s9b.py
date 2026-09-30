from common import *
with browser_page(1440,900,False) as page:
    boot(page); page.evaluate("DGApp.go('games')"); page.evaluate("window.scrollTo(0,800)"); page.wait_for_timeout(300)
    print('1440 header top after scroll', page.evaluate("document.querySelector('#top').getBoundingClientRect().top"))
    shot(page,'games-scrolled-1440')
