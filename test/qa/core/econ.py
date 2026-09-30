"""Economy invariants: >=300 settled matches through DGApp across all formats, random real games, forced outcomes.
Outcomes are forced by calling DGApp.ctx().end(...) with a score chosen relative to the bots' (recomputed) scores,
or by forfeit (DGApp.forfeit), error (ctx.end with NaN / bad outcome) or closing the overlay (DGApp.close)."""
import random, math, json, sys, time
from qa_common import *

random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 320
FAILS = []
def check(c, msg):
    if not c:
        FAILS.append(msg); print('  FAIL:', msg)

def jsround(x): return math.floor(x + 0.5)
def expect(a, b): return 1 / (1 + 10 ** ((b - a) / 400))
def elo(r, o, s): return jsround(24 * (s - expect(r, o)))
def elo_ffa(ratings, scores):
    d = 0
    for j in range(1, len(ratings)):
        s = 1 if scores[0] > scores[j] else 0 if scores[0] < scores[j] else 0.5
        d += (24 / 3) * (s - expect(ratings[0], ratings[j]))
    return jsround(d)
def winpay(s): return (2 * s * 90) // 100
def ffa_prizes(s):
    pot = (4 * s * 90) // 100
    return [(pot * 70) // 100, (pot * 30) // 100]
def ffa_split(scores, prizes):
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    places = [0]*len(scores); pay = [0]*len(scores); pos = 0
    while pos < len(order):
        end = pos
        while end + 1 < len(order) and scores[order[end+1]] == scores[order[pos]]: end += 1
        tot = sum(prizes[k] if k < len(prizes) else 0 for k in range(pos, end+1))
        each = tot // (end - pos + 1)
        for k in range(pos, end+1): places[order[k]] = pos + 1; pay[order[k]] = each
        pos = end + 1
    return places, pay
def tour_prizes(e, added=0):
    pool = (8 * e * 90) // 100 + added
    return pool, (pool*60)//100, (pool*25)//100, (pool*75)//1000
def dp_for(o, stake):
    o = 'draw' if o == 'place' else o
    return 10 + (20 + (stake // 100) * 5 if o == 'win' else 5 if o == 'draw' else 0)

BOTS_JS = r"""() => {
  const c = DGApp.ctx(); const cu = DGApp.current(); if (!c || !cu) return null;
  const g = DG.getGame(cu.games[0]) ; const gid = c.root.dataset.game || (c.root.closest('[data-game]')||{}).dataset?.game;
  const game = DG.getGame(document.querySelector('#gameRoot').dataset.game);
  const run = (p) => game.kind === 'race' ? game.bot(c.seed, p.skill, DG.util.rng(c.seed + ':' + p.name), c.mode).score : null;
  return { gid: game.id, kind: game.kind, seed: c.seed, mode: c.mode, opps: c.opponents.map(p => ({name:p.name, rating:p.rating, score: run(p)})),
           ally: (c.teammates||[]).map(p => ({name:p.name, rating:p.rating, score: run(p)})), myRating: c.me.rating };
}"""

def wait(page, cond, t=30):
    page.wait_for_function(cond, timeout=t*1000)

def phase(page):
    return page.evaluate("DGApp.current() ? DGApp.current().phase : null")

def to_play(page):
    wait(page, "DGApp.current() && ['ready','result','error'].includes(DGApp.current().phase)")
    if phase(page) != 'ready': return False
    page.evaluate("document.querySelector('#mStart').click()")
    wait(page, "DGApp.current() && (DGApp.current().phase !== 'ready') && (DGApp.current().phase !== 'play' || DGApp.ctx())")
    return phase(page) == 'play'

def force(page, info, want):
    """end the running round with a result that yields `want` (win/loss/draw) vs opps[0] (race) or directly (versus)."""
    if info['kind'] == 'versus':
        page.evaluate("(o) => DGApp.ctx().end({outcome:o, myScore:1, oppScore:0})", want)
        return None
    return None

def my_score_for(info, want, fmt):
    ops = [o['score'] for o in info['opps']]
    if fmt == '2v2':
        them = ops[0] + ops[1]; ally = info['ally'][0]['score']
        base = them - ally
        return base + 5 if want == 'win' else base - 5 if want == 'loss' else base
    if fmt == 'ffa':
        return None
    o = ops[0]
    return o + 5 if want == 'win' else o - 5 if want == 'loss' else o

def snapshot(page):
    return page.evaluate("DGApp.state()")

def main():
    games = None
    stats = {'matches': 0, 'byFormat': {}, 'byKind': {}, 'outcomes': {}}
    with browser_page() as page:
        boot(page)
        page.evaluate("DGApp.setSpeed(40)")
        # gold watcher: detect negative gold at any commit
        page.evaluate("""(() => { window.__minGold = Infinity; const P = window.DGP; const oc = P.commit; P.commit = function(){ window.__minGold = Math.min(window.__minGold, P.S.gold); return oc.apply(this, arguments); }; })()""")
        games = page.evaluate("DG.games.map(g => ({id:g.id, kind:g.kind, formats:g.formats}))")
        race = [g['id'] for g in games if g['kind'] == 'race']
        vs = [g['id'] for g in games if g['kind'] == 'versus']
        i = 0
        while stats['matches'] < N:
            i += 1
            S0 = snapshot(page)
            if S0['gold'] < 1200:
                page.evaluate("DGApp.set({gold: DGApp.state().gold + 5000})"); S0 = snapshot(page)
            fmt = random.choice(['1v1', '1v1', '2v2', 'ffa', 'tournament', 'mix'])
            gid = random.choice(race if fmt in ('2v2', 'ffa', 'mix') else race + vs) if fmt != 'mix' else 'any'
            g = S0['gold']
            stake = random.choice([0, 10, 50, 100, 250, 500, 1000, g, 37])
            path = random.choices(['normal', 'forfeit_play', 'forfeit_ready', 'error', 'close_mm', 'close_play'], [70, 8, 4, 6, 4, 8])[0]
            err = page.evaluate("(o) => DGApp.startMatch(o)", {'game': gid, 'format': fmt, 'stake': stake})
            check(err == '', f'#{i} startMatch refused {gid}/{fmt}/{stake}: {err}')
            if err: continue
            S1 = snapshot(page)
            check(S1['gold'] == S0['gold'] - stake, f'#{i} escrow deduct {S0["gold"]}-{stake} != {S1["gold"]}')
            check(S1['gold'] >= 0, f'#{i} gold negative after escrow')
            if path == 'close_mm':
                ph0 = phase(page)
                page.evaluate("DGApp.close()")
                S2 = snapshot(page)
                if ph0 == 'mm':
                    check(S2['gold'] == S0['gold'], f'#{i} close in matchmaking did not refund: {S0["gold"]} -> {S2["gold"]}')
                    check(len(S2['history']) == len(S0['history']), f'#{i} close_mm added history')
                elif stake > 0:  # closing after matchmaking = forfeit (documented)
                    check(S2['gold'] == S0['gold'] - stake and S2['history'][0]['o'] == 'loss', f'#{i} close in {ph0} should forfeit')
                stats.setdefault('close_mm_phase', {}); stats['close_mm_phase'][ph0] = stats['close_mm_phase'].get(ph0, 0) + 1
                stats['outcomes']['close_mm'] = stats['outcomes'].get('close_mm', 0) + 1
                continue
            rounds = []  # per round: (info, want, myscore)
            ended_by = None
            tour_stage = None
            while True:
                ok = to_play(page) if phase(page) in ('mm', 'versus', 'ready', 'between', None) or phase(page) == 'ready' else phase(page) == 'play'
                ph = phase(page)
                if ph in ('result', 'error'): break
                if path == 'forfeit_ready' and not rounds:
                    pass
                if ph != 'play':
                    # e.g. forfeit_ready: we are at ready
                    break
                info = page.evaluate(BOTS_JS)
                if path == 'error' and random.random() < 0.6:
                    if info['kind'] == 'race': page.evaluate("DGApp.ctx().end({score: NaN})")
                    else: page.evaluate("DGApp.ctx().end({outcome: 'banana'})")
                    ended_by = 'error'
                    wait(page, "DGApp.current() && ['error','result'].includes(DGApp.current().phase)")
                    break
                if path == 'forfeit_play' and random.random() < 0.5:
                    page.evaluate("DGApp.forfeit()"); ended_by = 'forfeit'
                    wait(page, "DGApp.current() && ['result'].includes(DGApp.current().phase)")
                    rounds.append((info, 'forfeit', None)); break
                if path == 'close_play' and random.random() < 0.5:
                    page.evaluate("DGApp.close()"); ended_by = 'close'
                    rounds.append((info, 'forfeit', None)); break
                want = random.choice(['win', 'win', 'loss', 'draw'])
                if fmt == 'ffa':
                    ops = [o['score'] for o in info['opps']]
                    srt = sorted(ops, reverse=True)
                    choice = random.choice(['first', 'second', 'third', 'last', 'tie1', 'tie2'])
                    my = {'first': srt[0] + 7, 'second': (srt[0] + srt[1]) / 2 if srt[0] != srt[1] else srt[0] - 0.001, 'third': (srt[1] + srt[2]) / 2 if srt[1] != srt[2] else srt[2] - 0.001,
                          'last': srt[2] - 7, 'tie1': srt[0], 'tie2': srt[1]}[choice]
                    want = choice
                elif info['kind'] == 'race':
                    my = my_score_for(info, want, fmt)
                else:
                    my = None
                if info['kind'] == 'race':
                    page.evaluate("(s) => DGApp.ctx().end({score: s})", my)
                else:
                    page.evaluate("(o) => DGApp.ctx().end({outcome:o, myScore:1, oppScore:0})", want)
                rounds.append((info, want, my))
                wait(page, "DGApp.current() && ['ready','result','error','between'].includes(DGApp.current().phase)")
                if phase(page) in ('result', 'error'): break
                if path == 'forfeit_ready' and random.random() < 0.5:
                    wait(page, "DGApp.current() && DGApp.current().phase === 'ready'")
                    page.evaluate("DGApp.forfeit()"); ended_by = 'forfeit_ready'
                    rounds.append((None, 'forfeit', None))
                    break
            if path == 'forfeit_ready' and not rounds and phase(page) == 'ready':
                page.evaluate("DGApp.forfeit()"); ended_by = 'forfeit_ready'; rounds.append((None, 'forfeit', None))
            if False:
                S2 = snapshot(page)
                stats['free_close_unrecorded'] = stats.get('free_close_unrecorded', 0) + 1
                rd = {k: S2['games'].get(k, {}).get('r') for k in S2['games']}; r0 = {k: S0['games'].get(k, {}).get('r') for k in S2['games']}
                if rd != r0: stats['free_close_rating_changed'] = stats.get('free_close_rating_changed', 0) + 1
                stats['matches'] += 1
                continue
            if ended_by != 'close':
                wait(page, "DGApp.current() && ['result','error'].includes(DGApp.current().phase)")
            else:
                S2c = snapshot(page)
                check(S2c['gold'] == S0['gold'] - stake and len(S2c['history']) == min(50, len(S0['history']) + 1) and S2c['history'][0]['o'] == 'loss' and S2c.get('active') is None,
                      f'#{i} close mid-play ({fmt}, stake {stake}) not settled as forfeit: gold {S0["gold"]}->{S2c["gold"]} hist {S2c["history"][0]}')
                stats['matches'] += 1; stats['outcomes']['close'] = stats['outcomes'].get('close', 0) + 1
                continue
            cu = page.evaluate("DGApp.current()")
            last = page.evaluate("DGApp.last()")
            S2 = snapshot(page)
            if ended_by != 'close':
                check(cu['escrow'] == 0, f'#{i} escrow not released: {cu["escrow"]} phase {cu["phase"]}')
            check(page.evaluate("window.__minGold") >= 0, f'#{i} gold went negative')
            stats['matches'] += 1
            stats['byFormat'][fmt] = stats['byFormat'].get(fmt, 0) + 1
            key = ended_by or 'normal'
            stats['outcomes'][key] = stats['outcomes'].get(key, 0) + 1
            nf0 = len(FAILS)
            if ended_by == 'error' or (last and last.get('phase') == 'error'):
                check(S2['gold'] == S0['gold'], f'#{i} error path refund: {S0["gold"]} -> {S2["gold"]} ({fmt}, stake {stake})')
                check(len(S2['history']) == len(S0['history']), f'#{i} error path wrote history')
                page.evaluate("DGApp.close()")
                continue
            h = S2['history'][0]
            check(len(S2['history']) == min(50, len(S0['history']) + 1), f'#{i} history not +1')
            payout = last['payout']
            check(S2['gold'] == S0['gold'] - stake + payout, f'#{i} gold delta {S2["gold"]-S0["gold"]} != payout {payout} - stake {stake}')
            check(h['net'] == payout - stake and h['stake'] == stake and h['f'] == fmt, f'#{i} history row mismatch {h}')
            check(S2['dp'] - S0['dp'] == last['dp'], f'#{i} dp delta {S2["dp"]-S0["dp"]} != last.dp {last["dp"]}')
            # today
            check(S2['today']['net'] - S0['today']['net'] == payout - stake, f'#{i} today.net delta wrong')
            # expected payout by rules
            o = last['outcome']
            if fmt in ('1v1', 'mix', '2v2'):
                exp = winpay(stake) if o == 'win' else stake if o == 'draw' else 0
                check(payout == exp, f'#{i} {fmt} payout {payout} != {exp} (o={o}, stake={stake})')
                if fmt != 'mix' and rounds and rounds[0][1] in ('win', 'loss', 'draw'):
                    check(o == rounds[0][1], f'#{i} {fmt} forced {rounds[0][1]} but got {o} ({rounds[0][0]["gid"]})')
                check(S2['dp'] - S0['dp'] == dp_for(o, stake), f'#{i} dp rule')
                rec = S2['rec']; rec0 = S0['rec']
                check(sum(rec.values()) - sum(rec0.values()) == 1, f'#{i} rec not +1')
                if fmt in ('1v1', '2v2') and rounds and rounds[0][0]:
                    info = rounds[0][0]
                    gid = info['gid']
                    r0 = S0['games'].get(gid, {}).get('r', 1200); r2 = S2['games'][gid]['r']
                    s = 1 if o == 'win' else 0.5 if o == 'draw' else 0
                    if fmt == '1v1': e = elo(r0, info['opps'][0]['rating'], s)
                    else: e = elo((r0 + info['ally'][0]['rating']) / 2, (info['opps'][0]['rating'] + info['opps'][1]['rating']) / 2, s)
                    check(r2 - r0 == max(100, r0 + e) - r0, f'#{i} elo {fmt} {r2-r0} != {e}')
                    check(abs(r2 - r0) <= 24, f'#{i} elo unbounded')
            elif fmt == 'ffa':
                info = rounds[0][0] if rounds and rounds[0][0] else None
                if info and rounds[0][1] != 'forfeit':
                    scores = [rounds[0][2]] + [o_['score'] for o_ in info['opps']]
                    places, pay = ffa_split(scores, ffa_prizes(stake))
                    exp = pay[0] if stake > 0 else 0
                    check(payout == exp, f'#{i} ffa payout {payout} != {exp} scores {scores} stake {stake}')
                    check(last['place'] == places[0], f'#{i} ffa place')
                    gid = info['gid']; r0 = S0['games'].get(gid, {}).get('r', 1200)
                    e = elo_ffa([r0] + [o_['rating'] for o_ in info['opps']], scores)
                    check(S2['games'][gid]['r'] - r0 == e, f'#{i} ffa elo {S2["games"][gid]["r"] - r0} != {e}')
                    exp_o = ('draw' if places.count(1) > 1 else 'win') if places[0] == 1 else ('place' if payout > stake else 'loss')
                    check(o == exp_o, f'#{i} ffa outcome {o} != {exp_o} place {places[0]} payout {payout} stake {stake}')
                    stats.setdefault('ffa_outcomes', {}); stats['ffa_outcomes'][o] = stats['ffa_outcomes'].get(o, 0) + 1
                    check(S2['dp'] - S0['dp'] == dp_for(o, stake), f'#{i} ffa dp rule {S2["dp"]-S0["dp"]} vs {dp_for(o, stake)}')
                    if o == 'place': check(S2['streak'] == S0['streak'], f'#{i} place changed streak')
                else:
                    check(payout == 0, f'#{i} ffa forfeit paid {payout}')
            elif fmt == 'tournament':
                pool, ch, ru, se = tour_prizes(stake)
                stg = last['stage']
                exp = [0, se, ru, ch][stg] if stake > 0 else 0
                check(payout == exp, f'#{i} tour payout {payout} != {exp} stage {stg}')
                check(S2['tp'] - S0['tp'] == [10, 25, 50, 100][stg], f'#{i} tp delta')
                n_rounds = sum(1 for r in rounds if r[1] in ('win', 'loss', 'forfeit'))
                ties = sum(1 for r in rounds if r[1] == 'draw'); n_rounds += ties // 3
                recd = sum(S2['rec'].values()) - sum(S0['rec'].values())
                check(recd == n_rounds, f'#{i} tour rec delta {recd} != rounds {n_rounds} {[r[1] for r in rounds]}')
            check(S2['streak'] == 0 or S2['streak'] >= 1, 'streak')
            if len(FAILS) > nf0:
                print('   DEBUG', dict(i=i, fmt=fmt, gid=gid, stake=stake, path=path, ended_by=ended_by, rounds=[(r[0] and r[0]['gid'], r[1], r[2]) for r in rounds], cu=cu, last=last))
            page.evaluate("DGApp.close()")
            if stats['matches'] % 50 == 0:
                print('..', stats['matches'], 'matches, fails', len(FAILS), flush=True)
        print('console errors:', errs(page)[:5])
        S = snapshot(page)
        tot = S['rec']['w'] + S['rec']['l'] + S['rec']['d']
        print('final rec', S['rec'], 'streak', S['streak'], 'best', S['bestStreak'], 'history', len(S['history']))
    print(json.dumps(stats))
    print('FAILS', len(FAILS))
    for f in FAILS[:40]: print(' ', f)
main()
