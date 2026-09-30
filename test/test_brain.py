"""Pack B (brain) tests: sudoku, mines, queens, tiles2048, memory.
Run: python3 test/test_brain.py   (exits non-zero on failure)"""
import json, pathlib, statistics, sys, time, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dglib import browser_page, open_harness, wait_result, errors

FILES = ["brain.js"]
GAMES = ["sudoku", "mines", "queens", "tiles2048", "memory"]
SHOTS = pathlib.Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(exist_ok=True)
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)
    return cond


def start(page, game, mode="full", seed=7, speed=1, fmt="1v1"):
    # the harness does not stop a previous match; abort it so it cannot leak timers/keys into this one
    page.evaluate("window.__handle && window.__handle.abort()")
    page.evaluate(f"__run({{game:'{game}', mode:'{mode}', seed:{seed}, speed:{speed}, format:'{fmt}'}})")
    page.wait_for_timeout(60)


def T(page, js):
    return page.evaluate("(() => { const t = window.__handle.ctx.test; return " + js + "; })()")


def result_ok(page, r, label, min_score=None):
    check(isinstance(r, dict) and isinstance(r.get("score"), (int, float)), f"{label}: result shape {r}")
    check(isinstance(r.get("detail"), str) and len(r["detail"]) > 10, f"{label}: detail missing")
    if min_score is not None:
        check(r["score"] >= min_score, f"{label}: score {r['score']} < {min_score}")
    prog = page.evaluate("__progress")
    check(prog and prog[-1] == r["score"], f"{label}: last progress {prog[-1:] } != score {r['score']}")
    e = errors(page)
    check(not e, f"{label}: errors {e}")
    print(f"  {label}: score={r['score']}  detail={strip(r['detail'])}")


def strip(h):
    import re
    return re.sub(r"<[^>]+>", "", h).replace("\n", " ")[:110]


def no_hscroll(page, label):
    ok = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    check(ok, f"{label}: horizontal scroll at {page.viewport_size['width']}px "
              f"({page.evaluate('document.documentElement.scrollWidth')})")


def shot(page, name):
    page.screenshot(path=str(SHOTS / name), full_page=True)


# ------------------------------------------------------------------ SUDOKU
def sudoku_ui(page, mode, width):
    label = f"sudoku/{mode}/{width}"
    start(page, "sudoku", mode, seed=11)
    sol = T(page, "t.solution()"); puz = T(page, "t.puzzle()")
    empties = [i for i, v in enumerate(puz) if v == 0]
    n = 9 if mode == "full" else 6
    # 3 correct digits via real clicks on cell + pad
    for i in empties[:3]:
        page.click(f"[data-test=cell-{i}]")
        page.click(f"[data-test=num-{sol[i]}]")
    st = T(page, "t.state()")
    check(st["correct"] == 3, f"{label}: 3 pad entries -> correct={st['correct']}")
    check("user" in page.get_attribute(f"[data-test=cell-{empties[0]}]", "class"), f"{label}: user digit class")
    # one wrong digit via click -> red + mistake
    i = empties[3]; wrong = sol[i] % n + 1
    page.click(f"[data-test=cell-{i}]"); page.click(f"[data-test=num-{wrong}]")
    st = T(page, "t.state()")
    check(st["mistakes"] == 1 and st["wrong"][i] == wrong, f"{label}: mistake recorded {st['mistakes']}")
    check("wrong" in page.get_attribute(f"[data-test=cell-{i}]", "class"), f"{label}: wrong cell is red")
    check("Mistakes 1/3" in page.evaluate("__status"), f"{label}: status shows mistakes: {page.evaluate('__status')}")
    page.click("[data-test=erase]")
    check(T(page, "t.state()")["wrong"][i] == 0, f"{label}: erase clears wrong digit")
    # notes toggle via chip, pencil a note, then toggle back
    page.click("[data-test=notes]"); page.click(f"[data-test=num-{sol[i]}]")
    st = T(page, "t.state()")
    check(st["noteMode"] and st["notes"][i] != 0 and st["values"][i] == 0, f"{label}: note pencilled")
    page.click("[data-test=notes]")
    # keyboard: arrows + digit
    j = empties[4]
    page.click(f"[data-test=cell-{j}]")
    page.keyboard.press(str(sol[j]))
    check(T(page, "t.state()")["values"][j] == sol[j], f"{label}: keyboard digit")
    page.keyboard.press("ArrowRight")
    check(T(page, "t.state()")["selected"] == (j // n) * n + (j % n + 1) % n, f"{label}: arrow moves selection")
    no_hscroll(page, label)
    if width in (400, 1280) and mode == "full":
        page.click(f"[data-test=cell-{empties[6]}]")
        shot(page, f"sudoku-{width}.png")
    if mode == "mix" and width == 1280:
        shot(page, "sudoku-mix-1280.png")
    T(page, "t.solve()")
    r = wait_result(page, 10)
    result_ok(page, r, label, min_score=2800)
    check("Solved in" in r["detail"] and "1 mistake" in r["detail"], f"{label}: detail {strip(r['detail'])}")


def sudoku_paths(page):
    # three mistakes -> run ends, 25 per correct cell
    start(page, "sudoku", "full", seed=3)
    sol = T(page, "t.solution()"); puz = T(page, "t.puzzle()")
    empties = [i for i, v in enumerate(puz) if v == 0]
    for i in empties[:2]:
        page.click(f"[data-test=cell-{i}]"); page.click(f"[data-test=num-{sol[i]}]")
    for _ in range(3):
        T(page, "t.mistake()")
    r = wait_result(page, 5)
    result_ok(page, r, "sudoku/3-mistakes")
    check(r["score"] == 50 and "Three mistakes" in r["detail"], f"sudoku/3-mistakes score {r['score']}")
    # time-out (mix 45 s at speed 20)
    start(page, "sudoku", "mix", seed=4, speed=20)
    T(page, "t.select(t.puzzle().indexOf(0))")
    T(page, "t.place(t.solution()[t.puzzle().indexOf(0)])")
    r = wait_result(page, 10)
    result_ok(page, r, "sudoku/timeout")
    check(r["score"] == 25 and "Time up" in r["detail"], f"sudoku/timeout score {r['score']}")


# ------------------------------------------------------------------ MINES
def mines_ui(page, mode, width):
    label = f"mines/{mode}/{width}"
    start(page, "mines", mode, seed=21)
    mine = T(page, "t.solution()"); nums = T(page, "t.numbers()"); st = T(page, "t.state()")
    C = st["C"]; op = st["open"]
    check(op[T(page, "t.start")] == 1 and st["opened"] > 1, f"{label}: start cell pre-revealed ({st['opened']})")
    # reveal 3 unopened safe cells by real clicks
    safe = [i for i in range(len(mine)) if not mine[i] and not op[i]]
    clicked = 0
    for i in safe:
        if T(page, "t.state()")["open"][i]:
            continue
        page.click(f"[data-test=cell-{i}]")
        clicked += 1
        if clicked == 3:
            break
    st2 = T(page, "t.state()")
    check(st2["opened"] > st["opened"] and not st2["done"], f"{label}: UI reveal {st['opened']}->{st2['opened']}")
    mines_idx = [i for i in range(len(mine)) if mine[i]]
    # right-click flag
    page.click(f"[data-test=cell-{mines_idx[0]}]", button="right")
    check(T(page, "t.state()")["flags"][mines_idx[0]] == 1, f"{label}: right-click flag")
    # long-press flag
    box = page.locator(f"[data-test=cell-{mines_idx[1]}]").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down(); page.wait_for_timeout(600); page.mouse.up()
    check(T(page, "t.state()")["flags"][mines_idx[1]] == 1, f"{label}: long-press flag")
    # flag mode toggle + tap
    page.click("[data-test=flagmode]")
    page.click(f"[data-test=cell-{mines_idx[2]}]")
    check(T(page, "t.state()")["flags"][mines_idx[2]] == 1, f"{label}: flag-mode tap")
    page.click("[data-test=flagmode]")
    # chording: find an open number whose mine neighbours are all flagged and has a closed safe neighbour
    st = T(page, "t.state()"); R = st["R"]
    def nb(i):
        r, c = divmod(i, C)
        return [(r + dr) * C + c + dc for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr or dc) and 0 <= r + dr < R and 0 <= c + dc < C]
    chorded = False
    for i in range(len(mine)):
        if st["open"][i] and nums[i] > 0:
            ms = [j for j in nb(i) if mine[j]]
            closed_safe = [j for j in nb(i) if not mine[j] and not st["open"][j]]
            if ms and closed_safe:
                for j in ms:
                    if not T(page, "t.state()")["flags"][j]:
                        page.click(f"[data-test=cell-{j}]", button="right")
                before = T(page, "t.state()")["opened"]
                page.click(f"[data-test=cell-{i}]")
                chorded = T(page, "t.state()")["opened"] > before
                break
    check(chorded, f"{label}: chord opened neighbours")
    check("mines left" in page.evaluate("__status"), f"{label}: status {page.evaluate('__status')}")
    no_hscroll(page, label)
    if mode == "full" and width in (400, 1280):
        shot(page, f"mines-{width}.png")
    T(page, "t.solve()")
    r = wait_result(page, 10)
    result_ok(page, r, label, min_score=2000)
    check("Cleared in" in r["detail"], f"{label}: detail")


def mines_paths(page):
    start(page, "mines", "full", seed=5)
    T(page, "t.safeReveal(4)")
    opened = T(page, "t.state()")["opened"]
    i = T(page, "t.solution().indexOf(1)")
    page.click(f"[data-test=cell-{i}]")
    r = wait_result(page, 5)
    result_ok(page, r, "mines/boom")
    check(r["score"] == 10 * opened and "Hit a mine" in r["detail"], f"mines/boom score {r['score']} vs {opened}")
    shot(page, "mines-boom-400.png") if page.viewport_size["width"] == 400 else None
    start(page, "mines", "mix", seed=6, speed=20)
    r = wait_result(page, 10)
    result_ok(page, r, "mines/timeout")
    check("Time up" in r["detail"] and r["score"] < 2000, "mines/timeout detail")


# ------------------------------------------------------------------ QUEENS
def queens_ui(page, mode, width):
    label = f"queens/{mode}/{width}"
    start(page, "queens", mode, seed=31)
    st = T(page, "t.state()")
    check(st["N"] == 6, f"{label}: first grid 6x6")
    sol = T(page, "t.solution()")
    # conflict: two crowns in the same row
    a = sol[0]; b = (a // 6) * 6 + ((a % 6) + 3) % 6
    for _ in range(2): page.click(f"[data-test=cell-{a}]")
    for _ in range(2): page.click(f"[data-test=cell-{b}]")
    st = T(page, "t.state()")
    check(set(st["conflicts"]) == {a, b}, f"{label}: conflicts {st['conflicts']}")
    check("bad" in page.get_attribute(f"[data-test=cell-{b}]", "class"), f"{label}: conflict highlighted")
    page.click(f"[data-test=cell-{b}]")  # crown -> empty
    check(T(page, "t.state()")["marks"][b] == 0, f"{label}: tap cycles crown -> empty")
    x = next(i for i in range(36) if i not in sol)
    page.click(f"[data-test=cell-{x}]")
    check(T(page, "t.state()")["marks"][x] == 1, f"{label}: tap -> X mark")
    if width in (400, 1280) and mode == "full":
        shot(page, f"queens-{width}.png")
    # solve the rest by real clicks
    for i in sol[1:]:
        page.click(f"[data-test=cell-{i}]"); page.click(f"[data-test=cell-{i}]")
    no_hscroll(page, label)
    if mode == "mix":
        r = wait_result(page, 5)
        result_ok(page, r, label, min_score=1000)
        return
    page.wait_for_function("window.__handle.ctx.test.state().solved === 1 && !window.__handle.ctx.test.state().busy", timeout=5000)
    check(T(page, "t.state()")["N"] == 7, f"{label}: next grid is 7x7")
    for k in range(3):
        page.wait_for_function("!window.__handle.ctx.test.state().busy", timeout=5000)
        T(page, "t.solve()")
        page.wait_for_timeout(50)
    page.wait_for_function("!window.__handle.ctx.test.state().busy", timeout=5000)
    check(T(page, "t.state()")["solved"] == 4, f"{label}: 4 solved")
    page.evaluate("window.__handle.ctx.speed")  # noop
    r = wait_result(page, 100)
    result_ok(page, r, label, min_score=4000)
    check("4 grids solved" in r["detail"], f"{label}: detail {strip(r['detail'])}")


def queens_paths(page):
    start(page, "queens", "mix", seed=8, speed=20)
    r = wait_result(page, 10)
    result_ok(page, r, "queens/timeout")
    check(r["score"] == 0, "queens/timeout score 0")
    # partial credit: 2 right crowns + 1 wrong crown on an unsolved grid -> (2 - 1) x 100
    start(page, "queens", "mix", seed=8, speed=4)
    sol = T(page, "t.solution()")
    for i in sol[:2]:
        page.click(f"[data-test=cell-{i}]"); page.click(f"[data-test=cell-{i}]")
    check(page.evaluate("__progress")[-1] == 200, f"queens/partial progress {page.evaluate('__progress')[-3:]}")
    wrong = next(i for i in range(36) if i not in sol and i // 6 >= 4 and all(abs(i // 6 - j // 6) > 1 or abs(i % 6 - j % 6) > 1 for j in sol[:2]))
    page.click(f"[data-test=cell-{wrong}]"); page.click(f"[data-test=cell-{wrong}]")
    r = wait_result(page, 20)
    result_ok(page, r, "queens/partial")
    check(r["score"] == 100, f"queens/partial score {r['score']} (want 100)")
    start(page, "queens", "full", seed=9, speed=6)
    T(page, "t.solve()")
    r = wait_result(page, 30)
    result_ok(page, r, "queens/full-1-then-timeout")
    check(r["score"] > 1000 and r["score"] < 2000, f"queens/full one solved {r['score']}")


# ------------------------------------------------------------------ 2048
def tiles_ui(page, mode, width):
    label = f"tiles2048/{mode}/{width}"
    start(page, "tiles2048", mode, seed=41)
    b0 = T(page, "t.state()")["board"]
    moves = []
    for k in ["ArrowLeft", "ArrowUp", "a", "ArrowRight", "s", "ArrowDown"]:
        before = T(page, "t.state()")["moves"]
        page.keyboard.press(k)
        page.wait_for_timeout(140)
        if T(page, "t.state()")["moves"] > before:
            moves.append({"ArrowLeft": 3, "a": 3, "ArrowUp": 0, "ArrowRight": 1, "s": 2, "ArrowDown": 2}[k])
    # swipe via pointer drag (left)
    bb = page.locator("[data-test=board]").bounding_box()
    cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    for dx, dy, d in [(-120, 0, 3), (0, -120, 0), (120, 0, 1)]:
        before = T(page, "t.state()")["moves"]
        page.mouse.move(cx, cy); page.mouse.down(); page.mouse.move(cx + dx, cy + dy, steps=4); page.mouse.up()
        page.wait_for_timeout(140)
        if T(page, "t.state()")["moves"] > before:
            moves.append(d)
    check(len(moves) >= 4, f"{label}: UI moves applied {moves}")
    st = T(page, "t.state()")
    sim = page.evaluate(f"DG.getGame('tiles2048').lab.sim(41, {json.dumps(moves)})")
    check(sim["board"] == st["board"] and sim["score"] == st["score"], f"{label}: seeded replay matches UI board")
    ntiles = T(page, "t.tiles()")
    check(ntiles == sum(1 for v in st["board"] if v), f"{label}: DOM tiles {ntiles} match board")
    no_hscroll(page, label)
    if mode == "full" and width in (400, 1280):
        T(page, "(() => { for (let i = 0; i < 40; i++) t.move(t.best()); })()")
        page.wait_for_timeout(250)
        shot(page, f"tiles2048-{width}.png")
    T(page, "t.solve()")
    r = wait_result(page, 10)
    result_ok(page, r, label, min_score=100)
    check("No moves left" in r["detail"], f"{label}: game-over detail")


def tiles_paths(page):
    start(page, "tiles2048", "mix", seed=42, speed=20)
    T(page, "t.move('left')"); T(page, "t.move('up')")
    r = wait_result(page, 10)
    result_ok(page, r, "tiles2048/timeout")
    check("Time up" in r["detail"], "tiles2048/timeout detail")


# ------------------------------------------------------------------ MEMORY
def mem_wait_input(page, timeout=8000):
    page.wait_for_function("window.__handle.ctx.test.state().phase === 'input' || window.__handle.ctx.test.state().done", timeout=timeout)


def memory_ui(page, mode, width):
    label = f"memory/{mode}/{width}"
    start(page, "memory", mode, seed=51, speed=3)
    for lvl in range(1, 4):
        mem_wait_input(page)
        seq = T(page, "t.sequence()")
        check(len(seq) == lvl + 2, f"{label}: level {lvl} length {len(seq)}")
        for c in seq:
            page.click(f"[data-test=cell-{c}]")
        if lvl == 2 and width in (400, 1280) and mode == "full":
            page.wait_for_function("window.__handle.ctx.test.state().phase === 'show'", timeout=5000)
            page.wait_for_selector(".g-memory-cell.lit", timeout=3000)
            shot(page, f"memory-{width}.png")
    mem_wait_input(page)
    st = T(page, "t.state()")
    check(st["longest"] == 5 and st["level"] == 4, f"{label}: 3 levels cleared {st}")
    check("Level 4" in page.evaluate("__status"), f"{label}: status {page.evaluate('__status')}")
    no_hscroll(page, label)
    if mode == "full":
        # hook-solve up to level 9 to reach the 4x4 grid, then fail through the UI
        for _ in range(5):
            mem_wait_input(page, 15000)
            T(page, "t.solve()")
        mem_wait_input(page, 15000)
        st = T(page, "t.state()")
        check(st["level"] == 9 and st["grid"] == 4, f"{label}: level 9 grid 4x4 {st}")
    seq = T(page, "t.sequence()"); g = T(page, "t.state()")["grid"]
    page.click(f"[data-test=cell-{(seq[0] + 1) % (g * g)}]")
    r = wait_result(page, 5)
    result_ok(page, r, label, min_score=500)
    check("Missed on level" in r["detail"], f"{label}: detail")


def memory_paths(page):
    # the sequence is seeded: same seed -> same sequence, 3x3 part stays in 3x3
    s1 = page.evaluate("DG.getGame('memory').lab.sequence(77, 30)")
    s2 = page.evaluate("DG.getGame('memory').lab.sequence(77, 30)")
    s3 = page.evaluate("DG.getGame('memory').lab.sequence(78, 30)")
    check(s1 == s2 and s1 != s3, "memory: seeded sequence")
    check(all(r < 3 and c < 3 for r, c in s1[:10]), "memory: first 10 steps in 3x3")
    # mix cap: keep solving until the 45 s cap ends it
    start(page, "memory", "mix", seed=52, speed=12)
    t0 = time.time()
    while not page.evaluate("__result") and time.time() - t0 < 20:
        try:
            T(page, "t.solve()")
        except Exception:
            pass
        page.wait_for_timeout(40)
    r = wait_result(page, 5)
    result_ok(page, r, "memory/mix-cap")
    check("Time cap" in r["detail"], f"memory/mix-cap detail {strip(r['detail'])}")


# ------------------------------------------------------------------ shared checks
def abort_check(page, game, mode):
    label = f"{game}/abort/{mode}"
    start(page, game, mode, seed=61, speed=4)
    page.wait_for_timeout(700)
    if game == "sudoku":
        T(page, "(t.select(t.puzzle().indexOf(0)), t.place(t.solution()[t.puzzle().indexOf(0)]))")
    elif game == "mines":
        T(page, "t.safeReveal(2)")
    elif game == "tiles2048":
        T(page, "t.move(3)")
    page.evaluate("window.__handle.abort()")
    s1 = page.evaluate("__status"); p1 = len(page.evaluate("__progress"))
    # input after abort must be ignored
    page.keyboard.press("ArrowLeft"); page.keyboard.press("5")
    page.wait_for_timeout(1500)
    check(page.evaluate("__result") is None, f"{label}: ctx.end called after abort")
    check(page.evaluate("__status") == s1, f"{label}: status still updating after abort")
    check(len(page.evaluate("__progress")) == p1, f"{label}: progress after abort")
    check(not errors(page), f"{label}: errors {errors(page)}")


def scroll_keys():
    """PageUp/PageDown/Home/End/Space must not scroll the page while a board is shown (text inputs exempt,
    Space on a focused button still activates it)."""
    print("[scroll keys]")
    with browser_page(width=400, height=420) as page:
        open_harness(page, FILES)
        for g, cell in [("sudoku", "cell-10"), ("mines", "cell-0"), ("queens", "cell-3"), ("tiles2048", "board"), ("memory", "cell-0")]:
            start(page, g, "full", seed=81)
            page.wait_for_timeout(150)
            check(page.evaluate("document.documentElement.scrollHeight > window.innerHeight + 50"), f"{g}: page is scrollable for the test")
            page.evaluate("window.scrollTo(0, 60)")
            page.focus(f"[data-test={cell}]")
            y0 = page.evaluate("window.scrollY")
            for k in ("PageDown", "End", "PageUp", "Home", "PageDown"):
                page.keyboard.press(k)
            page.evaluate("document.activeElement.blur()")
            page.keyboard.press("Space")
            page.wait_for_timeout(250)
            y1 = page.evaluate("window.scrollY")
            check(y1 == y0, f"{g}: scroll keys moved the page {y0} -> {y1}")
            if g == "queens":
                page.focus("[data-test=cell-3]")
                before = T(page, "t.state()")["marks"][3]
                page.keyboard.press("Space")
                page.wait_for_timeout(50)
                check(T(page, "t.state()")["marks"][3] == (before + 1) % 3, "queens: Space on a focused cell still taps it")
            # text inputs keep their keys
            prevented = page.evaluate("""(() => { const i = document.createElement('input'); document.body.appendChild(i); i.focus();
              const ev = new KeyboardEvent('keydown', {key: 'End', bubbles: true, cancelable: true}); i.dispatchEvent(ev);
              const ev2 = new KeyboardEvent('keydown', {key: ' ', bubbles: true, cancelable: true}); i.dispatchEvent(ev2);
              i.remove(); return ev.defaultPrevented || ev2.defaultPrevented; })()""")
            check(not prevented, f"{g}: keys blocked inside a text input")
            page.evaluate("window.__handle.abort()")
            # after the match ends/aborts the page scrolls normally again
            page.evaluate("window.scrollTo(0, 0)")
            page.keyboard.press("PageDown"); page.wait_for_timeout(250)
            check(page.evaluate("window.scrollY") > 0, f"{g}: blocker still active after abort")
            print(f"  {g}: page stayed at y={y1}")
        check(not errors(page), f"scroll keys: errors {errors(page)}")


def uniqueness_and_speed(page):
    print("[generators]")
    res = page.evaluate("""(() => {
      const S = DG.getGame('sudoku').lab, Q = DG.getGame('queens').lab, M = DG.getGame('mines').lab;
      const out = {sud: [], sudMix: [], q: [], mines: [], same: true, diff: true};
      for (let s = 1; s <= 30; s++) {
        const tf = S.genTime(1000 + s, 'full'), tm = S.genTime(1000 + s, 'mix');
        const P = S.generate(1000 + s, 'full'), Pm = S.generate(1000 + s, 'mix');
        const okSol = P.puzzle.every((v, i) => !v || v === P.solution[i]);
        out.sud.push({t: tf, n: S.count(P.puzzle, 'full', 2), givens: P.givens, okSol});
        out.sudMix.push({t: tm, n: S.count(Pm.puzzle, 'mix', 2), givens: Pm.givens});
        for (const [k, n] of [[0, 6], [1, 7], [2, 8]]) {
          const t = Q.genTime(1000 + s, k, n), G = Q.generate(1000 + s, k, n);
          const regs = new Set(G.reg).size;
          out.q.push({n, t, cnt: Q.count(n, G.reg, 2), regs});
        }
        out.mines.push({t: M.genTime(1000 + s, 'full'), solvable: M.generate(1000 + s, 'full').solvable});
      }
      const a = S.generate(5, 'full'), b = S.generate(5, 'full'), c = S.generate(6, 'full');
      out.same = JSON.stringify(a.puzzle) === JSON.stringify(b.puzzle) && JSON.stringify(Q.generate(5,0,6)) === JSON.stringify(Q.generate(5,0,6));
      out.diff = JSON.stringify(a.puzzle) !== JSON.stringify(c.puzzle);
      return out;
    })()""")
    sud = res["sud"]
    check(all(x["n"] == 1 for x in sud), "sudoku: every 9x9 puzzle unique")
    check(all(x["okSol"] for x in sud), "sudoku: givens match solution")
    check(all(30 <= x["givens"] <= 36 for x in sud), f"sudoku givens {[x['givens'] for x in sud]}")
    check(all(x["n"] == 1 for x in res["sudMix"]), "sudoku: every 6x6 puzzle unique")
    check(max(x["t"] for x in sud) < 300, "sudoku: generation < 300 ms")
    print(f"  sudoku 9x9: 30/30 unique, givens {min(x['givens'] for x in sud)}-{max(x['givens'] for x in sud)}, "
          f"gen avg {statistics.mean(x['t'] for x in sud):.1f} ms max {max(x['t'] for x in sud):.1f} ms; "
          f"6x6: unique {sum(x['n'] == 1 for x in res['sudMix'])}/30, max {max(x['t'] for x in res['sudMix']):.1f} ms")
    q = res["q"]
    check(all(x["cnt"] == 1 for x in q), "queens: every puzzle unique")
    check(all(x["regs"] == x["n"] for x in q), "queens: N regions")
    check(max(x["t"] for x in q) < 400, "queens: generation < 400 ms")
    for n in (6, 7, 8):
        ts = [x["t"] for x in q if x["n"] == n]
        print(f"  queens {n}x{n}: 30/30 unique, gen avg {statistics.mean(ts):.1f} ms max {max(ts):.1f} ms")
    m = res["mines"]
    check(all(x["solvable"] for x in m), "mines: boards solvable without guessing")
    print(f"  mines 12x12: no-guess solvable {sum(x['solvable'] for x in m)}/30, gen max {max(x['t'] for x in m):.1f} ms")
    check(res["same"] and res["diff"], "same seed -> identical puzzle; different seed -> different")
    # in-page: two matches with the same seed show the same content
    for g, js in [("sudoku", "t.puzzle()"), ("mines", "t.solution()"), ("queens", "t.regions()"), ("tiles2048", "t.state().board")]:
        start(page, g, "full", seed=99); a = T(page, js); page.evaluate("window.__handle.abort()")
        start(page, g, "full", seed=99); b = T(page, js); page.evaluate("window.__handle.abort()")
        check(a == b, f"{g}: same seed -> same content in play()")


def bots(page):
    print("[bots] median [p10..p90] over 20 seeds; human = noiseless simulation of solid play")
    data = page.evaluate("""(() => {
      const out = {};
      for (const id of %s) {
        const g = DG.getGame(id);
        out[id] = {};
        for (const mode of ['full', 'mix']) {
          const r = {det: true, tl: true, maxMs: 0, sk: {}, human: []};
          for (const sk of [0.1, 0.5, 0.9]) {
            const sc = [];
            for (let s = 1; s <= 20; s++) {
              const t0 = performance.now();
              const a = g.bot(s, sk, DG.util.rng('bot' + s), mode);
              r.maxMs = Math.max(r.maxMs, performance.now() - t0);
              const b = g.bot(s, sk, DG.util.rng('bot' + s), mode);
              if (JSON.stringify(a) !== JSON.stringify(b)) r.det = false;
              const tl = a.timeline;
              if (!tl.length || tl[tl.length - 1][1] !== a.score) r.tl = false;
              for (let i = 1; i < tl.length; i++) if (tl[i][0] < tl[i - 1][0]) r.tl = false;
              if (tl[tl.length - 1][0] > (mode === 'mix' ? 45.01 : 360.01)) r.tl = false;
              sc.push(a.score);
            }
            r.sk[sk] = sc;
          }
          for (let s = 1; s <= 20; s++) r.human.push(g.lab.human(s, mode).score);
          out[id][mode] = r;
        }
      }
      return out;
    })()""" % json.dumps(GAMES))
    q = lambda a, p: sorted(a)[min(len(a) - 1, int(p * len(a)))]
    print(f"  {'game':10} {'mode':4} | {'skill 0.1':>18} | {'skill 0.5':>18} | {'skill 0.9':>18} | {'human':>6} | beats 0.5 / 0.9")
    for g in GAMES:
        for mode in ("full", "mix"):
            r = data[g][mode]
            check(r["det"], f"{g}/{mode}: bot deterministic")
            check(r["tl"], f"{g}/{mode}: timeline ascending, ends at score, within limit")
            check(r["maxMs"] < 50, f"{g}/{mode}: bot {r['maxMs']:.1f} ms")
            cells = []
            for sk in ("0.1", "0.5", "0.9"):
                a = r["sk"][sk]
                cells.append(f"{int(statistics.median(a)):>5} [{q(a, .1)}..{q(a, .9)}]")
            h = r["human"]
            w5 = sum(1 for i in range(20) if h[i] > r["sk"]["0.5"][i]) / 20
            w9 = sum(1 for i in range(20) if h[i] > r["sk"]["0.9"][i]) / 20
            print(f"  {g:10} {mode:4} | " + " | ".join(f"{c:>18}" for c in cells) +
                  f" | {int(statistics.median(h)):>6} | {w5:.0%} / {w9:.0%}")
            m1, m5, m9 = (statistics.median(r["sk"][k]) for k in ("0.1", "0.5", "0.9"))
            check(m1 <= m5 <= m9 and m1 < m9, f"{g}/{mode}: bot score grows with skill {m1} {m5} {m9}")
            check(w5 >= 0.6, f"{g}/{mode}: human beats 0.5 bot {w5:.0%}")
            check(0.02 <= w9 <= 0.8, f"{g}/{mode}: human beats 0.9 bot sometimes {w9:.0%}")
            print(f"      max bot time {r['maxMs']:.1f} ms")
    # sudoku bot finish rate must climb gradually with skill (no cliff); queens mix must not be zero-heavy
    fr = page.evaluate("""(() => {
      const out = {};
      for (const mode of ['full', 'mix']) {
        out[mode] = {};
        for (const sk of [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]) {
          let fin = 0;
          for (let s = 1; s <= 50; s++) if (DG.getGame('sudoku').bot(s, sk, DG.util.rng('fr' + s), mode).timeline.some(p => p[1] >= 2500)) fin++;
          out[mode][sk] = fin / 50;
        }
      }
      out.qzeros = {};
      for (const sk of [0.1, 0.5]) { let z = 0; for (let s = 1; s <= 50; s++) if (DG.getGame('queens').bot(s, sk, DG.util.rng('z' + s), 'mix').score === 0) z++; out.qzeros[sk] = z; }
      return out;
    })()""")
    for mode in ("full", "mix"):
        f = fr[mode]
        print(f"  sudoku {mode} bot finish rate: " + "  ".join(f"{k}:{v:.0%}" for k, v in f.items()))
        check(f["0.2"] <= 0.25 and 0.4 <= f["0.5"] <= 0.7 and f["0.8"] >= 0.8, f"sudoku/{mode}: finish-rate targets {f}")
        steps = [f[k] for k in ("0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8")]
        check(max(b - a for a, b in zip(steps, steps[1:])) <= 0.35, f"sudoku/{mode}: finish-rate jump too steep {steps}")
    print(f"  queens mix zeros /50: {fr['qzeros']}")
    check(fr["qzeros"]["0.1"] <= 5 and fr["qzeros"]["0.5"] <= 2, f"queens mix zero-heavy {fr['qzeros']}")


def registry(page):
    games = {g["id"]: g for g in page.evaluate("__games()")}
    for gid in GAMES:
        g = games.get(gid)
        if check(g is not None, f"{gid} registered"):
            check(g["kind"] == "race" and g["pack"] == "brain" and g["hasBot"], f"{gid}: race/brain/bot")
            check(g["formats"] == ["1v1", "2v2", "ffa", "tournament", "mix"], f"{gid}: formats")


def run():
    t0 = time.time()
    for width in (400, 1280):
        print(f"=== width {width}")
        with browser_page(width=width, height=900) as page:
            open_harness(page, FILES)
            if width == 400:
                registry(page)
                uniqueness_and_speed(page)
            for fn, name in [(sudoku_ui, "sudoku"), (mines_ui, "mines"), (queens_ui, "queens"), (tiles_ui, "tiles2048"), (memory_ui, "memory")]:
                for mode in ("full", "mix"):
                    try:
                        fn(page, mode, width)
                    except Exception as e:
                        check(False, f"{name}/{mode}/{width}: exception {e}")
                        traceback.print_exc()
            if width == 400:
                for fn in (sudoku_paths, mines_paths, queens_paths, tiles_paths, memory_paths):
                    try:
                        fn(page)
                    except Exception as e:
                        check(False, f"{fn.__name__}: exception {e}")
                        traceback.print_exc()
                for g in GAMES:
                    for mode in ("full", "mix"):
                        abort_check(page, g, mode)
                bots(page)
    scroll_keys()
    print("=== width 360 (no horizontal scroll)")
    with browser_page(width=360, height=780, touch=True) as page:
        open_harness(page, FILES)
        for g in GAMES:
            for mode in ("full", "mix"):
                start(page, g, mode, seed=71)
                page.wait_for_timeout(300)
                no_hscroll(page, f"{g}/{mode}/360")
                # tap targets >= 36 px for the main controls
                small = page.evaluate("""(() => [...document.querySelectorAll('#root button')].filter(b => {
                    const r = b.getBoundingClientRect(); return r.width > 0 && (r.width < 30 || r.height < 30); }).length)()""")
                if g == "sudoku":
                    check(not page.is_visible("[data-test=hint-keys]"), f"sudoku/{mode}/360 touch: keyboard hint hidden")
                if g in ("queens",):
                    clipped = page.evaluate("""[...document.querySelectorAll('.g-queens-stat b')].filter(b => b.scrollWidth > b.clientWidth + 1).length""")
                    check(clipped == 0, f"queens/{mode}/360: {clipped} HUD values clipped")
                if g == "sudoku":
                    key = page.locator("[data-test=num-1]").bounding_box()
                    check(key["height"] >= 44 and key["width"] >= 36, f"sudoku/{mode}/360 pad key {key}")
                    board = page.locator("[data-test=board]").bounding_box()
                    check(key["y"] > board["y"] + board["height"] - 1, "sudoku/360: pad below board")
                if g in ("queens", "memory", "tiles2048") or (g == "mines" and mode == "mix"):
                    check(small == 0, f"{g}/{mode}/360: {small} buttons under 30 px")
                page.evaluate("window.__handle.abort()")
        start(page, "sudoku", "mix", seed=71)
        shot(page, "sudoku-360.png")
        page.evaluate("window.__handle.abort()")
        start(page, "mines", "full", seed=71)
        shot(page, "mines-360.png")
        page.evaluate("window.__handle.abort()")
        check(not errors(page), f"360: errors {errors(page)}")
    print(f"--- {len(FAILS)} failure(s) in {time.time() - t0:.0f} s")
    for f in FAILS:
        print("  -", f)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(run())
