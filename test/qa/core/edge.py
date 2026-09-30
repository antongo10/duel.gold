"""Edge cases: stake validation via hooks, double-click Find, rematch with low balance, concurrent start,
close in each phase, reload mid-match, under-18 on every staked path, loss limit + rollover, cool-off expiry/bypass."""
from qa_common import *
R = []
def rep(name, ok, detail=''):
    R.append((name, ok, detail)); print(('OK  ' if ok else 'BUG ') + name, detail)

def run_to(page, ph, t=20):
    page.wait_for_function(f"DGApp.current() && DGApp.current().phase === '{ph}'", timeout=t*1000)

with browser_page() as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(20)")
    S = lambda: page.evaluate("DGApp.state()")
    # 1. stake validation through the hook
    for stake, want_err in [(10, False), (9, True), (-50, True), (10.9, False), ('abc', False), (10**9, True), (float('inf'), True)]:
        g0 = S()['gold']
        e = page.evaluate("(s)=>DGApp.startMatch({game:'rush', format:'1v1', stake:s})", stake if stake != float('inf') else 1e400)
        cu = page.evaluate("DGApp.current()")
        taken = g0 - S()['gold']
        rep(f'stake {stake!r} via hook', bool(e) == want_err, f'err={e!r} taken={taken} escrow={cu and cu["escrow"]}')
        page.evaluate("DGApp.close()")
    # 2. double click on Find opponent (real UI)
    page.evaluate("DGApp.go('home')")
    page.click('#dnS-100')
    g0 = S()['gold']
    page.evaluate("() => { const b = document.querySelector('#dnFind'); b.click(); b.click(); }")
    page.wait_for_timeout(100)
    rep('double click Find opponent escrows once', g0 - S()['gold'] == 100, f'taken {g0 - S()["gold"]}')
    # 3. start another match while one is running
    e = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:50})")
    e2 = page.evaluate("DGApp.watch(0)")
    rep('second start while running refused', bool(e) and bool(e2), f'{e!r} / {e2!r}')
    page.evaluate("DGApp.close()")
    page.evaluate("DGApp.setSpeed(1)")
    g0 = S()['gold']; page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100})"); ph = page.evaluate("DGApp.current().phase"); page.evaluate("DGApp.close()")
    rep('close in matchmaking refunds', S()['gold'] == g0, f'{ph}: {g0} -> {S()["gold"]}')
    page.evaluate("DGApp.setSpeed(20)")
    # 4. close in each phase (1v1 race stake 100)
    for target in ['versus_or_ready', 'play', 'result']:
        g0 = S()['gold']; h0 = len(S()['history'])
        page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100})")
        run_to(page, 'ready')
        if target in ('play', 'result'):
            page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
        if target == 'result':
            page.evaluate("DGApp.ctx().end({score: 1e6})"); run_to(page, 'result')
        page.evaluate("DGApp.close()")
        s = S(); d = s['gold'] - g0
        rep(f'close in {target}', (d == 80 if target == 'result' else d == -100) and len(s['history']) == h0 + 1, f'delta {d}, history +{len(s["history"]) - h0}, last {s["history"][0]["o"]}')
    # 5. rematch when balance is too low
    page.evaluate("DGApp.set({gold: 300})")
    page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:300})")
    run_to(page, 'ready'); page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
    page.evaluate("DGApp.ctx().end({score: 0})"); run_to(page, 'result')
    dis = page.evaluate("document.querySelector('#resRematch').disabled")
    rep('rematch disabled when balance < stake', dis, f'gold {S()["gold"]}')
    page.evaluate("document.querySelector('#resRematch').removeAttribute('disabled'); document.querySelector('#resRematch').click()")
    page.wait_for_timeout(200)
    rep('forced rematch click still refused', S()['gold'] == 0 and page.evaluate("DGApp.current()") is None, f'gold {S()["gold"]} cur {page.evaluate("DGApp.current()")}')
    page.evaluate("DGApp.set({gold: 10000})")
    # 6. rematch reuses opponents + new seed
    page.evaluate("DGApp.startMatch({game:'rush', format:'ffa', stake:100})")
    run_to(page, 'ready'); c1 = page.evaluate("DGApp.current()")
    page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
    page.evaluate("DGApp.ctx().end({score: 0})"); run_to(page, 'result')
    page.click('#resRematch'); run_to(page, 'ready'); c2 = page.evaluate("DGApp.current()")
    rep('rematch same opponents, new seed', [o['name'] for o in c1['opps']] == [o['name'] for o in c2['opps']] and c1['seed'] != c2['seed'], '')
    page.evaluate("DGApp.close()")
    # 7. reload mid-match: is the escrowed stake lost?
    for fmt in ['1v1', 'tournament', 'mix']:
        g0 = S()['gold']; h0 = len(S()['history']); net0 = S()['today']['net']
        page.evaluate(f"DGApp.startMatch({{game:'{'rush' if fmt != 'mix' else 'any'}', format:'{fmt}', stake:500}})")
        run_to(page, 'ready'); page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
        page.reload(); page.wait_for_function("window.DG && DG.__appReady === true")
        page.evaluate("DGApp.setSpeed(20)")
        s = S()
        rep(f'reload mid-{fmt}: stake handled', s['gold'] == g0 or (len(s['history']) == h0 + 1), f'gold {g0} -> {s["gold"]}, history +{len(s["history"]) - h0}, today.net {net0} -> {s["today"]["net"]}, played {s["today"]["played"]}')
    # 8. loss limit escape via reload
    page.evaluate("DGApp.set({gold: 10000, limits: {loss: 1000, remind: 0, coolUntil: 0}})")
    lost = 0
    for k in range(4):
        e = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:900})")
        if e: print('   start refused:', e); break
        run_to(page, 'ready'); page.reload(); page.wait_for_function("window.DG && DG.__appReady === true"); page.evaluate("DGApp.setSpeed(20)")
        lost += 900
    s = S()
    rep('loss limit 1000 holds across reloads', 10000 - s['gold'] <= 1000, f'gold lost {10000 - s["gold"]} while today.net = {s["today"]["net"]}, stakeError(100) = {page.evaluate("DGP.stakeError(100)")!r}')
    page.evaluate("DGApp.setSpeed(20)")
    # 9. loss limit arithmetic across several matches + midnight rollover
    page.evaluate("DGApp.set({gold: 10000, limits: {loss: 1000, remind: 0, coolUntil: 0}})")
    page.evaluate("DGApp.advanceDays(1)")
    seq = []
    for stake, win in [(400, False), (300, True), (500, False), (440, False)]:
        e = page.evaluate(f"DGApp.startMatch({{game:'rush', format:'1v1', stake:{stake}}})")
        if e: seq.append((stake, 'refused', e)); continue
        run_to(page, 'ready'); page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
        page.evaluate(f"DGApp.ctx().end({{score: {1e7 if win else -1}}})"); run_to(page, 'result'); page.evaluate("DGApp.close()")
        seq.append((stake, 'win' if win else 'loss', S()['today']['net']))
    room = page.evaluate("DGP.lossRoom()")
    rep('loss-limit arithmetic', seq[-1][1] == 'refused' and room == 1000 - 660, f'{seq} room={room}')
    e = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:340})")
    rep('stake == remaining room allowed', e == '', repr(e)); page.evaluate("DGApp.close()")
    page.evaluate("DGApp.advanceDays(1)")
    rep('midnight rollover resets room', page.evaluate("DGP.lossRoom()") == 1000 and S()['today']['net'] == 0, f'room {page.evaluate("DGP.lossRoom()")}')
    # 10. cool-off expiry and bypass
    page.evaluate("DGApp.set({limits: {loss: 0, remind: 0, coolUntil: DGP.clock.now() + 86400000}})")
    rep('cool-off blocks stakes', page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:50})") != '', '')
    rep('cool-off allows free play', page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:0})") == ''); page.evaluate("DGApp.close()")
    page.evaluate("DGApp.advanceDays(1.01)")
    rep('cool-off expires', page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:50})") == ''); page.evaluate("DGApp.close()")
    page.evaluate("DGApp.set({limits: {loss: 1000, remind: 0, coolUntil: DGP.clock.now() + 7*86400000}})")
    page.evaluate("DGApp.go('settings')"); page.click('#resetBtn'); page.click('#confirmYes'); page.wait_for_timeout(100)
    if page.locator('#ageAdult').count(): page.click('#ageAdult')
    s = S()
    rep('Reset demo data keeps cool-off / loss limit', s['limits']['coolUntil'] > 0 and s['limits']['loss'] == 1000, f'after reset limits={s["limits"]}')
    # 11. under-18
    page.evaluate("DGApp.set({age: 'minor'})")
    paths = {}
    paths['hook 1v1'] = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:50})")
    paths['hook tournament'] = page.evaluate("DGApp.startMatch({game:'rush', format:'tournament', stake:100})")
    paths['friend challenge'] = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100, opponent:{name:'Mira', rating:1320}})")
    paths['weekend tour'] = page.evaluate("DGP.tours().find(t=>t.id==='weekend').block()")
    paths['high stakes tour'] = page.evaluate("DGP.tours().find(t=>t.id==='high').block()")
    paths['daily (free, 5000 added)'] = page.evaluate("DGP.tours().find(t=>t.id==='daily').block()")
    page.evaluate("DGApp.go('home')")
    paths['UI stake chips disabled'] = page.evaluate("[...document.querySelectorAll('#dnBody [data-stake]')].filter(b=>b.dataset.stake!=='0').every(b=>b.disabled)")
    for k, v in paths.items(): print('   minor:', k, '->', repr(v))
    rep('under-18 blocks every staked path', all(paths[k] for k in ['hook 1v1', 'hook tournament', 'friend challenge', 'weekend tour', 'high stakes tour']) and paths['UI stake chips disabled'] is True)
    # rematch for a minor after flipping age mid-result
    page.evaluate("DGApp.set({age: 'adult'})")
    page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:100})"); run_to(page, 'ready')
    page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
    page.evaluate("DGApp.set({age: 'minor'})")
    page.evaluate("DGApp.ctx().end({score: 1e7})"); run_to(page, 'result')
    rep('rematch disabled for minor', page.evaluate("document.querySelector('#resRematch').disabled"))
    page.evaluate("DGApp.close()")
    # can a minor self-upgrade?
    page.evaluate("DGApp.go('settings')")
    has = page.locator('#ageAgain').count()
    if has:
        page.click('#ageAgain'); page.click('#ageAdult')
    rep('minor cannot self-declare adult from Settings', S()['age'] == 'minor', f'ageAgain button={has}, age now {S()["age"]}')
    # 12. loss limit can be switched off instantly
    page.evaluate("DGApp.set({age:'adult', limits:{loss:1000, remind:0, coolUntil:0}, today: Object.assign(DGApp.state().today, {net:-1000})})")
    blocked = page.evaluate("DGP.stakeBlock()")
    page.evaluate("DGApp.go('settings')"); page.click('#loss-0')
    rep('loss limit cannot be lifted instantly once reached', page.evaluate("DGP.stakeBlock()") != '', f'blocked before: {blocked!r}; after Off: {page.evaluate("DGP.stakeBlock()")!r}')
    print('console errors:', errs(page)[:3])
