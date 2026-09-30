"""Pack D (builder) tests: Base Duel, City Duel, Restaurant Duel.

Run:  python3 test/test_builder.py
Covers SPEC.md testing: real-UI play in full + mix at 400/1280 px, time-outs, abort, determinism (incl. speed 1 vs 8),
bot determinism / calibration / runtime, balance (single-type spam vs mixed), path-blocking prevention, 360 px
overflow, touch tap-to-confirm, and screenshots in build + result phases (test/shots/).
"""
import pathlib, statistics, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dglib import browser_page, open_harness, wait_result, errors  # noqa: E402

SHOTS = pathlib.Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(exist_ok=True)
FILES = ["builder.js"]
GAMES = ["base", "city", "restaurant"]
FAILS = []


def check(cond, msg):
    if cond:
        print("  ok  ", msg)
    else:
        print("  FAIL", msg)
        FAILS.append(msg)


def run(page, game, mode="full", seed=7, speed=1, skill=0.5):
    page.evaluate(f"__run({{game:'{game}', mode:'{mode}', seed:{seed}, speed:{speed}, skill:{skill}}})")
    page.wait_for_timeout(150)


def T(page, expr):
    return page.evaluate("(() => { const t = window.__handle.ctx.test; return " + expr + "; })()")


def result_ok(r, label):
    check(r is not None and isinstance(r.get("score"), (int, float)) and r["score"] >= 0, f"{label}: result has numeric score ({r and r.get('score')})")


def no_errors(page, label):
    e = errors(page)
    check(not e, f"{label}: no console errors {e[:2] if e else ''}")


def no_hscroll(page, label):
    sw = page.evaluate("document.documentElement.scrollWidth")
    iw = page.evaluate("window.innerWidth")
    check(sw <= iw, f"{label}: no horizontal scroll ({sw} <= {iw})")


def click_test(page, sel):
    page.click(f'[data-test="{sel}"]')


# ---------------------------------------------------------------- Base Duel UI
def base_ui_game(page, mode, width, shots=False):
    label = f"base {mode} @{width}"
    run(page, "base", mode, seed=11, speed=4 if mode == "mix" else 10)
    st = T(page, "t.state()")
    check(st["phase"] == "build", f"{label}: starts in build phase")
    if shots:
        page.screenshot(path=str(SHOTS / f"base-{width}.png"), full_page=True)
    # place towers by clicking real tiles
    placed = 0
    for tool in ["frost", "spike", "cannon", "arrow", "spike"]:
        click_test(page, f"tool-{tool}")
        legal = T(page, f"t.legal('{tool}')")
        if not legal:
            continue
        # prefer tiles near the base core (they cover the most path)
        legal.sort(key=lambda p: -p[0])
        x, y = legal[len(legal) // 4]
        pt = T(page, f"t.tilePoint({x},{y})")
        before = T(page, "t.state().structs.length")
        page.mouse.click(pt["x"], pt["y"])
        if T(page, "t.state().structs.length") == before + 1:
            placed += 1
    check(placed >= 4, f"{label}: placed {placed} structures by clicking tiles")
    # sell one for a full refund
    s = T(page, "t.state()")
    g0 = s["gold"]
    tgt = s["structs"][0]
    click_test(page, "tool-sell")
    pt = T(page, f"t.tilePoint({tgt['x']},{tgt['y']})")
    page.mouse.click(pt["x"], pt["y"])
    s2 = T(page, "t.state()")
    check(len(s2["structs"]) == len(s["structs"]) - 1 and s2["gold"] > g0, f"{label}: sell refunds ({g0} -> {s2['gold']})")
    # rebuild with the refund
    click_test(page, "tool-arrow")
    for x, y in T(page, "t.legal('arrow')")[:3]:
        pt = T(page, f"t.tilePoint({x},{y})")
        page.mouse.click(pt["x"], pt["y"])
        if T(page, "t.state().gold") < 50:
            break
    click_test(page, "go")
    # firebomb during the wave
    bombs0 = T(page, "t.state().bombs")
    fired = False
    for _ in range(80):
        st = T(page, "t.state()")
        if st["phase"] == "wave" and st["enemies"]:
            e = st["enemies"][0]
            click_test(page, "tool-bomb")
            pt = T(page, f"t.mapPoint({e['x']},{e['y']})")
            page.mouse.click(pt["x"], pt["y"])
            if T(page, "t.state().bombs") == bombs0 - 1:
                fired = True
                break
        page.wait_for_timeout(40)
    check(fired, f"{label}: firebomb thrown via map tap")
    r = wait_result(page, timeout=120)
    result_ok(r, label)
    st = T(page, "t.state()")
    check(st["phase"] == "done", f"{label}: finished ({st['survived']} waves, {st['kills']} kills)")
    check(page.evaluate("__progress.length") >= 2, f"{label}: ctx.progress called per wave")
    if shots:
        page.screenshot(path=str(SHOTS / f"base-{width}-result.png"), full_page=True)
        no_hscroll(page, label + " result")
    # determinism: the recorded actions replayed headlessly give the same score
    rep = T(page, "t.replay()")
    check(rep["score"] == r["score"], f"{label}: headless replay of UI actions = UI score ({rep['score']} vs {r['score']})")
    no_errors(page, label)
    return r


# ---------------------------------------------------------------- City Duel UI
def city_ui_game(page, mode, width, shots=False):
    label = f"city {mode} @{width}"
    run(page, "city", mode, seed=5, speed=4)
    st = T(page, "t.state()")
    n = st["n"]
    free = [i for i in range(n * n) if st["tiles"][i] == 0]
    want = ["res", "res", "power", "water", "com", "park", "school", "res"] if mode == "full" else ["res", "power", "water", "park", "com"]
    k = 0
    for t in want:
        click_test(page, f"tool-{t}")
        click_test(page, f"tile-{free[k]}")
        k += 1
    st = T(page, "t.state()")
    built = sum(1 for p in st["plan"] if p)
    check(built == len(want), f"{label}: built {built}/{len(want)} buildings by clicking")
    check(st["eval"]["score10"] > 0, f"{label}: live projected score {st['eval']['score10'] / 10}")
    # bulldoze
    left0 = st["eval"]["left"]
    click_test(page, "tool-bulldoze")
    click_test(page, f"tile-{free[0]}")
    st2 = T(page, "t.state()")
    check(st2["plan"][free[0]] is None and st2["eval"]["left"] == left0 + 500, f"{label}: bulldoze refunds in full")
    # blocked tiles reject
    water = [i for i in range(n * n) if st["tiles"][i] == 1]
    if water:
        click_test(page, "tool-park")
        click_test(page, f"tile-{water[0]}")
        check(T(page, "t.state().plan")[water[0]] is None, f"{label}: cannot build on water")
    if shots:
        page.screenshot(path=str(SHOTS / f"city-{width}.png"), full_page=True)
    proj = T(page, "t.score()")
    click_test(page, "finish")
    r = wait_result(page, timeout=30)
    result_ok(r, label)
    check(abs(r["score"] - proj) < 1e-9, f"{label}: final score = projected ({r['score']} vs {proj})")
    if shots:
        page.screenshot(path=str(SHOTS / f"city-{width}-result.png"), full_page=True)
        no_hscroll(page, label + " result")
    no_errors(page, label)
    return r


# ---------------------------------------------------------------- Restaurant Duel UI
def rest_ui_game(page, mode, width, shots=False):
    label = f"restaurant {mode} @{width}"
    run(page, "restaurant", mode, seed=9, speed=4)
    for _ in range(4):
        click_test(page, "tables-inc")
    click_test(page, "kitchen-1")
    click_test(page, "chefs-inc")
    click_test(page, "dish-burger")      # remove
    click_test(page, "dish-sushi")       # add
    click_test(page, "dish-tacos")       # add
    click_test(page, "price-inc")
    click_test(page, "price-inc")
    click_test(page, "marketing-inc")
    p = T(page, "t.state().plan")
    check(p["tables"] == 12 and p["kitchen"] == 1 and p["chefs"] == 3 and "sushi" in p["menu"] and "burger" not in p["menu"]
          and abs(p["price"] - 1.1) < 1e-9 and p["marketing"] == 750, f"{label}: plan set through the UI {p}")
    # menu bounds: removing down to 2 dishes disables Open
    menu = list(p["menu"])
    for d in menu[:len(menu) - 2]:
        click_test(page, f"dish-{d}")
    check(page.is_disabled('[data-test="open"]'), f"{label}: Open disabled with < 3 dishes")
    for d in menu[:len(menu) - 2]:
        click_test(page, f"dish-{d}")
    check(not page.is_disabled('[data-test="open"]'), f"{label}: Open enabled again")
    proj = T(page, "t.state().proj.score")
    if shots:
        page.screenshot(path=str(SHOTS / f"restaurant-{width}.png"), full_page=True)
    click_test(page, "open")
    r = wait_result(page, timeout=30)
    result_ok(r, label)
    check(r["score"] == proj, f"{label}: final score = projection ({r['score']} vs {proj})")
    check(page.query_selector('[data-test="pnl"] table') is not None, f"{label}: P&L shown")
    if shots:
        page.screenshot(path=str(SHOTS / f"restaurant-{width}-result.png"), full_page=True)
        no_hscroll(page, label + " result")
    no_errors(page, label)
    return r


# ---------------------------------------------------------------- scenarios
def test_ui():
    print("== UI games (full + mix, 400 + 1280)")
    for width in (400, 1280):
        with browser_page(width=width) as page:
            open_harness(page, FILES)
            for mode in ("full", "mix"):
                base_ui_game(page, mode, width, shots=(mode == "full"))
                city_ui_game(page, mode, width, shots=(mode == "full"))
                rest_ui_game(page, mode, width, shots=(mode == "full"))


def test_timeouts():
    print("== time-outs (no input, high speed)")
    with browser_page(width=400) as page:
        open_harness(page, FILES)
        for g in GAMES:
            for mode in ("full", "mix"):
                t0 = time.time()
                run(page, g, mode, seed=3, speed=20)
                r = wait_result(page, timeout=90)
                result_ok(r, f"{g} {mode} timeout ({time.time() - t0:.1f}s)")
                statuses = page.evaluate("__status")
                check(statuses.startswith("Final"), f"{g} {mode}: status shows final ({statuses})")
        no_errors(page, "timeouts")


def test_abort():
    print("== abort mid-play and mid-simulation")
    with browser_page(width=400) as page:
        open_harness(page, FILES)
        page.evaluate("""(() => { window.__rafCount = 0; const o = window.requestAnimationFrame.bind(window);
            window.requestAnimationFrame = (f) => { window.__rafCount++; return o(f); }; })()""")

        def settle(label):
            page.evaluate("__handle.abort()")
            page.wait_for_timeout(200)
            c0, p0 = page.evaluate("__rafCount"), page.evaluate("__progress.length")
            s0 = page.evaluate("__status")
            page.wait_for_timeout(1500)
            check(page.evaluate("__rafCount") == c0, f"{label}: rAF stopped after abort")
            check(page.evaluate("__result") is None, f"{label}: no ctx.end after abort")
            check(page.evaluate("__progress.length") == p0 and page.evaluate("__status") == s0, f"{label}: no progress/status after abort")

        # base: during the build phase and mid-wave
        run(page, "base", "mix", seed=4, speed=1)
        page.wait_for_timeout(300)
        settle("base build")
        run(page, "base", "full", seed=4, speed=2)
        T(page, "t.placeAI(0.6)")
        T(page, "t.skipToDefence()")
        page.wait_for_timeout(1500)
        check(T(page, "t.state().phase") == "wave", "base: wave running before abort")
        settle("base mid-wave")
        # city: mid simulation animation
        run(page, "city", "full", seed=4, speed=1)
        T(page, "t.autoBuild(0.5)")
        T(page, "t.finish(false)")
        page.wait_for_timeout(500)
        check(T(page, "t.state().phase") == "sim", "city: simulation running before abort")
        settle("city mid-sim")
        # restaurant: mid day animation
        run(page, "restaurant", "full", seed=4, speed=1)
        T(page, "t.finish(false)")
        page.wait_for_timeout(500)
        check(T(page, "t.state().phase") == "sim", "restaurant: day running before abort")
        settle("restaurant mid-sim")
        no_errors(page, "abort")


def test_determinism():
    print("== determinism")
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        # Base: same actions at speed 1 and speed 8 -> identical sim result (and = headless replay)
        scores = {}
        for speed in (1, 8):
            run(page, "base", "mix", seed=21, speed=speed)
            T(page, "t.placeAI(0.8)")
            T(page, "t.skipToDefence()")
            r = wait_result(page, timeout=120)
            scores[speed] = (r["score"], T(page, "t.state().survived"), T(page, "t.state().kills"), T(page, "t.state().baseHp"))
            check(T(page, "t.replay()")["score"] == r["score"], f"base speed {speed}: replay matches")
        check(scores[1] == scores[8], f"base: sim identical at speed 1 vs 8 {scores}")
        # Base content identical for the same seed (map + waves)
        same = page.evaluate("""(() => { const L = DG.getGame('base')._lab;
            const a = JSON.stringify(L.baseWaves(33,'full')), b = JSON.stringify(L.baseWaves(33,'full')), c = JSON.stringify(L.baseWaves(34,'full'));
            return [a === b, a !== c]; })()""")
        check(same == [True, True], "base: seeded map/waves identical for a seed, different across seeds")
        # City: same placements -> same score
        vals = []
        for _ in range(2):
            run(page, "city", "mix", seed=8, speed=8)
            for i, t in [(6, "res"), (7, "power"), (8, "water"), (12, "park"), (13, "com")]:
                T(page, f"t.place({i}, '{t}')")
            T(page, "t.finish()")
            vals.append(wait_result(page, 20)["score"])
        check(vals[0] == vals[1], f"city: same placements -> same score {vals}")
        # Restaurant: same plan -> same score, independent of speed
        vals = []
        for speed in (1, 8):
            run(page, "restaurant", "mix", seed=8, speed=speed)
            T(page, "t.setPlan({kitchen:1, tables:14, chefs:3, waiters:2, menu:['pasta','sushi','tacos'], price:1.2, marketing:750})")
            T(page, "t.finish(false)")
            vals.append(wait_result(page, 30)["score"])
        check(vals[0] == vals[1], f"restaurant: same plan at speed 1 and 8 -> same score {vals}")
        no_errors(page, "determinism")


def test_bots():
    print("== bots: determinism, runtime, calibration (20 seeds)")
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        data = page.evaluate("""(() => {
          const U = DG.util, out = {};
          for (const id of ['base','city','restaurant']) {
            const g = DG.getGame(id);
            for (let i = 0; i < 4; i++) g.bot(900 + i, 0.5, U.rng('warm' + i), 'full');   // JIT warm-up
            const det = ['full','mix'].every(m => [0.1,0.5,0.9].every(sk => {
              const a = g.bot(77, sk, U.rng('r'), m), b = g.bot(77, sk, U.rng('r'), m);
              return JSON.stringify(a) === JSON.stringify(b); }));
            let shapeOk = true, maxMs = 0, slow = 0, calls = 0; const times = [];
            const table = {};
            for (const m of ['full','mix']) for (const sk of [0.1,0.5,0.9]) {
              const sc = [];
              for (let s = 1; s <= 20; s++) {
                const t0 = performance.now();
                const r = g.bot(s, sk, U.rng('bot:' + s + ':' + sk), m);
                const dt = performance.now() - t0; calls++; times.push(dt);
                maxMs = Math.max(maxMs, dt); if (dt > 50) slow++;
                const tl = r.timeline;
                if (!tl.length || tl[tl.length-1][1] !== r.score || tl.some((p, k) => k && p[0] < tl[k-1][0]) || !(r.score >= 0)) shapeOk = false;
                if (m === 'mix' && tl[tl.length-1][0] > 45) shapeOk = false;
                sc.push(r.score);
              }
              sc.sort((a, b) => a - b);
              table[m + ' ' + sk] = { p10: sc[2], median: sc[10], p90: sc[17], mean: sc.reduce((a, b) => a + b, 0) / 20 };
            }
            times.sort((a, b) => a - b);
            out[id] = { det, shapeOk, maxMs, slow, calls, table, median: times[times.length >> 1], p95: times[Math.floor(times.length * 0.95)] };
          }
          // reference "human" levels from the same engines
          const L = DG.getGame('base')._lab, C = DG.getGame('city')._lab, R = DG.getGame('restaurant')._lab;
          const ref = { base: {}, city: {}, restaurant: {} };
          for (const m of ['full','mix']) {
            const strong = [], typical = [], cstrong = [], ctyp = [], rstrong = [], rtyp = [];
            for (let s = 1; s <= 10; s++) {
              let best = 0; for (let k = 0; k < 12; k++) best = Math.max(best, L.baseBot(s, 0.95, U.rng('h' + k), m).score); strong.push(best);
              typical.push(L.baseBot(s, 0.6, U.rng('t' + s), m).score);
              cstrong.push(C.cityPlan(C.cityMap(s, m), U.rng('c' + s), 1, 25000).score10 / 10);
              const bd = C.cityMap(s, m); const typ = C.cityPlan(bd, U.rng('ct' + s), 0.6); ctyp.push(typ.score10 / 10);
              const d = R.restDay(s); let rb = 0; for (let k = 0; k < 3; k++) rb = Math.max(rb, R.restOptimise(d, U.rng('ro' + k), 1, 800).score); rstrong.push(rb);
              rtyp.push(R.restSim(d, R.restDefaultPlan()).score);
            }
            const med = a => a.slice().sort((x, y) => x - y)[a.length >> 1];
            ref.base[m] = { strong: med(strong), typical: med(typical) };
            ref.city[m] = { strong: med(cstrong), typical: med(ctyp) };
            ref.restaurant[m] = { strong: med(rstrong), 'default plan': med(rtyp) };
          }
          out.ref = ref;
          return out;
        })()""")
        for g in GAMES:
            d = data[g]
            check(d["det"], f"{g}: bot deterministic for (seed, skill, rng, mode)")
            check(d["shapeOk"], f"{g}: timelines ascending, last == score, mix <= 45 s")
            check(d["maxMs"] < 50 and d["median"] < 15, f"{g}: bot runtime median {d['median']:.1f} ms, p95 {d['p95']:.1f} ms, max {d['maxMs']:.1f} ms over {d['calls']} calls")
            print(f"     {g:<11} {'mode/skill':<10} {'p10':>8} {'median':>8} {'p90':>8}")
            for k, v in d["table"].items():
                print(f"     {'':<11} {k:<10} {v['p10']:>8.1f} {v['median']:>8.1f} {v['p90']:>8.1f}")
            for m in ("full", "mix"):
                t = d["table"]
                check(t[f"{m} 0.1"]["mean"] < t[f"{m} 0.5"]["mean"] < t[f"{m} 0.9"]["mean"], f"{g} {m}: mean score rises with skill")
            print(f"     reference: {data['ref'][g]}")
        for m in ("full", "mix"):
            check(data["ref"]["base"][m]["strong"] > data["base"]["table"][f"{m} 0.9"]["median"], f"base {m}: strong play beats the 0.9 bot median")
            check(data["ref"]["city"][m]["strong"] > data["city"]["table"][f"{m} 0.9"]["median"], f"city {m}: strong play beats the 0.9 bot median")
            check(data["ref"]["restaurant"][m]["strong"] > data["restaurant"]["table"][f"{m} 0.9"]["median"], f"restaurant {m}: strong play beats the 0.9 bot median")
        no_errors(page, "bots")


def test_balance():
    print("== balance: single-type spam vs mixed plans")
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        res = page.evaluate("""(() => {
          const U = DG.util, out = {};
          // City: fill every legal tile with one building type (within budget) vs a planned mixed city
          const C = DG.getGame('city')._lab;
          out.city = {};
          for (const m of ['full','mix']) {
            const spam = {}, mixed = [];
            for (let s = 1; s <= 6; s++) {
              const map = C.cityMap(s, m);
              for (const t of C.BLD_ORDER) {
                const plan = new Array(map.n * map.n).fill(null);
                for (let i = 0; i < plan.length; i++) if (!C.cityCanPlace(map, plan, i, t)) plan[i] = t;
                spam[t] = Math.max(spam[t] || 0, C.cityEval(map, plan).score10 / 10);
              }
              mixed.push(C.cityPlan(map, U.rng('m' + s), 0.5).score10 / 10);
            }
            out.city[m] = { spamMax: spam, mixedMin: Math.min(...mixed), mixedMedian: mixed.sort((a,b)=>a-b)[3] };
          }
          // Restaurant: trivial one-lever plans vs an optimised plan
          const R = DG.getGame('restaurant')._lab;
          const triv = {
            defaultPlan: R.restDefaultPlan(),
            cheapest: {kitchen:0,tables:4,chefs:1,waiters:1,menu:['soup','tacos','salad'],price:0.7,marketing:0},
            maxTables: {kitchen:0,tables:24,chefs:2,waiters:2,menu:['burger','pizza','pasta'],price:1,marketing:0},
            maxPrice: {kitchen:0,tables:8,chefs:2,waiters:2,menu:['steak','sushi','seafood'],price:1.6,marketing:0},
            maxMarketing: {kitchen:0,tables:8,chefs:2,waiters:2,menu:['burger','pizza','pasta'],price:1,marketing:3000},
            maxStaff: {kitchen:2,tables:12,chefs:6,waiters:6,menu:['burger','pizza','pasta'],price:1,marketing:0},
            premiumOnly: {kitchen:2,tables:12,chefs:3,waiters:2,menu:['steak','sushi','seafood'],price:1.2,marketing:500},
          };
          const rt = {}, opt = [], plans = new Set();
          for (let s = 1; s <= 8; s++) {
            const d = R.restDay(s);
            for (const [k, p] of Object.entries(triv)) { const v = R.restValid(p, 10000); rt[k] = rt[k] || []; rt[k].push(v ? null : R.restSim(d, p).score); }
            const o = R.restOptimise(d, U.rng('opt' + s), 1, 800); opt.push(o.score); plans.add(o.plan.menu.slice().sort().join('+') + '/k' + o.plan.kitchen);
          }
          const med = a => { const b = a.filter(x => x != null).sort((x, y) => x - y); return b.length ? b[b.length >> 1] : null; };
          out.restaurant = { trivial: Object.fromEntries(Object.entries(rt).map(([k, a]) => [k, med(a)])), optimised: med(opt), distinctOptimalPlans: plans.size };
          // Base: single-tower builds vs mixed builds (same perfect placement/bomb policy)
          const L = DG.getGame('base')._lab;
          const good = {maze:0,search:1,noise:0,sloppy:0,bomb:1,bombNeed:200,repair:true,hold:0,mine:false};
          const avg = (comp) => { let t = 0; for (let s = 1; s <= 12; s++) t += L.baseBot(s, 0.5, U.rng('b' + s), 'full', Object.assign({}, good, {comp})).score; return Math.round(t / 12); };
          out.base = {};
          for (const c of ['arrow','cannon','frost','spike','mine']) out.base['only ' + c] = avg([c]);
          out.base['mixed frost+spikes+cannon'] = avg(['frost','spike','spike','cannon']);
          out.base['mixed frost+cannon+arrow'] = avg(['frost','cannon','arrow']);
          return out;
        })()""")
        for m in ("full", "mix"):
            c = res["city"][m]
            worst = max(c["spamMax"].values())
            print(f"     city {m}: best single-type spam {worst:.1f} ({max(c['spamMax'], key=c['spamMax'].get)}), mixed (skill-0.5 planner) min {c['mixedMin']:.1f} median {c['mixedMedian']:.1f}")
            check(worst < c["mixedMedian"] * 0.5, f"city {m}: every single-type spam scores clearly below a mixed city")
        r = res["restaurant"]
        print(f"     restaurant: trivial plans {r['trivial']}, optimised median {r['optimised']}, distinct optimal plans over 8 days: {r['distinctOptimalPlans']}")
        best_triv = max(v for v in r["trivial"].values() if v is not None)
        check(best_triv < r["optimised"] - 700, f"restaurant: optimised plan beats every trivial plan by > 700 ({best_triv} vs {r['optimised']})")
        check(r["distinctOptimalPlans"] >= 4, "restaurant: best plan changes with the seeded day")
        b = res["base"]
        print(f"     base: {b}")
        single = max(v for k, v in b.items() if k.startswith("only"))
        check(b["mixed frost+spikes+cannon"] > single, f"base: a mixed defence beats every single-tower spam ({b['mixed frost+spikes+cannon']} vs {single})")
        no_errors(page, "balance")


def test_path_blocking():
    print("== base: path can never be sealed")
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        res = page.evaluate("""(() => {
          const L = DG.getGame('base')._lab, U = DG.util; let rejected = 0, placed = 0, alwaysOpen = true;
          for (let seed = 1; seed <= 15; seed++) {
            const S = L.BaseSim(seed, 'full'); S.gold = 1e6; const rng = U.rng('pb' + seed);
            const tiles = []; for (let y = 0; y < L.BH; y++) for (let x = 0; x < L.BW; x++) tiles.push([x, y]);
            for (const [x, y] of U.shuffle(rng, tiles)) {
              const why = S.canPlace('wall', x, y);
              if (why === 'Zombies need a path') rejected++;
              if (!S.place('wall', x, y)) placed++;
              if (!S.map.spawns.every(sp => S.field[sp.y * L.BW + sp.x] < 1e9)) alwaysOpen = false;
            }
          }
          return { rejected, placed, alwaysOpen };
        })()""")
        check(res["alwaysOpen"], f"base: after filling the map with walls every spawn still reaches the core ({res['placed']} walls)")
        check(res["rejected"] > 0, f"base: sealing placements rejected ({res['rejected']} times)")
        # the UI says why
        run(page, "base", "full", seed=2, speed=1)
        info = page.evaluate("""(() => {
          const t = __handle.ctx.test; const L = DG.getGame('base')._lab;
          // wall off greedily through the UI until a tile is refused for sealing the path
          for (let k = 0; k < 400; k++) {
            const legal = t.legal('wall');
            let found = null;
            for (let y = 0; y < L.BH && !found; y++) for (let x = 0; x < L.BW && !found; x++) if (t.why('wall', x, y) === 'Zombies need a path') found = [x, y];
            if (found) return found;
            if (!legal.length) return null;
            const [x, y] = legal[Math.floor(legal.length / 2)];
            if (t.state().gold < 10) return 'broke';
            const p = t.tilePoint(x, y); document.elementFromPoint(p.x, p.y).dispatchEvent(new PointerEvent('pointerdown', {clientX: p.x, clientY: p.y, pointerType: 'mouse', bubbles: true}));
          }
          return null;
        })()""")
        if isinstance(info, list):
            click_test(page, "tool-wall")
            pt = T(page, f"t.tilePoint({info[0]},{info[1]})")
            n0 = T(page, "t.state().structs.length")
            page.mouse.click(pt["x"], pt["y"])
            msg = page.inner_text('[data-test="msg"]')
            check(T(page, "t.state().structs.length") == n0 and "path" in msg, f"base UI: sealing click refused with message '{msg}'")
        else:
            print("     (budget ran out before a sealing tile appeared in the UI; engine test above covers it)")
        page.evaluate("__handle.abort()")
        no_errors(page, "path blocking")


def test_phone():
    print("== 360 px + touch tap-to-confirm")
    with browser_page(width=360, height=740, touch=True) as page:
        open_harness(page, FILES)
        for g in GAMES:
            run(page, g, "mix", seed=6, speed=1)
            page.wait_for_timeout(200)
            no_hscroll(page, f"{g} @360 build")
            if g == "restaurant":
                h = page.evaluate("document.getElementById('root').getBoundingClientRect().height")
                check(h <= 2 * 780, f"restaurant @360: plan screen {h:.0f} px tall (<= 2 phone screens)")
            if g == "base":
                check(page.inner_text('[data-test="score"]') == "0", "base: score shows 0 before the defence starts")
                box = lambda sel: page.evaluate(f"(() => {{ const r = document.querySelector('{sel}').getBoundingClientRect(); return [r.top, r.bottom]; }})()")
                m, b = box('[data-test=map] canvas'), box('[data-test=tool-bomb]')
                # the app overlay adds ~48 px header + ~70 px race panel above ctx.root
                check(b[1] + 130 <= 780 and m[0] >= 0, f"base @360x780: map {m} and Firebomb {b} fit on one screen with app chrome")
                page.tap('[data-test="tool-cannon"]')
                x, y = T(page, "t.legal('cannon')")[0]
                pt = T(page, f"t.tilePoint({x},{y})")
                page.touchscreen.tap(pt["x"], pt["y"])
                one = T(page, "t.state().structs.length")
                page.touchscreen.tap(pt["x"], pt["y"])
                two = T(page, "t.state().structs.length")
                check(one == 0 and two == 1, f"base touch: costly tower needs a second tap to confirm ({one}, {two})")
            if g == "city":
                page.tap('[data-test="tool-hosp"]')
                st = T(page, "t.state()")
                i = next(k for k in range(st["n"] ** 2) if st["tiles"][k] == 0)
                page.tap(f'[data-test="tile-{i}"]')
                one = T(page, f"t.state().plan[{i}]")
                check(one == "hosp", f"city touch: one tap places any building (no confirm step) ({one})")
                page.tap('[data-test="undo"]')
                check(T(page, f"t.state().plan[{i}]") is None, "city touch: visible Undo removes the last placement")
                T(page, "t.autoBuild(0.5)")
            T(page, "t.fastForward()" if g == "base" else "t.finish()")
            wait_result(page, 20)
            no_hscroll(page, f"{g} @360 result")
        no_errors(page, "phone")


def test_city_projection():
    print("== city: projection always equals the final report (random hand play)")
    with browser_page(width=360, height=780, touch=True) as page:
        open_harness(page, FILES)
        mism = []
        for k in range(12):
            mode = "full" if k % 2 else "mix"
            run(page, "city", mode, seed=100 + k, speed=6)
            st = T(page, "t.state()")
            n, tiles = st["n"], st["tiles"]
            import random
            rnd = random.Random(k)
            tools = ["res", "com", "ind", "park", "power", "water", "transit", "hosp", "school", "police", "stadium"]
            for _ in range(rnd.randint(4, 14)):
                i = rnd.randrange(n * n)
                if rnd.random() < 0.15:
                    page.tap('[data-test="tool-bulldoze"]')
                elif rnd.random() < 0.08:
                    if not page.is_disabled('[data-test="undo"]'):
                        page.tap('[data-test="undo"]')
                    continue
                else:
                    page.tap(f'[data-test="tool-{rnd.choice(tools)}"]')
                page.tap(f'[data-test="tile-{i}"]')
            hud = float(page.inner_text('[data-test="score"]'))
            proj = T(page, "t.score()")
            page.tap('[data-test="finish"]')
            page.wait_for_timeout(300)
            mid = float(page.inner_text('[data-test="final"]').split("\n")[0])
            # tapping tiles during the animation must not change anything
            page.evaluate("document.querySelector('[data-test=tile-0]').click(); __handle.ctx.test.place(1, 'res')")
            r = wait_result(page, 20)
            fin = float(page.inner_text('[data-test="final"]').split("\n")[0])
            if not (hud == proj == mid == fin == r["score"]):
                mism.append((k, hud, proj, mid, fin, r["score"]))
        check(not mism, f"city: HUD == projection == report (mid-animation and final) == result over 12 random games {mism}")
        eq = page.evaluate("""(() => { const C = DG.getGame('city')._lab, U = DG.util; let bad = 0, n = 0;
          for (const m of ['full','mix']) for (let s = 1; s <= 30; s++) { const map = C.cityMap(s, m), rng = U.rng('eq' + s), plan = new Array(map.n * map.n).fill(null);
            for (let k = 0; k < 50; k++) { const i = Math.floor(rng() * plan.length); if (map.tiles[i]) continue; plan[i] = rng() < 0.2 ? null : U.pick(rng, C.BLD_ORDER); n++;
              if (C.cityScore(map, plan) !== C.cityEval(map, plan).score10) bad++; } }
          return [bad, n]; })()""")
        check(eq[0] == 0, f"city: fast planner score == full evaluation on {eq[1]} random plans")
        no_errors(page, "city projection")


if __name__ == "__main__":
    t0 = time.time()
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        games = page.evaluate("__games()")
        print("registered:", [(g["id"], g["kind"], g["category"], g["formats"]) for g in games])
        check([g["id"] for g in games] == GAMES and all(g["hasBot"] and g["kind"] == "race" for g in games), "three race games with bots registered")
        no_errors(page, "load")
    for fn in (test_ui, test_timeouts, test_abort, test_determinism, test_bots, test_balance, test_path_blocking, test_phone, test_city_projection):
        try:
            fn()
        except Exception as e:  # keep going so one failure does not hide others
            import traceback
            traceback.print_exc()
            FAILS.append(f"{fn.__name__} crashed: {e}")
    print(f"\n{len(FAILS)} failure(s) in {time.time() - t0:.0f}s")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)
