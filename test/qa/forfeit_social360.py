from qalib import *
with new_page_ctx(360, touch=True) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    for gid in ['durak', 'liars', 'auction']:
        g0 = st(page)['gold']
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.tap('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test"); page.wait_for_timeout(800)
        page.tap('#ovForfeit'); page.tap('#forfeitYes'); wait_result(page, 10)
        a = page.evaluate("[__qa.rafCalls, document.querySelector('#ovStatus').textContent]"); page.wait_for_timeout(2000); b = page.evaluate("[__qa.rafCalls, document.querySelector('#ovStatus').textContent, __qa.keydown, __qa.iv]")
        print(gid, last(page)['outcome'], 'gold delta', st(page)['gold'] - g0, 'raf after', b[0] - a[0], 'status same', a[1] == b[1], 'kd/iv', b[2:])
        page.click('[data-test=back]')
    print(errs(page))
