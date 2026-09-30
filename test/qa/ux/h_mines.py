from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'mines','mine')
    tap_start(page)
    mine = page.evaluate("DGApp.ctx().test.solution()")
    st = page.evaluate("DGApp.ctx().test.state()")
    C=st['C']; opn=st['open']
    # tap a few safe unopened cells adjacent to opened region
    cnt=0
    for i,v in enumerate(opn):
        if not v and not mine[i] and cnt<4:
            page.tap(f'[data-test=cell-{i}]'); cnt+=1; page.wait_for_timeout(120)
    # flag mode, flag a mine
    page.tap('[data-test=flagmode]'); mi = mine.index(1); page.tap(f'[data-test=cell-{mi}]'); page.wait_for_timeout(150)
    shot(page,'hand-mines-flag-360')
    print(page.evaluate("DGApp.ctx().test.state().flags").count(1), status(page))
    page.tap('[data-test=flagmode]')
    # zoom
    page.tap('[data-test=zoom]'); page.wait_for_timeout(300); shot(page,'hand-mines-zoom-360')
    print('hscroll zoom', hscroll(page), page.evaluate("(()=>{const w=document.querySelector('.g-mines-wrap');return [w.scrollWidth,w.clientWidth]})()"))
    page.tap('[data-test=zoom]')
    # boom: tap an unflagged mine
    mj=[i for i,v in enumerate(mine) if v][1]
    page.tap(f'[data-test=cell-{mj}]'); page.wait_for_timeout(600)
    shot(page,'hand-mines-boom-360')
    wait_result(page, 20000); page.wait_for_timeout(300)
    shot(page,'hand-mines-result-360')
    print(page.evaluate("DGApp.last()"))
