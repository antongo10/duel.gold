import json
from qalib import *

def rep(*a): print(*a, flush=True)
AE = "(() => { const a = document.activeElement; return a ? (a.id || a.dataset.test || a.className || a.tagName) + (document.getElementById('ov').contains(a) ? ' [in ov]' : (a === document.body ? '' : ' [OUTSIDE ov]')) : null })()"
SCR = "[document.getElementById('ovScroll').scrollTop, window.scrollY, document.getElementById('ovScroll').scrollHeight - document.getElementById('ovScroll').clientHeight]"

def launch_kb(page, gid):
    """Games tab -> Duel -> sheet -> Find, then Start with the keyboard (Space on the autofocused Start)."""
    start_via_games_tab(page, gid, '1v1', 100)
    page.wait_for_selector('[data-test=matchmaking]')
    ae_mm = page.evaluate(AE)
    page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000)
    page.wait_for_timeout(100)
    ae_ready = page.evaluate(AE)
    page.keyboard.press('Space')
    page.wait_for_function("DGApp.current().phase === 'play' && DGApp.ctx() && DGApp.ctx().test", timeout=5000)
    page.wait_for_timeout(200)
    return ae_mm, ae_ready, page.evaluate(AE)

with new_page_ctx(1280, height=700) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(1)")
    tests = {}
    # sudoku: digits + arrows
    def k_sudoku():
        T(page, "t.select(t.puzzle().findIndex(v => !v))")
        i = T(page, "t.state().selected"); d = T(page, f"t.solution()[{i}]")
        s0 = page.evaluate(SCR)
        page.keyboard.press('ArrowDown'); page.keyboard.press('ArrowDown'); page.keyboard.press('ArrowRight')
        sel2 = T(page, "t.state().selected")
        T(page, f"t.select({i})"); page.keyboard.press(str(d))
        return dict(digit=T(page, f"t.state().values[{i}]") == d, arrows=sel2 != i, scroll=[s0, page.evaluate(SCR)])
    def k_tiles2048():
        m0 = T(page, "t.state().moves"); s0 = page.evaluate(SCR)
        for k in ['ArrowLeft', 'ArrowUp', 'ArrowRight', 'ArrowDown', 'a', 'w', 'd', 's']: page.keyboard.press(k); page.wait_for_timeout(120)
        return dict(moves=T(page, "t.state().moves") - m0, scroll=[s0, page.evaluate(SCR)])
    def k_reaction():
        s0 = page.evaluate(SCR)
        page.keyboard.press('Space')
        armed = page.evaluate("document.querySelector('[data-test=pad]').dataset.state")
        page.wait_for_function("document.querySelector('[data-test=pad]').dataset.state === 'go'", timeout=6000)
        page.keyboard.press('Enter'); page.wait_for_timeout(50)
        return dict(armed=armed, result=T(page, "t.state().results[0]"), scroll=[s0, page.evaluate(SCR)])
    def k_rush():
        c = T(page, "t.state().current.correct"); page.keyboard.press(str(c + 1)); page.wait_for_timeout(50)
        return dict(right=T(page, "t.state().right"))
    def k_trivia():
        page.wait_for_function("DGApp.ctx().test.state().phase === 'ask'")
        a = T(page, "t.state().ans"); page.keyboard.press(str(a + 1)); page.wait_for_timeout(50)
        return dict(correct=T(page, "t.state().correct"))
    def k_four():
        page.wait_for_function("DGApp.ctx().test.legalMoves().length > 0", timeout=10000)
        T(page, "t.freezeTimer()")
        s0 = T(page, "JSON.stringify(t.state().cells)"); page.keyboard.press('4'); page.wait_for_timeout(100)
        return dict(moved=T(page, "JSON.stringify(t.state().cells)") != s0)
    def k_mines():
        c0 = T(page, "t.state().cursor"); s0 = page.evaluate(SCR)
        page.keyboard.press('ArrowRight'); page.keyboard.press('ArrowDown')
        c1 = T(page, "t.state().cursor")
        f0 = sum(T(page, "t.state().flags")); page.keyboard.press('f'); f1 = sum(T(page, "t.state().flags"))
        o0 = T(page, "t.state().opened"); page.keyboard.press('f'); 
        return dict(cursor=[c0, c1], flag=f1 - f0, scroll=[s0, page.evaluate(SCR)])
    def k_queens():
        s0 = page.evaluate(SCR)
        page.keyboard.press('ArrowRight'); page.keyboard.press('Space'); page.wait_for_timeout(50)
        return dict(mark=T(page, "t.state().marks[1]"), ae=page.evaluate(AE), scroll=[s0, page.evaluate(SCR)])
    def k_memory():
        page.wait_for_function("DGApp.ctx().test.state().phase === 'input'", timeout=10000)
        seq = T(page, "t.sequence()"); keys = "123456789"
        for c in seq: page.keyboard.press(keys[c])
        page.wait_for_timeout(50)
        return dict(longest=T(page, "t.state().longest"), n=len(seq))
    def k_base():
        page.keyboard.press('3'); t = T(page, "t.state().tool")
        page.keyboard.press('Enter'); page.wait_for_timeout(100)
        return dict(tool3=t, phase=T(page, "t.state().phase"))
    def k_groups():
        sol = T(page, "t.solution()")
        for w in sol[0]['words']: page.click(f"[data-test=wg-tile][data-w=\"{w}\"]")
        page.keyboard.press('Enter'); page.wait_for_timeout(100)
        return dict(found=T(page, "t.state().found"))
    for gid, fn in [('sudoku', k_sudoku), ('tiles2048', k_tiles2048), ('reaction', k_reaction), ('rush', k_rush), ('trivia', k_trivia), ('four', k_four),
                    ('mines', k_mines), ('queens', k_queens), ('memory', k_memory), ('base', k_base), ('groups', k_groups)]:
        e0 = len(errs(page))
        try:
            aes = launch_kb(page, gid)
            r = fn()
            r['focus_mm/ready/play'] = aes
            r['modals'] = page.evaluate("document.querySelectorAll('.modal').length")
            r['sheet_open'] = page.locator('[data-test=duel-sheet]').count()
        except Exception as ex:
            r = {'EXC': repr(ex)[:300]}; shot(page, f'kb-exc-{gid}')
        r['err'] = errs(page)[e0:]
        rep(gid, json.dumps(r))
        page.evaluate("DGApp.close()"); page.wait_for_timeout(100)
        while page.locator('.modal-x').count(): page.locator('.modal-x').first.click()
