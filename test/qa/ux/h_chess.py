from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'chess','chess')
    shot(page,'hand-chess-sheetdone-360')
    tap_start(page)
    st = page.evaluate("DGApp.ctx().test.state()")
    print('human', st['human'])
    moves = [('e2','e4'),('g1','f3'),('f1','c4'),('d2','d3')] if st['human']=='w' else [('e7','e5'),('g8','f6'),('f8','c5'),('d7','d6')]
    for a,b in moves:
        page.wait_for_function("(()=>{const s=DGApp.ctx().test.state();return s.turn===s.human||s.over})()", timeout=15000)
        page.tap(f'[data-test=sq-{a}]'); page.wait_for_timeout(150)
        page.tap(f'[data-test=sq-{b}]'); page.wait_for_timeout(300)
        print(a,b, page.evaluate("DGApp.ctx().test.state().sans"), status(page))
    page.wait_for_timeout(1500)
    shot(page,'hand-chess-midgame-360')
    shot(page,'hand-chess-midgame-360-full', full=True)
    # forfeit via UI
    page.tap('#ovForfeit'); page.wait_for_timeout(300)
    shot(page,'hand-forfeit-confirm-360')
    # check Escape in confirm
    page.keyboard.press('Escape'); page.wait_for_timeout(200)
    print('after esc modal?', page.evaluate("!!document.querySelector('[data-test=forfeit-confirm]')"), 'phase', page.evaluate("DGApp.current().phase"))
    page.tap('#ovForfeit'); page.wait_for_timeout(200)
    page.tap('#forfeitYes'); page.wait_for_timeout(500)
    shot(page,'hand-chess-forfeit-result-360')
    print(page.evaluate("DGApp.last()"), page.evaluate("DGApp.state().gold"))
    print(errs(page))
