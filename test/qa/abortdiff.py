import json
from qalib import *
with new_page_ctx(1280) as page:
    boot(page); page.evaluate("DGApp.setSpeed(3)")
    for gid in ['chess', 'reversi', 'gomoku', 'aim', 'hockey']:
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
        try: T(page, "t.autoplay && t.autoplay(0.9)")
        except Exception: pass
        page.wait_for_timeout(1200)
        page.evaluate("window.__old = DGApp.ctx()")
        page.evaluate("DGApp.forfeit()")
        a = page.evaluate("window.__old.test.state()")
        page.wait_for_timeout(3000)
        b = page.evaluate("window.__old.test.state()")
        diff = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
        print(gid, json.dumps(diff)[:600])
        page.click('[data-test=back]')
