import json
from qalib import *
from finish import play_round, FIN
def rep(*a): print(*a, flush=True)
with new_page_ctx(1280) as page:
    boot(page); page.evaluate("DGApp.setSpeed(4)")
    # tournament forfeit mid semi (after winning QF)
    g0 = st(page)['gold']
    page.evaluate("DGApp.startMatch({game:'trivia', format:'tournament', stake:100})")
    play_round(page)
    page.wait_for_function("DGApp.current().phase==='result' || (DGApp.current().tour && DGApp.current().tour.round===1)", timeout=60000)
    rep('after QF', cur(page)['tour'], cur(page)['phase'])
    if cur(page)['phase'] != 'result':
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(800)
        page.click('#ovForfeit'); page.click('#forfeitYes'); wait_result(page, 10)
        L = last(page); rep('tour forfeit in SF:', L, 'gold delta', st(page)['gold'] - g0, 'expected', -100 + 54, 'hist', st(page)['history'][0]['s'])
        shot(page, 'tour-forfeit-sf')
        rep('bracket', page.inner_text('[data-test=bracket]').replace('\n', ' | '))
    page.click('[data-test=back]')
    # tournament lose in QF on purpose (forfeit at rules card)
    g0 = st(page)['gold']
    page.evaluate("DGApp.startMatch({game:'four', format:'tournament', stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('#ovForfeit'); page.click('#forfeitYes'); wait_result(page, 10)
    rep('tour QF forfeit', last(page), 'gold delta', st(page)['gold'] - g0)
    page.click('[data-test=rematch]'); page.wait_for_selector('[data-test=bracket]')
    rep('Enter again ->', cur(page)['format'], cur(page)['games'], 'gold', st(page)['gold'] - g0)
    page.evaluate("DGApp.forfeit()"); page.click('[data-test=back]')
    # mix forfeit in round 2
    g0 = st(page)['gold']
    page.evaluate("DGApp.startMatch({game:'any', format:'mix', stake:100})")
    play_round(page)
    page.wait_for_function("DGApp.current().phase==='result' || (DGApp.current().mix && DGApp.current().mix.rounds.length===1)", timeout=60000)
    page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(500)
    page.click('#ovForfeit'); page.click('#forfeitYes'); wait_result(page, 10)
    rep('mix forfeit r2', last(page), 'gold delta', st(page)['gold'] - g0, 'hist', st(page)['history'][0])
    shot(page, 'mix-forfeit')
    games = cur(page)['games']
    page.click('[data-test=rematch]'); page.wait_for_selector('[data-test=mix]')
    rep('mix rematch games', cur(page)['games'], 'prev', games, 'same opp', cur(page)['opps'])
    page.evaluate("DGApp.forfeit()"); page.click('[data-test=back]')
    # 2v2 and FFA forfeit
    for f in ('2v2', 'ffa'):
        g0 = st(page)['gold']
        page.evaluate(f"DGApp.startMatch({{game:'sudoku', format:'{f}', stake:100}})")
        page.wait_for_selector('[data-test=start]:not([disabled])'); page.click('[data-test=start]'); page.wait_for_timeout(500)
        page.click('#ovForfeit'); page.click('#forfeitYes'); wait_result(page, 10)
        rep(f, 'forfeit', last(page), 'gold delta', st(page)['gold'] - g0)
        page.click('[data-test=back]')
    # cancel during matchmaking refunds
    g0 = st(page)['gold']
    page.evaluate("DGApp.startMatch({game:'sudoku', format:'1v1', stake:250})"); page.click('#mmCancel')
    rep('mm cancel refund', st(page)['gold'] - g0, 'history unchanged')
    rep('errors', errs(page))
