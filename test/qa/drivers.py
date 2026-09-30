"""Per-game UI drivers: prove real input works inside the overlay, then finish via ctx.test hooks."""
import time, math
from qalib import T, shot

def tap(page, sel, touch):
    loc = page.locator(sel).first
    loc.scroll_into_view_if_needed()
    if touch: loc.tap()
    else: loc.click()

def ptap(page, x, y, touch):
    if touch: page.touchscreen.tap(x, y)
    else: page.mouse.click(x, y)

def touch_drag(page, pts, hold_ms=0):
    cdp = page.context.new_cdp_session(page)
    x, y = pts[0]
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
    if hold_ms: page.wait_for_timeout(hold_ms)
    for (x, y) in pts[1:]:
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y}]})
        page.wait_for_timeout(30)
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})

def ended(page):
    return page.evaluate("!DGApp.ctx() || DGApp.ctx().signal.ended")

def wait_until(page, js, timeout=10):
    page.wait_for_function(js, timeout=timeout * 1000)

HUMAN_TURN = "(() => { const t = DGApp.ctx() && DGApp.ctx().test; return !t || DGApp.ctx().signal.ended || (t.legalMoves && t.legalMoves().length > 0); })()"

def d_chess(page, touch):
    wait_until(page, HUMAN_TURN, 15)
    T(page, "t.freezeClocks()")
    ms = T(page, "t.legalMoves()")
    m = next((m for m in ms if m['piece'] == 'p'), ms[0])
    n0 = len(T(page, "t.state().sans"))
    tap(page, f"[data-test=sq-{m['from']}]", touch); tap(page, f"[data-test=sq-{m['to']}]", touch)
    page.wait_for_timeout(100)
    ok = len(T(page, "t.state().sans")) > n0
    T(page, "t.autoplay(0.98)")
    return ok, f"clicked {m['from']}-{m['to']}"

def _turn(page, touch, selfn, key=None):
    wait_until(page, HUMAN_TURN, 15)
    T(page, "t.freezeTimer()")
    ms = T(page, "t.legalMoves()")
    m = ms[len(ms) // 2]
    s0 = T(page, "JSON.stringify(t.state())")
    if key:
        page.keyboard.press(str(m + 1)); how = f"key {m+1}"
    else:
        tap(page, selfn(m), touch); how = f"tap {selfn(m)}"
    page.wait_for_timeout(150)
    ok = T(page, "JSON.stringify(t.state())") != s0
    T(page, "t.autoplay(0.98)")
    return ok, how

def d_four(page, touch): return _turn(page, touch, lambda m: f"[data-test=col-{m}]")
def d_reversi(page, touch): return _turn(page, touch, lambda m: f"[data-test=sq-{m}]")
def d_gomoku(page, touch): return _turn(page, touch, lambda m: f"[data-test=pt-{m}]")

def d_sudoku(page, touch):
    sol = T(page, "t.solution()"); pz = T(page, "t.puzzle()")
    empt = [i for i, v in enumerate(pz) if not v][:2]
    for i in empt:
        tap(page, f"[data-test=cell-{i}]", touch); tap(page, f"[data-test=num-{sol[i]}]", touch)
    vals = T(page, "t.state().values")
    ok = all(vals[i] == sol[i] for i in empt)
    T(page, "t.solve()")
    return ok, "tapped 2 cells+digits"

def d_mines(page, touch):
    st = T(page, "t.state()"); mine = T(page, "t.solution()")
    i = next(i for i in range(len(mine)) if not mine[i] and not st['open'][i])
    tap(page, f"[data-test=cell-{i}]", touch)
    ok = T(page, "t.state().opened") > st['opened']
    T(page, "t.solve()")
    return ok, f"revealed cell {i}"

def d_queens(page, touch):
    tap(page, "[data-test=cell-0]", touch)
    ok = T(page, "t.state().marks[0]") == 1
    tap(page, "[data-test=cell-0]", touch)  # -> crown? then solve clears
    T(page, "t.solve()")
    # queens may have more puzzles; solve repeatedly
    for _ in range(20):
        if ended(page): break
        page.wait_for_timeout(300)
        T(page, "t.solve()")
    return ok, "tapped cell marks"

def d_tiles2048(page, touch):
    if touch:
        bb = page.locator("[data-test=board]").bounding_box()
        cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
        m0 = T(page, "t.state().moves")
        for dx, dy in [(-120, 0), (0, -120), (120, 0), (0, 120)]:
            touch_drag(page, [(cx, cy), (cx + dx / 2, cy + dy / 2), (cx + dx, cy + dy)])
            page.wait_for_timeout(150)
        ok = T(page, "t.state().moves") > m0; how = "touch swipes"
    else:
        m0 = T(page, "t.state().moves")
        for k in ["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"]:
            page.keyboard.press(k); page.wait_for_timeout(120)
        ok = T(page, "t.state().moves") > m0; how = "arrow keys"
    T(page, "t.solve()")
    return ok, how

def d_memory(page, touch):
    wait_until(page, "DGApp.ctx().test.state().phase === 'input'", 15)
    seq = T(page, "t.sequence()")
    for c in seq: tap(page, f"[data-test=cell-{c}]", touch)
    page.wait_for_timeout(100)
    ok = T(page, "t.state().longest") >= len(seq)
    wait_until(page, "DGApp.ctx().test.state().phase === 'input'", 15)
    T(page, "t.mistake()")
    return ok, f"tapped sequence of {len(seq)}"

def d_reaction(page, touch):
    # arm by tap, then tap on go
    tap(page, "[data-test=pad]", touch)
    wait_until(page, "document.querySelector('[data-test=pad]').dataset.state === 'go'", 8)
    tap(page, "[data-test=pad]", touch)
    page.wait_for_timeout(50)
    r = T(page, "t.state().results")
    ok = len(r) == 1 and r[0].get('ms') is not None
    for _ in range(10):
        if ended(page): break
        page.wait_for_timeout(50)
        T(page, "t.fire(250)")
    return ok, f"tap reaction {r[0] if r else None}"

def d_aim(page, touch):
    hits = 0
    t_end = time.time() + 8
    while time.time() < t_end and hits < 2 and not ended(page):
        al = T(page, "t.alive()")
        if al:
            a = al[0]; ptap(page, a['cx'], a['cy'], touch); page.wait_for_timeout(60)
            hits = T(page, "t.state().hits")
        else: page.wait_for_timeout(50)
    ok = hits >= 1
    # finish: keep hitting via hooks until end
    for _ in range(600):
        if ended(page): break
        T(page, "t.hitNext()"); page.wait_for_timeout(30)
    return ok, f"canvas taps hit {hits}"

def d_rush(page, touch):
    c = T(page, "t.state().current.correct")
    if touch: tap(page, f"[data-test=opt-{c}]", touch); how = "tap option"
    else: page.keyboard.press(str(c + 1)); how = f"key {c+1}"
    page.wait_for_timeout(80)
    ok = T(page, "t.state().right") == 1
    for _ in range(800):
        if ended(page): break
        T(page, "t.answerCorrect()"); page.wait_for_timeout(15)
    return ok, how

def d_darts(page, touch):
    wait_until(page, "DGApp.ctx().test.state().phase === 'aim'", 8)
    p = T(page, "t.boardToClient(0, 103)")
    if touch:
        touch_drag(page, [(p['x'], p['y']), (p['x'] + 1, p['y'])], hold_ms=300); how = "touch hold+release"
    else:
        page.mouse.move(p['x'], p['y']); page.mouse.down(); page.wait_for_timeout(300); page.mouse.up(); how = "mouse hold+release"
    page.wait_for_timeout(80)
    ok = len(T(page, "t.state().thrown")) == 1
    for _ in range(400):
        if ended(page): break
        T(page, "t.throwAt(0, 0)"); page.wait_for_timeout(40)
    return ok, how

def d_hockey(page, touch):
    page.wait_for_timeout(300)
    p0 = T(page, "t.state().pads[0]")
    a = T(page, "t.physToClient(90, 420)"); b = T(page, "t.physToClient(220, 330)")
    if touch: touch_drag(page, [(a['x'], a['y']), (b['x'], b['y']), (a['x'], a['y'])]); how = "touch drag paddle"
    else:
        page.mouse.move(a['x'], a['y'], steps=4); page.mouse.move(b['x'], b['y'], steps=4); how = "mouse move paddle"
    page.wait_for_timeout(150)
    p1 = T(page, "t.state().pads[0]")
    ok = abs(p1['x'] - p0['x']) + abs(p1['y'] - p0['y']) > 5
    for _ in range(5):
        if ended(page): break
        T(page, "t.forceGoal('me')"); page.wait_for_timeout(40)
    return ok, how

def d_base(page, touch):
    tap(page, "[data-test=tool-arrow]", touch)
    legal = T(page, "t.legal('arrow')")
    n0 = T(page, "t.state().structs.length")
    for (x, y) in legal[len(legal)//3: len(legal)//3 + 3]:
        pt = T(page, f"t.tilePoint({x},{y})")
        ptap(page, pt['x'], pt['y'], touch)
        if touch: page.wait_for_timeout(60); ptap(page, pt['x'], pt['y'], touch)  # tap-to-confirm
        page.wait_for_timeout(60)
        if T(page, "t.state().structs.length") > n0: break
    ok = T(page, "t.state().structs.length") > n0
    T(page, "t.placeAI(0.9)")
    T(page, "t.fastForward()")
    return ok, "tap tool + map tile"

def d_city(page, touch):
    st = T(page, "t.state()")
    free = [i for i, t in enumerate(st['tiles']) if t == 0]
    tap(page, "[data-test=tool-res]", touch)
    tap(page, f"[data-test=tile-{free[0]}]", touch)
    if touch and T(page, f"t.state().plan[{free[0]}]") is None: tap(page, f"[data-test=tile-{free[0]}]", touch)
    ok = T(page, f"t.state().plan[{free[0]}]") == 'res'
    T(page, "t.autoBuild(0.9)")
    tap(page, "[data-test=finish]", touch)
    return ok, "tool + tile tap, Finish button"

def d_restaurant(page, touch):
    t0 = T(page, "t.state().plan.tables")
    tap(page, "[data-test=tables-inc]", touch)
    ok = T(page, "t.state().plan.tables") == t0 + 1
    T(page, "t.optimise(0.9)")
    tap(page, "[data-test=open]", touch)
    return ok, "tables +, Open button"

def d_trivia(page, touch):
    wait_until(page, "DGApp.ctx().test.state().phase === 'ask'", 8)
    a = T(page, "t.state().ans")
    if touch: tap(page, f"[data-test=tv-opt][data-i='{a}']", touch); how = "tap answer"
    else: page.keyboard.press(str(a + 1)); how = f"key {a+1}"
    page.wait_for_timeout(80)
    ok = T(page, "t.state().correct") == 1
    for _ in range(600):
        if ended(page): break
        T(page, "t.answerCorrect()"); page.wait_for_timeout(40)
    return ok, how

def d_groups(page, touch):
    sol = T(page, "t.solution()")
    for w in sol[0]['words']: tap(page, f"[data-test=wg-tile][data-w=\"{w}\"]", touch)
    tap(page, "[data-test=wg-submit]", touch)
    page.wait_for_timeout(100)
    ok = 0 in T(page, "t.state().found")
    for i in range(1, 4): T(page, f"t.submitGroup({i})"); page.wait_for_timeout(50)
    return ok, "tapped 4 tiles + submit"

def d_durak(page, touch):
    wait_until(page, "(() => { const t = DGApp.ctx().test; return DGApp.ctx().signal.ended || t.state().legal.some(m => m.c != null && (m.t==='attack'||m.t==='beat'||m.t==='throw')); })()", 20)
    lg = [m for m in T(page, "t.state().legal") if m.get('c') is not None]
    s0 = T(page, "JSON.stringify(t.state().table)")
    tap(page, f"[data-test=dk-card][data-c='{lg[0]['c']}']", touch)
    page.wait_for_timeout(100)
    ok = T(page, "JSON.stringify(t.state().table)") != s0 or T(page, "t.state().hands[0]") != None
    T(page, "t.autoplay()")
    return ok, f"tapped card {lg[0]}"

def d_liars(page, touch):
    wait_until(page, "!!document.querySelector('[data-test=ld-ctl]') || DGApp.ctx().signal.ended", 20)
    f = page.locator("[data-test=ld-face]:not([disabled])").first
    f.scroll_into_view_if_needed(); f.tap() if touch else f.click()
    b0 = T(page, "JSON.stringify(t.state().bid)")
    tap(page, "[data-test=ld-raise]", touch)
    page.wait_for_timeout(100)
    ok = T(page, "JSON.stringify(t.state().bid)") != b0
    T(page, "t.autoplay()")
    return ok, "face + bid"

def d_auction(page, touch):
    wait_until(page, "!!document.querySelector('[data-test=au-input]')", 10)
    page.fill("[data-test=au-input]", "1000")
    tap(page, "[data-test=au-bid]", touch)
    page.wait_for_timeout(200)
    ok = T(page, "t.state().phase") == 'result' or T(page, "t.state().round") > 0
    T(page, "t.autoplay()")
    return ok, "typed bid + Seal"

DRIVERS = {k[2:]: v for k, v in globals().items() if k.startswith('d_')}
SPEED = {'chess': 10, 'four': 6, 'reversi': 6, 'gomoku': 6, 'hockey': 3, 'durak': 8, 'liars': 8, 'auction': 8,
         'reaction': 1, 'aim': 3, 'rush': 2, 'darts': 2, 'memory': 3, 'tiles2048': 3, 'sudoku': 2, 'mines': 2, 'queens': 2,
         'base': 4, 'city': 3, 'restaurant': 3, 'trivia': 2, 'groups': 2}
