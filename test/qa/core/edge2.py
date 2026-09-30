"""Re-verification: each case runs in a fresh page. Covers reload/close semantics, reset keeping limits/age,
24 h delay on raising/removing a loss limit, minor age lock, FFA 2nd-place recording, stake edge cases."""
from qa_common import *
def rep(name, ok, detail=''): print(('OK  ' if ok else 'BUG ') + name, detail)
def run_to(page, ph, t=20): page.wait_for_function(f"DGApp.current() && DGApp.current().phase === '{ph}'", timeout=t*1000)
def play(page, g='rush', fmt='1v1', stake=100):
    e = page.evaluate("(o)=>DGApp.startMatch(o)", {'game': g, 'format': fmt, 'stake': stake}); assert not e, e
    run_to(page, 'ready'); page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
def reboot(page):
    page.reload(); page.wait_for_function("window.DG && DG.__appReady === true"); page.evaluate("DGApp.setSpeed(20)")
S = lambda p: p.evaluate("DGApp.state()")

# 1 reload semantics per phase/format
for fmt, where in [('1v1', 'mm'), ('1v1', 'ready'), ('1v1', 'play'), ('tournament', 'play'), ('mix', 'play'), ('2v2', 'play'), ('ffa', 'ready'), ('1v1', 'result')]:
    with browser_page() as page:
        boot(page); page.evaluate("DGApp.setSpeed(20)" if where != 'mm' else "DGApp.setSpeed(1)")
        s0 = S(page)
        page.evaluate("(o)=>DGApp.startMatch(o)", {'game': 'any' if fmt == 'mix' else 'rush', 'format': fmt, 'stake': 500})
        if where in ('ready', 'play', 'result'): run_to(page, 'ready')
        if where in ('play', 'result'): page.evaluate("document.querySelector('#mStart').click()"); run_to(page, 'play')
        if where == 'result': page.evaluate("DGApp.ctx().end({score:1e7})"); run_to(page, 'result')
        reboot(page); s1 = S(page)
        d = s1['gold'] - s0['gold']; h = len(s1['history']) - len(s0['history'])
        exp = 0 if where == 'mm' else 400 if where == 'result' else -500
        ok = d == exp and h == (0 if where == 'mm' else 1) and s1.get('active') is None and s1['today']['net'] == exp
        rep(f'reload {fmt}@{where}', ok, f'delta {d} (exp {exp}) hist +{h} today.net {s1["today"]["net"]} rec {s1["rec"]} active={s1.get("active")} notice={page.evaluate("DGP.match.notice || null")!r} errs={errs(page)[:1]}')

# 2 reload twice / reload after close must not double-settle; tournament 'once' re-entry after mm refund
with browser_page() as page:
    boot(page); page.evaluate("DGApp.setSpeed(20)")
    play(page, stake=300); reboot(page); g1 = S(page)['gold']; reboot(page)
    rep('second reload does not settle again', S(page)['gold'] == g1 and len(S(page)['history']) == 1, f'{g1} -> {S(page)["gold"]}')
    play(page, stake=300); page.evaluate("DGApp.close()"); g2 = S(page)['gold']; reboot(page)
    rep('close then reload no double charge', S(page)['gold'] == g2 and len(S(page)['history']) == 2, f'{g2} -> {S(page)["gold"]}, hist {len(S(page)["history"])}')
    # free match reload now counts
    play(page, g='chess', stake=0); reboot(page)
    rep('free chess reload counts as loss', (S(page)['games'].get('chess') or {}).get('l') == 1)

# 3 reset keeps limits/age/cool-off
with browser_page() as page:
    boot(page)
    page.evaluate("DGApp.set({limits:{loss:1000, remind:0, coolUntil: DGP.clock.now()+7*86400000, pending:null}})")
    page.evaluate("DGApp.go('settings')"); page.click('#resetBtn'); page.click('#confirmYes'); page.wait_for_timeout(200)
    s = S(page)
    rep('reset keeps limits/cool-off/age', s['limits']['loss'] == 1000 and s['limits']['coolUntil'] > 0 and s['age'] == 'adult' and not page.locator('#ageAdult').count() and s['gold'] == 10000,
        f'limits {s["limits"]} age {s["age"]} gold {s["gold"]} gate={page.locator("#ageAdult").count()}')
    page.evaluate("DGApp.set({age:'minor'})"); page.evaluate("DGApp.go('settings')"); page.click('#resetBtn'); page.click('#confirmYes'); page.wait_for_timeout(200)
    rep('reset keeps minor', S(page)['age'] == 'minor' and not page.locator('#ageAdult').count())

# 4 loss limit raise/remove delay
with browser_page() as page:
    boot(page); page.evaluate("DGApp.setSpeed(20)")
    page.evaluate("DGApp.go('settings')"); page.click('#loss-1000')
    rep('setting a first (stricter) limit is instant', S(page)['limits']['loss'] == 1000, str(S(page)['limits']))
    page.evaluate("DGApp.set({today: Object.assign(DGApp.state().today, {date: DGP.dayKey(), net:-1000})})")
    page.evaluate("DGApp.go('settings')"); page.click('#loss-0')
    b1 = page.evaluate("DGP.stakeBlock()")
    page.evaluate("DGApp.go('settings')"); page.click('#loss-5000'); b1b = page.evaluate("DGP.stakeBlock()"); L1 = S(page)['limits']
    page.fill('#lossCustom', '999999'); page.click('#lossSet'); b1c = page.evaluate("DGP.stakeBlock()")
    rep('remove/raise limit is delayed', bool(b1) and bool(b1b) and bool(b1c) and S(page)['limits']['loss'] == 1000, f'after Off: {b1!r}; limits {L1}; custom raise block {b1c!r}')
    page.evaluate("DGApp.go('settings')"); page.click('#loss-2500'); lower_after = S(page)['limits']
    page.evaluate("DGApp.advanceDays(0.5)"); m = S(page)['limits']['loss']
    reboot(page); page.evaluate("DGApp.advanceDays(0.99)"); page.evaluate("DGApp.go('settings')")
    rep('pending applies after 24 h (incl. reload)', S(page)['limits']['loss'] in (2500, 0, 999999) and m == 1000, f'at 12h: {m}; at 24h+: {S(page)["limits"]}; pending set {lower_after}')
    # stricter cancels pending
    page.evaluate("DGApp.set({limits:{loss:2500, remind:0, coolUntil:0, pending:null}})"); page.evaluate("DGApp.go('settings')")
    page.click('#loss-5000'); page.click('#loss-1000')
    rep('stricter limit applies instantly + clears pending', S(page)['limits']['loss'] == 1000 and not S(page)['limits'].get('pending'), str(S(page)['limits']))
    # hook bypass?
    page.evaluate("DGApp.set({limits:{loss:0, remind:0, coolUntil:0, pending:null}})")
    rep('(info) DGApp.set can still bypass (test hook only)', True, str(S(page)['limits']))

# 5 minor age lock
with browser_page() as page:
    boot(page, adult=False); page.click('#ageMinor')
    page.evaluate("DGApp.go('settings')")
    btn = page.locator('#ageAgain').count()
    page.evaluate("DGP.ageGate(true)"); gate = page.locator('#ageAdult').count()
    reboot(page)
    rep('minor cannot change age (UI, ageGate(true), reload)', btn == 0 and gate == 0 and S(page)['age'] == 'minor', f'btn {btn} gate {gate} age {S(page)["age"]}')

# 6 FFA 2nd place recording
with browser_page() as page:
    boot(page); page.evaluate("DGApp.setSpeed(20)")
    page.evaluate("DGApp.set({streak: 2, bestStreak: 2})")
    play(page, fmt='ffa', stake=100)
    info = page.evaluate("() => { const c = DGApp.ctx(), g = DG.getGame('rush'); return c.opponents.map(p => g.bot(c.seed, p.skill, DG.util.rng(c.seed + ':' + p.name), c.mode).score); }")
    s = sorted(info, reverse=True)
    my = (s[0] + s[1]) / 2 if s[0] != s[1] else s[0] - 0.5
    page.evaluate("(x)=>DGApp.ctx().end({score:x})", my); run_to(page, 'result')
    st = S(page); last = page.evaluate("DGApp.last()"); h = st['history'][0]
    title = page.inner_text('#resTitle')
    page.evaluate("DGApp.go('profile')"); wr = page.inner_text('#tWinrate')
    rep('FFA 2nd = placement', last['outcome'] == 'place' and last['payout'] == 108 and st['streak'] == 2 and st['rec']['l'] == 0 and h['o'] == 'place',
        f'outcome {last["outcome"]} payout {last["payout"]} streak {st["streak"]} rec {st["rec"]} today {st["today"]} title {title!r} winrate tile {wr!r} hist o={h["o"]} dp {last["dp"]}')
    print('   profile history row:', page.evaluate("document.querySelector('#histTable tbody tr') && document.querySelector('#histTable tbody tr').innerText"))
    print('   errors', errs(page)[:2])

# 7 earlier-OK edge cases still OK
with browser_page() as page:
    boot(page); page.evaluate("DGApp.setSpeed(1)")
    for stake, want in [(10, ''), (9, 'err'), (-50, 'err'), (10**9, 'err'), ('abc', '?'), (10.9, '?')]:
        g0 = S(page)['gold']; e = page.evaluate("(s)=>DGApp.startMatch({game:'rush', format:'1v1', stake:s})", stake); taken = g0 - S(page)['gold']; page.evaluate("DGApp.close()")
        print(f'   stake {stake!r}: err={e!r} taken={taken}')
    page.evaluate("DGApp.go('home')"); page.click('#dnS-100'); g0 = S(page)['gold']
    page.evaluate("() => { const b = document.querySelector('#dnFind'); b.click(); b.click(); }"); page.wait_for_timeout(100)
    rep('double-click Find', g0 - S(page)['gold'] == 100); page.evaluate("DGApp.close()")
    rep('close in mm refunds', S(page)['gold'] == g0)
    page.evaluate("DGApp.setSpeed(20)")
    page.evaluate("DGApp.set({gold: 300})"); play(page, stake=300); page.evaluate("DGApp.ctx().end({score:-1})"); run_to(page, 'result')
    rep('rematch disabled when broke', page.evaluate("document.querySelector('#resRematch').disabled")); page.evaluate("DGApp.close()")
    print('   errors', errs(page)[:2])
