from qalib import *
with new_page_ctx(1280) as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    for gid, key, probe in [('trivia', None, "t.state().qi"), ('tiles2048', 'ArrowLeft', "t.state().moves"), ('rush', None, "t.state().right + t.state().wrong")]:
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_function("DGApp.ctx() && DGApp.ctx().test")
        if gid == 'trivia': page.wait_for_function("DGApp.ctx().test.state().phase === 'ask'")
        k = key or str(1 + (T(page, "t.state().ans") if gid == 'trivia' else T(page, "t.state().current.correct")))
        page.click('#ovForfeit'); page.wait_for_selector('#forfeitNo')
        a = T(page, probe); page.keyboard.press(k); page.wait_for_timeout(200); b = T(page, probe)
        print(gid, 'key', k, 'pressed while Forfeit dialog open -> game reacted:', a != b, a, b, 'dialog still open', page.locator('[data-test=forfeit-confirm]').count())
        page.click('#forfeitNo'); page.evaluate("DGApp.close()")
    # friend challenge: focus restored to the Challenge button behind the overlay?
    page.click('#tab-social'); page.locator('[data-challenge]').first.click(); page.wait_for_selector('[data-test=duel-sheet]')
    page.click('#shS-100'); page.click('#shFind'); page.wait_for_timeout(200)
    print('after friend challenge launch, focus:', page.evaluate("[document.activeElement.tagName, document.activeElement.dataset.challenge || document.activeElement.id, document.getElementById('ov').contains(document.activeElement)]"))
    print(errs(page))
