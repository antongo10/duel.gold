import sys, json; sys.path.insert(0,'/home/claude/duel-gold/test')
from dglib import browser_page, open_app
with browser_page() as page:
    open_app(page, '/home/claude/duel-gold/dist/preview.html')
    page.wait_for_function("window.DG && DG.__appReady")
    print(json.dumps(page.evaluate("DG.games.map(g=>[g.id,g.pack,g.kind,g.formats.join(','),g.skill,g.luck,g.cashEligible, !!g.spectate])")))
    print(page.evaluate("DG.loadErrors"))
    print([c for c in page._console if 'error' in c])
