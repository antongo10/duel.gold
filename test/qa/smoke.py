from qalib import *
with new_page_ctx(1280) as page:
    boot(page)
    print(st(page)['gold'], st(page)['age'])
    start_via_games_tab(page, 'sudoku')
    through_to_play(page, shotname='smoke-rules')
    print(cur(page))
    print(T(page, "Object.keys(t)"))
    page.click('[data-test=cell-0]')
    shot(page, 'smoke-play')
    print(errs(page))
