"""Part 1: every game, 1v1 stake 100, launched from the real UI at 1280 and 360 touch."""
import sys, json, traceback, math
from qalib import *
from drivers import DRIVERS, SPEED, ended

only = sys.argv[2:] if len(sys.argv) > 2 else list(GAMES)
width = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
touch = width < 500
out = []

def one(page, gid):
    rec = {'game': gid, 'w': width}
    page.evaluate(f"DGApp.setSpeed({SPEED[gid]})")
    s0 = st(page); g0 = s0['gold']; r0 = s0['games'].get(gid, {}).get('r', 1200); h0 = len(s0['history'])
    n_err0 = len(errs(page))
    start_via_games_tab(page, gid, '1v1', 100, touch)
    page.wait_for_selector('[data-test=matchmaking]', timeout=5000)
    rec['escrow_ok'] = st(page)['gold'] == g0 - 100
    through_to_play(page, touch, shotname=f"{gid}-{width}-rules")
    ok, how = DRIVERS[gid](page, touch)
    rec['input_ok'] = ok; rec['how'] = how
    if not ended(page) and gid not in ('memory',):
        shot(page, f"{gid}-{width}-play")
    ph = wait_result(page, 150)
    rec['phase'] = ph
    shot(page, f"{gid}-{width}-result")
    L = last(page)
    s1 = st(page)
    rec['outcome'] = L.get('outcome'); rec['payout'] = L.get('payout')
    exp = {'win': math.floor(2 * 100 * 0.9), 'draw': 100, 'loss': 0}.get(L.get('outcome'))
    rec['payout_ok'] = L.get('payout') == exp and s1['gold'] == g0 - 100 + exp
    dr = s1['games'][gid]['r'] - r0
    rec['dr'] = dr; rec['dr_ok'] = dr == L.get('dr') and ((L['outcome'] == 'win' and dr > 0) or (L['outcome'] == 'loss' and dr < 0) or L['outcome'] == 'draw')
    h = s1['history'][0] if s1['history'] else {}
    rec['hist_ok'] = len(s1['history']) == h0 + 1 and h.get('g') == gid and h.get('o') == L['outcome'] and h.get('net') == exp - 100 and h.get('stake') == 100
    # screen shows outcome
    title = page.text_content('#resTitle')
    rec['title'] = title
    rec['screen_outcome'] = page.get_attribute('[data-test=result]', 'data-outcome')
    tiles = page.locator('.res-tiles').inner_text().replace('\n', ' ')
    rec['tiles'] = tiles
    # Rematch
    opp0 = cur(page)['opps'][0]['name']; seed0 = cur(page)['seed']
    b = page.locator('[data-test=rematch]'); b.scroll_into_view_if_needed(); b.tap() if touch else b.click()
    page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000)
    c = cur(page)
    rec['rematch_ok'] = c and c['games'] == [gid] and c['opps'][0]['name'] == opp0 and c['seed'] != seed0 and st(page)['gold'] == s1['gold'] - 100
    # forfeit from versus screen to clean up (stake lost)
    g2 = st(page)['gold']
    page.locator('#ovForfeit').click() if not touch else page.locator('#ovForfeit').tap()
    page.click('#forfeitYes') if not touch else page.tap('#forfeitYes')
    wait_result(page, 10)
    rec['rematch_forfeit'] = (last(page)['outcome'], st(page)['gold'] - g2)
    page.locator('[data-test=back]').click()
    page.wait_for_function("DGApp.current() === null")
    rec['errors'] = errs(page)[n_err0:]
    return rec

with new_page_ctx(width, touch=touch) as page:
    boot(page)
    for gid in only:
        try:
            r = one(page, gid)
        except Exception as e:
            r = {'game': gid, 'w': width, 'EXC': repr(e)[:400]}
            shot(page, f"{gid}-{width}-EXC")
            try:
                page.evaluate("DGApp.close()")
            except Exception: pass
        out.append(r)
        bad = [k for k in ('escrow_ok', 'input_ok', 'payout_ok', 'dr_ok', 'hist_ok', 'rematch_ok') if r.get(k) is False]
        print(json.dumps(r) if (bad or 'EXC' in r or r.get('errors')) else f"OK {gid}@{width} {r['outcome']} dr={r['dr']} how={r['how']} rf={r['rematch_forfeit']} title={r['title']}", flush=True)
    sw = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    print('scrollwidth', sw)
    print('all console errors:', errs(page))
json.dump(out, open(f'/home/claude/duel-gold/test/qa/e2e_1v1_{width}.json', 'w'), indent=1)
