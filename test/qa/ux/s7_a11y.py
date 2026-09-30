from common import *
with browser_page(1440,900,False) as page:
    open_app(page, APP); page.wait_for_function("DG.__appReady")
    page.wait_for_timeout(300)
    # age gate focus + Tab trap?
    print('age focus', page.evaluate("document.activeElement.id"))
    seq=[]
    for i in range(6):
        page.keyboard.press('Tab'); seq.append(page.evaluate("(document.activeElement.id||document.activeElement.className||document.activeElement.tagName)+'|'+(document.activeElement.closest('.modal')?'modal':'page')"))
    print('age tab seq', seq)
    page.keyboard.press('Escape'); print('age after esc still open', bool(page.query_selector('[data-test=age-gate]')))
    page.click('#ageAdult')
    page.evaluate("document.activeElement.blur()")
    seq=[]
    for i in range(16):
        page.keyboard.press('Tab'); seq.append(page.evaluate("(document.activeElement.id||document.activeElement.textContent.trim().slice(0,14))"))
    print('lobby tab order', seq)
    shot(page,'a11y-focus-lobby-1440')
    # focus ring style of chip
    page.focus('#dnF-2v2'); shot(page,'a11y-focus-chip-1440')
    print('outline', page.evaluate("getComputedStyle(document.activeElement).outlineStyle+' '+getComputedStyle(document.activeElement).outlineColor"))
    # open a duel sheet via keyboard, tab out beyond modal?
    page.evaluate("DGApp.go('games')"); page.wait_for_timeout(200)
    page.focus('[data-duel="chess"]'); page.keyboard.press('Enter'); page.wait_for_timeout(300)
    print('sheet open', bool(page.query_selector('[data-test=duel-sheet]')), 'focus', page.evaluate("document.activeElement.id||document.activeElement.className"))
    out=[]
    for i in range(40):
        page.keyboard.press('Tab'); out.append(page.evaluate("!!document.activeElement.closest('.modal')"))
    print('focus escapes sheet modal after tabbing:', out.count(False), 'of 40')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    print('focus returned to', page.evaluate("document.activeElement.getAttribute('data-duel')"))
    # match overlay: Escape during play? Tab focus goes behind overlay?
    page.evaluate("DGApp.startMatch({game:'sudoku',format:'1v1',stake:0})"); page.wait_for_selector('[data-test=start]')
    out=[]
    for i in range(25):
        page.keyboard.press('Tab'); out.append(page.evaluate("!!document.activeElement.closest('#ov')"))
    print('focus leaves match overlay into page behind:', out.count(False), 'of 25')
    shot(page,'a11y-overlay-tab-1440')
    page.keyboard.press('Escape'); print('overlay after Esc phase', page.evaluate("DGApp.current() && DGApp.current().phase"))
    page.evaluate("DGApp.close()")
    # buttons without accessible name
    print('unlabelled', page.evaluate("[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&!(b.textContent.trim()||b.getAttribute('aria-label'))).map(b=>b.id||b.className).slice(0,10)"))
    # meter semantic
    # home: 'Live now' dot color only
    # wallet pill: gold pill goes home?
    # hash nav
    page.goto(page.url.split('#')[0]+'#profile'); page.wait_for_function("DG.__appReady"); page.wait_for_timeout(200)
    print('hash deep link view', page.evaluate("[...document.querySelectorAll('.view')].find(v=>!v.hidden).id"))
    # lang attr
    print('lang', page.evaluate("document.documentElement.lang"))
    # fonts
    print('fonts', page.evaluate("[getComputedStyle(document.querySelector('.logo')).fontFamily, document.fonts.check('16px \"Big Shoulders Display\"')]"))
