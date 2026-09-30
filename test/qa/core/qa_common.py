"""Shared helpers for core QA scripts (real app: dist/preview.html)."""
import sys, pathlib, json, time
sys.path.insert(0, '/home/claude/duel-gold/test')
from dglib import browser_page, open_app  # noqa
APP = '/home/claude/duel-gold/dist/preview.html'
RACE = ['sudoku', 'mines', 'queens', 'tiles2048', 'memory', 'reaction', 'aim', 'rush', 'darts', 'base', 'city', 'restaurant', 'trivia', 'groups']
VERSUS = ['chess', 'four', 'reversi', 'gomoku', 'hockey', 'durak', 'liars', 'auction']

def boot(page, adult=True, init=None):
    if init:
        for s in (init if isinstance(init, list) else [init]):
            page.add_init_script(s)
    open_app(page, APP)
    page.wait_for_function("window.DG && DG.__appReady === true", timeout=20000)
    if adult and page.locator('#ageAdult').count():
        page.click('#ageAdult')

def errs(page):
    return [c for c in page._console if c.startswith(('error', 'pageerror')) and 'Failed to load resource' not in c]
