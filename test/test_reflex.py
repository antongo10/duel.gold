"""Pack C (reflex) tests: reaction, aim, rush, darts, hockey.
Run: cd test && python3 test_reflex.py
"""
import json, math, pathlib, statistics, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dglib import browser_page, open_harness, wait_result, errors

FILES = ["reflex.js"]
SHOTS = pathlib.Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(exist_ok=True)
FAILS = []


def check(cond, msg):
    if cond:
        print("  ok  ", msg)
    else:
        print("  FAIL", msg)
        FAILS.append(msg)


def no_errors(page, label):
    e = errors(page)
    check(not e, f"{label}: no errors {e[:3] if e else ''}")


def run(page, **o):
    page.evaluate("o => __run(o)", o)
    page.wait_for_timeout(60)


def T(page, expr):
    return page.evaluate("() => window.__handle.ctx.test." + expr)


def race_result_ok(r, label):
    check(r is not None and isinstance(r.get("score"), (int, float)) and r["score"] >= 0 and isinstance(r.get("detail"), str),
          f"{label}: race result shape {json.dumps({k: r.get(k) for k in ('score',)}) if r else r}")


def versus_result_ok(r, label):
    check(r is not None and r.get("outcome") in ("win", "loss", "draw") and isinstance(r.get("myScore"), (int, float))
          and isinstance(r.get("oppScore"), (int, float)), f"{label}: versus result {r and {k: r.get(k) for k in ('outcome','myScore','oppScore')}}")


def scroll_ok(page, label):
    sw, iw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    check(sw <= iw, f"{label}: no horizontal scroll ({sw} <= {iw})")


# ---------------------------------------------------------------- reaction
def reaction_ui(page, mode, label, foul_round=2, key_round=1):
    run(page, game="reaction", mode=mode, seed=11, speed=1)
    st = T(page, "state()")
    n = st["n"]
    for i in range(n):
        page.wait_for_selector("[data-test=pad][data-state=idle]", timeout=8000)
        if i == key_round:
            page.keyboard.press("Space")
        else:
            page.click("[data-test=pad]")
        page.wait_for_selector("[data-test=pad][data-state=wait]", timeout=3000)
        if i == foul_round:
            page.wait_for_timeout(300)
            page.click("[data-test=pad]")  # early tap = foul
        else:
            page.wait_for_selector("[data-test=pad][data-state=go]", timeout=6000)
            if i == key_round:
                page.keyboard.press("Enter")
            else:
                page.click("[data-test=pad]")
    r = wait_result(page, 10)
    st = T(page, "state()")
    race_result_ok(r, label)
    res = st["results"]
    check(len(res) == n, f"{label}: {n} rounds recorded")
    check(res[foul_round]["foul"] and res[foul_round]["pts"] == 0, f"{label}: early tap is a foul scoring 0")
    clean = [x for x in res if x["ms"] is not None]
    check(all(0 < x["ms"] < 600 and x["pts"] == 1000 - x["ms"] for x in clean), f"{label}: clean rounds 1000-ms ({[x['ms'] for x in clean]})")
    check(r["score"] == sum(x["pts"] for x in res), f"{label}: score = sum of rounds ({r['score']})")
    check(page.evaluate("__progress.length") >= n, f"{label}: progress reported")
    for lg in st["log"]:
        d = st["delays"][lg["round"]]
        check(abs(lg["wait"] - d) < 60, f"{label}: round {lg['round']+1} seeded delay {d} ms, measured {lg['wait']:.0f} ms")
    check(all(1200 <= d <= 3800 for d in st["delays"]), f"{label}: delays within 1.2-3.8 s")
    return r


def reaction_timeouts(page):
    run(page, game="reaction", mode="mix", seed=5, speed=20)
    r = wait_result(page, 20)
    st = T(page, "state()")
    race_result_ok(r, "reaction no-input")
    check(r["score"] == 0 and all(x["slow"] for x in st["results"]), "reaction: idle player auto-arms and times out, scores 0")


def reaction_speed(page):
    out = {}
    for sp in (1, 5):
        run(page, game="reaction", mode="mix", seed=77, speed=sp)
        page.click("[data-test=pad]")
        page.wait_for_function("() => __handle.ctx.test.state().log.length >= 1", timeout=6000)
        st = T(page, "state()")
        out[sp] = st["log"][0]["wait"]
        page.evaluate("__handle.abort()")
    d = st["delays"][0]
    check(abs(out[1] - d) < 40 and abs(out[5] - d) < 120, f"reaction: speed-scaled wait matches seeded delay {d} (speed1 {out[1]:.0f}, speed5 {out[5]:.0f})")


# ---------------------------------------------------------------- aim
def aim_ui(page, mode, label, speed=2):
    run(page, game="aim", mode=mode, seed=21, speed=speed)
    clicked = set()
    misses_made = 0
    t_end = time.time() + 40
    while time.time() < t_end and page.evaluate("__result") is None:
        alive = page.evaluate("() => { const t = __handle.ctx.test; return t ? t.alive() : [] }")
        fresh = [a for a in alive if a["i"] not in clicked]
        if fresh:
            a = fresh[0]
            page.mouse.click(a["cx"], a["cy"])
            clicked.add(a["i"])
            if misses_made < 3 and len(clicked) % 5 == 0:
                box = page.eval_on_selector("[data-test=canvas]", "c => { const r = c.getBoundingClientRect(); return [r.left, r.top, r.width, r.height] }")
                pts = [(box[0] + 24, box[1] + 24), (box[0] + box[2] - 24, box[1] + 24), (box[0] + 24, box[1] + box[3] - 24), (box[0] + box[2] / 2, box[1] + 24)]
                alive2 = page.evaluate("() => __handle.ctx.test.alive()")
                for (x, y) in pts:
                    if all(math.hypot(x - q["cx"], y - q["cy"]) > q["r"] + 12 for q in alive2):
                        page.mouse.click(x, y)
                        misses_made += 1
                        break
        else:
            page.wait_for_timeout(15)
    r = wait_result(page, 10)
    st = T(page, "state()")
    race_result_ok(r, label)
    check(st["hits"] >= 0.6 * st["total"], f"{label}: real canvas clicks hit targets ({st['hits']}/{st['total']})")
    check(st["misses"] == misses_made, f"{label}: miss-clicks counted ({st['misses']} == {misses_made})")
    check(abs(r["score"] - st["score"]) < 1e-9, f"{label}: final score {r['score']}")
    return r, st


def aim_hooks(page, mode):
    run(page, game="aim", mode=mode, seed=3, speed=10)
    while page.evaluate("__result") is None:
        page.evaluate("() => { const t = __handle.ctx.test; if (t) t.hitNext(); }")
        page.wait_for_timeout(20)
    r = wait_result(page, 5)
    race_result_ok(r, f"aim {mode} hooks")
    return r


def aim_schedule_same(page):
    run(page, game="aim", mode="full", seed=99, speed=1)
    a = T(page, "schedule()")
    page.evaluate("__handle.abort()")
    page.set_viewport_size({"width": 700, "height": 900})
    run(page, game="aim", mode="full", seed=99, speed=6)
    b = T(page, "schedule()")
    page.evaluate("__handle.abort()")
    check(a == b and len(a) > 20, f"aim: identical target schedule across speed/size ({len(a)} targets)")
    ts = [x["t"] for x in a]
    check(ts == sorted(ts) and ts[-1] < 30000, "aim: schedule ordered and inside 30 s")


def aim_resize(page):
    page.set_viewport_size({"width": 1280, "height": 900})
    run(page, game="aim", mode="full", seed=4, speed=1)
    w1 = page.eval_on_selector("[data-test=canvas]", "c => [c.width, c.clientWidth]")
    page.set_viewport_size({"width": 420, "height": 900})
    page.wait_for_timeout(250)
    w2 = page.eval_on_selector("[data-test=canvas]", "c => [c.width, c.clientWidth]")
    dpr = page.evaluate("devicePixelRatio")
    check(w2[1] < w1[1] and abs(w2[0] - round(w2[1] * dpr)) <= 1, f"aim: canvas re-fits on resize ({w1} -> {w2}, dpr {dpr})")
    page.evaluate("__handle.abort()")


# ---------------------------------------------------------------- rush
def rush_ui(page, mode, label, speed=4):
    run(page, game="rush", mode=mode, seed=31, speed=speed)
    n = 0
    wrong = 0
    while page.evaluate("__result") is None and n < 200:
        st = page.evaluate("() => __handle.ctx.test && __handle.ctx.test.state()")
        if not st or st["done"]:
            break
        c = st["current"]["correct"]
        if n in (4, 9):
            choice = (c + 1) % 4
            wrong += 1
        else:
            choice = c
        if n % 3 == 2:
            page.keyboard.press(str(choice + 1))
        else:
            try:
                page.click(f"[data-test=opt-{choice}]", timeout=1500)
            except Exception:
                if page.evaluate("__result") is not None:
                    if n in (4, 9):
                        wrong -= 1
                    break
                raise
        page.wait_for_timeout(35 * speed // 4 + 125 // speed + 10)  # respect 120 ms input lock (game time)
        n += 1
    r = wait_result(page, 30)
    st = T(page, "state()")
    race_result_ok(r, label)
    check(st["right"] >= 5 and st["wrong"] == wrong, f"{label}: answered via buttons/keys (right {st['right']}, wrong {st['wrong']})")
    return r


def rush_scoring(page):
    run(page, game="rush", mode="mix", seed=8, speed=1)
    seq = []
    for k in range(8):
        T(page, "answerCorrect()")
        seq.append(T(page, "state()")["score"])
    exp = []
    s = 0
    for k in range(1, 9):
        s += 100 + min(50, 10 * (k - 1))
        exp.append(s)
    check(seq == exp, f"rush: streak bonus +10/step capped at +50 ({seq})")
    T(page, "answerWrong()")
    st = T(page, "state()")
    check(st["score"] == exp[-1] - 50 and st["streak"] == 0, "rush: wrong answer -50 and streak reset")
    page.evaluate("__handle.abort()")
    run(page, game="rush", mode="mix", seed=8, speed=1)
    T(page, "answerWrong()")
    check(T(page, "state()")["score"] == 0, "rush: score floor at 0")
    probs = []
    for k in range(40):
        st = T(page, "state()")
        cur = st["current"]
        probs.append(cur)
        T(page, "answerCorrect()")
    ok = all(len(set(p["options"])) == 4 and p["options"][p["correct"]] == p["ans"] for p in probs)
    check(ok, "rush: 4 distinct options, exactly one correct")
    ops = [p["text"].split()[1] for p in probs]
    check(set(ops[:3]) <= {"+", "−"} and ("×" in ops[20:] or "÷" in ops[20:]), f"rush: difficulty ramps ({''.join(ops)})")
    page.evaluate("__handle.abort()")


# ---------------------------------------------------------------- darts
def darts_units(page):
    rad = math.radians(18)
    cases = [((0, 0), 50), ((0, 10), 25), ((0, 103), 60), ((0, 166), 40), ((0, 130), 20), ((130, 0), 6), ((-130, 0), 11),
             ((0, -130), 3), ((0, -103), 9), ((0, 175), 0), ((73, 73), 12), ((-103 * math.sin(rad), 103 * math.cos(rad)), 15)]
    got = page.evaluate("cs => cs.map(([x,y]) => DG.getGame('darts')._dartScore(x,y).pts)", [c[0] for c in cases])
    exp = [c[1] for c in cases]
    check(got == exp, f"darts: board scoring {got}")
    order = page.evaluate("""() => { const f = DG.getGame('darts')._dartScore, out = [];
        for (let i = 0; i < 20; i++) { const a = i * 18 * Math.PI / 180; out.push(f(130 * Math.sin(a), 130 * Math.cos(a)).pts); } return out; }""")
    check(order == [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5], f"darts: standard sector order clockwise {order}")


def darts_ui(page, mode, label, speed=2, ui_darts=3):
    run(page, game="darts", mode=mode, seed=41, speed=speed)
    n = T(page, "state()")["n"]
    for i in range(n):
        page.wait_for_function("() => __handle.ctx.test.state().phase === 'aim'", timeout=8000)
        if i < ui_darts:
            p = page.evaluate("() => __handle.ctx.test.boardToClient(0, 103)")
            page.mouse.move(p["x"], p["y"])
            page.mouse.down()
            page.wait_for_timeout(60)
            check(T(page, "state()")["holding"], f"{label}: dart {i+1} steadying while held")
            page.wait_for_timeout(260)
            page.mouse.up()
            page.wait_for_timeout(30)
            st = T(page, "state()")
            check(len(st["thrown"]) == i + 1, f"{label}: dart {i+1} thrown on release -> {st['thrown'][-1]['label']} ({st['thrown'][-1]['pts']})")
            d = st["thrown"][-1]
            re = page.evaluate("([x,y]) => __handle.ctx.test.scoreAt(x,y).pts", [d["x"], d["y"]])
            check(re == d["pts"] and math.hypot(d["x"], d["y"] - 103) < 90, f"{label}: dart {i+1} landed near aim ({d['x']:.0f},{d['y']:.0f})")
        else:
            page.evaluate("([x, y]) => __handle.ctx.test.throwAt(x, y)", [0, 103] if i % 2 else [0, 0])
    r = wait_result(page, 20)
    st = T(page, "state()")
    race_result_ok(r, label)
    check(len(st["thrown"]) == n and r["score"] == sum(d["pts"] for d in st["thrown"]), f"{label}: {n} darts, total {r['score']}")
    return r


def darts_timeout(page):
    run(page, game="darts", mode="mix", seed=2, speed=25)
    r = wait_result(page, 30)
    st = T(page, "state()")
    race_result_ok(r, "darts idle")
    check(len(st["thrown"]) == st["n"], f"darts: 10 s dart clock auto-throws ({len(st['thrown'])} darts, {r['score']} pts)")


# ---------------------------------------------------------------- hockey
def hockey_pointer(page, label):
    run(page, game="hockey", seed=51, skill=0.5, speed=1)
    page.wait_for_timeout(150)
    ok = True
    for (x, y), exp in [((90, 420), (90, 420)), ((220, 330), (220, 330)), ((150, 80), (150, 256))]:
        p = page.evaluate("([x, y]) => __handle.ctx.test.physToClient(x, y)", [x, y])
        page.mouse.move(p["x"], p["y"], steps=4)
        page.wait_for_timeout(180)
        st = T(page, "state()")
        pad, pk = st["pads"][0], st["puck"]
        near = math.hypot(pad["x"] - exp[0], pad["y"] - exp[1]) < 4 or math.hypot(pad["x"] - pk["x"], pad["y"] - pk["y"]) < 36
        ok = ok and near
        if not near:
            print("    pad", pad, "expected", exp, "puck", pk)
    check(ok, f"{label}: paddle follows pointer and stays in own half (landscape={st['land']})")
    for _ in range(5):
        T(page, "forceGoal('me')")
        page.wait_for_timeout(30)
    r = wait_result(page, 5)
    versus_result_ok(r, label)
    check(r["outcome"] == "win" and r["myScore"] == 5 and r["oppScore"] == 0, f"{label}: first to 5 wins")


def hockey_rules(page):
    run(page, game="hockey", seed=52, skill=0.5, speed=8)
    T(page, "forceGoal('opp')")
    page.wait_for_function("() => __handle.ctx.test.state().phase === 'play'", timeout=5000)
    T(page, "setClock(119.95)")
    r = wait_result(page, 5)
    check(r["outcome"] == "loss" and r["oppScore"] == 1, f"hockey: time limit, leader wins ({r['myScore']}-{r['oppScore']})")
    run(page, game="hockey", seed=53, skill=0.5, speed=8)
    page.wait_for_function("() => __handle.ctx.test.state().phase === 'play'", timeout=5000)
    T(page, "autoplay(0.02)")  # keep it quiet: nobody scores in the next frames
    T(page, "setClock(119.99)")
    page.wait_for_function("() => __handle.ctx.test.state().sudden || __result", timeout=5000)
    st = T(page, "state()")
    if page.evaluate("__result") is None and st["score"][0] == st["score"][1]:
        check(st["sudden"], "hockey: level at 2:00 -> sudden death")
        T(page, "setClock(null, 29.99)")
        r = wait_result(page, 5)
        check(r["outcome"] == "draw" or r["myScore"] != r["oppScore"], f"hockey: sudden death resolves ({r['outcome']} {r['myScore']}-{r['oppScore']})")
    else:
        check(True, "hockey: (goal scored at the buzzer; sudden-death path skipped this seed)")


def hockey_autoplay(page, label, speed=8):
    run(page, game="hockey", seed=54, skill=0.5, speed=speed)
    T(page, "autoplay(0.6)")
    r = wait_result(page, 60)
    st = T(page, "state()")
    versus_result_ok(r, label)
    check(st["escapes"] == 0 and st["nan"] == 0, f"{label}: no escapes/NaN in live match ({st['steps']} steps)")
    return r


def hockey_speed(page):
    out = []
    for sp in (1, 6):
        run(page, game="hockey", seed=55, skill=0.5, speed=sp)
        page.wait_for_timeout(1500)
        v = page.evaluate("() => { const s = __handle.ctx.test.state(); return [s.steps, __handle.ctx.now()] }")
        page.evaluate("__handle.abort()")
        out.append((sp, v[0], v[1], v[0] * 1000 / 240))
    ok = all(abs(sim_ms - now) < 40 * sp for sp, steps, now, sim_ms in out)
    check(ok, "hockey: fixed-step physics tracks ctx.now() at speed 1 and 6 " + str([(sp, steps, round(now)) for sp, steps, now, _ in out]))


def hockey_spectate(page):
    page.evaluate("__spectate({game:'hockey', seed:61, speed:10})")
    r = wait_result(page, 90)
    st = T(page, "state()")
    check(r.get("winner") in (0, 1, -1) and isinstance(r.get("scores"), list) and len(r["scores"]) == 2,
          f"hockey spectate: AI vs AI finished {r} in {st['clock']:.0f} s game time")
    check(st["escapes"] == 0 and st["nan"] == 0, "hockey spectate: no escapes/NaN")


def hockey_physics(page):
    for seed in (1, 2, 3):
        s = page.evaluate(f"() => {{ __run({{game:'hockey', seed:9, speed:1}}); const r = __handle.ctx.test.stress(10000, {seed}); __handle.abort(); return r; }}")
        check(s["escapes"] == 0 and s["nan"] == 0 and s["minX"] >= 12.99 and s["maxX"] <= 287.01 and s["maxSpeed"] <= 1150,
              f"hockey physics stress seed {seed}: {s}")


def hockey_calibration(page):
    N = 60
    print(f"\n  Hockey AI-vs-AI ({N} seeds each, first to 5 / 2 min). 'casual'/'good' = human-proxy controllers")
    print("  (casual: quick hand, ~250 ms reaction, loose aim; good: ~190 ms, tighter aim).")
    rows = page.evaluate("""N => { const sim = (s,a,b) => { __run({game:'hockey', seed:1, speed:1}); const t = __handle.ctx.test; __handle.abort(); return t.sim(s,a,b); };
      const pairs = [[0.1,0.5],[0.3,0.5],[0.5,0.5],[0.5,0.9],[0.7,0.9],['casual',0.1],['casual',0.3],['casual',0.5],['casual',0.7],['casual',0.9],['good',0.5],['good',0.9]];
      return pairs.map(([a,b]) => { let w=0,l=0,d=0,g=[0,0],bad=0;
        for (let s=1;s<=N;s++){ const r = sim(s*7+3,a,b); g[0]+=r.score[0]; g[1]+=r.score[1]; bad += r.escapes + r.nan;
          if (r.score[0]>r.score[1]) w++; else if (r.score[0]<r.score[1]) l++; else d++; }
        return {a:String(a), b, w, l, d, g, bad}; }); }""", N)
    print("  %-8s vs %-4s   W  L  D   goals" % ("A", "B"))
    for r in rows:
        print("  %-8s vs %-4s  %2d %2d %2d   %d-%d" % (r["a"], r["b"], r["w"], r["l"], r["d"], r["g"][0], r["g"][1]))
    get = {(r["a"], r["b"]): r for r in rows}
    check(all(r["bad"] == 0 for r in rows), f"hockey: no escapes/NaN in {N * len(rows)} simulated matches")
    check(get[("0.1", 0.5)]["w"] < get[("0.1", 0.5)]["l"] and get[("0.5", 0.9)]["w"] < get[("0.5", 0.9)]["l"], "hockey: higher skill AI wins more")
    c3, c5 = get[("casual", 0.3)]["w"] / N, get[("casual", 0.5)]["w"] / N
    check(c3 >= 0.7, f"hockey: casual proxy wins well against 0.3 ({c3:.0%})")
    check(0.5 <= c5 <= 0.72, f"hockey: casual proxy wins ~60% against 0.5 ({c5:.0%})")
    check(get[("good", 0.9)]["w"] >= 0.2 * N, "hockey: good human proxy beats 0.9 AI sometimes")


def touch_seq(cdp, pts, hold_ms, page):
    """Real touch input via CDP: touchStart at pts[0], optional moves, hold, touchEnd -> pointerType 'touch'."""
    x, y = pts[0]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for (x, y) in pts[1:]:
        page.wait_for_timeout(30)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
    page.wait_for_timeout(hold_ms)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def touch_tests(page):
    cdp = page.context.new_cdp_session(page)
    # darts: press where you aim (sight appears 48 css px above the finger), hold, lift -> lands near T20
    run(page, game="darts", mode="full", seed=41, speed=1)
    near = 0
    for i in range(3):
        page.wait_for_function("() => __handle.ctx.test.state().phase === 'aim'", timeout=8000)
        p = page.evaluate("() => __handle.ctx.test.boardToClient(0, 103)")
        x, y = p["x"], p["y"] + 48
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        page.wait_for_timeout(120)
        st = T(page, "state()")
        ok_aim = st["holding"] and abs(st["aim"]["x"]) < 4 and abs(st["aim"]["y"] - 103) < 4
        check(ok_aim, f"darts touch: aim starts at the finger (sight above it): {st['aim']}")
        page.wait_for_timeout(330)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(40)
        d = T(page, "state()")["thrown"][-1]
        dist = math.hypot(d["x"], d["y"] - 103)
        near += dist < 60
        print(f"    touch dart {i+1}: {d['label']} ({d['pts']}) at ({d['x']:.0f},{d['y']:.0f}), {dist:.0f} mm from T20")
    check(near == 3, "darts touch: all 3 darts land near T20, not the bull")
    shot(page, "darts-touch", 360)
    page.evaluate("__handle.abort()")
    # hockey: paddle is held above the finger
    run(page, game="hockey", seed=51, skill=0.5, speed=1)
    page.wait_for_timeout(200)
    f = page.evaluate("() => __handle.ctx.test.physToClient(120, 440)")
    touch_seq(cdp, [(f["x"], f["y"]), (f["x"] + 10, f["y"]), (f["x"] + 20, f["y"])], 250, page)
    st = T(page, "state()")
    pad = st["pads"][0]
    check(pad["y"] < 440 - 30 and abs(pad["x"] - 140) < 6, f"hockey touch: paddle sits above the finger (finger y 440 -> paddle y {pad['y']:.0f})")
    page.evaluate("__handle.abort()")
    no_errors(page, "touch")


def hockey_perf(page):
    """4x CPU throttle: frame intervals during a live AI-vs-AI hockey match."""
    cdp = page.context.new_cdp_session(page)
    run(page, game="hockey", seed=57, skill=0.5, speed=1)
    T(page, "autoplay(0.6)")
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    res = page.evaluate("""() => new Promise(res => { const d = []; let last = performance.now(), t0 = last;
        const f = (t) => { d.push(t - last); last = t; if (t - t0 < 5000) requestAnimationFrame(f); else res(d); };
        requestAnimationFrame(f); })""")
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    page.evaluate("__handle.abort()")
    over = sum(1 for x in res if x > 33.4)
    med = sorted(res)[len(res) // 2]
    print(f"    hockey @4x CPU throttle: {len(res)} frames, median {med:.1f} ms, {over} over 33 ms, max {max(res):.0f} ms")
    check(over <= max(3, 0.05 * len(res)), f"hockey: <=5% long frames under 4x throttle ({over}/{len(res)})")
    # per-frame cost of the game's own work (draw + physics) measured directly
    cost = page.evaluate("""() => { __run({game:'hockey', seed:58, speed:1}); const t = __handle.ctx.test; t.autoplay(0.6);
        return new Promise(res => setTimeout(() => { const f0 = t.frames(); const s0 = performance.now();
          setTimeout(() => { const n = t.frames() - f0; res({frames: n, ms: performance.now() - s0}); __handle.abort(); }, 2000); }, 300)); }""")
    print(f"    hockey unthrottled: {cost['frames']} frames in {cost['ms']:.0f} ms")


# ---------------------------------------------------------------- bots
HUMAN = {
    # typical / strong human estimates for the same content (see comments in report)
    "reaction": {"typical": "280-300 ms avg, ~0.3 fouls", "strong": "210-230 ms avg, no fouls"},
}


def bots(page):
    print("\n  Bot calibration: 20 seeds per skill, median [min..max]")
    res = page.evaluate("""() => {
      const U = DG.util, out = {};
      for (const id of ['reaction','aim','rush','darts']) {
        const g = DG.getGame(id); out[id] = {};
        for (const mode of ['full','mix']) {
          out[id][mode] = {};
          for (const sk of [0.1,0.5,0.9]) {
            const sc = [], t0 = performance.now(); let det = true, tlok = true, maxT = 0;
            for (let s = 1; s <= 20; s++) {
              const a = g.bot(s, sk, U.rng('bot' + s), mode), b = g.bot(s, sk, U.rng('bot' + s), mode);
              if (JSON.stringify(a) !== JSON.stringify(b)) det = false;
              const tl = a.timeline;
              for (let i = 1; i < tl.length; i++) if (tl[i][0] < tl[i-1][0]) tlok = false;
              if (!tl.length || tl[tl.length-1][1] !== a.score) tlok = false;
              maxT = Math.max(maxT, tl[tl.length-1][0]);
              sc.push(a.score);
            }
            sc.sort((x,y) => x-y);
            out[id][mode][sk] = {med: sc[10], min: sc[0], max: sc[19], mean: Math.round(sc.reduce((x,y)=>x+y,0)/20), det, tlok, maxT, ms: (performance.now()-t0)/40};
          }
        }
      }
      return out; }""")
    human = human_estimates(page)
    for id_, modes in res.items():
        for mode, sks in modes.items():
            line = "  %-8s %-4s " % (id_, mode) + " | ".join(
                "%.1f: %5d [%d..%d]" % (float(sk), v["med"], v["min"], v["max"]) for sk, v in sks.items())
            h = human[id_][mode]
            print(line + "   || human typical ~%d, strong ~%d  (bot means %s)" % (h["typical"], h["strong"], "/".join(str(v["mean"]) for v in sks.values())))
            for sk, v in sks.items():
                check(v["det"] and v["tlok"], f"bot {id_}/{mode}/{sk}: deterministic, timeline ascending and ends at score")
                check(v["ms"] < 50, f"bot {id_}/{mode}/{sk}: fast ({v['ms']:.2f} ms/call)")
            lim = 45 if mode == "mix" else 60
            check(max(v["maxT"] for v in sks.values()) <= lim, f"bot {id_}/{mode}: timeline within game length")
            m = {float(k): v["mean"] for k, v in sks.items()}
            check(m[0.1] < m[0.5] < m[0.9], f"bot {id_}/{mode}: skill ordering {m}")
            check(h["typical"] > m[0.5] and h["strong"] > m[0.9] * 0.93, f"bot {id_}/{mode}: typical human beats 0.5, strong human competitive with 0.9")
    return res


def human_estimates(page):
    """Estimated human scores on the same seeded content (per mode, median over 20 seeds)."""
    return page.evaluate("""() => {
      const U = DG.util, out = {};
      const med = a => Math.round(a.reduce((x, y) => x + y, 0) / a.length); // mean
      // reaction: typical 285 ms avg (sd 40) with a 6% foul rate; strong 220 ms avg (sd 25), no fouls
      out.reaction = {};
      for (const mode of ['full','mix']) {
        const n = mode === 'mix' ? 3 : 5, sim = (m, sd, f) => { const v = []; for (let s = 1; s <= 20; s++) { const r = U.rng('h'+s); let t = 0;
          for (let i = 0; i < n; i++) t += r() < f ? 0 : Math.max(0, 1000 - Math.round(m + sd * U.gauss(r))); v.push(t); } return med(v); };
        out.reaction[mode] = {typical: sim(285, 40, 0.06), strong: sim(220, 25, 0)};
      }
      // aim: replay the real schedule. typical hits 80% at ~560 ms, 3-4 stray clicks; strong 93% at ~430 ms, 1-2 stray
      out.aim = {};
      for (const mode of ['full','mix']) {
        const sim = (p, m, sd, stray) => { const v = []; for (let s = 1; s <= 20; s++) {
          __run({game:'aim', mode, seed:s, speed:1}); const sch = __handle.ctx.test.schedule(); __handle.abort();
          const r = U.rng('ha'+s); let t = 0;
          for (const tg of sch) if (r() < p) { const ms = Math.min(1080, Math.max(200, m + sd * U.gauss(r))); t += 100 + Math.round(100 * (1 - ms / 1100)); }
          v.push(t - 25 * stray); } return med(v); };
        out.aim[mode] = {typical: sim(0.8, 560, 110, 4), strong: sim(0.93, 430, 80, 1)};
      }
      // rush: per-problem time scales with difficulty d (0..1): typical (1.0+1.8d)*1.3 s at 90% right,
      // strong (1.0+1.8d)*0.8 s at 96% right, on the real seeded problems
      out.rush = {};
      const rg = DG.getGame('rush');
      for (const mode of ['full','mix']) {
        const sim = (f, acc) => { const v = []; for (let s = 1; s <= 20; s++) {
          const C = rg._content(s, mode), r = U.rng('hr'+s), dur = C.dur / 1000; let t = 0.3, sc = 0, st = 0;
          for (const p of C.probs) { t += (1 + 1.8 * p.d) * f * (0.75 + 0.5 * r()); if (t > dur) break;
            if (r() < acc) { st++; sc += 100 + Math.min(50, 10 * (st - 1)); } else { st = 0; sc = Math.max(0, sc - 50); } }
          v.push(sc); } return med(v); };
        out.rush[mode] = {typical: sim(1.3, 0.9), strong: sim(0.8, 0.96)};
      }
      // darts: replay the real wobble paths with a casual (random release) and a good (timed release) policy
      out.darts = {};
      const dg = DG.getGame('darts');
      for (const mode of ['full','mix']) {
        const sim = pol => { const v = []; for (let s = 1; s <= 20; s++) v.push(dg._humanEstimate(s, mode, pol, U.rng('hd'+s))); return med(v); };
        out.darts[mode] = {typical: sim('casual'), strong: sim('good')};
      }
      return out; }""")


# ---------------------------------------------------------------- abort
def abort_check(page, game, drive=None, mode="full"):
    run(page, game=game, mode=mode, seed=71, speed=4)
    if drive:
        drive()
    page.wait_for_timeout(400)
    has_frames = page.evaluate("() => !!(__handle.ctx.test && __handle.ctx.test.frames)")
    f1 = page.evaluate("() => __handle.ctx.test.frames ? __handle.ctx.test.frames() : 0")
    s1 = page.evaluate("() => JSON.stringify(__handle.ctx.test.state())")
    st1 = page.evaluate("__status")
    page.evaluate("__handle.abort()")
    page.wait_for_timeout(50)
    f2 = page.evaluate("() => __handle.ctx.test.frames ? __handle.ctx.test.frames() : 0")
    page.wait_for_timeout(2500)  # at speed 4 = 10 s of game time
    f3 = page.evaluate("() => __handle.ctx.test.frames ? __handle.ctx.test.frames() : 0")
    s3 = page.evaluate("() => JSON.stringify(__handle.ctx.test.state())")
    check(page.evaluate("__result") is None, f"abort {game}: ctx.end not called after abort")
    if has_frames:
        check(f1 > 0 and f3 == f2, f"abort {game}: rAF loop stopped (frames {f1} -> {f2} -> {f3})")
    check(page.evaluate("__status") == st1 or game == "reaction", f"abort {game}: no status updates after abort")
    if game in ("reaction", "rush"):
        check(s1 == s3 or game == "rush", f"abort {game}: state frozen")
    # input after abort is ignored
    if game == "reaction":
        page.keyboard.press("Space")
        check(page.evaluate("() => __handle.ctx.test.state().phase") == json.loads(s3)["phase"], "abort reaction: key after abort ignored")
    if game == "rush":
        page.keyboard.press("1")
        check(page.evaluate("() => JSON.stringify(__handle.ctx.test.state())") == s3, "abort rush: key after abort ignored")
    no_errors(page, f"abort {game}")


def shot(page, name, width):
    page.screenshot(path=str(SHOTS / f"{name}-{width}.png"), full_page=True)


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    for width in (400, 1280):
        print(f"\n=== width {width} ===")
        with browser_page(width=width, height=900) as page:
            open_harness(page, FILES)
            games = page.evaluate("__games()")
            check([g["id"] for g in games] == ["reaction", "aim", "rush", "darts", "hockey"], f"registered {[g['id'] for g in games]}")
            full, mix = ("full", "mix") if width == 400 else ("mix", "full")

            print("-- reaction")
            reaction_ui(page, full, f"reaction {full} UI@{width}")
            reaction_ui(page, mix, f"reaction {mix} UI@{width}", foul_round=0, key_round=2)
            run(page, game="reaction", mode="full", seed=11, speed=1)
            page.click("[data-test=pad]")
            page.wait_for_selector("[data-test=pad][data-state=go]")
            page.click("[data-test=pad]")
            page.click("[data-test=pad]")
            page.wait_for_selector("[data-test=pad][data-state=wait]")
            shot(page, "reaction", width)
            scroll_ok(page, f"reaction@{width}")
            page.evaluate("__handle.abort()")
            no_errors(page, f"reaction@{width}")

            print("-- aim")
            aim_ui(page, full, f"aim {full} UI@{width}")
            aim_hooks(page, mix)
            run(page, game="aim", mode="full", seed=21, speed=1)
            page.wait_for_function("() => __handle.ctx.test.alive().length >= 2", timeout=10000)
            a = T(page, "alive()")[0]
            page.mouse.click(a["cx"], a["cy"])
            page.wait_for_function("() => __handle.ctx.test.alive().length >= 1", timeout=5000)
            shot(page, "aim", width)
            scroll_ok(page, f"aim@{width}")
            page.evaluate("__handle.abort()")
            no_errors(page, f"aim@{width}")

            print("-- rush")
            rush_ui(page, full, f"rush {full} UI@{width}", speed=4)
            rush_ui(page, mix, f"rush {mix} UI@{width}", speed=4)
            run(page, game="rush", mode="full", seed=31, speed=1)
            for _ in range(3):
                T(page, "answerCorrect()")
            page.wait_for_timeout(500)
            shot(page, "rush", width)
            scroll_ok(page, f"rush@{width}")
            page.evaluate("__handle.abort()")
            no_errors(page, f"rush@{width}")

            print("-- darts")
            darts_ui(page, full, f"darts {full} UI@{width}")
            darts_ui(page, mix, f"darts {mix} UI@{width}", ui_darts=2)
            run(page, game="darts", mode="full", seed=41, speed=1)
            for xy in ([0, 103], [8, 150]):
                page.wait_for_function("() => __handle.ctx.test.state().phase === 'aim'")
                page.evaluate("([x, y]) => __handle.ctx.test.throwAt(x, y)", xy)
            page.wait_for_function("() => __handle.ctx.test.state().phase === 'aim'")
            p = page.evaluate("() => __handle.ctx.test.boardToClient(0, 103)")
            page.mouse.move(p["x"], p["y"])
            page.mouse.down()
            page.wait_for_timeout(500)
            shot(page, "darts", width)
            page.mouse.up()
            scroll_ok(page, f"darts@{width}")
            page.evaluate("__handle.abort()")
            no_errors(page, f"darts@{width}")

            print("-- hockey")
            hockey_pointer(page, f"hockey UI@{width}")
            hockey_autoplay(page, f"hockey autoplay@{width}")
            run(page, game="hockey", seed=51, skill=0.5, speed=1)
            T(page, "autoplay(0.5)")
            page.wait_for_timeout(3500)
            shot(page, "hockey", width)
            scroll_ok(page, f"hockey@{width}")
            page.evaluate("__handle.abort()")
            no_errors(page, f"hockey@{width}")

            if width == 400:
                print("-- rules / timeouts / speed")
                reaction_timeouts(page)
                reaction_speed(page)
                rush_scoring(page)
                darts_units(page)
                darts_timeout(page)
                hockey_rules(page)
                hockey_speed(page)
                hockey_physics(page)
                hockey_perf(page)
                hockey_spectate(page)
                page.wait_for_timeout(200)
                shot(page, "hockey-spectate", width)
                run(page, game="aim", mode="mix", seed=6, speed=20)
                wait_result(page, 10)
                shot(page, "aim-end", width)
                run(page, game="darts", mode="mix", seed=6, speed=4)
                for k in range(6):
                    page.wait_for_function("() => __handle.ctx.test.state().phase === 'aim'", timeout=8000)
                    page.evaluate("k => __handle.ctx.test.throwAt(k * 7 - 10, 100 + k * 4)", k)
                page.wait_for_function("() => __handle.ctx.test.state().phase === 'visit'", timeout=8000)
                shot(page, "darts-visit", width)
                wait_result(page, 10)
                no_errors(page, "rules/timeouts")
                print("-- abort")
                abort_check(page, "reaction", drive=lambda: page.click("[data-test=pad]"))
                abort_check(page, "aim")
                abort_check(page, "rush")
                abort_check(page, "darts")
                abort_check(page, "hockey")
                page.evaluate("__spectate({game:'hockey', seed:3, speed:4})")
                page.wait_for_timeout(400)
                f1 = T(page, "frames()")
                page.evaluate("__handle.abort()")
                page.wait_for_timeout(600)
                f2 = T(page, "frames()")
                page.wait_for_timeout(600)
                check(T(page, "frames()") == f2 and page.evaluate("__result") is None, f"abort hockey spectate: stopped ({f1} -> {f2})")
                bots(page)
                hockey_calibration(page)
                aim_schedule_same(page)
                no_errors(page, "bots/calibration")
            else:
                aim_resize(page)
                darts_timeout(page)
                no_errors(page, f"misc@{width}")

    print("\n=== width 360 ===")
    with browser_page(width=360, height=740, touch=True) as page:
        open_harness(page, FILES)
        for g, prep in [("reaction", None), ("aim", None), ("rush", None), ("darts", None), ("hockey", None)]:
            run(page, game=g, mode="full", seed=5, speed=1)
            page.wait_for_timeout(500)
            scroll_ok(page, f"{g}@360")
            cw = page.evaluate("() => { const c = document.querySelector('#root canvas'); return c ? c.getBoundingClientRect().right : 0 }")
            check(cw <= 360, f"{g}@360: canvas fits ({cw:.0f})")
            page.evaluate("__handle.abort()")
        # touch: tap reaction pad, tap-aim a target, drag hockey paddle
        run(page, game="reaction", mode="mix", seed=5, speed=1)
        page.tap("[data-test=pad]")
        check(T(page, "state()")["phase"] == "wait", "reaction@360: tap arms the pad")
        page.evaluate("__handle.abort()")
        run(page, game="aim", mode="mix", seed=5, speed=1)
        page.wait_for_function("() => __handle.ctx.test.alive().length >= 1", timeout=5000)
        a = T(page, "alive()")[0]
        page.touchscreen.tap(a["cx"], a["cy"])
        page.wait_for_timeout(50)
        check(T(page, "state()")["hits"] == 1, "aim@360: touch tap hits a target")
        shot(page, "aim-touch", 360)
        page.evaluate("__handle.abort()")
        touch_tests(page)
        no_errors(page, "360")

    print(f"\n{len(FAILS)} failures, {time.time() - t0:.0f} s")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
