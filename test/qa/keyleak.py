import json
from qalib import *
def rep(*a): print(*a, flush=True)
SCR = "document.getElementById('ovScroll').scrollTop"
with new_page_ctx(1280, height=600) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(1)")
    for gid in GAMES:
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
        page.wait_for_timeout(300)
        try: T(page, "t.freezeTimer && t.freezeTimer()"); T(page, "t.freezeClocks && t.freezeClocks()")
        except Exception: pass
        maxs = page.evaluate("document.getElementById('ovScroll').scrollHeight - document.getElementById('ovScroll').clientHeight")
        # A: arrow/space/pagedown with focus on body, after clicking empty overlay area (sub bar info)
        page.click('#ovInfo')
        page.evaluate("document.getElementById('ovScroll').scrollTop = 0")
        for k in ['ArrowDown', 'ArrowDown', 'ArrowDown', 'PageDown', 'Space']:
            page.keyboard.press(k); page.wait_for_timeout(30)
        page.wait_for_timeout(250)
        scrolled = page.evaluate(SCR)
        # B: Forfeit -> Keep playing -> Space / Enter
        page.evaluate("document.getElementById('ovScroll').scrollTop = 0")
        page.click('#ovForfeit'); page.wait_for_selector('#forfeitNo'); page.click('#forfeitNo')
        ae = page.evaluate("document.activeElement.id")
        opened = {}
        for k in ['Space', 'Enter']:
            page.keyboard.press(k); page.wait_for_timeout(120)
            opened[k] = page.locator('[data-test=forfeit-confirm]').count()
            if opened[k]: page.click('#forfeitNo')
        still = cur(page)['phase']
        rep(gid, json.dumps(dict(overlay_scrollable=maxs, scrolled_by_keys=scrolled, focus_after_keep_playing=ae, forfeit_dialog_reopened=opened, phase=still)))
        page.evaluate("DGApp.close()"); page.wait_for_timeout(100)
        while page.locator('.modal-x').count(): page.locator('.modal-x').first.click()
    print(errs(page))
