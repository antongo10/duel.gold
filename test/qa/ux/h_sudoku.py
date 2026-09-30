from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'sudoku','sudoku')
    tap_start(page)
    sol = page.evaluate("DGApp.ctx().test.solution()"); puz = page.evaluate("DGApp.ctx().test.puzzle()")
    empties=[i for i,v in enumerate(puz) if not v]
    # enter 5 correct digits by tapping, and 1 wrong
    cells = page.query_selector_all('.g-sudoku-cell')
    for i in empties[:5]:
        cells[i].tap(); page.tap(f'[data-d="{sol[i]}"]'); page.wait_for_timeout(80)
    i=empties[5]; cells[i].tap(); page.tap(f'[data-d="{sol[i]%9+1}"]'); page.wait_for_timeout(300)
    shot(page,'hand-sudoku-wrong-360')
    shot(page,'hand-sudoku-wrong-360-full', full=True)
    print(page.evaluate("DGApp.ctx().test.state().mistakes"), status(page))
    # notes
    page.tap('[data-test=notes]'); cells[empties[6]].tap(); page.tap('[data-d="1"]'); page.tap('[data-d="2"]'); page.wait_for_timeout(200)
    shot(page,'hand-sudoku-notes-360')
    page.tap('[data-test=notes]')
    # finish solving by taps
    for i in empties[5:]:
        cells[i].tap(); 
        # erase wrong if present
        page.tap(f'[data-d="{sol[i]}"]')
    wait_result(page, 20000)
    page.wait_for_timeout(300)
    shot(page,'hand-sudoku-result-360')
    print(page.evaluate("DGApp.last()"))
