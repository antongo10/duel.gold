"""Hook-only finishers (after Start) for each game, used for format tests."""
from qalib import T
def ended(page): return page.evaluate("!DGApp.ctx() || DGApp.ctx().signal.ended")
def loop(page, expr, n=800, ms=25):
    for _ in range(n):
        if ended(page): return
        try: T(page, expr)
        except Exception: pass
        page.wait_for_timeout(ms)
FIN = {
 'sudoku': lambda p: loop(p, "t.solve()", 50, 100),
 'mines': lambda p: loop(p, "t.solve()", 50, 100),
 'queens': lambda p: loop(p, "t.solve()", 400, 60),
 'tiles2048': lambda p: loop(p, "t.solve()", 50, 100),
 'memory': lambda p: loop(p, "(t.state().phase==='input' && t.state().level>=3) ? t.mistake() : t.solve()", 2000, 40),
 'reaction': lambda p: loop(p, "t.fire(220)", 3000, 20),
 'aim': lambda p: loop(p, "t.hitNext()", 4000, 20),
 'rush': lambda p: loop(p, "t.answerCorrect()", 4000, 20),
 'darts': lambda p: loop(p, "t.throwAt(0,0)", 1500, 30),
 'base': lambda p: (T(p, "t.placeAI(0.9)"), loop(p, "t.fastForward()", 50, 100)),
 'city': lambda p: (T(p, "t.autoBuild(0.9)"), loop(p, "t.finish(true)", 50, 100)),
 'restaurant': lambda p: (T(p, "t.optimise(0.9)"), loop(p, "t.finish(true)", 50, 100)),
 'trivia': lambda p: loop(p, "t.answerCorrect()", 3000, 30),
 'groups': lambda p: loop(p, "[0,1,2,3].forEach(i => t.submitGroup(i))", 50, 150),
 'chess': lambda p: (T(p, "t.freezeClocks && t.freezeClocks()"), T(p, "t.autoplay(0.98)")),
 'four': lambda p: (T(p, "t.freezeTimer()"), T(p, "t.autoplay(0.98)")),
 'reversi': lambda p: (T(p, "t.freezeTimer()"), T(p, "t.autoplay(0.98)")),
 'gomoku': lambda p: (T(p, "t.freezeTimer()"), T(p, "t.autoplay(0.98)")),
 'hockey': lambda p: loop(p, "t.forceGoal('me')", 20, 60),
 'durak': lambda p: T(p, "t.autoplay()"),
 'liars': lambda p: T(p, "t.autoplay()"),
 'auction': lambda p: T(p, "t.autoplay()"),
}
def play_round(page, touch=False):
    """from rules card: click Start, finish the game via hooks."""
    page.wait_for_selector('[data-test=start]:not([disabled])', timeout=15000)
    b = page.locator('[data-test=start]'); b.scroll_into_view_if_needed(); b.tap() if touch else b.click()
    page.wait_for_function("DGApp.ctx() && DGApp.ctx().test", timeout=8000)
    gid = page.evaluate("document.querySelector('#gameRoot').dataset.game")
    FIN[gid](page)
    return gid
