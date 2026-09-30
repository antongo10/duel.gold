"""Known issue check: Sudoku (and other solve-or-nothing races) finish rates by skill, mix and full."""
from qa_common import *
JS = r"""
({gid, mode, n, solvedMin}) => {
  const g = DG.getGame(gid), U = DG.util, out = [];
  for (const sk of [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.98]) {
    let fin = 0, sum = 0;
    for (let i = 0; i < n; i++) { const seed = 300000 + i * 104729; const r = g.bot(seed, sk, U.rng(seed + ':Kofi'), mode); if (r.score >= solvedMin) fin++; sum += r.score; }
    out.push([sk, fin, Math.round(sum / n)]);
  }
  const hum = g.lab && g.lab.human ? (()=>{ let f=0, s=0; for (let i=0;i<n;i++){ const seed=300000+i*104729; const h=g.lab.human(seed, mode); s+=h.score; if (h.score>=solvedMin) f++; } return [f, Math.round(s/n)]; })() : null;
  return {out, hum};
}
"""
with browser_page() as page:
    boot(page)
    for gid, thr in [('sudoku', 2000), ('mines', 2000), ('queens', 1000)]:
        for mode in ['mix', 'full']:
            r = page.evaluate(JS, {'gid': gid, 'mode': mode, 'n': 100, 'solvedMin': thr})
            print(gid, mode, 'finish-rate/100 & mean by skill:', ' '.join(f"{sk}:{f}%/{m}" for sk, f, m in r['out']), '| lab human (finish, mean):', r['hum'])
