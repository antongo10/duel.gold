def home_start(page, pick, fmt, stake):
    page.click('#tab-home'); page.wait_for_selector('#dnFind')
    if pick.startswith('cat:') or pick in ('any', 'surprise', 'favs'):
        page.click(f'[data-pick="{pick}"]')
    else:
        page.select_option('#dnGame', pick)
    page.click(f'#dnF-{fmt}')
    page.click(f'#dnS-{stake}')
    page.click('#dnFind')
