"""Pack E (social) tests: trivia, groups, durak, liars, auction.
Run:  cd test && python3 test_social.py        (exit code 0 = pass)"""
import json, pathlib, random, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dglib import browser_page, open_harness, wait_result, errors

FILES = ["social.js"]
SHOTS = pathlib.Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(exist_ok=True)
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)
    return cond


def no_errors(page, where):
    e = errors(page)
    check(not e, f"{where}: errors {e[:3]}")


def start(page, **kw):
    page.evaluate(f"__run({json.dumps(kw)})")


def hook(page, expr):
    return page.evaluate(f"window.__handle.ctx.test.{expr}")


STATUS_SEEN = []


def status_ok(page, where):
    st = page.evaluate("__status") or ""
    STATUS_SEEN.append(st)
    check(len(st) <= 40, f"{where}: status too long ({len(st)}): {st}")


def scroll_ok(page, where):
    # the harness status bar prints the raw result JSON on one line; clip it so only the game is measured
    page.evaluate("document.getElementById('bar').style.overflow='hidden'")
    sw, iw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    check(sw <= iw, f"{where}: horizontal scroll {sw} > {iw}")


def pump(page, step, limit_s, poll=60):
    t0 = time.time()
    while time.time() - t0 < limit_s:
        if page.evaluate("window.__result !== null"):
            return True
        body = page.evaluate("document.getElementById('root').innerText")
        bad = __import__("re").findall(r"\bYou (?:opens|bids|calls|loses|wins|leads|attacks|throws|beats|takes|picks)\b", body)
        check(not bad, f"'You' verb agreement: {bad}")
        st = page.evaluate("__status") or ""
        if not st.startswith("ENDED"):
            check(len(st) <= 40, f"status too long ({len(st)}): {st}")
        try:
            step()
        except Exception as e:  # the game re-rendered between query and click (AI moved) - retry next poll
            if "not attached" not in str(e) and "Timeout" not in str(e):
                raise
        page.wait_for_timeout(poll)
    return page.evaluate("window.__result !== null")


def versus_shape(r, where):
    check(r.get("outcome") in ("win", "loss", "draw"), f"{where}: bad outcome {r}")
    check(isinstance(r.get("myScore"), (int, float)) and isinstance(r.get("oppScore"), (int, float)), f"{where}: scores {r}")


# ------------------------------------------------------------------ data validation
def test_data(page):
    print("== data validation")
    d = page.evaluate("""(() => { const D = DG._socialData; return {
        trivia: D.TRIVIA, wg: D.WG.map(p => ({d: p.d, groups: p.groups.map(g => ({name: g.name, words: g.words}))})) }; })()""")
    T = d["trivia"]
    check(len(T) >= 150, f"trivia bank only {len(T)}")
    qs = [q["q"].strip().lower() for q in T]
    check(len(set(qs)) == len(qs), "duplicate trivia questions")
    cats = {}
    for q in T:
        opts = [q["a"]] + q["w"]
        check(len(opts) == 4 and len(set(o.strip().lower() for o in opts)) == 4, f"trivia options not 4 unique: {q['q']}")
        check(q["d"] in (1, 2, 3), f"difficulty tag {q}")
        cats[q["c"]] = cats.get(q["c"], 0) + 1
    check(len(cats) == 8 and min(cats.values()) >= 15, f"category spread {cats}")
    print(f"  trivia: {len(T)} questions, categories {cats}")
    # every selection shows exactly one correct option, identical across calls
    sel = page.evaluate("""(() => { const D = DG._socialData, out = [];
        for (let s = 1; s <= 60; s++) for (const m of ['full','mix']) { const a = D.triviaSet(s, m), b = D.triviaSet(s, m);
          out.push({n: a.length, same: JSON.stringify(a) === JSON.stringify(b), ok: a.every(q => D.TRIVIA[q.id].a === q.opts[q.ans] && q.opts.filter(o => o === D.TRIVIA[q.id].a).length === 1), uniq: new Set(a.map(q => q.id)).size === a.length, m}); }
        return out; })()""")
    check(all(x["same"] and x["ok"] and x["uniq"] for x in sel), "trivia selection not deterministic/valid")
    check(all(x["n"] == (10 if x["m"] == "full" else 5) for x in sel), "trivia selection size")
    W = d["wg"]
    check(len(W) >= 30, f"word groups bank only {len(W)}")
    allnames = set()
    for i, p in enumerate(W):
        words = [w for g in p["groups"] for w in g["words"]]
        check(len(p["groups"]) == 4 and all(len(g["words"]) == 4 for g in p["groups"]), f"puzzle {i} shape")
        check(len(set(words)) == 16, f"puzzle {i} has duplicate words")
        check(all(w.isupper() and w.replace(" ", "").isalpha() for w in words), f"puzzle {i} word format {words}")
        # a word may not equal / contain another group's name root trivially
        allnames.add(tuple(sorted(words)))
    check(len(allnames) == len(W), "duplicate puzzles")
    print(f"  word groups: {len(W)} puzzles, all 16 unique words each")


# ------------------------------------------------------------------ trivia
def trivia_click_game(page, mode, pattern):
    start(page, game="trivia", mode=mode, seed=4242 if mode == "full" else 77, skill=0.5, speed=4)
    i = [0]

    def step():
        st = hook(page, "state()")
        if st["phase"] == "ask":
            btns = page.query_selector_all("[data-test=tv-opt]")
            want = st["ans"] if pattern[i[0] % len(pattern)] else (st["ans"] + 1) % 4
            btns[want].click()
            i[0] += 1
    ok = pump(page, step, 60)
    check(ok, f"trivia {mode}: did not finish")
    r = page.evaluate("__result")
    check(isinstance(r.get("score"), (int, float)), f"trivia result {r}")
    return r


def test_trivia(page, width):
    print(f"== trivia @{width}")
    r = trivia_click_game(page, "full", [1, 1, 0, 1])
    exp_correct = sum(1 for k in range(10) if [1, 1, 0, 1][k % 4])
    check(100 * exp_correct <= r["score"] <= 150 * exp_correct, f"trivia full score {r['score']} for {exp_correct} correct")
    check(len(page.evaluate("__progress")) == 10, "trivia progress per question")
    print("  full:", r["score"])
    r = trivia_click_game(page, "mix", [1])
    check(500 <= r["score"] <= 750, f"trivia mix all-correct score {r['score']}")
    print("  mix:", r["score"])
    no_errors(page, f"trivia@{width}")


def test_trivia_timeout(page):
    print("== trivia timeouts")
    start(page, game="trivia", mode="mix", seed=5, speed=20)
    r = wait_result(page, 20)
    check(r["score"] == 0, f"trivia no-answer score {r['score']}")
    no_errors(page, "trivia timeout")


# ------------------------------------------------------------------ groups
def groups_click_game(page, mode, seed, wrong_first=0, solve=4):
    start(page, game="groups", mode=mode, seed=seed, speed=2)
    sol = hook(page, "solution()")
    # wrong guesses through the UI: 2 words from group 0 + 2 from group 1
    for k in range(wrong_first):
        words = sol[0]["words"][:2] + sol[1]["words"][k:k + 2] if k < 3 else sol[0]["words"][:1] + sol[1]["words"][:1] + sol[2]["words"][:2]
        if page.query_selector("[data-test=wg-clear]:not([disabled])"):
            page.click("[data-test=wg-clear]")
        for w in words:
            page.click(f"[data-test=wg-tile][data-w='{w}']")
        page.click("[data-test=wg-submit]")
        page.wait_for_timeout(50)
        if page.evaluate("__result !== null") or hook(page, "state()")["over"]:
            break
    order = [3, 0, 2, 1]
    for gi in order[:solve]:
        if hook(page, "state()")["over"]:
            break
        page.click("[data-test=wg-shuffle]")
        if page.query_selector("[data-test=wg-clear]:not([disabled])"):
            page.click("[data-test=wg-clear]")
        for w in sol[gi]["words"]:
            page.click(f"[data-test=wg-tile][data-w='{w}']")
        page.click("[data-test=wg-submit]")
        page.wait_for_timeout(40)
    return sol


def test_groups(page, width):
    print(f"== groups @{width}")
    groups_click_game(page, "full", 11, wrong_first=1)
    st = hook(page, "state()")
    r = wait_result(page, 10)
    check(len(st["found"]) == 4 and st["mistakes"] == 1, f"groups state {st}")
    check(1100 - 50 + 200 <= r["score"] <= 1100 - 50 + 300, f"groups full score {r['score']}")
    print("  full (1 mistake):", r["score"])
    # deselect + one-away message
    start(page, game="groups", mode="mix", seed=12, speed=1)
    sol = hook(page, "solution()")
    for w in sol[0]["words"][:3] + sol[1]["words"][:1]:
        page.click(f"[data-test=wg-tile][data-w='{w}']")
    page.click("[data-test=wg-submit]")
    check("One away" in page.inner_text("[data-test=wg-msg]"), "groups one-away hint")
    page.click(f"[data-test=wg-tile][data-w='{sol[2]['words'][0]}']")
    page.click("[data-test=wg-clear]")
    check(hook(page, "state()")["sel"] == [], "deselect")
    for w in sol[1]["words"]:
        page.click(f"[data-test=wg-tile][data-w='{w}']")
    page.click("[data-test=wg-submit]")
    check(page.evaluate("__progress")[-1] == 250 - 50, f"groups progress {page.evaluate('__progress')}")
    page.evaluate("window.__handle.abort()")
    # mix: all four
    groups_click_game(page, "mix", 13)
    r = wait_result(page, 10)
    check(r["score"] >= 1100, f"groups mix all found {r['score']}")
    print("  mix all:", r["score"])
    no_errors(page, f"groups@{width}")


def test_groups_endings(page):
    print("== groups endings")
    groups_click_game(page, "full", 21, wrong_first=4, solve=0)
    r = wait_result(page, 10)
    st = hook(page, "state()") if False else None
    check(r["score"] == 0, f"groups 4 mistakes score {r['score']}")
    start(page, game="groups", mode="mix", seed=22, speed=15)
    hook(page, "submitGroup(0)")
    r = wait_result(page, 15)
    check(r["score"] == 200, f"groups timeout with one group {r['score']}")
    no_errors(page, "groups endings")


# ------------------------------------------------------------------ durak
def durak_click_game(page, seed, skill=0.3, limit=150):
    start(page, game="durak", seed=seed, skill=skill, speed=8)
    rng = random.Random(seed)
    seen = {"beat": 0, "attack": 0, "throw": 0, "take": 0, "bito": 0, "done": 0}

    def step():
        st = hook(page, "state()")
        if st["phase"] == "over" or st["toMove"] != 0 or not st["legal"]:
            return
        check(st["total"] == 36, f"durak conservation {st['total']}")
        lg = st["legal"]
        kinds = {m["t"] for m in lg}
        if "attack" in kinds or "beat" in kinds:
            cards = [m for m in lg if m["t"] in ("attack", "beat")]
            if "take" in kinds and rng.random() < 0.1:
                btn = page.query_selector("[data-test=dk-take]")
                if btn: btn.click(); seen["take"] += 1
                return
            m = min(cards, key=lambda m: (m["c"] // 9 == st["trump"], m["c"] % 9))
            el = page.query_selector(f"[data-test=dk-card][data-c='{m['c']}']")
            if el:
                el.click(timeout=2000); seen[m["t"]] += 1
        elif "take" in kinds:
            btn = page.query_selector("[data-test=dk-take]")
            if btn: btn.click(); seen["take"] += 1
        else:
            thr = [m for m in lg if m["t"] == "throw"]
            if thr and rng.random() < 0.4:
                el = page.query_selector(f"[data-test=dk-card][data-c='{thr[0]['c']}']")
                if el: el.click(); seen["throw"] += 1
                return
            for t in ("bito", "done"):
                btn = page.query_selector(f"[data-test=dk-{t}]")
                if btn:
                    btn.click(); seen[t] += 1
                    return
    ok = pump(page, step, limit, poll=50)
    check(ok, f"durak seed {seed}: did not finish by clicks")
    return seen


def test_durak(page, width):
    print(f"== durak @{width}")
    seen = durak_click_game(page, 31)
    r = page.evaluate("__result")
    versus_shape(r, "durak")
    want = {"win": (1, 0), "loss": (0, 1), "draw": (0.5, 0.5)}[r["outcome"]]
    check((r["myScore"], r["oppScore"]) == want, f"durak scores should be winner-higher {r}")
    check("Cards left" in r.get("detail", ""), "durak detail lists cards left")
    print("  click game:", r, seen)
    check(seen["attack"] + seen["beat"] > 3, "durak human played cards")
    # autoplay path
    start(page, game="durak", seed=32, skill=0.9, speed=8)
    hook(page, "autoplay()")
    r = wait_result(page, 60)
    versus_shape(r, "durak autoplay")
    no_errors(page, f"durak@{width}")


def test_durak_fuzz(page):
    print("== durak rules fuzz (200 AI-vs-AI games)")
    start(page, game="durak", seed=1, speed=1)
    res = hook(page, "simulate(200, 'fuzz')")
    page.evaluate("window.__handle.abort()")
    print("  ", {k: res[k] for k in ("games", "wins", "draws", "maxMoves")}, "violations", res["violations"][:3])
    check(res["games"] == 200 and not res["violations"], "durak fuzz violations")
    for a, b in ((0.9, 0.1), (0.9, 0.5), (0.5, 0.1)):
        start(page, game="durak", seed=1, speed=1)
        r1 = hook(page, f"simulate(100, 'c{a}{b}', [{a},{b}])")
        r2 = hook(page, f"simulate(100, 'd{a}{b}', [{b},{a}])")
        page.evaluate("window.__handle.abort()")
        pct = (r1["wins"][0] + r2["wins"][1]) / 2
        print(f"   durak AI {a} vs {b}: {pct:.0f}% wins ({r1['draws'] + r2['draws']} draws)")
        check(pct > 50, f"durak stronger AI should win more ({a} vs {b}: {pct})")


# ------------------------------------------------------------------ liars
def liars_click_game(page, seed, skill=0.3):
    start(page, game="liars", seed=seed, skill=skill, speed=8)
    rng = random.Random(seed)

    def step():
        if page.query_selector("[data-test=ld-next]"):
            page.click("[data-test=ld-next]")
            return
        ctl = page.query_selector("[data-test=ld-ctl]")
        if not ctl:
            return
        st = hook(page, "state()")
        call = page.query_selector("[data-test=ld-call]:not([disabled])")
        if call and st["bid"] and st["bid"]["q"] >= 3 and rng.random() < 0.45:
            call.click()
            return
        faces = page.query_selector_all("[data-test=ld-face]:not([disabled])")
        if faces and rng.random() < 0.6:
            mine = st["dice"][0]
            best = max(range(2, 7), key=lambda f: sum(1 for d in mine if d == f or d == 1))
            el = page.query_selector(f"[data-test=ld-face][data-f='{best}']:not([disabled])")
            if el:
                el.click()
        raise_ = page.query_selector("[data-test=ld-raise]:not([disabled])")
        if raise_:
            raise_.click()
        elif call:
            call.click()
    ok = pump(page, step, 150, poll=60)
    check(ok, f"liars seed {seed}: did not finish by clicks")


def test_liars(page, width):
    print(f"== liars @{width}")
    liars_click_game(page, 51)
    r = page.evaluate("__result")
    versus_shape(r, "liars")
    check((r["myScore"] == 0) != (r["oppScore"] == 0), f"liars exactly one side at 0 dice {r}")
    print("  click game:", r)
    start(page, game="liars", seed=53, skill=0.6, speed=1)
    page.wait_for_timeout(1500)
    txt = page.inner_text("[data-test=liars]")
    check(" dies" not in txt and "1 dice" not in txt, f"liars copy grammar: {txt[:200]}")
    import re as _re
    bad = _re.findall(r"\bYou (?:opens|bids|calls|loses|wins|leads|attacks|throws|beats|takes|picks)\b", txt)
    check(not bad, f"liars 'You' verb agreement: {bad}")
    page.evaluate("window.__handle.abort()")
    start(page, game="liars", seed=52, skill=0.6, speed=8)
    hook(page, "autoplay()")
    r = wait_result(page, 60)
    versus_shape(r, "liars autoplay")
    no_errors(page, f"liars@{width}")


def test_liars_fuzz(page):
    print("== liars fuzz (200 AI-vs-AI games)")
    start(page, game="liars", seed=1, speed=1)
    res = hook(page, "simulate(200, 'fuzz')")
    print("  ", res)
    check(res["games"] == 200 and not res["violations"], "liars fuzz violations")
    for a, b in ((0.9, 0.1), (0.9, 0.5), (0.5, 0.1)):
        r1 = hook(page, f"simulate(200, 'c{a}{b}', [{a},{b}])")
        r2 = hook(page, f"simulate(200, 'd{a}{b}', [{b},{a}])")
        pct = (r1["wins"][0] + r2["wins"][1]) / 4
        print(f"   liars AI {a} vs {b}: {pct:.0f}% wins")
        check(pct > 50, f"liars stronger AI should win more ({a} vs {b})")
    page.evaluate("window.__handle.abort()")


# ------------------------------------------------------------------ auction
def test_auction(page, width):
    print(f"== auction @{width}")
    start(page, game="auction", seed=61, skill=0.5, speed=8)
    bids = []

    def step():
        if page.query_selector("[data-test=au-finish]"):
            page.click("[data-test=au-finish]")
            return
        if page.query_selector("[data-test=au-next]"):
            page.click("[data-test=au-next]")
            return
        inp = page.query_selector("[data-test=au-input]")
        if inp:
            st = hook(page, "state()")
            b = min(st["cash"][0], int(st["sig"] * 0.85 / 10) * 10)
            if len(bids) == 2:
                page.click("[data-test=au-plus]")
                b = None
            else:
                inp.fill(str(b))
            bids.append(b)
            page.click("[data-test=au-bid]")
    ok = pump(page, step, 60, poll=60)
    check(ok, "auction click game did not finish")
    r = page.evaluate("__result")
    versus_shape(r, "auction")
    check(len(bids) == 6, f"auction six bids {bids}")
    print("  click game:", r)
    # overbid is clamped to cash
    start(page, game="auction", seed=62, speed=8)
    page.fill("[data-test=au-input]", "999999")
    page.click("[data-test=au-bid]")
    st = hook(page, "state()")
    check(min(st["cash"]) >= 0, f"auction cash negative {st}")
    hook(page, "autoplay()")
    r = wait_result(page, 30)
    versus_shape(r, "auction autoplay")
    no_errors(page, f"auction@{width}")


def test_auction_ai(page):
    print("== auction AI strength (1000 sims each)")
    start(page, game="auction", seed=1, speed=1)
    for a, b in ((0.9, 0.1), (0.9, 0.5), (0.5, 0.1), (0.5, 0.5)):
        r = hook(page, f"simulate(1000, 'a{a}{b}', [{a},{b}])")
        print(f"   auction AI {a} vs {b}: {r['wins'][0] / 10:.0f}% wins")
        if a != b:
            check(r["wins"][0] > r["wins"][1], f"auction stronger AI should win more ({a} vs {b})")
    page.evaluate("window.__handle.abort()")


# ------------------------------------------------------------------ bots / calibration
def test_bots(page):
    print("== race bot determinism + calibration (20 seeds)")
    for g in ("trivia", "groups"):
        for mode in ("full", "mix"):
            det = page.evaluate(f"""(() => {{ const g = DG.getGame('{g}'); let ok = true, fast = 0;
                for (let s = 1; s <= 20; s++) for (const k of [0.1,0.5,0.9]) {{
                  const t0 = performance.now(); const a = g.bot(s, k, DG.util.rng(s + ':x'), '{mode}'); fast = Math.max(fast, performance.now() - t0);
                  const b = g.bot(s, k, DG.util.rng(s + ':x'), '{mode}');
                  if (JSON.stringify(a) !== JSON.stringify(b)) ok = false;
                  const tl = a.timeline; if (tl[tl.length-1][1] !== a.score) ok = false;
                  for (let i = 1; i < tl.length; i++) if (tl[i][0] < tl[i-1][0]) ok = false; }}
                return {{ok, fast}}; }})()""")
            check(det["ok"], f"{g} {mode} bot not deterministic / bad timeline")
            check(det["fast"] < 50, f"{g} bot slow {det['fast']}")
            rows = page.evaluate(f"""(() => {{ const g = DG.getGame('{g}'), out = {{}};
                for (const k of [0.1,0.5,0.9]) {{ const a = []; for (let s = 1; s <= 20; s++) a.push(g.bot(s, k, DG.util.rng('c' + s), '{mode}').score);
                  a.sort((x,y)=>x-y); out[k] = [Math.min(...a), a[10], Math.round(a.reduce((x,y)=>x+y)/a.length), Math.max(...a)]; }} return out; }})()""")
            ref = {("trivia", "full"): "human optimal 1,500 (all right, instant); strong ~1,150 (9/10, 4 s); typical ~780 (6/10, 6 s)",
                   ("trivia", "mix"): "optimal 750; strong ~580; typical ~400",
                   ("groups", "full"): "optimal 1,400; strong ~1,250 (0-1 mistakes, 60 s); typical ~900 (3-4 groups, 1-2 mistakes); beginner ~450 (1-2 groups)",
                   ("groups", "mix"): "optimal 1,400; strong ~1,000 (4 groups in 45 s); typical ~400 (1-2 groups); beginner ~200 (yellow only)"}[(g, mode)]
            print(f"  {g:7} {mode:4}  skill: min/median/mean/max   " + "   ".join(f"{k}: {v[0]}/{v[1]}/{v[2]}/{v[3]}" for k, v in rows.items()))
            print(f"               reference: {ref}")
            check(rows["0.1"][2] < rows["0.5"][2] < rows["0.9"][2], f"{g} {mode} bot not monotone in skill")
            if g == "groups":
                zeros = page.evaluate(f"""(() => {{ const g = DG.getGame('groups'), z = {{}}; for (const k of [0.1,0.5]) {{ let n = 0;
                    for (let s = 1; s <= 50; s++) if (g.bot(s, k, DG.util.rng('z' + s), '{mode}').score === 0) n++; z[k] = n; }} return z; }})()""")
                print(f"               zero scores in 50 seeds: skill 0.1 -> {zeros['0.1']}, 0.5 -> {zeros['0.5']}")
                check(zeros["0.1"] <= 7 and zeros["0.5"] <= 1, f"groups {mode} bot zero-heavy {zeros}")


# ------------------------------------------------------------------ abort / spectate / screenshots
def test_abort(page):
    print("== abort mid-game")
    for g, mode in (("trivia", "full"), ("groups", "full"), ("durak", "full"), ("liars", "full"), ("auction", "full")):
        start(page, game=g, mode=mode, seed=90, speed=10)
        page.wait_for_timeout(300)
        if g == "trivia": hook(page, "answerCorrect()")
        if g == "groups": hook(page, "submitGroup(0)")
        if g in ("durak", "liars", "auction"): hook(page, "autoplay()")
        page.wait_for_timeout(150)
        page.evaluate("window.__handle.abort()")
        s1 = page.evaluate("__status")
        page.wait_for_timeout(1500)
        check(page.evaluate("__result") is None, f"{g}: ctx.end called after abort")
        check(page.evaluate("__status") == s1, f"{g}: still running after abort")
        no_errors(page, f"abort {g}")


def test_spectate(page):
    print("== spectate")
    for g in ("durak", "liars", "auction"):
        page.evaluate(f"__spectate({{game:'{g}', seed:7, speed:12}})")
        r = wait_result(page, 90)
        check(r.get("winner") in (0, 1, -1) and len(r.get("scores", [])) == 2, f"{g} spectate result {r}")
        if r.get("winner") in (0, 1):
            check(r["scores"][r["winner"]] > r["scores"][1 - r["winner"]], f"{g} spectate: winner must have the higher score {r}")
        print(f"  {g}: {r}")
        no_errors(page, f"spectate {g}")


def screenshot_state(page, g, width):
    if g == "trivia":
        start(page, game="trivia", seed=3, speed=1)
        hook(page, "answerWrong()")
        page.wait_for_timeout(200)
    elif g == "groups":
        start(page, game="groups", seed=4, speed=1)
        sol = hook(page, "solution()")
        hook(page, "submitGroup(0)")
        for w in sol[2]["words"][:2]:
            page.click(f"[data-test=wg-tile][data-w='{w}']")
    elif g == "durak":
        start(page, game="durak", seed=5, skill=0.5, speed=6)
        page.wait_for_timeout(200)
        # let human attack/defend a couple of times to show pairs on the table
        for _ in range(60):
            st = hook(page, "state()")
            if len(st["table"]) >= 2 and st["toMove"] == 0 and st["legal"]:
                break
            if st["toMove"] == 0 and st["legal"]:
                lg = [m for m in st["legal"] if m["t"] in ("attack", "beat", "throw")]
                if lg:
                    page.click(f"[data-test=dk-card][data-c='{lg[0]['c']}']")
                else:
                    b = page.query_selector("[data-test=dk-bito], [data-test=dk-done], [data-test=dk-take]")
                    if b: b.click()
            page.wait_for_timeout(120)
    elif g == "liars":
        start(page, game="liars", seed=6, speed=6)
        page.wait_for_timeout(700)
        if page.query_selector("[data-test=ld-raise]:not([disabled])"):
            page.click("[data-test=ld-raise]")
        page.wait_for_timeout(500)
    elif g == "auction":
        start(page, game="auction", seed=7, speed=6)
        page.fill("[data-test=au-input]", "1500")
        page.click("[data-test=au-bid]")
        page.wait_for_timeout(100)
    page.wait_for_timeout(400)
    page.screenshot(path=str(SHOTS / f"{g}-{width}.png"), full_page=True)
    page.evaluate("window.__handle.abort()")


def test_narrow(page):
    print("== 360 px layout")
    for g in ("trivia", "groups", "durak", "liars", "auction"):
        start(page, game=g, seed=8, speed=6)
        page.wait_for_timeout(500)
        scroll_ok(page, f"{g}@360")
        if g in ("durak", "liars", "auction"):
            hook(page, "autoplay()")
            for _ in range(20):
                page.wait_for_timeout(250)
                scroll_ok(page, f"{g}@360 during play")
                status_ok(page, f"{g}@360")
                if page.evaluate("__result !== null"): break
        page.evaluate("window.__handle.abort()")
    # auction reveal table at 360
    start(page, game="auction", seed=9, speed=8)
    hook(page, "autoplay()")
    page.wait_for_function("document.querySelector('[data-test=au-reveal]')", timeout=20000)
    scroll_ok(page, "auction reveal @360")
    page.screenshot(path=str(SHOTS / "auction-reveal-360.png"), full_page=True)
    page.evaluate("window.__handle.abort()")
    no_errors(page, "narrow")


def main():
    t0 = time.time()
    with browser_page(width=1280) as page:
        open_harness(page, FILES)
        games = {g["id"]: g for g in page.evaluate("__games()")}
        check(set(games) == {"trivia", "groups", "durak", "liars", "auction"}, f"registered {list(games)}")
        check(games["durak"]["cashEligible"] is False and games["liars"]["cashEligible"] is False and games["auction"]["cashEligible"] is False, "cashEligible flags")
        check(all(games[g]["hasSpectate"] for g in ("durak", "liars", "auction")), "spectate missing")
        test_data(page)
        test_bots(page)
        test_durak_fuzz(page)
        test_liars_fuzz(page)
        test_auction_ai(page)
        test_trivia_timeout(page)
        test_groups_endings(page)
        test_abort(page)
        test_spectate(page)
        for fn in (test_trivia, test_groups, test_durak, test_liars, test_auction):
            fn(page, 1280)
        for g in games:
            screenshot_state(page, g, 1280)
        no_errors(page, "1280 run")
    with browser_page(width=400, height=860, touch=False) as page:
        open_harness(page, FILES)
        for fn in (test_trivia, test_groups, test_durak, test_liars, test_auction):
            fn(page, 400)
        for g in ("trivia", "groups", "durak", "liars", "auction"):
            screenshot_state(page, g, 400)
        no_errors(page, "400 run")
    with browser_page(width=360, height=740) as page:
        open_harness(page, FILES)
        test_narrow(page)
    print(f"\n{len(FAILS)} failure(s) in {time.time() - t0:.0f}s")
    for f in FAILS:
        print(" -", f)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
