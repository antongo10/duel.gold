"""Bot calibration: game.bot over 50 seeds x skills 0.1/0.5/0.9 x modes. Flags cliffs, zero-heavy, inversions."""
import json
from qa_common import *
JS = r"""
({gid, mode, n}) => {
  const g = DG.getGame(gid), U = DG.util, out = {};
  for (const sk of [0.1, 0.3, 0.5, 0.7, 0.9]) {
    const arr = []; let tmax = 0, bad = 0;
    const t0 = performance.now();
    for (let i = 0; i < n; i++) {
      const seed = 200000 + i * 7919;
      const r = g.bot(seed, sk, U.rng(seed + ':Mira'), mode);
      arr.push(r.score);
      const tl = r.timeline; if (!tl.length || tl[tl.length-1][1] !== r.score) bad++;
      for (let k = 1; k < tl.length; k++) if (tl[k][0] < tl[k-1][0]) bad++;
    }
    const ms = (performance.now() - t0) / n;
    arr.sort((a,b)=>a-b);
    const mean = arr.reduce((a,b)=>a+b,0)/n;
    out[sk] = {mean: Math.round(mean*10)/10, p10: arr[Math.floor(n*0.1)], med: arr[Math.floor(n/2)], p90: arr[Math.floor(n*0.9)], zeros: arr.filter(x=>x===0).length, msPerBot: Math.round(ms*10)/10, badTl: bad};
  }
  // determinism
  const s = 424242, a = g.bot(s, 0.5, U.rng(s+':X'), mode), b = g.bot(s, 0.5, U.rng(s+':X'), mode);
  out.det = JSON.stringify(a) === JSON.stringify(b);
  return out;
}
"""
with browser_page() as page:
    boot(page)
    res = {}
    for gid in RACE:
        for mode in ['full', 'mix']:
            r = page.evaluate(JS, {'gid': gid, 'mode': mode, 'n': 50})
            res[f'{gid}/{mode}'] = r
            flags = []
            m = [r[str(k)]['mean'] if str(k) in r else r[k]['mean'] for k in ['0.1','0.3','0.5','0.7','0.9']]
            for i in range(4):
                if m[i] > m[i+1]: flags.append(f'INVERSION {[0.1,0.3,0.5,0.7,0.9][i]}>{[0.1,0.3,0.5,0.7,0.9][i+1]}')
            for k in ['0.1','0.5','0.9']:
                if r[k]['zeros'] >= 10: flags.append(f'zeros@{k}={r[k]["zeros"]}/50')
                if r[k]['msPerBot'] > 50: flags.append(f'slow@{k}={r[k]["msPerBot"]}ms')
                if r[k]['badTl']: flags.append(f'badTimeline@{k}')
            if not r['det']: flags.append('NONDETERMINISTIC')
            print(f"{gid:11s} {mode:4s} " + " | ".join(f"{k}: mean {r[k]['mean']:>8} [p10 {r[k]['p10']}, med {r[k]['med']}, p90 {r[k]['p90']}] z{r[k]['zeros']} {r[k]['msPerBot']}ms" for k in ['0.1','0.5','0.9']), ('  <<' + ', '.join(flags)) if flags else '')
    json.dump(res, open('/home/claude/duel-gold/test/qa/core/calib.json', 'w'), indent=1)
