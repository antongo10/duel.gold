from dglib import *
with browser_page(width=400) as page:
    open_harness(page, files=["_samples.js"], game="sample-tap", speed=4)
    print(page.evaluate("__games()"))
    page.evaluate("__run()")
    for _ in range(10): page.click("[data-test=tap]")
    r = wait_result(page, 10); print("tap result", r["score"])
    page.evaluate("__run({game:'sample-nim', skill:0.2})")
    for _ in range(20):
        if page.evaluate("__result"): break
        btn = page.query_selector("[data-take]:not([disabled])")
        if btn: btn.click()
        page.wait_for_timeout(700)
    print("nim", page.evaluate("__result"))
    print("errors", errors(page))
