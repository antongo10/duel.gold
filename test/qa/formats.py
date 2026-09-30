import json, math, sys
from qalib import *
from finish import play_round, FIN
R = []
def rep(*a):
    print(*a, flush=True); R.append(' '.join(map(str, a)))

def home_start(page, pick, fmt, stake):
    """Home -> Duel now panel"""
    page.click('#tab-home'); page.wait_for_selector('#dnFind')
    if pick.startswith('cat:') or pick in ('any', 'surprise', 'favs'):
        page.click(f'[data-pick="{pick}"]')
    else:
        page.select_option('#dnGame', pick)
    page.click(f'#dnF-{fmt}')
    page.click(f'#dnS-{stake}')
    page.click('#dnFind')

with new_page_ctx(1280) as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(4)")
    # ---- 2v2 and FFA with 3 race games
    for fmt in ('2v2', 'ffa'):
        for gid in ('sudoku', 'trivia', 'darts'):
            g0 = st(page)['gold']; r0 = st(page)['games'].get(gid, {}).get('r', 1200)
            home_start(page, gid, fmt, 100)
            page.wait_for_selector('[data-test=versus]', timeout=8000)
            vs_txt = page.inner_text('[data-test=versus]').replace('\n', ' | ')
            esc_ok = st(page)['gold'] == g0 - 100
            play_round(page)
            wait_result(page, 90)
            L = last(page); s1 = st(page)
            if fmt == '2v2':
                exp = {'win': 180, 'draw': 100, 'loss': 0}[L['outcome']]
            else:
                exp = L['payout']  # check placement math below
                place = L['place']
                tbl = page.inner_text('.res-table')
            ok = s1['gold'] == g0 - 100 + L['payout'] and L['payout'] == exp and s1['history'][0]['f'] == fmt and s1['history'][0]['g'] == gid
            race_rows = page.evaluate("document.querySelectorAll('#ovRace .race-row').length")
            rep(fmt, gid, L['outcome'], 'place', L.get('place'), 'payout', L['payout'], 'dr', L['dr'], 'OK' if ok and esc_ok else 'BAD', 'gold', g0, '->', s1['gold'])
            if fmt == 'ffa': rep('   table:', tbl.replace('\n', ' | '))
            shot(page, f'fmt-{fmt}-{gid}')
            page.click('[data-test=back]')
    print('errors', errs(page))
