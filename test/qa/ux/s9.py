from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("window.scrollTo(0,900)"); page.wait_for_timeout(300)
    shot(page,'home-scrolled-360')
    print(page.evaluate("[document.querySelector('#top').getBoundingClientRect().top, getComputedStyle(document.querySelector('#top')).position, getComputedStyle(document.body).overflowX, getComputedStyle(document.documentElement).overflowX]"))
    page.mouse.wheel(0,500); page.wait_for_timeout(300)
    print(page.evaluate("document.querySelector('#top').getBoundingClientRect().top"))
