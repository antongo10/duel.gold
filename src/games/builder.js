/* Duel.gold — Pack D: BUILDER & BATTLE
   Games: base (Base Duel), city (City Duel), restaurant (Restaurant Duel). All kind 'race'.
   Each game has a pure, DOM-free engine ("lab") shared by play() and bot(); the lab is also exposed on the
   game definition as `_lab` for automated balance tests. */
(function () {
  "use strict";
  const U = DG.util;
  const clamp = U.clamp;
  const FORMATS = ["1v1", "2v2", "ffa", "tournament", "mix"];

  /* ------------------------------------------------------------------ shared helpers */
  function mmss(ms) {
    const s = Math.max(0, Math.ceil(ms / 1000));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }
  function money(n) {
    const v = Math.round(n);
    return (v < 0 ? "−$" : "$") + Math.abs(v).toLocaleString("en-GB");
  }
  /* A canvas that fills its container width, keeps an aspect ratio and handles devicePixelRatio. */
  function makeCanvas(ctx, host, aspect, draw, maxH) {
    const cv = document.createElement("canvas");
    cv.style.display = "block";
    cv.style.margin = "0 auto";
    cv.style.touchAction = "none";
    host.appendChild(cv);
    const g = cv.getContext("2d");
    const st = { cv, g, w: 0, h: 0, dpr: 1 };
    function fit() {
      let w = Math.max(200, Math.min(860, host.clientWidth || 320));
      const mh = maxH ? maxH() : 1e9;
      if (w / aspect > mh) w = Math.max(200, Math.floor(mh * aspect));
      const h = Math.round(w / aspect);
      cv.style.width = w + "px";
      const dpr = Math.min(3, window.devicePixelRatio || 1);
      if (w === st.w && h === st.h && dpr === st.dpr) return;
      st.w = w; st.h = h; st.dpr = dpr;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      cv.style.height = h + "px";
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!ctx.signal.ended && st.ready) draw();
    }
    fit();
    st.ready = true;
    let ro = null;
    if (window.ResizeObserver) {
      ro = new ResizeObserver(() => { if (ctx.signal.ended) { ro.disconnect(); return; } fit(); });
      ro.observe(host);
    }
    const onWin = () => { if (!ctx.signal.ended) fit(); };
    window.addEventListener("resize", onWin);
    st.fit = fit;
    st.stop = () => { if (ro) ro.disconnect(); ro = null; window.removeEventListener("resize", onWin); };
    if (ctx.onCleanup) ctx.onCleanup(st.stop); else onEndWatch(ctx, st.stop);
    return st;
  }
  /* Watches ctx.signal.ended so observers/listeners die with the match even on abort. */
  function onEndWatch(ctx, fn) {
    const tick = () => { if (ctx.signal.ended) { fn(); return; } setTimeout(tick, 500); };
    setTimeout(tick, 500);
  }

  /* ====================================================================================
     BASE DUEL — engine
     ==================================================================================== */
  const BW = 12, BH = 9;
  const DT = 0.05; // fixed sim step (s)
  const TOWERS = {
    wall:   { name: "Wall",   short: "Wall",   cost: 10, hp: 120, block: true,  desc: "Blocks the path. Zombies walk around it; Brutes smash it." },
    arrow:  { name: "Arrow tower", short: "Arrow", cost: 50, hp: 60, block: true, range: 2.6, dmg: 5, cd: 0.5, desc: "Fast single-target shots (5 dmg). Weak against armoured Brutes. Range 2.6." },
    cannon: { name: "Cannon", short: "Cannon", cost: 90, hp: 80, block: true, range: 2.3, dmg: 22, cd: 1.8, splash: 0.9, desc: "Slow heavy shells (22 dmg) that splash a whole group. Range 2.3." },
    frost:  { name: "Frost tower", short: "Frost", cost: 60, hp: 50, block: true, range: 2.0, dps: 4, slow: 0.45, desc: "Slows every zombie in range to under half speed and chills them. Range 2." },
    spike:  { name: "Spike trap", short: "Spikes", cost: 30, hp: 0, block: false, dps: 12, desc: "Built on the path. Hurts zombies walking over it (12 dmg/s); great under Frost." },
    mine:   { name: "Gold mine", short: "Mine", cost: 60, hp: 40, block: true, income: 1, desc: "Earns 1 gold per second while waves run. Pays off after about 3 waves." },
  };
  const TOWER_ORDER = ["wall", "arrow", "cannon", "frost", "spike", "mine"];
  const ENEMIES = {
    walker:  { name: "Walker",  hp: 30,  spd: 1.3,  dmg: 5,  bounty: 4,  r: 0.22, armor: 1 },
    runner:  { name: "Runner",  hp: 14,  spd: 2.4,  dmg: 3,  bounty: 3,  r: 0.17 },
    brute:   { name: "Brute",   hp: 110, spd: 0.75, dmg: 15, bounty: 12, r: 0.3, wallDps: 30, armor: 4 },
    spitter: { name: "Spitter", hp: 40,  spd: 1.0,  dmg: 6,  bounty: 8,  r: 0.22, range: 2.4, dps: 8 },
  };
  const ENEMY_ORDER = ["walker", "runner", "brute", "spitter"];
  const BASE_HP = 100;

  function baseConfig(mode) {
    return mode === "mix"
      ? { waves: 3, buildMs: 20000, gold: 260, bombs: 2, windowMs: 2000, scale: 3.2, accelMs: 4500, capS: 36, diffs: [2, 3.5, 5] }
      : { waves: 8, buildMs: 60000, gold: 300, bombs: 3, windowMs: 5000, scale: 2, accelMs: 10000, capS: 90, diffs: [1, 2, 3, 4, 5, 6, 7, 8] };
  }
  /* Playback: sim seconds shown per real ms. Presentation only — the sim itself is tick-based. After accelMs of a
     wave, playback runs 3x faster so long waves never drag (keeps mix under 45 s). */
  function baseSimAt(cfg, realMs) {
    const a = cfg.accelMs;
    return (realMs <= a ? realMs * cfg.scale : a * cfg.scale + (realMs - a) * cfg.scale * 3) / 1000;
  }
  function baseRealFor(cfg, simS) {
    const a = cfg.accelMs, simA = a * cfg.scale / 1000;
    return simS <= simA ? simS * 1000 / cfg.scale : a + (simS - simA) * 1000 / (cfg.scale * 3);
  }

  function baseMap(seed, mode) {
    const rng = U.rng("base-map:" + seed);
    for (let attempt = 0; attempt < 50; attempt++) {
      const grid = new Array(BW * BH).fill(0); // 0 free, 1 rock
      const base = { x: BW - 2, y: U.randInt(rng, 2, BH - 3) };
      const nSpawn = rng() < 0.5 ? 2 : 3;
      const spawns = [];
      const cands = [];
      for (let y = 0; y < BH; y++) cands.push({ x: 0, y });
      for (let x = 1; x <= 4; x++) { cands.push({ x, y: 0 }); cands.push({ x, y: BH - 1 }); }
      const sh = U.shuffle(rng, cands);
      for (const c of sh) {
        if (spawns.length >= nSpawn) break;
        if (spawns.every((s) => Math.abs(s.x - c.x) + Math.abs(s.y - c.y) >= 4)) spawns.push(c);
      }
      const nRock = U.randInt(rng, 7, 11);
      let tries = 0;
      while (tries++ < 200 && grid.reduce((a, b) => a + b, 0) < nRock) {
        const x = U.randInt(rng, 1, BW - 1), y = U.randInt(rng, 0, BH - 1);
        if (Math.abs(x - base.x) + Math.abs(y - base.y) <= 1) continue;
        if (spawns.some((s) => Math.abs(s.x - x) + Math.abs(s.y - y) <= 1)) continue;
        grid[y * BW + x] = 1;
      }
      const map = { seed, grid, base, spawns };
      const f = bfsField(map, (i) => grid[i] === 1);
      if (spawns.every((s) => f[s.y * BW + s.x] < 1e9)) {
        // every free tile must be reachable (no sealed pockets)
        let ok = true;
        for (let i = 0; i < BW * BH; i++) if (!grid[i] && f[i] >= 1e9) { grid[i] = 1; }
        if (ok) return map;
      }
    }
    throw new Error("base map generation failed");
  }

  function bfsField(map, blocked) {
    const N = BW * BH, f = new Float64Array(N).fill(1e9);
    const b = map.base.y * BW + map.base.x;
    f[b] = 0;
    const q = new Int16Array(N);
    let tail = 0; q[tail++] = b;
    const visit = (j, v) => { if (f[j] < 1e9 || blocked(j)) return; f[j] = v; q[tail++] = j; };
    for (let h = 0; h < tail; h++) {
      const i = q[h], x = i % BW, y = (i / BW) | 0, v = f[i] + 1;
      if (x < BW - 1) visit(i + 1, v);
      if (x > 0) visit(i - 1, v);
      if (y < BH - 1) visit(i + BW, v);
      if (y > 0) visit(i - BW, v);
    }
    return f;
  }
  /* Dijkstra for Brutes: walls are passable at extra cost (they smash through). */
  function bruteField(map, structs) {
    const N = BW * BH, f = new Float64Array(N).fill(1e9), done = new Uint8Array(N);
    const b = map.base.y * BW + map.base.x;
    f[b] = 0;
    const relax = (i, j) => {
      if (done[j] || map.grid[j]) return;
      const s = structs[j];
      let c = 1;
      if (s) { if (s.type === "wall") c = 1 + s.hp / ENEMIES.brute.wallDps * ENEMIES.brute.spd; else if (TOWERS[s.type].block) return; }
      if (f[i] + c < f[j]) f[j] = f[i] + c;
    };
    for (;;) {
      let i = -1, best = 1e9;
      for (let k = 0; k < N; k++) if (!done[k] && f[k] < best) { best = f[k]; i = k; }
      if (i < 0) break;
      done[i] = 1;
      const x = i % BW, y = (i / BW) | 0;
      if (x < BW - 1) relax(i, i + 1);
      if (x > 0) relax(i, i - 1);
      if (y < BH - 1) relax(i, i + BW);
      if (y > 0) relax(i, i - BW);
    }
    return f;
  }

  function baseWaves(seed, mode) {
    const cfg = baseConfig(mode);
    const rng = U.rng("base-waves:" + seed + ":" + mode);
    const map = baseMap(seed, mode);
    const waves = [];
    cfg.diffs.forEach((d, wi) => {
      const pts = 8 + d * 4.2;
      const pool = ["walker", "walker", "runner"];
      if (d >= 2) pool.push("runner");
      if (d >= 3) pool.push("brute");
      if (d >= 4) pool.push("spitter", "walker");
      if (d >= 6) pool.push("brute", "spitter");
      const cost = { walker: 1, runner: 0.7, brute: 4, spitter: 2 };
      const list = [];
      let left = pts;
      if (d >= 3) { list.push("brute"); left -= cost.brute; }
      if (d >= 4) { list.push("spitter"); left -= cost.spitter; }
      let guard = 0;
      while (left > 0.6 && guard++ < 100) {
        const t = U.pick(rng, pool);
        if (cost[t] > left + 0.5) continue;
        list.push(t); left -= cost[t];
      }
      const order = U.shuffle(rng, list);
      const hpMul = 1 + 0.08 * (d - 1);
      const gap = mode === "mix" ? 0.4 : 0.65;
      let t = 0;
      const spawns = order.map((type) => {
        const e = { t: Math.round(t / DT), type, spawn: Math.floor(rng() * map.spawns.length), hpMul };
        t += gap * (0.6 + rng() * 0.8) * (type === "brute" ? 1.6 : 1);
        return e;
      });
      waves.push({ d, spawns, counts: ENEMY_ORDER.map((k) => [k, list.filter((x) => x === k).length]).filter((c) => c[1]) });
    });
    return { map, waves, cfg };
  }

  /* The simulation. Owns structures, enemies, gold, base HP. Deterministic given the same calls at the same ticks. */
  function BaseSim(seed, mode) {
    const W = baseWaves(seed, mode);
    const S = {
      seed, mode, map: W.map, waves: W.waves, cfg: W.cfg,
      structs: new Array(BW * BH).fill(null),
      enemies: [], fx: [], gold: W.cfg.gold, kills: 0, baseHp: BASE_HP,
      bombs: W.cfg.bombs, bombCd: 0, wave: 0, survived: 0, inWave: false, tick: 0, waveTick: 0,
      over: false, dead: false, spent: 0, nextId: 1, mineAcc: 0, leaks: 0,
      field: null,
      dt: DT, tickScale: 1, // bots may use a coarser step: setStep(0.1)
    };
    S.setStep = function (dt) { S.dt = dt; S.tickScale = dt / DT; };
    const idx = (x, y) => y * BW + x;
    const isBlockedFor = (structs) => (i) => S.map.grid[i] === 1 || (structs[i] && TOWERS[structs[i].type].block);
    function refreshFields() {
      S.list = S.structs.filter(Boolean);
      S.field = bfsField(S.map, isBlockedFor(S.structs));
      S._bf = null;
    }
    Object.defineProperty(S, "bfield", { get() { if (!S._bf) S._bf = S.list.some((q) => q.type === "wall") ? bruteField(S.map, S.structs) : S.field; return S._bf; } });
    refreshFields();

    S.canPlace = function (type, x, y) {
      if (x < 0 || y < 0 || x >= BW || y >= BH) return "Off the map";
      const i = idx(x, y);
      if (S.map.grid[i]) return "Rock";
      if (S.structs[i]) return "Occupied";
      if (x === S.map.base.x && y === S.map.base.y) return "That is your base";
      if (S.map.spawns.some((s) => s.x === x && s.y === y)) return "Spawn point";
      if (TOWERS[type].cost > S.gold) return "Not enough gold";
      if (S.inWave) return "Wait for the wave to end";
      if (type === "spike" && !S.onPath(i)) return "Spikes go on a zombie path";
      if (TOWERS[type].block) {
        const tmp = S.structs.slice(); tmp[i] = { type };
        const f = bfsField(S.map, isBlockedFor(tmp));
        if (!S.map.spawns.every((s) => f[idx(s.x, s.y)] < 1e9)) return "Zombies need a path";
      }
      return "";
    };
    S.place = function (type, x, y) {
      const why = S.canPlace(type, x, y);
      if (why) return why;
      const T = TOWERS[type];
      S.structs[idx(x, y)] = { id: S.nextId++, type, x, y, hp: T.hp, maxHp: T.hp, cd: 0, paid: T.cost, flash: 0 };
      S.gold -= T.cost; S.spent += T.cost;
      refreshFields();
      if (S.onAct) S.onAct("place", [type, x, y]);
      return "";
    };
    S.sell = function (x, y) {
      const i = idx(x, y), s = S.structs[i];
      if (!s) return "Nothing to sell";
      if (S.wave > 0 || S.inWave) return "You can only sell during the build phase";
      S.structs[i] = null; S.gold += s.paid; S.spent -= s.paid;
      refreshFields();
      if (S.onAct) S.onAct("sell", [x, y]);
      return "";
    };
    S.repairCost = (s) => (s && s.hp > 0 && s.maxHp > 0 && s.hp < s.maxHp ? Math.max(1, Math.ceil((1 - s.hp / s.maxHp) * TOWERS[s.type].cost * 0.6)) : 0);
    S.repair = function (x, y) {
      const s = S.structs[idx(x, y)];
      if (!s) return "Tap a damaged structure";
      const c = S.repairCost(s);
      if (!c) return "Not damaged";
      if (c > S.gold) return "Repair costs " + c + " gold";
      S.gold -= c; s.hp = s.maxHp; s.flash = 0.4;
      if (S.onAct) S.onAct("repair", [x, y]);
      return "";
    };
    S.bombRadius = 1.25;
    S.bombDamage = () => 35 + 5 * (S.waves[Math.min(S.wave, S.waves.length - 1)] || { d: 1 }).d;
    S.bomb = function (x, y) {
      if (!S.inWave) return "Firebombs work during waves";
      if (S.bombs <= 0) return "No firebombs left";
      if (S.bombCd > 0) return "Firebomb cooling down";
      S.bombs--; S.bombCd = 5;
      const dmg = S.bombDamage();
      for (const e of S.enemies) if (Math.hypot(e.x - x, e.y - y) <= S.bombRadius + ENEMIES[e.type].r) hurt(e, dmg, true);
      S.fx.push({ k: "bomb", x, y, t: 0.6, r: S.bombRadius });
      if (S.onAct) S.onAct("bomb", [x, y]);
      return "";
    };
    S.startWave = function () {
      if (S.inWave || S.over) return false;
      S.inWave = true; S.waveTick = 0; S.spawnIdx = 0;
      return true;
    };
    function hurt(e, d, hit) {
      if (e.hp <= 0) return;
      if (hit) d = Math.max(1, d - (ENEMIES[e.type].armor || 0)); // armour blunts single hits (arrows, shells, bombs)
      e.hp -= d;
      if (e.hp <= 0) { S.kills++; S.gold += ENEMIES[e.type].bounty; }
    }
    function destroy(s) {
      S.structs[idx(s.x, s.y)] = null;
      if (!S.headless) S.fx.push({ k: "boom", x: s.x + 0.5, y: s.y + 0.5, t: 0.4 });
      refreshFields();
    }
    function progressOf(e) { return (e.type === "brute" ? S.bfield : S.field)[e.ti] || 0; }
    function nextTile(e) {
      const f = e.type === "brute" ? S.bfield : S.field;
      const i = e.ti, x = i % BW, y = (i / BW) | 0;
      let best = -1, bv = f[i];
      if (x < BW - 1 && f[i + 1] < bv) { bv = f[i + 1]; best = i + 1; }
      if (y < BH - 1 && f[i + BW] < bv) { bv = f[i + BW]; best = i + BW; }
      if (x > 0 && f[i - 1] < bv) { bv = f[i - 1]; best = i - 1; }
      if (y > 0 && f[i - BW] < bv) { bv = f[i - BW]; best = i - BW; }
      return best;
    }
    const d2 = (ax, ay, bx, by) => (ax - bx) * (ax - bx) + (ay - by) * (ay - by);
    S.step = function () {
      const DT = S.dt;
      if (S.over) return;
      S.tick++;
      if (!S.headless) {
        for (const f of S.fx) f.t -= DT;
        if (S.fx.length) S.fx = S.fx.filter((f) => f.t > 0);
        for (const s of S.list) if (s.flash > 0) s.flash -= DT;
      }
      if (!S.inWave) return;
      const wv = S.waves[S.wave];
      if (S.bombCd > 0) S.bombCd = Math.max(0, S.bombCd - DT);
      // spawns
      while (S.spawnIdx < wv.spawns.length && wv.spawns[S.spawnIdx].t <= S.waveTick * S.tickScale + 1e-9) {
        const sp = wv.spawns[S.spawnIdx++], E = ENEMIES[sp.type], p = S.map.spawns[sp.spawn];
        const hp = Math.round(E.hp * sp.hpMul);
        S.enemies.push({ id: S.nextId++, type: sp.type, x: p.x + 0.5, y: p.y + 0.5, ti: idx(p.x, p.y), to: -1, hp, maxHp: hp, slow: 1, busy: 0 });
      }
      S.waveTick++;
      // mines
      for (const s of S.list) if (s.type === "mine" && s.hp > 0) S.mineAcc += TOWERS.mine.income * DT;
      if (S.mineAcc >= 1) { const g = Math.floor(S.mineAcc); S.gold += g; S.mineAcc -= g; }
      // frost aura + spikes
      for (const e of S.enemies) e.slow = 1;
      for (const s of S.list) {
        if (s.type === "frost") {
          const cx = s.x + 0.5, cy = s.y + 0.5, R2 = TOWERS.frost.range * TOWERS.frost.range;
          for (const e of S.enemies) if (e.hp > 0 && d2(e.x, e.y, cx, cy) <= R2) { e.slow = TOWERS.frost.slow; hurt(e, TOWERS.frost.dps * DT); }
        } else if (s.type === "spike") {
          for (const e of S.enemies) if (e.hp > 0 && Math.floor(e.x) === s.x && Math.floor(e.y) === s.y) hurt(e, TOWERS.spike.dps * DT);
        }
      }
      // towers fire
      for (const s of S.list) {
        if (s.hp <= 0 || (s.type !== "arrow" && s.type !== "cannon")) continue;
        if (s.cd > 0) s.cd -= DT;
        if (s.cd > 1e-9) continue;
        const T = TOWERS[s.type], cx = s.x + 0.5, cy = s.y + 0.5, R2 = T.range * T.range;
        let tgt = null, tp = 1e9;
        for (const e of S.enemies) {
          if (e.hp <= 0 || d2(e.x, e.y, cx, cy) > R2) continue;
          const p = progressOf(e);
          if (p < tp || (p === tp && e.id < tgt.id)) { tp = p; tgt = e; }
        }
        if (!tgt) continue;
        s.cd += T.cd;
        if (s.type === "arrow") { hurt(tgt, T.dmg, true); if (!S.headless) S.fx.push({ k: "shot", x: cx, y: cy, x2: tgt.x, y2: tgt.y, t: 0.12 }); }
        else {
          const tx0 = tgt.x, ty0 = tgt.y, SP2 = T.splash * T.splash;
          for (const e of S.enemies) if (e.hp > 0 && d2(e.x, e.y, tx0, ty0) <= SP2) hurt(e, T.dmg, true);
          if (!S.headless) S.fx.push({ k: "splash", x: tgt.x, y: tgt.y, t: 0.3, r: T.splash, x0: cx, y0: cy });
        }
      }
      // enemies act
      for (const e of S.enemies) {
        if (e.hp <= 0) continue;
        const E = ENEMIES[e.type];
        if (e.type === "spitter") {
          let tgt = null, td = 1e9;
          for (const s of S.list) {
            if (s.hp <= 0 || s.type === "wall" || s.type === "spike") continue;
            const d = d2(s.x + 0.5, s.y + 0.5, e.x, e.y);
            if (d <= E.range * E.range && (d < td || (d === td && s.id < tgt.id))) { td = d; tgt = s; }
          }
          if (tgt) {
            tgt.hp -= E.dps * DT; tgt.flash = 0.1;
            if (!S.headless && S.tick % 8 === 0) S.fx.push({ k: "spit", x: e.x, y: e.y, x2: tgt.x + 0.5, y2: tgt.y + 0.5, t: 0.2 });
            if (tgt.hp <= 0) destroy(tgt);
            continue;
          }
        }
        if (e.to < 0) {
          if (e.ti === idx(S.map.base.x, S.map.base.y)) {
            S.baseHp -= E.dmg; e.hp = 0; e.leaked = true; S.leaks++;
            if (!S.headless) S.fx.push({ k: "hit", x: S.map.base.x + 0.5, y: S.map.base.y + 0.5, t: 0.35 });
            continue;
          }
          const n = nextTile(e);
          if (n < 0) continue;
          const s = S.structs[n];
          if (s && TOWERS[s.type].block) {
            if (e.type === "brute" && s.type === "wall") {
              s.hp -= E.wallDps * DT; s.flash = 0.1;
              if (s.hp <= 0) destroy(s);
            }
            continue;
          }
          e.to = n;
        }
        const tx = (e.to % BW) + 0.5, ty = ((e.to / BW) | 0) + 0.5;
        const sp = E.spd * e.slow * DT;
        const dx = tx - e.x, dy = ty - e.y, d = Math.hypot(dx, dy);
        if (d <= sp) { e.x = tx; e.y = ty; e.ti = e.to; e.to = -1; }
        else { e.x += (dx / d) * sp; e.y += (dy / d) * sp; }
      }
      let dead = 0;
      for (const e of S.enemies) if (e.hp <= 0) dead++;
      if (dead) S.enemies = S.enemies.filter((e) => e.hp > 0);
      if (S.baseHp <= 0) {
        S.baseHp = 0; S.inWave = false; S.over = true; S.dead = true;
        return;
      }
      const capTicks = Math.round(S.cfg.capS / DT);
      if (S.over) return;
      if (S.spawnIdx >= wv.spawns.length && (S.enemies.length === 0 || S.waveTick > capTicks)) {
        for (const e of S.enemies) { S.baseHp -= ENEMIES[e.type].dmg; S.leaks++; }
        S.enemies = [];
        S.inWave = false;
        if (S.baseHp <= 0) { S.baseHp = 0; S.over = true; S.dead = true; return; }
        S.survived++; S.wave++;
        if (S.wave >= S.waves.length) S.over = true;
      }
    };
    S.score = function () {
      return 1000 * S.survived + Math.max(0, Math.round(S.baseHp)) * 5 + 10 * S.kills + Math.floor(S.gold / 10);
    };
    S.path = function (sp) {
      const out = [];
      let i = idx(sp.x, sp.y), guard = 0;
      out.push(i);
      while (S.field[i] > 0 && guard++ < 200) {
        const x = i % BW, y = (i / BW) | 0;
        let best = -1, bv = S.field[i];
        for (const j of [x < BW - 1 ? i + 1 : -1, y < BH - 1 ? i + BW : -1, x > 0 ? i - 1 : -1, y > 0 ? i - BW : -1])
          if (j >= 0 && S.field[j] < bv) { bv = S.field[j]; best = j; }
        if (best < 0) break;
        i = best; out.push(i);
      }
      return out;
    };
    S.onPath = function (i) {
      if (!S._pathSet || S._pathFor !== S.field) {
        S._pathSet = new Set(); S._pathFor = S.field;
        for (const sp of S.map.spawns) for (const k of S.path(sp)) S._pathSet.add(k);
      }
      return S._pathSet.has(i);
    };
    /* Paths the zombies would take if `type` were built at (x,y) — used for the placement preview. */
    S.previewPaths = function (type, x, y) {
      const saved = S.field, i = idx(x, y);
      if (type && TOWERS[type].block && !S.structs[i] && !S.map.grid[i]) {
        const tmp = S.structs.slice(); tmp[i] = { type };
        S.field = bfsField(S.map, isBlockedFor(tmp));
      }
      const out = S.map.spawns.map((sp) => (S.field[idx(sp.x, sp.y)] < 1e9 ? S.path(sp) : []));
      S.field = saved;
      return out;
    };
    S.idx = idx;
    return S;
  }

  /* ---- Base Duel AI: shared by the bot and the ctx.test.placeAI hook ---- */
  function baseTileScores(S, type) {
    // traffic-weighted coverage of each tile over the current paths
    const traffic = new Float32Array(BW * BH);
    for (const sp of S.map.spawns) for (const i of S.path(sp)) traffic[i] += 1;
    const out = [];
    const hot = [];
    for (let j = 0; j < BW * BH; j++) if (traffic[j]) hot.push(j);
    const R = type === "spike" ? 0 : (TOWERS[type].range || 1.5), R2 = R * R;
    const hx = hot.map((j) => j % BW), hy = hot.map((j) => (j / BW) | 0);
    const hw = hot.map((j) => traffic[j] * (1 + 0.08 * (S.field[j] < 6 ? 6 - S.field[j] : 0)));
    for (let y = 0; y < BH; y++) for (let x = 0; x < BW; x++) {
      const i = y * BW + x;
      if (S.map.grid[i] || S.structs[i]) continue;
      if (type === "spike") { if (traffic[i] > 0) out.push({ x, y, v: traffic[i] * (1 + 0.3 * nearFrost(S, x, y)) }); continue; }
      if (traffic[i] > 0 && type !== "wall") { /* towers on the path block it; allowed but reroutes */ }
      let v = 0;
      for (let k = 0; k < hot.length; k++) {
        const dx = hx[k] - x, dy = hy[k] - y;
        if (dx * dx + dy * dy <= R2) v += hw[k];
      }
      if (traffic[i] > 0) v *= 0.8;
      out.push({ x, y, v });
    }
    return out;
  }
  function nearFrost(S, x, y) {
    let n = 0;
    for (const s of S.structs) if (s && s.type === "frost" && Math.hypot(s.x - x, s.y - y) <= TOWERS.frost.range) n = 1;
    return n;
  }
  function pathLen(S) { let t = 0; for (const sp of S.map.spawns) t += S.field[sp.y * BW + sp.x]; return t; }

  /* Place walls that lengthen the path the most (mazing). Strong bots maze well; weak ones barely. */
  /* The Base Duel AI is driven by explicit knobs so its strength is measurable:
       maze   share of starting gold spent on path-lengthening walls
       search share of candidate tiles evaluated for each wall / tower
       noise  multiplicative noise on tile values (bad reads of the map)
       sloppy chance a tower goes on a random legal tile
       comp   'smart' (frost + arrows + cannons + spikes in proportion) or 'random'
       bomb   firebomb policy: 0 = random throws, 1 = waits for clusters near the base
       repair whether it repairs damaged towers between/during waves */
  function aiParams(skill, rng) {
    const j = () => 0.85 + 0.3 * rng();
    const orders = [["frost", "spike", "spike", "cannon"], ["frost", "spike", "cannon", "spike"], ["cannon", "frost", "spike", "spike"]];
    return {
      maze: clamp((0.55 - skill) * 0.35 * j(), 0, 0.3), // weak bots waste gold on walls that do not form a maze
      search: clamp(0.1 + 0.9 * skill, 0.1, 1),
      noise: (1 - skill) * 0.9,
      sloppy: clamp(0.95 - skill * 1.15, 0, 0.85),
      comp: skill > 0.65 ? U.pick(rng, orders) : skill > 0.35 ? "smart" : "random",
      bomb: skill > 0.4 ? 1 : 0,
      bombNeed: 120 + 90 * skill,
      repair: skill > 0.55,
      hold: Math.round((1 - skill) * 40),
      mine: skill > 0.6 && skill < 0.8 && rng() < 0.5,
    };
  }
  function aiWalls(S, rng, P, budget) {
    let spentW = 0, guard = 0;
    while (spentW + TOWERS.wall.cost <= budget && S.gold >= TOWERS.wall.cost && guard++ < 30) {
      const base = pathLen(S);
      let best = null, bv = 0;
      const cands = [];
      for (let y = 0; y < BH; y++) for (let x = 0; x < BW; x++) {
        const i = y * BW + x;
        if (S.map.grid[i] || S.structs[i]) continue;
        if (Math.abs(x - S.map.base.x) + Math.abs(y - S.map.base.y) <= 1) continue;
        cands.push([x, y]);
      }
      const n = Math.min(40, Math.max(6, Math.round(cands.length * P.search)));
      const pickFrom = U.shuffle(rng, cands).slice(0, n);
      for (const [x, y] of pickFrom) {
        const i = y * BW + x;
        S.structs[i] = { type: "wall" };
        const f = bfsField(S.map, (k) => S.map.grid[k] === 1 || (S.structs[k] && TOWERS[S.structs[k].type].block));
        S.structs[i] = null;
        let len = 0; for (const sp of S.map.spawns) len += f[sp.y * BW + sp.x];
        if (len >= 1e9) continue; // would seal the path
        const gain = len - base + U.gauss(rng) * P.noise * 2;
        if (gain > bv) { bv = gain; best = [x, y]; }
      }
      if (!best || bv < 0.9) break;
      if (S.place("wall", best[0], best[1])) break;
      spentW += TOWERS.wall.cost;
    }
  }
  function aiPickTile(S, rng, P, type) {
    const sc = baseTileScores(S, type);
    if (!sc.length) return null;
    const ok = (c) => !S.canPlace(type, c.x, c.y);
    if (rng() < P.sloppy) { // sloppy placement: any legal tile
      const sh = U.shuffle(rng, sc);
      for (const c of sh.slice(0, 12)) if (ok(c)) return c;
      return null;
    }
    const pool = P.search >= 1 ? sc : U.shuffle(rng, sc).slice(0, Math.max(4, Math.round(sc.length * P.search)));
    for (const c of pool) c.nv = c.v * (1 + U.gauss(rng) * P.noise * 0.6);
    pool.sort((a, b) => b.nv - a.nv || a.y - b.y || a.x - b.x);
    for (const c of pool.slice(0, 12)) if (ok(c)) return c;
    return null;
  }
  function aiBuild(S, rng, P, phase) {
    if (typeof P === "number") P = aiParams(P, rng);
    if (phase === "build") {
      aiWalls(S, rng, P, Math.floor(S.gold * P.maze / 10) * 10);
      if (S.mode === "full" && P.mine) { const t = aiPickTile(S, rng, { sloppy: 0, search: 1, noise: 0.3 }, "wall"); if (t) S.place("mine", t.x, t.y); }
    }
    let guard = 0;
    while (guard++ < 20) {
      let type;
      const counts = {}; for (const s of S.list) counts[s.type] = (counts[s.type] || 0) + 1;
      if (Array.isArray(P.comp)) {
        type = P.comp[(S.list.filter((q) => q.type !== "wall").length) % P.comp.length];
      } else if (P.comp === "smart") {
        if (!counts.frost && S.gold >= 60) type = "frost";
        else if ((counts.cannon || 0) < ((counts.arrow || 0) + 1) / 2 && S.gold >= 90) type = "cannon";
        else if (S.gold < 50 && S.gold >= 30 && (counts.spike || 0) < 3) type = "spike";
        else type = "arrow";
      } else {
        type = U.pick(rng, ["arrow", "arrow", "cannon", "frost", "spike", "wall", "mine"]);
      }
      if (TOWERS[type].cost > S.gold) {
        type = ["arrow", "spike"].find((t) => TOWERS[t].cost <= S.gold);
        if (!type) break;
      }
      const hold = phase === "window" ? P.hold : 0;
      if (S.gold - TOWERS[type].cost < hold) break;
      const t = aiPickTile(S, rng, P, type);
      if (!t) break;
      if (S.place(type, t.x, t.y)) break;
    }
  }
  /* In-wave decision policy for the bot: firebomb timing + repairs. Called every 10 ticks. */
  function aiAct(S, rng, P) {
    if (typeof P === "number") P = aiParams(P, rng);
    if (S.bombs > 0 && S.bombCd <= 0 && S.enemies.length) {
      const R2 = S.bombRadius * S.bombRadius, dmg = S.bombDamage();
      if (P.bomb) {
        let best = null, bv = 0;
        for (const e of S.enemies) {
          let v = 0;
          for (const o of S.enemies) if ((o.x - e.x) * (o.x - e.x) + (o.y - e.y) * (o.y - e.y) <= R2) v += Math.min(o.hp, dmg) * (1 + 0.15 * Math.max(0, 6 - S.field[o.ti]));
          if (v > bv) { bv = v; best = e; }
        }
        const wavesLeft = S.waves.length - S.wave;
        const need = P.bombNeed * (wavesLeft > S.bombs ? 1.25 : 0.8);
        if (best && bv >= need) S.bomb(best.x + U.gauss(rng) * P.noise * 0.4, best.y + U.gauss(rng) * P.noise * 0.4);
      } else if (rng() < 0.05) {
        const e = U.pick(rng, S.enemies);
        S.bomb(e.x + U.gauss(rng) * 0.8, e.y + U.gauss(rng) * 0.8);
      }
    }
    if (P.repair) {
      for (const s of S.list) {
        if (!s.maxHp || s.hp > s.maxHp * 0.45) continue;
        const c = S.repairCost(s);
        if (c && c <= S.gold - 10) S.repair(s.x, s.y);
      }
    }
  }
  function baseWaveSeconds(S) { return S.waveTick * S.dt; }
  const BOT_DT = 0.1;
  function baseBot(seed, skill, rng, mode, params) {
    const S = BaseSim(seed, mode);
    S.headless = true;
    S.setStep(BOT_DT); // coarser fixed step for the headless bot only (documented; ~2x faster, same rules)
    const cfg = S.cfg;
    const P = params || aiParams(skill, rng);
    aiBuild(S, rng, P, "build");
    const timeline = [];
    let t = cfg.buildMs / 1000 * (0.55 + 0.45 * rng());
    timeline.push([Math.round(t * 10) / 10, 0]);
    while (!S.over) {
      if (S.wave > 0) { aiBuild(S, rng, P, "window"); t += cfg.windowMs / 1000; }
      S.startWave();
      while (S.inWave && !S.over) {
        if (S.waveTick % Math.round(0.5 / S.dt) === 0) aiAct(S, rng, P);
        S.step();
      }
      t += baseRealFor(cfg, baseWaveSeconds(S)) / 1000;
      timeline.push([Math.round(t * 10) / 10, S.score()]);
    }
    const score = S.score();
    timeline[timeline.length - 1][1] = score;
    return { score, timeline };
  }

  /* Re-run a recorded game headlessly: log entries are [wave, waveTick (-1 = before the wave), op, ...args]. */
  function baseReplay(seed, mode, log) {
    const S = BaseSim(seed, mode);
    S.headless = true;
    let li = 0;
    const apply = (en) => {
      const op = en[2], a = en[3], b = en[4], c = en[5];
      if (op === "place") S.place(a, b, c); else if (op === "sell") S.sell(a, b); else if (op === "repair") S.repair(a, b); else if (op === "bomb") S.bomb(a, b);
    };
    while (!S.over) {
      while (li < log.length && log[li][0] === S.wave && log[li][1] === -1) apply(log[li++]);
      S.startWave();
      while (S.inWave && !S.over) {
        while (li < log.length && log[li][0] === S.wave && log[li][1] === S.waveTick) apply(log[li++]);
        S.step();
      }
    }
    return { score: S.score(), survived: S.survived, hp: S.baseHp, kills: S.kills, gold: S.gold };
  }
  const BASE_LAB = { baseReplay, aiParams, baseSimAt, baseRealFor, BaseSim, baseMap, baseWaves, baseConfig, aiBuild, aiAct, baseBot, TOWERS, ENEMIES, BW, BH, DT };

  /* ====================================================================================
     CITY DUEL — engine
     ==================================================================================== */
  // use: energy/water consumption; traf: trips generated; crime; pol: pollution emitted (felt within radius 2)
  const BLD = {
    res:  { name: "Residential", short: "Homes", tile: "Home", key: "R", cost: 500,  col: "#5AD690", house: 150, energy: 1, water: 1, traf: 1, crime: 1,
            desc: "Houses 150 people. Needs jobs, power and water. Likes parks and services; hates pollution." },
    com:  { name: "Commercial", short: "Shops", tile: "Shop", key: "C", cost: 700,  col: "#6FC3FF", jobs: 50, energy: 1, water: 0.5, traf: 2, crime: 1.5,
            desc: "50 jobs. Homes within 2 tiles get +6 happiness. Sells to up to 300 residents." },
    ind:  { name: "Industrial", short: "Factory", tile: "Fact", key: "I", cost: 700, col: "#C9A26B", jobs: 110, energy: 2, water: 1, traf: 2, crime: 0.5, pol: 3,
            desc: "110 jobs and $220 output. Pollutes homes within 2 tiles (−8 happiness per point)." },
    park: { name: "Park", short: "Park", tile: "Park", key: "P", cost: 250, col: "#2FA36B", energy: 0, water: 0.5, clean: 1,
            desc: "+7 happiness for homes within 2 tiles (2 parks max). Cancels 1 pollution next to it." },
    power:{ name: "Power plant", short: "Power", tile: "Power", key: "E", cost: 1100, col: "#FFB35C", jobs: 20, gen: 9, water: 0.5, traf: 1, pol: 2,
            desc: "+9 energy for the whole city. Pollutes within 2 tiles." },
    transit:{ name: "Transit stop", short: "Transit", tile: "Bus", key: "T", cost: 400, col: "#B48CFF", energy: 0.5, jobs: 5, radius: 2,
            desc: "Halves traffic from buildings within 2 tiles. Stacks do not help." },
    hosp: { name: "Hospital", short: "Hospital", tile: "Hosp", key: "H", cost: 1200, col: "#FF8FA3", jobs: 45, energy: 1, water: 1, traf: 1, radius: 3,
            desc: "+14 happiness for homes within 3 tiles. 45 jobs." },
    school:{ name: "School", short: "School", tile: "Schl", key: "S", cost: 900, col: "#F2C14E", jobs: 30, energy: 1, water: 0.5, traf: 1, radius: 2,
            desc: "+9 happiness and faster growth for homes within 2 tiles. 30 jobs." },
    police:{ name: "Police", short: "Police", tile: "Cops", key: "X", cost: 800, col: "#8FB3FF", jobs: 20, energy: 0.5, water: 0.5, radius: 3,
            desc: "Cuts crime by 70% within 3 tiles; +5 happiness for homes there. 20 jobs." },
    water: { name: "Water tower", short: "Water", tile: "Water", key: "W", cost: 600, col: "#4FC3D9", wgen: 8, energy: 0.5,
            desc: "+8 water for the whole city." },
    stadium:{ name: "Stadium", short: "Stadium", tile: "Arena", key: "D", cost: 2200, col: "#E06CE0", jobs: 50, energy: 2, water: 1, traf: 4, crime: 2,
            desc: "+6 happiness city-wide (once), $250 ticket income, 50 jobs. Heavy traffic." },
  };
  const BLD_ORDER = ["res", "com", "ind", "park", "power", "water", "transit", "hosp", "school", "police", "stadium"];
  const OUTSIDE = { energy: 3, water: 3 };

  function cityConfig(mode) {
    return mode === "mix" ? { n: 5, budget: 6000, buildMs: 35000, cap: 18 } : { n: 7, budget: 10000, buildMs: 90000, cap: 30 };
  }
  function cityMap(seed, mode) {
    const c = cityConfig(mode), rng = U.rng("city-map:" + seed + ":" + mode);
    const tiles = new Array(c.n * c.n).fill(0); // 0 land, 1 water, 2 rock
    const nW = mode === "mix" ? U.randInt(rng, 2, 3) : U.randInt(rng, 3, 5);
    const nR = mode === "mix" ? U.randInt(rng, 1, 2) : U.randInt(rng, 2, 3);
    // water as a small lake cluster on an edge
    let x = rng() < 0.5 ? 0 : c.n - 1, y = U.randInt(rng, 0, c.n - 1);
    if (rng() < 0.5) [x, y] = [y, x];
    for (let k = 0, guard = 0; k < nW && guard < 50; guard++) {
      if (!tiles[y * c.n + x]) { tiles[y * c.n + x] = 1; k++; }
      const d = U.pick(rng, [[1, 0], [-1, 0], [0, 1], [0, -1]]);
      x = clamp(x + d[0], 0, c.n - 1); y = clamp(y + d[1], 0, c.n - 1);
    }
    for (let k = 0, guard = 0; k < nR && guard < 50; guard++) {
      const i = U.randInt(rng, 0, c.n * c.n - 1);
      if (!tiles[i]) { tiles[i] = 2; k++; }
    }
    return { n: c.n, tiles, budget: c.budget, cap: c.cap };
  }
  /* Evaluate a city. plan = array (n*n) of building keys or null. Pure, fast.
     Each home's happiness depends on what it can reach (coverage radii, Chebyshev distance) and on city-wide
     problems (jobs, utilities, traffic, crime, pollution). Population = housing scaled by happiness. */
  function cityEval(map, plan) {
    const n = map.n, list = [];
    let spent = 0;
    for (let i = 0; i < plan.length; i++) if (plan[i]) { list.push({ t: plan[i], x: i % n, y: (i / n) | 0, B: BLD[plan[i]] }); spent += BLD[plan[i]].cost; }
    const dist = (a, b) => Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
    let eUse = 0, eGen = OUTSIDE.energy, wUse = 0, wGen = OUTSIDE.water;
    for (const b of list) { eUse += b.B.energy || 0; eGen += b.B.gen || 0; wUse += b.B.water || 0; wGen += b.B.wgen || 0; }
    const pRatio = eUse ? Math.min(1, eGen / eUse) : 1, wRatio = wUse ? Math.min(1, wGen / wUse) : 1;
    const util = Math.min(pRatio, wRatio);
    const by = (t) => list.filter((b) => b.t === t);
    const homes = by("res"), transits = by("transit"), polices = by("police");
    let traf = 0, crime = 0;
    for (const b of list) {
      if (b.B.traf) traf += b.B.traf * (transits.some((t) => dist(t, b) <= 2) ? 0.5 : 1);
      if (b.B.crime) crime += b.B.crime * (polices.some((p) => dist(p, b) <= 3) ? 0.3 : 1);
    }
    const trafficPct = clamp(100 * traf / map.cap, 0, 100);
    const crimePct = clamp(100 * crime / (map.cap * 0.5), 0, 100);
    let housing = 0, jobs = 0;
    for (const b of list) { housing += b.B.house || 0; jobs += b.B.jobs || 0; }
    housing *= util; jobs *= util;
    const hasStadium = list.some((b) => b.t === "stadium");
    const workers = housing * 0.5;
    const employed = Math.min(workers, jobs);
    const employment = workers > 0 ? employed / workers : 0;
    const jobFill = jobs > 0 ? employed / jobs : 0;
    let happy = 0, polSum = 0, schoolCov = 0;
    const homeHap = {};
    for (const h of homes) {
      let pol = 0, parks = 0, hosp = false, school = false, police = false, shop = false;
      for (const b of list) {
        const d = dist(b, h);
        if (b.B.pol && d <= 2) pol += b.B.pol * (d <= 1 ? 1 : 0.5);
        if (b.t === "park" && d <= 1) pol -= 1;
        if (b.t === "park" && d <= 2) parks++;
        if (b.t === "hosp" && d <= 3) hosp = true;
        if (b.t === "school" && d <= 2) school = true;
        if (b.t === "police" && d <= 3) police = true;
        if (b.t === "com" && d <= 2) shop = true;
      }
      pol = Math.max(0, pol); polSum += pol;
      if (school) schoolCov++;
      const hh = 44 + Math.min(2, parks) * 7 + (hosp ? 14 : 0) + (school ? 9 : 0) + (police ? 5 : 0) + (shop ? 6 : 0) + (hasStadium ? 6 : 0)
        - pol * 8 - crimePct * 0.25 - trafficPct * 0.2 - (1 - employment) * 30 - (1 - util) * 60;
      happy += clamp(hh, 0, 100);
      homeHap[h.y * n + h.x] = Math.round(clamp(hh, 0, 100));
    }
    const happiness = homes.length ? happy / homes.length : 0;
    const population = housing * (0.4 + 0.6 * happiness / 100);
    const shops = by("com").length, facts = by("ind").length;
    const taxes = employed * 1.5;
    const sales = Math.min(shops * 300, population) * 0.9 * Math.min(1, jobFill * 1.25);
    const output = facts * 220 * util * Math.min(1, jobFill * 1.25);
    const tickets = hasStadium ? 250 * util : 0;
    const upkeep = spent * 0.04;
    const revenue = taxes + sales + output + tickets - upkeep;
    const pollutionPct = homes.length ? clamp(polSum / homes.length * 20, 0, 100) : 0;
    const growth = homes.length ? clamp((happiness - 45) / 5 * employment * (0.5 + 0.5 * schoolCov / homes.length), -10, 10) : 0;
    const content = population * (15 + happiness) / 115;
    const parts = { people: content / 6, money: Math.max(-40, revenue / 40), growth: growth >= 0 ? growth * 3 : growth };
    const scoreRaw = parts.people + parts.money + parts.growth;
    const score10 = Math.max(0, Math.round(scoreRaw * 10));
    return {
      spent, left: map.budget - spent, population, happiness, revenue, trafficPct, crimePct, pollutionPct,
      energy: [eGen, eUse], water: [wGen, wUse], util, employment, jobs, housing, growth, content, parts,
      score10, count: list.length, homeHap,
    };
  }
  /* Allocation-free score-only twin of cityEval for the planner. Same formulas, same summation order, so
     cityScore(map, plan) === cityEval(map, plan).score10 exactly (asserted by the tests). */
  const BIDX = {}; BLD_ORDER.forEach((k, i) => (BIDX[k] = i));
  const CB = BLD_ORDER.map((k) => BLD[k]);
  const _cx = new Int8Array(64), _cy = new Int8Array(64), _ct = new Int8Array(64);
  function cityScore(map, plan) {
    const n = map.n;
    let m = 0, spent = 0;
    for (let i = 0; i < plan.length; i++) { const k = plan[i]; if (k) { _ct[m] = BIDX[k]; _cx[m] = i % n; _cy[m] = (i / n) | 0; m++; spent += BLD[k].cost; } }
    let eUse = 0, eGen = OUTSIDE.energy, wUse = 0, wGen = OUTSIDE.water;
    for (let a = 0; a < m; a++) { const B = CB[_ct[a]]; eUse += B.energy || 0; eGen += B.gen || 0; wUse += B.water || 0; wGen += B.wgen || 0; }
    const pRatio = eUse ? Math.min(1, eGen / eUse) : 1, wRatio = wUse ? Math.min(1, wGen / wUse) : 1;
    const util = Math.min(pRatio, wRatio);
    const T_RES = BIDX.res, T_TR = BIDX.transit, T_PO = BIDX.police, T_PARK = BIDX.park, T_HOSP = BIDX.hosp, T_SCH = BIDX.school, T_COM = BIDX.com, T_IND = BIDX.ind, T_ST = BIDX.stadium;
    const dist = (a, b) => Math.max(Math.abs(_cx[a] - _cx[b]), Math.abs(_cy[a] - _cy[b]));
    let traf = 0, crime = 0;
    for (let a = 0; a < m; a++) {
      const B = CB[_ct[a]];
      if (B.traf) { let near = false; for (let b = 0; b < m && !near; b++) if (_ct[b] === T_TR && dist(b, a) <= 2) near = true; traf += B.traf * (near ? 0.5 : 1); }
      if (B.crime) { let near = false; for (let b = 0; b < m && !near; b++) if (_ct[b] === T_PO && dist(b, a) <= 3) near = true; crime += B.crime * (near ? 0.3 : 1); }
    }
    const trafficPct = clamp(100 * traf / map.cap, 0, 100);
    const crimePct = clamp(100 * crime / (map.cap * 0.5), 0, 100);
    let housing = 0, jobs = 0, hasStadium = false, nHomes = 0, shops = 0, facts = 0;
    for (let a = 0; a < m; a++) {
      const t = _ct[a], B = CB[t]; housing += B.house || 0; jobs += B.jobs || 0;
      if (t === T_ST) hasStadium = true; else if (t === T_RES) nHomes++; else if (t === T_COM) shops++; else if (t === T_IND) facts++;
    }
    housing *= util; jobs *= util;
    const workers = housing * 0.5;
    const employed = Math.min(workers, jobs);
    const employment = workers > 0 ? employed / workers : 0;
    const jobFill = jobs > 0 ? employed / jobs : 0;
    let happy = 0, schoolCov = 0;
    for (let h = 0; h < m; h++) {
      if (_ct[h] !== T_RES) continue;
      let pol = 0, parks = 0, hosp = false, school = false, police = false, shop = false;
      for (let b = 0; b < m; b++) {
        const t = _ct[b], B = CB[t], d = dist(b, h);
        if (B.pol && d <= 2) pol += B.pol * (d <= 1 ? 1 : 0.5);
        if (t === T_PARK && d <= 1) pol -= 1;
        if (t === T_PARK && d <= 2) parks++;
        if (t === T_HOSP && d <= 3) hosp = true;
        if (t === T_SCH && d <= 2) school = true;
        if (t === T_PO && d <= 3) police = true;
        if (t === T_COM && d <= 2) shop = true;
      }
      pol = Math.max(0, pol);
      if (school) schoolCov++;
      const hh = 44 + Math.min(2, parks) * 7 + (hosp ? 14 : 0) + (school ? 9 : 0) + (police ? 5 : 0) + (shop ? 6 : 0) + (hasStadium ? 6 : 0)
        - pol * 8 - crimePct * 0.25 - trafficPct * 0.2 - (1 - employment) * 30 - (1 - util) * 60;
      happy += clamp(hh, 0, 100);
    }
    const happiness = nHomes ? happy / nHomes : 0;
    const population = housing * (0.4 + 0.6 * happiness / 100);
    const taxes = employed * 1.5;
    const sales = Math.min(shops * 300, population) * 0.9 * Math.min(1, jobFill * 1.25);
    const output = facts * 220 * util * Math.min(1, jobFill * 1.25);
    const tickets = hasStadium ? 250 * util : 0;
    const upkeep = spent * 0.04;
    const revenue = taxes + sales + output + tickets - upkeep;
    const growth = nHomes ? clamp((happiness - 45) / 5 * employment * (0.5 + 0.5 * schoolCov / nHomes), -10, 10) : 0;
    const content = population * (15 + happiness) / 115;
    const scoreRaw = content / 6 + Math.max(-40, revenue / 40) + (growth >= 0 ? growth * 3 : growth);
    return Math.max(0, Math.round(scoreRaw * 10));
  }
  function cityCanPlace(map, plan, i, t) {
    if (map.tiles[i]) return map.tiles[i] === 1 ? "Water" : "Rock";
    if (plan[i]) return "Occupied";
    let spent = 0; for (const k of plan) if (k) spent += BLD[k].cost;
    if (spent + BLD[t].cost > map.budget) return "Over budget";
    return "";
  }
  /* Planner: simulated annealing over the same scoring function. The iteration budget (search effort) and a
     noisy acceptance scale with skill; snapshots of the best-so-far give the bot's build timeline. */
  function cityPlan(map, rng, skill, itersOverride) {
    const N = map.n * map.n, plan = new Array(N).fill(null);
    const full = map.n >= 7;
    const iters = itersOverride || Math.round((full ? 200 : 120) + (full ? 3200 : 2000) * Math.pow(skill, 2.2));
    const T0 = full ? 120 : 60;
    let cur = cityScore(map, plan), best = cur, bp = plan.slice(), spent = 0;
    const free = [];
    for (let i = 0; i < N; i++) if (!map.tiles[i]) free.push(i);
    const snaps = [];
    const every = Math.max(1, Math.floor(iters / 12));
    for (let k = 0; k < iters; k++) {
      const T = T0 * (1 - k / iters) + 0.5;
      const i = free[Math.floor(rng() * free.length)], old = plan[i];
      const nt = old && rng() < 0.3 ? null : BLD_ORDER[Math.floor(rng() * BLD_ORDER.length)];
      const ns = spent - (old ? BLD[old].cost : 0) + (nt ? BLD[nt].cost : 0);
      if (ns > map.budget) { if (k % every === every - 1) snaps.push(best); continue; }
      plan[i] = nt;
      const sc = cityScore(map, plan);
      if (sc >= cur || rng() < Math.exp((sc - cur) / T)) { cur = sc; spent = ns; if (sc > best) { best = sc; bp = plan.slice(); } }
      else plan[i] = old;
      if (k % every === every - 1) snaps.push(best);
    }
    return { plan: bp, score10: best, snaps };
  }
  function cityBot(seed, skill, rng, mode) {
    const map = cityMap(seed, mode), cfg = cityConfig(mode);
    const res = cityPlan(map, rng, skill);
    const T = cfg.buildMs / 1000 * (0.6 + 0.35 * rng());
    const timeline = [];
    res.snaps.forEach((v, k) => timeline.push([Math.round(T * (k + 1) / res.snaps.length * 10) / 10, v / 10]));
    const score = res.score10 / 10;
    timeline.push([Math.round((cfg.buildMs / 1000 + 3) * 10) / 10, score]);
    return { score, timeline };
  }
  const CITY_LAB = { cityScore, BLD, BLD_ORDER, cityConfig, cityMap, cityEval, cityCanPlace, cityPlan, cityBot };

  /* ====================================================================================
     RESTAURANT DUEL — engine
     ==================================================================================== */
  const CTYPES = {
    family:   { name: "Families",  budget: 22, sens: 1.0, patience: [15, 30], size: [3, 6], stay: 45 },
    business: { name: "Business",  budget: 40, sens: 0.35, patience: [8, 18], size: [1, 3], stay: 35 },
    student:  { name: "Students",  budget: 14, sens: 1.6, patience: [15, 35], size: [2, 4], stay: 40 },
    foodie:   { name: "Foodies",   budget: 38, sens: 0.45, patience: [20, 40], size: [1, 3], stay: 55 },
    tourist:  { name: "Tourists",  budget: 28, sens: 0.8, patience: [10, 25], size: [2, 4], stay: 45 },
  };
  const CT_ORDER = ["family", "business", "student", "foodie", "tourist"];
  // cost = ingredients per plate; prep = chef minutes; pop by customer type
  const DISHES = {
    burger:  { name: "Burger",        cost: 5,  price: 16, prep: 7,  pop: { family: 0.9, business: 0.45, student: 1.0, foodie: 0.25, tourist: 0.7 } },
    pizza:   { name: "Pizza",         cost: 4,  price: 18, prep: 10, pop: { family: 1.0, business: 0.4, student: 0.9, foodie: 0.35, tourist: 0.75 } },
    salad:   { name: "Salad bowl",    cost: 3,  price: 13, prep: 4,  pop: { family: 0.35, business: 0.8, student: 0.45, foodie: 0.5, tourist: 0.45 } },
    pasta:   { name: "Fresh pasta",   cost: 4,  price: 20, prep: 9,  pop: { family: 0.8, business: 0.65, student: 0.6, foodie: 0.7, tourist: 0.85 } },
    steak:   { name: "Steak frites",  cost: 14, price: 38, prep: 14, pop: { family: 0.45, business: 1.0, student: 0.1, foodie: 0.8, tourist: 0.7 } },
    sushi:   { name: "Sushi set",     cost: 11, price: 32, prep: 12, pop: { family: 0.3, business: 0.8, student: 0.3, foodie: 1.0, tourist: 0.85 } },
    curry:   { name: "Curry",         cost: 4,  price: 17, prep: 8,  pop: { family: 0.6, business: 0.5, student: 0.8, foodie: 0.75, tourist: 0.6 } },
    tacos:   { name: "Tacos",         cost: 3,  price: 12, prep: 5,  pop: { family: 0.75, business: 0.35, student: 0.95, foodie: 0.45, tourist: 0.65 } },
    soup:    { name: "Soup & bread",  cost: 2,  price: 9,  prep: 3,  pop: { family: 0.5, business: 0.45, student: 0.6, foodie: 0.3, tourist: 0.4 } },
    seafood: { name: "Seafood platter", cost: 20, price: 52, prep: 18, pop: { family: 0.25, business: 0.75, student: 0.05, foodie: 1.0, tourist: 1.0 } },
  };
  const DISH_ORDER = ["burger", "pizza", "salad", "pasta", "steak", "sushi", "curry", "tacos", "soup", "seafood"];
  const KITCHEN = [
    { name: "Basic", cost: 0, speed: 1.0, maxChefs: 2, quality: 0 },
    { name: "Pro", cost: 900, speed: 1.3, maxChefs: 4, quality: 0.03 },
    { name: "Elite", cost: 2600, speed: 1.6, maxChefs: 6, quality: 0.07 },
  ];
  const RCOST = { table: 120, chef: 300, waiter: 180, dish: 150 };
  const DRINK = { price: 5, cost: 1.5 };
  const DEPR = 0.35; // kitchen + tables are assets: one day is charged 35% of their cost
  const DAY_OPEN = 11 * 60, DAY_MIN = 12 * 60; // 11:00 – 23:00

  function restConfig(mode) {
    return mode === "mix" ? { budget: 10000, planMs: 30000, simMs: 3000 } : { budget: 10000, planMs: 60000, simMs: 4000 };
  }
  function restDay(seed) {
    const rng = U.rng("rest-day:" + seed);
    // type mix shifts per seed so the best menu differs by day
    const w = CT_ORDER.map(() => 0.4 + rng());
    const tw = w.reduce((a, b) => a + b, 0);
    const parties = [];
    for (let k = 0; k < 100; k++) {
      let r = rng() * tw, ti = 0;
      while (r > w[ti]) { r -= w[ti]; ti++; }
      const type = CT_ORDER[Math.min(ti, 4)], C = CTYPES[type];
      // arrival: lunch peak, dinner peak, or spread
      const z = rng();
      let t;
      if (z < 0.36) t = 60 + U.gauss(rng) * 45;         // ~12:00
      else if (z < 0.8) t = 480 + U.gauss(rng) * 60;   // ~19:00
      else t = rng() * DAY_MIN;
      t = Math.round(clamp(t, 0, DAY_MIN - 60));
      const jit = {};
      for (const d of DISH_ORDER) jit[d] = (rng() - 0.5) * 0.3;
      parties.push({
        id: k, type, t, size: U.randInt(rng, C.size[0], C.size[1]),
        patience: U.randInt(rng, C.patience[0], C.patience[1]),
        budget: C.budget * (0.8 + rng() * 0.45), sens: C.sens * (0.8 + rng() * 0.4),
        th: rng(), jit,
      });
    }
    parties.sort((a, b) => a.t - b.t || a.id - b.id);
    return { seed, parties, mix: CT_ORDER.map((k, i) => [k, Math.round(100 * w[i] / tw)]) };
  }
  function restDefaultPlan() {
    return { kitchen: 0, tables: 8, chefs: 2, waiters: 2, menu: ["burger", "pizza", "pasta"], price: 1.0, marketing: 500 };
  }
  function restSpend(plan) {
    return KITCHEN[plan.kitchen].cost + plan.tables * RCOST.table + plan.chefs * RCOST.chef + plan.waiters * RCOST.waiter + plan.menu.length * RCOST.dish + plan.marketing;
  }
  function restValid(plan, budget) {
    if (plan.menu.length < 3) return "Pick at least 3 dishes";
    if (plan.menu.length > 5) return "Pick at most 5 dishes";
    if (plan.chefs > KITCHEN[plan.kitchen].maxChefs) return KITCHEN[plan.kitchen].name + " kitchen fits " + KITCHEN[plan.kitchen].maxChefs + " chefs";
    if (restSpend(plan) > budget) return "Over budget";
    return "";
  }
  /* Simulate the day. Returns totals, P&L, reputation and a per-10-minute trace for the animation. */
  function restSim(day, plan, withTrace) {
    const K = KITCHEN[plan.kitchen];
    const chefs = Math.min(plan.chefs, K.maxChefs);
    const complexity = 1 + 0.07 * Math.max(0, plan.menu.length - 3);
    const mkt = 1 - Math.exp(-plan.marketing / 1000);
    const pm = plan.price;
    // per-party order: each guest picks the dish with best utility; utility < 0.1 -> orders nothing
    const orders = [];
    let visitors = 0;
    for (const p of day.parties) {
      let bestD = null, bu = -9, fitSum = 0;
      for (const d of plan.menu) {
        const D = DISHES[d];
        const price = D.price * pm;
        const u = D.pop[p.type] + p.jit[d] + K.quality - p.sens * Math.max(0, price - p.budget) / p.budget * 1.6 - 0.1 * (pm - 1);
        if (u > bu) { bu = u; bestD = d; }
        fitSum += Math.max(0, u);
      }
      const appeal = 0.3 + 0.5 * mkt + 0.3 * clamp(bu, 0, 1) + 0.04 * Math.min(1, fitSum / 2) - 0.55 * Math.max(0, pm - 1) * p.sens + 0.25 * Math.max(0, 1 - pm) * p.sens;
      orders.push({ p, come: appeal >= p.th, dish: bu >= 0.1 ? bestD : null, u: bu });
      if (appeal >= p.th) visitors++;
    }
    const tables = new Array(plan.tables).fill(0); // free-at minute
    const chefFree = new Array(chefs).fill(0), waiterFree = new Array(plan.waiters).fill(0);
    let revenue = 0, cogs = 0, served = 0, unhappy = 0, satSum = 0, guests = 0, walked = 0, lostWait = 0, lostMenu = 0;
    const queue = []; // {o, t}
    const out = [];
    const events = []; // for animation: [minute, kind, size]
    function tryServe(o, now) {
      const need = Math.ceil(o.p.size / 4);
      const free = [];
      for (let i = 0; i < tables.length && free.length < need; i++) if (tables[i] <= now) free.push(i);
      if (free.length < need) return false;
      const waited = now - o.p.t;
      // waiter takes the order (2 min per party + 0.5 per guest)
      let wi = 0; for (let i = 1; i < waiterFree.length; i++) if (waiterFree[i] < waiterFree[wi]) wi = i;
      const orderAt = Math.max(now, waiterFree[wi]);
      waiterFree[wi] = orderAt + 3 + 1.2 * o.p.size; // take order, carry plates, bill
      // kitchen: each plate on the chef that frees first
      const D = DISHES[o.dish];
      // one chef cooks the party's order as a batch: first plate takes full prep, extra plates 30% each
      const prep = D.prep * (1 + 0.3 * (o.p.size - 1)) * complexity / K.speed;
      let ci = 0; for (let i = 1; i < chefFree.length; i++) if (chefFree[i] < chefFree[ci]) ci = i;
      const st = Math.max(orderAt + 2, chefFree[ci]);
      chefFree[ci] = st + prep;
      const ready = st + prep;
      const leaveAt = ready + CTYPES[o.p.type].stay;
      for (const i of free) tables[i] = leaveAt + 3;
      const foodWait = ready - o.p.t;
      const price = D.price * pm;
      const sat = clamp(0.55 + 0.35 * clamp(o.u, 0, 1.2) - 0.015 * Math.max(0, foodWait - 20) - 0.012 * waited - 0.25 * Math.max(0, pm - 1) * o.p.sens + K.quality, 0, 1);
      revenue += (price + DRINK.price * pm) * o.p.size * (1 + 0.12 * sat); // drinks + tips that scale with happiness
      cogs += (D.cost + DRINK.cost) * o.p.size;
      served++; guests += o.p.size; satSum += sat;
      out.push({ id: o.p.id, r: "served", seat: now, ready, leave: leaveAt, sat });
      events.push([now, "seat", o.p.size], [leaveAt, "leave", o.p.size]);
      return true;
    }
    let oi = 0;
    for (let now = 0; now <= DAY_MIN + 120; now++) {
      if (!queue.length) { // nothing waits: jump straight to the next arrival (exactly equivalent, much faster)
        if (oi >= orders.length) break;
        if (orders[oi].p.t > now) now = orders[oi].p.t;
      }
      while (oi < orders.length && orders[oi].p.t <= now) {
        const o = orders[oi++];
        if (!o.come) { walked++; continue; }
        if (!o.dish) { unhappy++; lostMenu++; out.push({ id: o.p.id, r: "menu" }); events.push([now, "left", o.p.size]); continue; }
        queue.push(o);
        events.push([now, "arrive", o.p.size]);
      }
      for (let q = 0; q < queue.length; q++) {
        const o = queue[q];
        if (now - o.p.t > o.p.patience) { queue.splice(q--, 1); unhappy++; lostWait++; out.push({ id: o.p.id, r: "wait" }); events.push([now, "left", o.p.size]); continue; }
        if (tryServe(o, now)) queue.splice(q--, 1);
      }
      if (now > DAY_MIN && !queue.length && oi >= orders.length) break;
    }
    const spend = restSpend(plan);
    const equip = KITCHEN[plan.kitchen].cost + plan.tables * RCOST.table;
    const depreciation = Math.round(equip * DEPR);
    const wages = plan.chefs * RCOST.chef + plan.waiters * RCOST.waiter;
    const menuCost = plan.menu.length * RCOST.dish;
    const reviews = served + unhappy;
    const stars = reviews ? 1 + 4 * (satSum / reviews) : 3;
    const repBonus = Math.round((stars - 3) * 900);
    const profit = Math.round(revenue - cogs - depreciation - wages - menuCost - plan.marketing);
    const score = Math.max(0, 5000 + profit + repBonus);
    const res = { visitors, served, unhappy, walked, guests, lostWait, lostMenu, revenue: Math.round(revenue), cogs: Math.round(cogs), spend, depreciation, wages, menuCost, marketing: plan.marketing, profit, stars, repBonus, score };
    if (withTrace) {
      res.out = out;
      // per-10-min trace of seated guests, queue, served & left totals
      events.sort((a, b) => a[0] - b[0]);
      const trace = [];
      let seated = 0, qn = 0, sv = 0, lf = 0, ei = 0;
      const arrivals = orders.filter((o) => o.come && o.dish);
      for (let m = 0; m <= DAY_MIN; m += 10) {
        while (ei < events.length && events[ei][0] <= m) {
          const [, k, n] = events[ei++];
          if (k === "seat") seated += n; else if (k === "leave") { seated -= n; sv++; } else if (k === "left") lf++;
        }
        qn = 0;
        for (const o of arrivals) {
          const r = out.find((x) => x.id === o.p.id);
          if (o.p.t <= m && r && ((r.r === "served" && r.seat > m) || (r.r === "wait" && o.p.t + o.p.patience >= m))) qn++;
        }
        trace.push({ m, seated: Math.max(0, seated), queue: qn, served: sv, left: lf });
      }
      res.trace = trace;
    }
    return res;
  }
  /* Optimiser used by the bot: random-restart hill climbing with a skill-scaled evaluation budget. */
  function restNeighbor(plan, rng) {
    const q = JSON.parse(JSON.stringify(plan));
    const r = Math.floor(rng() * 7);
    const step = rng() < 0.5 ? -1 : 1;
    if (r === 0) q.kitchen = clamp(q.kitchen + step, 0, 2);
    else if (r === 1) q.tables = clamp(q.tables + step * (1 + Math.floor(rng() * 3)), 2, 24);
    else if (r === 2) q.chefs = clamp(q.chefs + step, 1, 6);
    else if (r === 3) q.waiters = clamp(q.waiters + step, 1, 6);
    else if (r === 4) {
      const off = DISH_ORDER.filter((d) => !q.menu.includes(d));
      const mv = rng();
      if (mv < 0.5 && q.menu.length > 0) q.menu[Math.floor(rng() * q.menu.length)] = U.pick(rng, off);
      else if (mv < 0.75 && q.menu.length < 5) q.menu.push(U.pick(rng, off));
      else if (q.menu.length > 3) q.menu.splice(Math.floor(rng() * q.menu.length), 1);
    } else if (r === 5) q.price = Math.round(clamp(q.price + step * 0.05 * (1 + Math.floor(rng() * 2)), 0.7, 1.6) * 100) / 100;
    else q.marketing = clamp(q.marketing + step * 250, 0, 3000);
    if (q.chefs > KITCHEN[q.kitchen].maxChefs) q.chefs = KITCHEN[q.kitchen].maxChefs;
    return q;
  }
  function restRandomPlan(rng) {
    const k = Math.floor(rng() * 3);
    return {
      kitchen: k, tables: U.randInt(rng, 4, 16), chefs: U.randInt(rng, 1, KITCHEN[k].maxChefs), waiters: U.randInt(rng, 1, 4),
      menu: U.shuffle(rng, DISH_ORDER).slice(0, U.randInt(rng, 3, 5)),
      price: Math.round((0.8 + rng() * 0.6) * 20) / 20, marketing: 250 * U.randInt(rng, 0, 8),
    };
  }
  function restOptimise(day, rng, skill, evals) {
    const budget = 10000;
    let cur = restDefaultPlan();
    if (rng() > skill) cur = restRandomPlan(rng);
    while (restValid(cur, budget)) cur = restRandomPlan(rng);
    const noise = (1 - skill) * 700;
    let bestTrue = restSim(day, cur).score, cv = bestTrue + U.gauss(rng) * noise, best = cur;
    const snaps = [];
    const every = Math.max(1, Math.floor(evals / 10));
    for (let k = 0; k < evals; k++) {
      const q = restNeighbor(cur, rng);
      if (!restValid(q, budget)) {
        const tv = restSim(day, q).score;
        const v = tv + U.gauss(rng) * noise; // noisy judgement of the real simulation
        if (v >= cv) { cur = q; cv = v; best = q; bestTrue = tv; } // commits to what it believes is better
      }
      if (k % every === every - 1) snaps.push(bestTrue);
    }
    return { plan: best, score: bestTrue, snaps };
  }
  function restBot(seed, skill, rng, mode) {
    const day = restDay(seed), cfg = restConfig(mode);
    const evals = Math.round((mode === "mix" ? 8 : 12) + (mode === "mix" ? 90 : 160) * skill * skill);
    const r = restOptimise(day, rng, skill, evals);
    const T = cfg.planMs / 1000 * (0.6 + 0.35 * rng());
    const timeline = [];
    r.snaps.forEach((v, k) => timeline.push([Math.round(T * (k + 1) / Math.max(1, r.snaps.length) * 10) / 10, v]));
    timeline.push([Math.round((cfg.planMs + cfg.simMs) / 100) / 10, r.score]);
    return { score: r.score, timeline };
  }
  const REST_LAB = { CTYPES, CT_ORDER, DISHES, DISH_ORDER, KITCHEN, RCOST, restConfig, restDay, restDefaultPlan, restSpend, restValid, restSim, restOptimise, restRandomPlan, restNeighbor, restBot };

  /* ====================================================================================
     Shared UI styles (one block per game id, same structure)
     ==================================================================================== */
  function packCss(P) {
    return `
    .${P}{display:grid;gap:12px;container-type:inline-size;min-width:0}
    .${P} *{min-width:0}
    .${P}-hud{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
    @container (min-width:520px){.${P}-hud{grid-template-columns:repeat(auto-fit,minmax(96px,1fr))}}
    .${P}-stat{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:6px 10px}
    .${P}-stat span{display:block;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .${P}-stat b{display:block;font-family:var(--f-mono);font-size:18px;font-variant-numeric:tabular-nums;white-space:nowrap}
    .${P}-stat.me{border-color:color-mix(in srgb,var(--gold) 55%,var(--line))}
    .${P}-stat.me b{color:var(--gold)}
    .${P}-main{display:grid;gap:12px;grid-template-columns:1fr}
    @container (min-width:700px){.${P}-main{grid-template-columns:minmax(0,1fr) var(--side,260px)}}
    .${P}-col{display:grid;gap:10px;align-content:start}
    .${P}-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
    .${P}-phase{font-size:14px;font-weight:600}
    .${P}-msg{min-height:20px;font-size:13px;color:var(--muted)}
    .${P}-msg.bad{color:var(--bad)} .${P}-msg.good{color:var(--good)}
    .${P}-pal{display:flex;flex-wrap:wrap;gap:6px}
    .${P}-tool{display:flex;align-items:center;gap:8px;min-height:44px;padding:5px 10px 5px 8px;background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);text-align:left;line-height:1.15;flex:1 1 104px}
    .${P}-tool:hover:not(:disabled){background:var(--panel-3)}
    .${P}-tool .sw{flex:none;width:14px;height:14px;border-radius:4px}
    .${P}-tool .tx{display:grid}
    .${P}-tool b{font-size:13px;font-weight:700}
    .${P}-tool small{font-family:var(--f-mono);font-size:12px;color:var(--gold)}
    .${P}-tool.poor small{color:var(--muted)}
    .${P}-tool[aria-pressed="true"]{border-color:var(--gold);background:color-mix(in srgb,var(--gold) 14%,var(--panel-2))}
    .${P}-tool:disabled{opacity:.4;cursor:not-allowed}
    .${P}-info{font-size:13px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:8px 10px}
    .${P}-info b{color:var(--fg)}
    .${P} details{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:8px 10px;font-size:13px}
    .${P} summary{cursor:pointer;font-weight:600;min-height:28px}
    .${P}-rules{margin:6px 0 0;padding-left:18px;color:var(--muted)}
    .${P}-rules li{margin:2px 0}
    .${P}-res{background:var(--panel);border:1px solid color-mix(in srgb,var(--gold) 45%,var(--line));border-radius:var(--r-lg);padding:14px 16px;display:grid;gap:10px}
    .${P}-big{font-family:var(--f-display);font-size:44px;line-height:1;color:var(--gold);text-transform:uppercase}
    .${P}-big small{display:block;font-family:var(--f-body);font-size:14px;line-height:1.35;color:var(--muted);text-transform:none;margin-top:6px}
    .${P} .dg-table td,.${P} .dg-table th{padding:5px 6px}
    .${P} .tot td{font-weight:700;border-top:2px solid var(--line)}
    .${P} .dg-table .num{white-space:nowrap}
    `;
  }
  function stat(P, label, test, me) {
    return `<div class="${P}-stat${me ? " me" : ""}"><span>${label}</span><b data-test="${test}">–</b></div>`;
  }
  function makeSay(el, P) {
    return (t, kind) => { el.textContent = t || ""; el.className = P + "-msg" + (kind ? " " + kind : ""); };
  }
  function cssVar(el, k, d) {
    try { const v = getComputedStyle(el).getPropertyValue(k).trim(); return v || d; } catch (e) { return d; }
  }

  /* ====================================================================================
     BASE DUEL — play
     ==================================================================================== */
  const ECOL = { walker: "#8FBF6A", runner: "#D8E36B", brute: "#B07CD8", spitter: "#4FD1B8" };
  const TCOL = { wall: "#7A7FA8", arrow: "#F2C14E", cannon: "#FFB35C", frost: "#6FC3FF", spike: "#C9C6DD", mine: "#E8D27A" };
  const ENEMY_DESC = {
    walker: "Steady and common. Light armour (−1 per hit).",
    runner: "Twice as fast, very fragile.",
    brute: "Slow, 110+ HP, armour −4 per hit, smashes through walls.",
    spitter: "Stops to spit at towers within 2.4 tiles (not walls).",
  };
  function basePlay(ctx) {
    const P = "g-base";
    DG.css("base", packCss(P) + `
      .g-base-map{position:relative;border-radius:var(--r-md);overflow:hidden;border:1px solid var(--line);background:var(--panel)}
      .g-base-map canvas{cursor:crosshair}
      .g-base-map{background:transparent;border:0}
      .g-base-map canvas{border:1px solid var(--line);border-radius:var(--r-md)}
      .g-base-tb{display:grid;grid-template-columns:repeat(auto-fill,minmax(58px,1fr));gap:4px}
      .g-base-tbb{display:grid;align-content:center;justify-items:center;min-height:42px;padding:3px 2px;border-radius:var(--r-sm);border:1px solid var(--line);border-top:3px solid var(--c);background:var(--panel-2);line-height:1.1}
      .g-base-tbb b{font-size:12.5px;font-weight:700}
      .g-base-tbb small{font-family:var(--f-mono);font-size:11px;color:var(--gold)}
      .g-base-tbb.poor small{color:var(--muted)}
      .g-base-tbb:hover:not(:disabled){background:var(--panel-3)}
      .g-base-tbb[aria-pressed="true"]{border-color:var(--gold);border-top-color:var(--c);background:color-mix(in srgb,var(--gold) 16%,var(--panel-2))}
      .g-base-tbb:disabled{opacity:.4;cursor:not-allowed}
      .g-base-tbb.bomb.live{box-shadow:0 0 0 1px var(--bad) inset}
      .g-base .g-base-hud{grid-template-columns:repeat(5,minmax(0,1fr));gap:4px}
      .g-base .g-base-stat{padding:4px 6px}
      .g-base .g-base-stat span{font-size:9px;letter-spacing:.08em}
      .g-base .g-base-stat b{font-size:15px}
      .g-base .g-base-bar .dg-btn{min-height:38px;padding:6px 12px}
      .g-base .g-base-phase{font-size:13px}
      .g-base-prev{display:flex;flex-wrap:wrap;gap:6px}
      .g-base-prev span{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:3px 8px;font-size:13px;display:inline-flex;gap:6px;align-items:center}
      .g-base-prev i{width:10px;height:10px;border-radius:50%;display:inline-block}
      .g-base-elist{margin:6px 0 0;padding:0;list-style:none;display:grid;gap:4px;color:var(--muted)}
      .g-base-elist i{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px}
    `);
    const S = BaseSim(ctx.seed, ctx.mode), cfg = S.cfg;
    const log = [];
    S.onAct = (op, a) => log.push([S.wave, S.inWave ? S.waveTick : -1, op].concat(a));
    let phase = "build", phaseStart = 0, waveStart = 0, tool = "arrow", lastTower = "arrow", hover = null, pending = null;
    const towerTools = TOWER_ORDER.filter((t) => ctx.mode === "full" || t !== "mine");
    ctx.root.innerHTML = `<div class="${P}">
      <div class="${P}-hud">${stat(P, "Wave", "wave")}${stat(P, "HP", "hp")}${stat(P, "Gold", "gold")}${stat(P, "Kills", "kills")}${stat(P, "Score", "score", true)}</div>
      <div data-test="result"></div>
      <div class="${P}-main">
        <div class="${P}-col">
          <div class="${P}-map" data-test="map"></div>
          <div class="${P}-tb" data-test="palette" role="toolbar" aria-label="Build and actions">${towerTools.map((t, k) => `<button class="${P}-tbb" data-tool="${t}" data-test="tool-${t}" title="${U.esc(TOWERS[t].name + ": " + TOWERS[t].desc)} (key ${k + 1})" style="--c:${TCOL[t]}"><b>${TOWERS[t].short}</b><small>${TOWERS[t].cost}g</small></button>`).join("")}
            <button class="${P}-tbb" data-tool="sell" data-test="tool-sell" title="Sell: full refund, build phase only (S)" style="--c:var(--muted)"><b>Sell</b><small>refund</small></button>
            <button class="${P}-tbb" data-tool="repair" data-test="tool-repair" title="Repair a damaged structure (R)" style="--c:var(--good)"><b>Repair</b><small>gold</small></button>
            <button class="${P}-tbb bomb" data-tool="bomb" data-test="tool-bomb" title="Firebomb: area damage during waves (F)" style="--c:var(--bad)"><b>Bomb</b><small data-test="bombs">${S.bombs} left</small></button>
          </div>
          <div class="${P}-bar"><span class="${P}-phase" data-test="phase"></span><button class="dg-btn primary" data-test="go"></button></div>
          <div class="${P}-msg" data-test="msg"></div>
        </div>
        <div class="${P}-col" data-test="side">
          <div class="${P}-info" data-test="info"></div>
          <div class="dg-eyebrow" data-test="prev-title">Next wave</div>
          <div class="${P}-prev" data-test="preview"></div>
          <details><summary>Rules and zombies</summary>
            <ul class="${P}-rules">${BASE_RULES(ctx.mode).map((r) => `<li>${r}</li>`).join("")}</ul>
            <ul class="${P}-elist">${ENEMY_ORDER.map((k) => `<li><i style="background:${ECOL[k]}"></i><b style="color:var(--fg)">${ENEMIES[k].name}</b> — ${ENEMY_DESC[k]}</li>`).join("")}</ul>
          </details>
        </div>
      </div></div>`;
    const $ = (t) => ctx.root.querySelector(`[data-test="${t}"]`);
    const say = makeSay($("msg"), P);
    const C = {
      gold: cssVar(ctx.root, "--gold", "#F2C14E"), bad: cssVar(ctx.root, "--bad", "#FF6275"), good: cssVar(ctx.root, "--good", "#5AD690"),
      ally: cssVar(ctx.root, "--ally", "#6FC3FF"), panel2: cssVar(ctx.root, "--panel-2", "#212440"), panel3: cssVar(ctx.root, "--panel-3", "#2A2E52"),
      line: cssVar(ctx.root, "--line", "#30345A"), ink: cssVar(ctx.root, "--ink", "#10111F"), fg: cssVar(ctx.root, "--fg", "#EEEAF7"), muted: cssVar(ctx.root, "--muted", "#9D9BC0"),
    };
    // keep map + tool bar on one phone screen: cap the map height by the viewport
    const cvs = makeCanvas(ctx, $("map"), BW / BH, () => draw(), () => Math.max(180, (window.innerHeight || 800) - 330));
    let pathCache = null, pathFor = null;

    function tileAt(e) {
      const r = cvs.cv.getBoundingClientRect();
      const fx = ((e.clientX - r.left) / r.width) * BW, fy = ((e.clientY - r.top) / r.height) * BH;
      if (fx < 0 || fy < 0 || fx >= BW || fy >= BH) return null;
      return { x: Math.floor(fx), y: Math.floor(fy), fx: Math.round(fx * 100) / 100, fy: Math.round(fy * 100) / 100 };
    }
    function draw() {
      const g = cvs.g, w = cvs.w, h = cvs.h, ts = w / BW;
      if (!w) return;
      g.clearRect(0, 0, w, h);
      for (let y = 0; y < BH; y++) for (let x = 0; x < BW; x++) {
        const i = y * BW + x;
        g.fillStyle = (x + y) % 2 ? "#1B1E36" : "#1F2340";
        g.fillRect(x * ts, y * ts, ts + 0.5, ts + 0.5);
        if (S.map.grid[i]) {
          g.fillStyle = "#3B3552";
          g.beginPath();
          const cx = x * ts + ts / 2, cy = y * ts + ts / 2, r = ts * 0.42;
          for (let k = 0; k < 7; k++) { const a = (k / 7) * Math.PI * 2 + i, rr = r * (0.78 + 0.22 * Math.abs(Math.sin(i * 7 + k * 3))); g.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); }
          g.closePath(); g.fill();
          g.strokeStyle = "#4E4770"; g.lineWidth = 1; g.stroke();
        }
      }
      // paths (preview when hovering a blocking tool)
      let paths;
      const hv = pending || hover;
      if (hv && TOWERS[tool] && TOWERS[tool].block && phase !== "wave" && phase !== "done" && !S.canPlace(tool, hv.x, hv.y)) paths = S.previewPaths(tool, hv.x, hv.y);
      else { if (pathFor !== S.field) { pathCache = S.previewPaths(null, 0, 0); pathFor = S.field; } paths = pathCache; }
      g.save();
      g.setLineDash([ts * 0.12, ts * 0.14]); g.lineWidth = Math.max(1.5, ts * 0.06); g.strokeStyle = "rgba(255,98,117,.45)"; g.lineCap = "round";
      for (const p of paths) {
        g.beginPath();
        p.forEach((i, k) => { const x = (i % BW + 0.5) * ts, y = (((i / BW) | 0) + 0.5) * ts; if (k) g.lineTo(x, y); else g.moveTo(x, y); });
        g.stroke();
      }
      g.restore();
      // spawns
      for (const sp of S.map.spawns) {
        const x = sp.x * ts, y = sp.y * ts;
        g.fillStyle = "rgba(255,98,117,.18)"; g.fillRect(x + 2, y + 2, ts - 4, ts - 4);
        g.strokeStyle = C.bad; g.lineWidth = 2; g.strokeRect(x + 3, y + 3, ts - 6, ts - 6);
        g.fillStyle = C.bad; g.font = `700 ${Math.round(ts * 0.3)}px system-ui,sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText("IN", x + ts / 2, y + ts / 2);
      }
      // base core
      {
        const b = S.map.base, x = b.x * ts, y = b.y * ts;
        g.fillStyle = "rgba(242,193,78,.16)"; g.fillRect(x + 1, y + 1, ts - 2, ts - 2);
        g.fillStyle = C.gold; g.fillRect(x + ts * 0.26, y + ts * 0.26, ts * 0.48, ts * 0.48);
        g.fillStyle = "#1A1406"; g.fillRect(x + ts * 0.4, y + ts * 0.4, ts * 0.2, ts * 0.2);
        g.strokeStyle = "rgba(255,255,255,.12)"; g.lineWidth = 3;
        g.beginPath(); g.arc(x + ts / 2, y + ts / 2, ts * 0.44, 0, Math.PI * 2); g.stroke();
        g.strokeStyle = S.baseHp > 50 ? C.good : S.baseHp > 25 ? "#FFB35C" : C.bad;
        g.beginPath(); g.arc(x + ts / 2, y + ts / 2, ts * 0.44, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * S.baseHp / BASE_HP); g.stroke();
      }
      for (const s of S.list) if (s.hp > 0 || s.type === "spike") drawTower(g, s.type, s.x, s.y, ts, 1, s);
      // enemies
      for (const e of S.enemies) {
        const E = ENEMIES[e.type], r = E.r * ts * 1.25, cx = e.x * ts, cy = e.y * ts;
        g.fillStyle = ECOL[e.type]; g.strokeStyle = "#0B0C16"; g.lineWidth = 2;
        g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.fill(); g.stroke();
        if (e.slow < 1) { g.strokeStyle = C.ally; g.lineWidth = 1.5; g.beginPath(); g.arc(cx, cy, r + 2.5, 0, Math.PI * 2); g.stroke(); }
        if (e.hp < e.maxHp) {
          g.fillStyle = "#0B0C16"; g.fillRect(cx - r, cy - r - 6, r * 2, 3.5);
          g.fillStyle = C.bad; g.fillRect(cx - r, cy - r - 6, r * 2 * Math.max(0, e.hp / e.maxHp), 3.5);
        }
      }
      // fx
      for (const f of S.fx) {
        const a = Math.max(0, Math.min(1, f.t / 0.3));
        if (f.k === "shot") { g.strokeStyle = `rgba(242,193,78,${a})`; g.lineWidth = 2; g.beginPath(); g.moveTo(f.x * ts, f.y * ts); g.lineTo(f.x2 * ts, f.y2 * ts); g.stroke(); }
        else if (f.k === "splash") { g.fillStyle = `rgba(255,179,92,${0.35 * a})`; g.beginPath(); g.arc(f.x * ts, f.y * ts, f.r * ts, 0, Math.PI * 2); g.fill(); }
        else if (f.k === "bomb") { g.fillStyle = `rgba(255,98,117,${0.45 * Math.min(1, f.t / 0.6)})`; g.beginPath(); g.arc(f.x * ts, f.y * ts, f.r * ts, 0, Math.PI * 2); g.fill(); }
        else if (f.k === "spit") { g.strokeStyle = `rgba(79,209,184,${a})`; g.lineWidth = 2; g.beginPath(); g.moveTo(f.x * ts, f.y * ts); g.lineTo(f.x2 * ts, f.y2 * ts); g.stroke(); }
        else if (f.k === "hit" || f.k === "boom") { g.strokeStyle = `rgba(255,98,117,${a})`; g.lineWidth = 3; g.beginPath(); g.arc(f.x * ts, f.y * ts, ts * (0.6 - f.t), 0, Math.PI * 2); g.stroke(); }
      }
      // hover ghost / aim
      if (hv && phase !== "done") {
        const cx = (hv.x + 0.5) * ts, cy = (hv.y + 0.5) * ts;
        if (tool === "bomb") {
          const bx = (hv.fx != null ? hv.fx : hv.x + 0.5) * ts, by = (hv.fy != null ? hv.fy : hv.y + 0.5) * ts;
          g.strokeStyle = C.bad; g.setLineDash([5, 4]); g.lineWidth = 2;
          g.beginPath(); g.arc(bx, by, S.bombRadius * ts, 0, Math.PI * 2); g.stroke(); g.setLineDash([]);
        } else if (TOWERS[tool]) {
          const ok = !S.canPlace(tool, hv.x, hv.y);
          const occ = S.structs[S.idx(hv.x, hv.y)];
          if (occ && TOWERS[occ.type].range) ring(g, cx, cy, TOWERS[occ.type].range * ts, C.gold);
          else if (!occ && !S.map.grid[S.idx(hv.x, hv.y)]) {
            drawTower(g, tool, hv.x, hv.y, ts, ok ? 0.55 : 0.25, null);
            if (TOWERS[tool].range) ring(g, cx, cy, TOWERS[tool].range * ts, ok ? C.gold : C.bad);
            if (!ok) { g.strokeStyle = C.bad; g.lineWidth = 2; g.strokeRect(hv.x * ts + 2, hv.y * ts + 2, ts - 4, ts - 4); }
          }
          if (pending) { g.strokeStyle = C.gold; g.lineWidth = 3; g.strokeRect(pending.x * ts + 1.5, pending.y * ts + 1.5, ts - 3, ts - 3); }
        } else {
          g.strokeStyle = tool === "sell" ? C.muted : C.good; g.lineWidth = 2; g.strokeRect(hv.x * ts + 2, hv.y * ts + 2, ts - 4, ts - 4);
        }
      }
    }
    function ring(g, cx, cy, r, col) {
      g.save(); g.strokeStyle = col; g.globalAlpha = 0.7; g.setLineDash([4, 4]); g.lineWidth = 1.5;
      g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke(); g.restore();
    }
    function drawTower(g, type, x, y, ts, alpha, s) {
      const cx = (x + 0.5) * ts, cy = (y + 0.5) * ts, col = TCOL[type];
      g.save(); g.globalAlpha = alpha;
      if (s && s.flash > 0) g.globalAlpha = alpha * 0.6;
      if (type === "wall") {
        g.fillStyle = "#565B85"; g.fillRect(x * ts + ts * 0.08, y * ts + ts * 0.08, ts * 0.84, ts * 0.84);
        g.strokeStyle = "#8388B5"; g.lineWidth = 1;
        for (let k = 1; k < 3; k++) { g.beginPath(); g.moveTo(x * ts + ts * 0.08, y * ts + ts * (0.08 + 0.28 * k)); g.lineTo(x * ts + ts * 0.92, y * ts + ts * (0.08 + 0.28 * k)); g.stroke(); }
      } else if (type === "spike") {
        g.fillStyle = col;
        for (let k = 0; k < 4; k++) {
          const ox = x * ts + ts * (0.22 + 0.36 * (k % 2)), oy = y * ts + ts * (0.22 + 0.36 * (k >> 1));
          g.beginPath(); g.moveTo(ox, oy - ts * 0.13); g.lineTo(ox + ts * 0.12, oy + ts * 0.1); g.lineTo(ox - ts * 0.12, oy + ts * 0.1); g.closePath(); g.fill();
        }
      } else {
        g.fillStyle = "#2A2E52"; g.strokeStyle = col; g.lineWidth = Math.max(2, ts * 0.07);
        g.beginPath(); g.arc(cx, cy, ts * 0.36, 0, Math.PI * 2); g.fill(); g.stroke();
        g.fillStyle = col;
        if (type === "arrow") { g.beginPath(); g.moveTo(cx, cy - ts * 0.2); g.lineTo(cx + ts * 0.15, cy + ts * 0.14); g.lineTo(cx - ts * 0.15, cy + ts * 0.14); g.closePath(); g.fill(); }
        else if (type === "cannon") { g.beginPath(); g.arc(cx, cy, ts * 0.16, 0, Math.PI * 2); g.fill(); g.fillRect(cx - ts * 0.05, cy - ts * 0.3, ts * 0.1, ts * 0.2); }
        else if (type === "frost") { g.beginPath(); g.moveTo(cx, cy - ts * 0.22); g.lineTo(cx + ts * 0.17, cy); g.lineTo(cx, cy + ts * 0.22); g.lineTo(cx - ts * 0.17, cy); g.closePath(); g.fill(); }
        else if (type === "mine") { g.font = `800 ${Math.round(ts * 0.34)}px system-ui,sans-serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("G", cx, cy + 1); }
      }
      if (s && s.maxHp && s.hp < s.maxHp) {
        g.globalAlpha = 1;
        g.fillStyle = "#0B0C16"; g.fillRect(x * ts + ts * 0.12, y * ts + ts * 0.86, ts * 0.76, 4);
        g.fillStyle = s.hp / s.maxHp > 0.45 ? C.good : C.bad; g.fillRect(x * ts + ts * 0.12, y * ts + ts * 0.86, ts * 0.76 * Math.max(0, s.hp / s.maxHp), 4);
      }
      g.restore();
    }
    // ---- HUD
    const hudCache = {};
    function setT(t, v) { if (hudCache[t] !== v) { hudCache[t] = v; const el = $(t); if (el) el.textContent = v; } }
    function setTool(t) {
      if (phase === "done") return;
      tool = t; pending = null;
      if (TOWERS[t]) lastTower = t;
      ctx.root.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tool === t)));
      const T = TOWERS[t];
      $("info").innerHTML = T ? `<b>${T.name}</b> · ${T.cost} gold${T.hp ? " · " + T.hp + " HP" : ""}<br>${T.desc}` :
        t === "sell" ? "<b>Sell</b> · tap a structure for a full refund. Build phase only." :
        t === "repair" ? "<b>Repair</b> · tap a damaged structure. Cost grows with the damage (up to 60% of its price)." :
        `<b>Firebomb</b> · during a wave, tap the map: ${S.bombDamage()} damage in a ${S.bombRadius}-tile radius. 5 s cooldown.`;
    }
    function hud() {
      setT("wave", Math.min(S.wave + (phase === "wave" ? 1 : 0), cfg.waves) + "/" + cfg.waves);
      setT("hp", String(Math.ceil(S.baseHp)));
      setT("gold", String(S.gold));
      setT("kills", String(S.kills));
      setT("score", phase === "build" ? "0" : U.fmt(S.score())); // nothing is scored until the defence starts
      setT("bombs", S.bombCd > 0 && phase === "wave" ? `cool ${Math.ceil(S.bombCd)}s` : `${S.bombs} left`);
      const goTxt = phase === "build" ? "Start waves" : phase === "window" ? "Next wave now" : phase === "wave" ? "Wave running" : "Finished";
      const go = $("go");
      if (go.textContent !== goTxt) { go.textContent = goTxt; go.disabled = phase === "wave" || phase === "done"; }
      const ph = phase === "build" ? `Build your defence · ${cfg.gold} gold budget` : phase === "window" ? `Wave ${S.wave} held · build, repair, or start the next wave` :
        phase === "wave" ? `Wave ${S.wave + 1} of ${cfg.waves} · use Firebomb and Repair` : "Defence over";
      setT("phase", ph);
      const wv = S.waves[S.wave];
      const pv = !wv || phase === "done" ? "" : wv.counts.map(([k, c]) => `<span><i style="background:${ECOL[k]}"></i>${ENEMIES[k].name} ×${c}</span>`).join("");
      if (hudCache.prev !== pv) { hudCache.prev = pv; $("preview").innerHTML = pv || '<span class="dg-muted">No more waves</span>'; }
      setT("prev-title", phase === "done" ? "Waves" : phase === "wave" ? `This wave (${S.wave + 1})` : `Next wave (${Math.min(S.wave + 1, cfg.waves)} of ${cfg.waves})`);
      ctx.root.querySelectorAll("[data-tool]").forEach((b) => {
        const T = TOWERS[b.dataset.tool];
        b.classList.toggle("poor", !!T && T.cost > S.gold);
        if (b.dataset.tool === "bomb") b.classList.toggle("live", phase === "wave" && S.bombs > 0 && S.bombCd <= 0);
      });
    }
    // ---- flow
    function startWave() {
      if (phase === "done" || phase === "wave" || S.over) return;
      phase = "wave"; pending = null;
      S.startWave(); waveStart = ctx.now();
      if (S.bombs > 0) setTool("bomb");
      say("Wave " + (S.wave + 1) + " incoming.", "");
    }
    function waveOver() {
      S.fx = [];
      ctx.progress(S.score());
      if (S.over) { finish(); return; }
      phase = "window"; phaseStart = ctx.now();
      setTool(lastTower);
      say(`Wave ${S.wave} held. +${cfg.windowMs / 1000} s to build or repair.`, "good");
    }
    function finish() {
      if (phase === "done") return;
      phase = "done"; hover = null; pending = null;
      const score = S.score();
      const rows = [
        ["Waves survived", `${S.survived} × 1,000`, 1000 * S.survived],
        ["Base HP left", `${Math.max(0, Math.round(S.baseHp))} × 5`, Math.max(0, Math.round(S.baseHp)) * 5],
        ["Kills", `${S.kills} × 10`, 10 * S.kills],
        ["Unspent gold", `${S.gold} ÷ 10`, Math.floor(S.gold / 10)],
      ];
      const table = `<table class="dg-table"><tbody>${rows.map((r) => `<tr><td>${r[0]}</td><td class="num dg-muted">${r[1]}</td><td class="num">${U.fmt(r[2])}</td></tr>`).join("")}
        <tr class="tot"><td>Total</td><td></td><td class="num dg-gold">${U.fmt(score)}</td></tr></tbody></table>`;
      const verdict = S.dead ? `Base destroyed in wave ${S.wave + 1}.` : `All ${cfg.waves} waves held.`;
      $("result").innerHTML = `<div class="${P}-res"><div class="dg-eyebrow">Base Duel · final</div>
        <div class="${P}-big" data-test="final">${U.fmt(score)}<small>points · ${verdict}</small></div>${table}</div>`;
      ctx.root.querySelectorAll("[data-tool]").forEach((b) => { b.disabled = true; b.setAttribute("aria-pressed", "false"); });
      say(verdict, S.dead ? "bad" : "good");
      hud(); draw();
      ctx.setStatus("Final · " + U.fmt(score));
      ctx.progress(score);
      ctx.timeout(() => ctx.end({ score, detail: `<p class="dg-note">${verdict} ${S.survived} waves, ${Math.max(0, Math.round(S.baseHp))} HP, ${S.kills} kills.</p>${table}` }), 900);
    }
    function frame(now) {
      if (ctx.signal.ended) return;
      if (phase === "wave") {
        const target = Math.round(baseSimAt(cfg, now - waveStart) / DT);
        let n = 0;
        while (S.inWave && !S.over && S.waveTick < target && n++ < 800) S.step();
        if (!S.inWave || S.over) waveOver();
      }
      draw(); hud();
      ctx.raf(frame);
    }
    function act(e) {
      if (phase === "done" || ctx.signal.ended) return;
      const p = tileAt(e);
      if (!p) return;
      hover = p;
      if (tool === "bomb") {
        const why = S.bomb(p.fx, p.fy);
        say(why || "Firebomb away.", why ? "bad" : "good");
        if (!why && S.bombs === 0) setTool("repair");
        return;
      }
      const s = S.structs[S.idx(p.x, p.y)];
      if (tool === "repair") { const why = S.repair(p.x, p.y); say(why || "Repaired.", why ? "bad" : "good"); return; }
      if (tool === "sell") { const why = S.sell(p.x, p.y); say(why || "Sold for a full refund.", why ? "bad" : "good"); return; }
      if (s) { say(`${TOWERS[s.type].name}: ${Math.ceil(s.hp)}/${s.maxHp} HP. Use Sell or Repair on it.`, ""); return; }
      const why = S.canPlace(tool, p.x, p.y);
      if (why) { say(why + ".", "bad"); pending = null; return; }
      const T = TOWERS[tool];
      if (e.pointerType && e.pointerType !== "mouse" && T.cost >= 50 && !(pending && pending.x === p.x && pending.y === p.y && pending.t === tool)) {
        pending = { x: p.x, y: p.y, t: tool };
        say(`Tap again to build ${T.name} for ${T.cost} gold.`, "");
        return;
      }
      pending = null;
      S.place(tool, p.x, p.y);
      say(`${T.name} built. ${S.gold} gold left.`, "good");
    }
    const cv = cvs.cv;
    cv.addEventListener("pointerdown", (e) => { e.preventDefault(); act(e); });
    cv.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse" || !pending) hover = tileAt(e); });
    cv.addEventListener("pointerleave", () => { if (!pending) hover = null; });
    ctx.root.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
    $("go").addEventListener("click", () => { if (phase === "build" || phase === "window") startWave(); });
    ctx.onKey((e) => {
      if (phase === "done") return;
      const k = e.key.toLowerCase();
      const n = parseInt(k, 10);
      if (n >= 1 && n <= towerTools.length) setTool(towerTools[n - 1]);
      else if (k === "s") setTool("sell"); else if (k === "r") setTool("repair"); else if (k === "f") setTool("bomb");
      else if (k === "enter" && (phase === "build" || phase === "window")) startWave();
    });
    ctx.interval(() => {
      const now = ctx.now();
      if (phase === "build") {
        const left = cfg.buildMs - now;
        ctx.setStatus("Build · " + mmss(left));
        if (left <= 0) startWave();
      } else if (phase === "window") {
        const left = cfg.windowMs - (now - phaseStart);
        ctx.setStatus(`Wave ${S.wave + 1} in ${Math.max(0, Math.ceil(left / 1000))} s`);
        if (left <= 0) startWave();
      } else if (phase === "wave") ctx.setStatus(`Wave ${S.wave + 1}/${cfg.waves}`);
    }, 200);
    setTool("arrow");
    say(ctx.mode === "mix" ? "Quick defence: 20 s to build, then 3 waves." : "Build towers on the grid. Walls and towers reroute the zombies (dashed lines).", "");
    ctx.setStatus("Build · " + mmss(cfg.buildMs));
    hud();
    ctx.raf(frame);

    ctx.test = {
      state: () => ({ phase, gold: S.gold, wave: S.wave, survived: S.survived, baseHp: S.baseHp, kills: S.kills, bombs: S.bombs, score: S.score(), over: S.over,
        structs: S.list.map((s) => ({ type: s.type, x: s.x, y: s.y, hp: s.hp })), enemies: S.enemies.map((e) => ({ type: e.type, x: e.x, y: e.y })), log: log.slice(), tool }),
      placeAI(skill) { if (phase === "wave" || phase === "done") return 0; const n0 = S.list.length; aiBuild(S, U.rng("ui-ai:" + ctx.seed + ":" + skill), skill == null ? 0.9 : skill, phase === "build" ? "build" : "window"); return S.list.length - n0; },
      skipToDefence() { if (phase === "build" || phase === "window") startWave(); },
      fastForward() {
        if (phase === "done") return;
        let guard = 0;
        while (!S.over && guard++ < 200000) { if (!S.inWave) S.startWave(); S.step(); }
        phase = "wave"; waveOver();
      },
      tilePoint(x, y) { const r = cv.getBoundingClientRect(); return { x: r.left + ((x + 0.5) / BW) * r.width, y: r.top + ((y + 0.5) / BH) * r.height }; },
      mapPoint(fx, fy) { const r = cv.getBoundingClientRect(); return { x: r.left + (fx / BW) * r.width, y: r.top + (fy / BH) * r.height }; },
      legal(type) { const out = []; for (let y = 0; y < BH; y++) for (let x = 0; x < BW; x++) if (!S.canPlace(type, x, y)) out.push([x, y]); return out; },
      why: (type, x, y) => S.canPlace(type, x, y),
      replay: (lg) => baseReplay(ctx.seed, ctx.mode, lg || log),
      setTool,
    };
  }
  function BASE_RULES(mode) {
    const c = baseConfig(mode);
    return [
      `Build phase (${c.buildMs / 1000} s): spend ${c.gold} gold on walls, towers and traps. Sell for a full refund while building.`,
      `Zombies walk the shortest route to your core (dashed lines). Towers and walls reroute them, but you can never seal the path.`,
      `Then ${c.waves} identical seeded waves attack. Between waves you get ${c.windowMs / 1000} s to spend gold earned from kills.`,
      `During waves: ${c.bombs} Firebombs (tap the map) and Repair (costs gold).`,
      `Score = 1,000 per wave survived + 5 × base HP + 10 per kill + unspent gold ÷ 10. Losing the base ends the run.`,
    ];
  }

  /* ====================================================================================
     CITY DUEL — play
     ==================================================================================== */
  const CITY_RADIUS = { park: 2, com: 2, ind: 2, power: 2, transit: 2, hosp: 3, school: 2, police: 3 };
  function cityFacts(k) {
    const B = BLD[k], f = [];
    if (B.house) f.push(`houses ${B.house}`);
    if (B.jobs) f.push(`${B.jobs} jobs`);
    if (B.gen) f.push(`+${B.gen} energy`);
    if (B.wgen) f.push(`+${B.wgen} water`);
    if (B.energy) f.push(`uses ${B.energy} energy`);
    if (B.water) f.push(`uses ${B.water} water`);
    if (B.traf) f.push(`traffic ${B.traf}`);
    if (B.crime) f.push(`crime ${B.crime}`);
    if (B.pol) f.push(`pollution ${B.pol}`);
    if (CITY_RADIUS[k]) f.push(`radius ${CITY_RADIUS[k]}`);
    return f.join(" · ");
  }
  function cityPlay(ctx) {
    const P = "g-city";
    DG.css("city", packCss(P) + `
      .g-city-grid{display:grid;gap:3px;background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:6px;touch-action:manipulation}
      .g-city-t{position:relative;aspect-ratio:1;min-height:36px;border-radius:6px;border:1px solid var(--line);background:#1F2340;padding:2px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0;font-size:11px;line-height:1.1;overflow:hidden;color:var(--fg)}
      .g-city-t:hover:not(:disabled){border-color:var(--muted)}
      .g-city-t.water{background:repeating-linear-gradient(135deg,#1C3E5E 0 6px,#18344F 6px 12px);cursor:not-allowed}
      .g-city-t.rock{background:#3B3552;cursor:not-allowed}
      .g-city-t .k{font-weight:700;letter-spacing:.02em;text-transform:uppercase;font-size:10px}
      .g-city-t .lg{display:none} .g-city-t .sm{display:inline}
      @container (min-width:560px){.g-city-t .lg{display:inline}.g-city-t .sm{display:none}.g-city-t .k{font-size:11px}}
      .g-city-t .v{font-family:var(--f-mono);font-size:11px}
      .g-city-t.in{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--gold) 60%,transparent)}
      .g-city-t.pend{box-shadow:inset 0 0 0 3px var(--gold)}
      .g-city-t.glow{box-shadow:inset 0 0 0 2px var(--gold)}
      .g-city-prog{flex:1 1 120px;max-width:220px;height:6px;border-radius:3px;background:var(--panel-2);overflow:hidden}
      .g-city-prog i{display:block;height:100%;width:0;background:var(--gold)}
      .g-city-stats{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:13px;background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:8px 10px}
      .g-city-stats span{color:var(--muted)} .g-city-stats b{font-family:var(--f-mono);font-weight:600;text-align:right}
      .g-city-stats .sc{border-top:1px solid var(--line);padding-top:4px;margin-top:2px}
      .g-city-stats .parts{grid-column:1/-1;font-size:12px}
      .g-city-rep{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px}
      .g-city-rep div{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:6px 10px}
      .g-city-rep span{display:block;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600}
      .g-city-rep b{font-family:var(--f-mono);font-size:17px}
      .g-city-leg td{font-size:12px;vertical-align:top}
    `);
    const map = cityMap(ctx.seed, ctx.mode), cfg = cityConfig(ctx.mode), n = map.n;
    const plan = new Array(n * n).fill(null);
    let tool = "res", phase = "build", pending = -1, lastPtr = "mouse", hoverI = -1, ev = cityEval(map, plan);
    const moves = [];
    ctx.root.innerHTML = `<div class="${P}">
      <div class="${P}-hud">${stat(P, "Budget left", "budget")}${stat(P, "Population", "pop")}${stat(P, "Happiness", "hap")}${stat(P, "City score", "score", true)}</div>
      <div data-test="result"></div>
      <div class="${P}-main">
        <div class="${P}-col">
          <div class="${P}-grid" data-test="grid" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${plan.map((_, i) =>
            `<button class="${P}-t${map.tiles[i] === 1 ? " water" : map.tiles[i] === 2 ? " rock" : ""}" data-i="${i}" data-test="tile-${i}" aria-label="Tile ${i % n + 1},${((i / n) | 0) + 1}"></button>`).join("")}</div>
          <div class="${P}-bar"><span class="${P}-phase" data-test="phase">Place buildings, then finish.</span><span class="dg-row" style="gap:8px"><button class="dg-btn" data-test="undo" disabled>Undo</button><button class="dg-btn primary" data-test="finish">Finish city</button></span></div>
          <div class="${P}-msg" data-test="msg"></div>
        </div>
        <div class="${P}-col">
          <div class="dg-eyebrow">Buildings (tap one, then a tile)</div>
          <div class="${P}-pal" data-test="palette">${BLD_ORDER.map((k) => `<button class="${P}-tool" data-tool="${k}" data-test="tool-${k}" title="${U.esc(BLD[k].desc)}"><i class="sw" style="background:${BLD[k].col}"></i><span class="tx"><b>${BLD[k].short}</b><small>$${U.fmt(BLD[k].cost)}</small></span></button>`).join("")}
            <button class="${P}-tool" data-tool="bulldoze" data-test="tool-bulldoze" title="Remove a building for a full refund"><i class="sw" style="background:var(--bad)"></i><span class="tx"><b>Bulldoze</b><small>refund</small></span></button></div>
          <div class="${P}-info" data-test="info"></div>
          <div class="dg-eyebrow">Projected city</div>
          <div class="${P}-stats" data-test="stats"></div>
          <details><summary>How the score works</summary><ul class="${P}-rules">${CITY_RULES(ctx.mode).map((r) => `<li>${r}</li>`).join("")}</ul></details>
          <details><summary>Building guide</summary><table class="dg-table ${P}-leg"><tbody>${BLD_ORDER.map((k) => `<tr><td><b>${BLD[k].name}</b><br><span class="dg-gold dg-mono">$${U.fmt(BLD[k].cost)}</span></td><td class="dg-muted">${BLD[k].desc}<br>${cityFacts(k)}</td></tr>`).join("")}</tbody></table></details>
        </div>
      </div></div>`;
    const $ = (t) => ctx.root.querySelector(`[data-test="${t}"]`);
    const say = makeSay($("msg"), P);
    const tiles = [...ctx.root.querySelectorAll(`.${P}-t`)];
    const hapCol = (h) => (h >= 60 ? "var(--good)" : h >= 40 ? "var(--warn)" : "var(--bad)");
    function renderTiles() {
      tiles.forEach((el, i) => {
        const k = plan[i];
        let html = "", bg = "";
        if (k) {
          const B = BLD[k];
          bg = `color-mix(in srgb,${B.col} 30%,#1F2340)`;
          html = `<span class="k" style="color:${B.col}"><span class="lg">${B.short}</span><span class="sm">${B.tile}</span></span>`;
          if (k === "res" && ev.homeHap[i] != null) html += `<span class="v" style="color:${hapCol(ev.homeHap[i])}">${ev.homeHap[i]}</span>`;
        }
        if (el._h !== html) { el.innerHTML = html; el._h = html; }
        if (!map.tiles[i]) el.style.background = bg;
        el.classList.toggle("pend", i === pending);
        const R = hoverI >= 0 && CITY_RADIUS[tool] != null && phase === "build" ? CITY_RADIUS[tool] : -1;
        el.classList.toggle("in", R >= 0 && Math.max(Math.abs((i % n) - (hoverI % n)), Math.abs(((i / n) | 0) - ((hoverI / n) | 0))) <= R);
      });
    }
    function pct(v) { return Math.round(v) + "%"; }
    function statsHtml(e) {
      const rows = [
        ["Population", U.fmt(e.population)], ["Happiness", pct(e.happiness)], ["Revenue", money(e.revenue) + "/day"],
        ["Employment", pct(e.employment * 100) + ` · ${U.fmt(e.jobs)} jobs`], ["Energy", `${e.energy[0]} / ${e.energy[1]} used`],
        ["Water", `${e.water[0]} / ${e.water[1]} used`], ["Traffic", pct(e.trafficPct)], ["Crime", pct(e.crimePct)], ["Pollution", pct(e.pollutionPct)],
        ["Growth", (e.growth >= 0 ? "+" : "") + e.growth.toFixed(1) + "%/yr"],
      ];
      const warn = (lab) => (lab === "Energy" && e.energy[1] > e.energy[0]) || (lab === "Water" && e.water[1] > e.water[0]) ? ' class="dg-bad"' : "";
      return rows.map(([a, b]) => `<span>${a}</span><b${warn(a)}>${b}</b>`).join("") +
        `<span class="sc">City score</span><b class="sc dg-gold">${(e.score10 / 10).toFixed(1)}</b><span class="parts">= People ${e.parts.people.toFixed(1)} + Money ${e.parts.money.toFixed(1)} + Growth ${e.parts.growth.toFixed(1)}</span>`;
    }
    let lastScore = null;
    function refresh() {
      ev = cityEval(map, plan);
      $("budget").textContent = "$" + U.fmt(ev.left);
      $("pop").textContent = U.fmt(ev.population);
      $("hap").textContent = pct(ev.happiness);
      $("score").textContent = (ev.score10 / 10).toFixed(1);
      $("stats").innerHTML = statsHtml(ev);
      ctx.root.querySelectorAll("[data-tool]").forEach((b) => { const B = BLD[b.dataset.tool]; b.classList.toggle("poor", !!B && B.cost > ev.left); });
      const ub = $("undo"); if (ub) ub.disabled = phase !== "build" || !moves.length;
      renderTiles();
      if (lastScore !== ev.score10) { lastScore = ev.score10; ctx.progress(ev.score10 / 10); }
    }
    function setTool(t) {
      tool = t; pending = -1;
      ctx.root.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tool === t)));
      $("info").innerHTML = t === "bulldoze" ? "<b>Bulldoze</b> · tap a building to remove it for a full refund." :
        `<b>${BLD[t].name}</b> · <span class="dg-gold dg-mono">$${U.fmt(BLD[t].cost)}</span><br>${BLD[t].desc}<br><span class="dg-note">${cityFacts(t)}</span>`;
      renderTiles();
    }
    function tap(i) {
      if (phase !== "build" || ctx.signal.ended) return;
      if (tool === "bulldoze") {
        if (!plan[i]) { say("Nothing to bulldoze there.", "bad"); return; }
        const k = plan[i]; plan[i] = null; moves.push(["x", i, k]);
        say(`${BLD[k].name} removed, $${U.fmt(BLD[k].cost)} refunded.`, "good"); refresh(); return;
      }
      if (plan[i]) { say(`${BLD[plan[i]].name} is here. Bulldoze it first.`, ""); return; }
      const why = cityCanPlace(map, plan, i, tool);
      if (why) { say(why + ".", "bad"); pending = -1; renderTiles(); return; }
      const B = BLD[tool];
      pending = -1;
      const before = ev.score10;
      plan[i] = tool; moves.push(["b", i, tool]);
      refresh();
      const d = (ev.score10 - before) / 10;
      say(`${B.name} built. Score ${d >= 0 ? "+" : ""}${d.toFixed(1)}.`, d >= 0 ? "good" : "bad");
    }
    tiles.forEach((el, i) => {
      el.addEventListener("pointerdown", (e) => { lastPtr = e.pointerType || "mouse"; });
      el.addEventListener("click", () => tap(i));
      el.addEventListener("pointerenter", () => { hoverI = i; renderTiles(); });
      el.addEventListener("pointerleave", () => { if (hoverI === i) { hoverI = -1; renderTiles(); } });
    });
    ctx.root.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
    $("finish").addEventListener("click", () => finish());
    $("undo").addEventListener("click", () => undo());
    function undo() {
      if (phase !== "build" || !moves.length) return;
      const m = moves.pop();
      if (m[0] === "b") { plan[m[1]] = null; say(`Undid ${BLD[m[2]].name}.`, ""); }
      else { plan[m[1]] = m[2]; say(`Restored ${BLD[m[2]].name}.`, ""); }
      refresh();
    }
    ctx.onKey((e) => {
      if (phase !== "build") return;
      const k = e.key.toUpperCase();
      const t = BLD_ORDER.find((q) => BLD[q].key === k);
      if ((e.ctrlKey || e.metaKey) && k === "Z") { e.preventDefault(); undo(); return; }
      if (t) setTool(t); else if (k === "B" || k === "DELETE") setTool("bulldoze");
    });
    const t0 = ctx.now();
    ctx.interval(() => {
      if (phase !== "build") return;
      const left = cfg.buildMs - (ctx.now() - t0);
      ctx.setStatus("Build · " + mmss(left));
      if (left <= 0) finish();
    }, 250);

    function finish(instant) {
      if (phase !== "build") return;
      phase = "sim"; pending = -1; hoverI = -1;
      const e = cityEval(map, plan), score = e.score10 / 10;
      ctx.root.querySelectorAll("button").forEach((b) => (b.disabled = true));
      say("", "");
      $("phase").textContent = "Simulating a year…";
      ctx.setStatus("Simulating");
      const metrics = [
        ["Population", (v) => U.fmt(v), e.population], ["Happiness", (v) => pct(v), e.happiness], ["Revenue", (v) => money(v) + "/day", e.revenue],
        ["Traffic", (v) => pct(v), e.trafficPct], ["Crime", (v) => pct(v), e.crimePct], ["Pollution", (v) => pct(v), e.pollutionPct],
        ["Energy", (v) => `${Math.round(v)} / ${e.energy[1]}`, e.energy[0]], ["Employment", (v) => pct(v), e.employment * 100],
        ["Growth", (v) => (v >= 0 ? "+" : "") + v.toFixed(1) + "%/yr", e.growth],
      ];
      $("result").innerHTML = `<div class="${P}-res"><div class="${P}-bar"><div class="dg-eyebrow" data-test="rep-title">Simulating a year…</div><div class="${P}-prog"><i data-test="simbar"></i></div></div>
        <div class="${P}-rep">${metrics.map((m, k) => `<div><span>${m[0]}</span><b data-m="${k}">${m[1](m[2])}</b></div>`).join("")}</div>
        <div class="${P}-big" data-test="final">${score.toFixed(1)}<small>city score</small></div>
        <p class="dg-note" style="margin:0">People ${e.parts.people.toFixed(1)} (population × (happiness + 15) ÷ 690) + Money ${e.parts.money.toFixed(1)} (revenue ÷ 40) + Growth ${e.parts.growth.toFixed(1)} (growth × 3, or × 1 if shrinking).</p></div>`;
      const built = tiles.map((_, i) => i).filter((i) => plan[i]);
      // Only the reveal animates. Every number above is the exact final value from the first frame, identical to the HUD.
      const paint = (t) => {
        const bar = $("simbar"); if (bar) bar.style.width = Math.round(t * 100) + "%";
        built.forEach((i, k) => tiles[i].classList.toggle("glow", t < 1 && Math.abs(k / Math.max(1, built.length) - t) < 0.15));
        if (t >= 1) { const ti = $("rep-title"); if (ti) ti.textContent = "City report"; }
      };
      const done = () => {
        paint(1);
        $("phase").textContent = "Final city";
        ctx.setStatus("Final · " + score.toFixed(1));
        ctx.progress(score);
        const detail = `<p class="dg-note">Population ${U.fmt(e.population)}, happiness ${pct(e.happiness)}, revenue ${money(e.revenue)}/day, growth ${e.growth.toFixed(1)}%/yr.</p>`;
        ctx.timeout(() => ctx.end({ score, detail }), 700);
      };
      if (ctx.reducedMotion || instant) { done(); return; }
      const DUR = ctx.mode === "mix" ? 3000 : 3600, s0 = ctx.now();
      const step = (now) => { const t = Math.min(1, (now - s0) / DUR); if (t >= 1) { done(); return; } paint(t); ctx.raf(step); };
      paint(0); ctx.raf(step);
    }
    setTool("res");
    refresh();
    say(`Budget $${U.fmt(map.budget)}. Homes need jobs, power, water and nearby services.`, "");
    ctx.setStatus("Build · " + mmss(cfg.buildMs));
    ctx.test = {
      state: () => ({ phase, plan: plan.slice(), eval: cityEval(map, plan), tiles: map.tiles.slice(), n, moves: moves.slice(),
        hud: $("score").textContent, report: $("final") ? parseFloat($("final").textContent) : null }),
      undo,
      place(i, t) { setTool(t); tap(i); return plan[i] === t; },
      autoBuild(skill) {
        if (phase !== "build") return 0;
        for (let i = 0; i < plan.length; i++) plan[i] = null;
        const r = cityPlan(map, U.rng("ui-city:" + ctx.seed + ":" + skill), skill == null ? 0.9 : skill);
        r.plan.forEach((k, i) => { plan[i] = k; });
        refresh();
        return r.score10 / 10;
      },
      finish: (instant) => finish(instant !== false),
      score: () => cityEval(map, plan).score10 / 10,
    };
  }
  function CITY_RULES(mode) {
    const c = cityConfig(mode);
    return [
      `Same ${c.n}×${c.n} plot for everyone, $${U.fmt(c.budget)} budget, ${c.buildMs / 1000} s. Bulldoze refunds in full.`,
      `Homes are the heart: each home's happiness (number on the tile) comes from parks, hospital, school, police and shops in reach, minus pollution, crime, traffic and unemployment.`,
      `Everything needs energy and water. Shortages hit every building.`,
      `Half of residents want jobs: shops, factories and services employ them and pay taxes.`,
      `City score = People (population × happiness) + Money (daily revenue) + Growth. Mixed cities beat any single-building spam.`,
    ];
  }

  /* ====================================================================================
     RESTAURANT DUEL — play
     ==================================================================================== */
  function restFix(plan) {
    const q = JSON.parse(JSON.stringify(plan));
    for (const d of ["soup", "tacos", "salad", "burger", "pasta"]) if (q.menu.length < 3 && !q.menu.includes(d)) q.menu.push(d);
    if (q.menu.length > 5) q.menu = q.menu.slice(0, 5);
    q.chefs = clamp(q.chefs, 1, KITCHEN[q.kitchen].maxChefs);
    let guard = 0;
    while (restSpend(q) > 10000 && guard++ < 200) {
      if (q.marketing > 0) q.marketing = Math.max(0, q.marketing - 250);
      else if (q.tables > 4) q.tables--;
      else if (q.waiters > 1) q.waiters--;
      else if (q.chefs > 1) q.chefs--;
      else if (q.kitchen > 0) q.kitchen--;
      else break;
    }
    return q;
  }
  const hhmm = (m) => { const t = DAY_OPEN + Math.round(m); return String(Math.floor(t / 60) % 24).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0"); };
  function restaurantPlay(ctx) {
    const P = "g-restaurant";
    DG.css("restaurant", packCss(P) + `
      .g-restaurant-sec{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-md);padding:10px 12px;display:grid;gap:8px}
      .g-restaurant{--side:320px}
      .g-restaurant-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:10px}
      .g-restaurant-row label{font-weight:600;font-size:14px}
      .g-restaurant-row .dg-note{display:block;font-weight:400}
      .g-restaurant-step{display:flex;align-items:center;gap:6px}
      .g-restaurant-step button{width:40px;height:40px;border-radius:8px;border:1px solid var(--line);background:var(--panel-2);font-size:20px;font-weight:700;line-height:1}
      .g-restaurant-step button:hover:not(:disabled){background:var(--panel-3)}
      .g-restaurant-step button:disabled{opacity:.35;cursor:not-allowed}
      .g-restaurant-step b{font-family:var(--f-mono);min-width:56px;text-align:center;font-size:16px}
      .g-restaurant-chips{display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:6px}
      .g-restaurant-chip{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:6px 9px;text-align:left;min-height:44px;line-height:1.2}
      .g-restaurant-chip b{display:block;font-size:13px}
      .g-restaurant-chip small{font-family:var(--f-mono);font-size:11.5px;color:var(--muted)}
      .g-restaurant-chip[aria-pressed="true"]{border-color:var(--gold);background:color-mix(in srgb,var(--gold) 14%,var(--panel-2))}
      .g-restaurant-chip[aria-pressed="true"] small{color:var(--gold)}
      .g-restaurant-chip:disabled{opacity:.4;cursor:not-allowed}
      .g-restaurant-meter{height:8px;border-radius:4px;background:var(--panel-2);overflow:hidden}
      .g-restaurant-meter i{display:block;height:100%;background:var(--gold)}
      .g-restaurant-hist{display:flex;align-items:flex-end;gap:2px;height:54px}
      .g-restaurant-hist i{flex:1;background:color-mix(in srgb,var(--ally) 60%,var(--panel-2));border-radius:2px 2px 0 0;min-height:2px}
      .g-restaurant-axis{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);font-family:var(--f-mono)}
      .g-restaurant-kv{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:13px}
      .g-restaurant-kv span{color:var(--muted)} .g-restaurant-kv b{font-family:var(--f-mono);font-weight:600;text-align:right}
      .g-restaurant-day{display:flex;align-items:flex-end;gap:1px;height:90px;border-bottom:1px solid var(--line)}
      .g-restaurant-day i{flex:1;background:var(--gold);opacity:.85;min-height:1px}
      .g-restaurant-day i.q{background:var(--bad)}
      .g-restaurant-live{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px}
      .g-restaurant-live div{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:6px 10px}
      .g-restaurant-live span{display:block;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600}
      .g-restaurant-live b{font-family:var(--f-mono);font-size:18px}
      .g-restaurant-pop{font-size:12px;color:var(--muted);min-height:32px}
      .g-restaurant-sec{padding:8px 10px;gap:8px}
      .g-restaurant-kit{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px}
      .g-restaurant-kit .g-restaurant-chip{padding:4px 6px;min-height:40px;overflow:hidden}
      .g-restaurant-kit b{font-size:12.5px}
      .g-restaurant-kit small{font-size:10.5px;overflow-wrap:anywhere}
      .g-restaurant-grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 10px}
      @container (min-width:560px){.g-restaurant-grid2{grid-template-columns:repeat(3,minmax(0,1fr))}}
      .g-restaurant-st{display:grid;gap:2px}
      .g-restaurant-stl{display:flex;gap:6px;align-items:baseline;font-size:13px;white-space:nowrap;overflow:hidden}
      .g-restaurant-stl span{font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis}
      .g-restaurant-st .g-restaurant-step{gap:2px}
      .g-restaurant-st .g-restaurant-step button{width:38px;height:38px;flex:none}
      .g-restaurant-st .g-restaurant-step b{flex:1;min-width:0;font-size:15px}
      .g-restaurant-dishes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px}
      @container (min-width:560px){.g-restaurant-dishes{grid-template-columns:repeat(3,minmax(0,1fr))}}
      .g-restaurant-dish{display:grid;grid-template-columns:auto minmax(0,1fr);grid-template-rows:auto auto;column-gap:6px;align-items:center;text-align:left;min-height:40px;padding:3px 7px;background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);line-height:1.15}
      .g-restaurant-dish i{grid-row:1/3;width:14px;height:14px;border-radius:4px;border:2px solid var(--muted)}
      .g-restaurant-dish b{font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .g-restaurant-dish small{font-family:var(--f-mono);font-size:10.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .g-restaurant-dish[aria-pressed="true"]{border-color:var(--gold);background:color-mix(in srgb,var(--gold) 14%,var(--panel-2))}
      .g-restaurant-dish[aria-pressed="true"] i{background:var(--gold);border-color:var(--gold)}
      .g-restaurant-dish[aria-pressed="true"] small{color:var(--gold)}
      .g-restaurant-dish:disabled{opacity:.4;cursor:not-allowed}
      .g-restaurant-fc summary{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
      .g-restaurant-fcs{font-size:12.5px;color:var(--fg);font-weight:500}
      .g-restaurant .g-restaurant-hud{gap:6px}
      .g-restaurant .g-restaurant-stat{padding:4px 8px}
      .g-restaurant .g-restaurant-stat b{font-size:16px}
      .g-restaurant-kv{gap:1px 10px}
    `);
    const day = restDay(ctx.seed), cfg = restConfig(ctx.mode);
    let plan = restDefaultPlan(), phase = "plan", lastDish = null;
    const budget = cfg.budget;
    const typeTop = (d) => CT_ORDER.slice().sort((a, b) => DISHES[d].pop[b] - DISHES[d].pop[a]).slice(0, 2).map((k) => CTYPES[k].name).join(", ");
    const hours = new Array(12).fill(0);
    for (const p of day.parties) hours[Math.min(11, Math.floor(p.t / 60))]++;
    const hmax = Math.max(...hours);
    const stepper = (key, label, note) => `<div class="${P}-st"><div class="${P}-stl"><b>${label}</b><span>${note}</span></div>
      <div class="${P}-step"><button data-dec="${key}" data-test="${key}-dec" aria-label="Less ${label}">−</button><b data-test="${key}"></b><button data-inc="${key}" data-test="${key}-inc" aria-label="More ${label}">+</button></div></div>`;
    const topMix = day.mix.slice().sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => `${CTYPES[k].name} ${v}%`).join(" · ");
    ctx.root.innerHTML = `<div class="${P}">
      <div class="${P}-hud">${stat(P, "Budget left", "budget")}${stat(P, "Proj. profit", "profit")}${stat(P, "Proj. reviews", "stars")}${stat(P, "Proj. score", "score", true)}</div>
      <div data-test="result"></div>
      <div class="${P}-main" data-test="planner">
        <div class="${P}-col">
          <details class="${P}-fc" data-test="forecast"><summary><span class="dg-eyebrow">Forecast</span> <span class="${P}-fcs">${topMix} · peaks 12:00 and 19:00</span></summary>
            <table class="dg-table"><thead><tr><th>Guests</th><th class="num">Share</th><th class="num">Spend</th><th class="num">Party</th></tr></thead><tbody>
            ${day.mix.map(([k, v]) => `<tr><td>${CTYPES[k].name}<br><span class="dg-note">${CTYPES[k].sens >= 1 ? "price-sensitive" : CTYPES[k].sens <= 0.5 ? "pays for quality" : "average"} · waits ${Math.round((CTYPES[k].patience[0] + CTYPES[k].patience[1]) / 2)}′</span></td><td class="num">${v}%</td><td class="num">$${CTYPES[k].budget}</td><td class="num">${CTYPES[k].size[0]}–${CTYPES[k].size[1]}</td></tr>`).join("")}
            </tbody></table>
            <div class="dg-eyebrow">Arrivals by hour</div>
            <div class="${P}-hist">${hours.map((h) => `<i style="height:${Math.round((h / hmax) * 100)}%" title="${h} groups"></i>`).join("")}</div>
            <div class="${P}-axis"><span>11:00</span><span>17:00</span><span>23:00</span></div>
          </details>
          <div class="${P}-sec"><div class="dg-eyebrow">Kitchen · seats · staff</div><div class="${P}-kit">${KITCHEN.map((k, i) => `<button class="${P}-chip" data-kitchen="${i}" data-test="kitchen-${i}"><b>${k.name}</b><small>$${U.fmt(k.cost)}</small><small>×${k.speed} · ${k.maxChefs} chefs</small></button>`).join("")}</div>
            <div class="${P}-grid2">
              ${stepper("tables", "Tables", "4 seats · $" + RCOST.table)}
              ${stepper("chefs", "Chefs", "$" + RCOST.chef + " each")}
              ${stepper("waiters", "Waiters", "$" + RCOST.waiter + " each")}
              ${stepper("price", "Prices", "× menu price")}
              ${stepper("marketing", "Marketing", "draws guests")}
            </div>
          </div>
          <div class="${P}-sec"><div class="dg-eyebrow">Menu · 3–5 dishes · $${RCOST.dish} setup each</div>
            <div class="${P}-dishes" data-test="menu">${DISH_ORDER.map((d) => `<button class="${P}-dish" data-dish="${d}" data-test="dish-${d}"><i></i><b>${DISHES[d].name}</b><small data-price="${d}"></small></button>`).join("")}</div>
            <div class="${P}-pop" data-test="dishinfo">Tap a dish to add or remove it and see who likes it.</div>
          </div>
          <div class="${P}-bar"><span class="${P}-msg" data-test="msg"></span><button class="dg-btn primary" data-test="open">Open for the day</button></div>
        </div>
        <div class="${P}-col">
          <div class="${P}-sec"><div class="dg-eyebrow">Projection</div><div class="${P}-kv" data-test="proj"></div></div>
          <details><summary>Rules</summary><ul class="${P}-rules">${REST_RULES(ctx.mode).map((r) => `<li>${r}</li>`).join("")}</ul></details>
        </div>
      </div></div>`;
    const $ = (t) => ctx.root.querySelector(`[data-test="${t}"]`);
    const say = makeSay($("msg"), P);
    const LIM = { tables: [2, 24, 1], chefs: [1, 6, 1], waiters: [1, 6, 1], price: [0.7, 1.6, 0.05], marketing: [0, 3000, 250] };
    function tryPlan(q) {
      const why = restValid(q, budget);
      if (why && why !== "Pick at least 3 dishes") return why;
      plan = q; refresh(); return "";
    }
    function bump(key, dir) {
      if (phase !== "plan") return;
      const [lo, hi, st] = LIM[key];
      const q = JSON.parse(JSON.stringify(plan));
      q[key] = Math.round(clamp(q[key] + dir * st, lo, hi) * 100) / 100;
      if (key === "chefs" && q.chefs > KITCHEN[q.kitchen].maxChefs) { say(`${KITCHEN[q.kitchen].name} kitchen fits ${KITCHEN[q.kitchen].maxChefs} chefs. Upgrade the kitchen.`, "bad"); return; }
      const why = tryPlan(q);
      say(why ? why + "." : "", why ? "bad" : "");
    }
    let lastProj = null;
    function refresh() {
      const spend = restSpend(plan), left = budget - spend;
      $("budget").textContent = money(left);
      ctx.root.querySelectorAll("[data-kitchen]").forEach((b) => {
        const i = +b.dataset.kitchen;
        b.setAttribute("aria-pressed", String(plan.kitchen === i));
        const q = Object.assign({}, plan, { kitchen: i, chefs: Math.min(plan.chefs, KITCHEN[i].maxChefs) });
        b.disabled = phase !== "plan" || restSpend(q) > budget;
      });
      for (const k of Object.keys(LIM)) {
        $(k).textContent = k === "price" ? "×" + plan.price.toFixed(2) : k === "marketing" ? "$" + U.fmt(plan.marketing) : String(plan[k]);
        const [lo, hi, st] = LIM[k];
        const up = Object.assign({}, plan, { [k]: plan[k] + st });
        $(k + "-dec").disabled = phase !== "plan" || plan[k] <= lo + 1e-9;
        $(k + "-inc").disabled = phase !== "plan" || plan[k] >= hi - 1e-9 || restSpend(up) > budget || (k === "chefs" && plan.chefs >= KITCHEN[plan.kitchen].maxChefs);
      }
      ctx.root.querySelectorAll("[data-dish]").forEach((b) => {
        const d = b.dataset.dish, on = plan.menu.includes(d);
        b.setAttribute("aria-pressed", String(on));
        b.disabled = phase !== "plan" || (!on && (plan.menu.length >= 5 || left < RCOST.dish));
        ctx.root.querySelector(`[data-price="${d}"]`).textContent = `$${(DISHES[d].price * plan.price).toFixed(0)} · ${DISHES[d].prep}′ · cost $${DISHES[d].cost}`;
      });
      const valid = !restValid(plan, budget);
      $("open").disabled = phase !== "plan" || !valid;
      const r = restSim(day, plan);
      const kv = [
        ["Visit / served", `${r.visitors} / ${r.served} groups`],
        ["Left: wait / menu", `${r.lostWait} / ${r.lostMenu}`],
        ["Revenue", money(r.revenue)], ["Costs", money(r.cogs + r.wages + r.depreciation + r.menuCost + r.marketing)],
        ["Profit", money(r.profit)], ["Reviews", r.stars.toFixed(1) + " / 5 → " + (r.repBonus >= 0 ? "+" : "") + U.fmt(r.repBonus)],
      ];
      $("proj").innerHTML = valid ? kv.map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join("") + `<span>Score</span><b class="dg-gold">${U.fmt(r.score)}</b>` : `<span>${restValid(plan, budget)}</span><b></b>`;
      $("profit").textContent = valid ? money(r.profit) : "–";
      $("stars").textContent = valid ? r.stars.toFixed(1) + "/5" : "–";
      $("score").textContent = valid ? U.fmt(r.score) : "–";
      if (valid && lastProj !== r.score) { lastProj = r.score; ctx.progress(r.score); }
      if (lastDish) {
        const D = DISHES[lastDish];
        $("dishinfo").innerHTML = `<b style="color:var(--fg)">${D.name}</b>: sells for $${(D.price * plan.price).toFixed(0)}, ingredients $${D.cost}, ${D.prep} min to cook. Popular with ${typeTop(lastDish)}.`;
      }
    }
    ctx.root.querySelectorAll("[data-kitchen]").forEach((b) => b.addEventListener("click", () => {
      if (phase !== "plan") return;
      const i = +b.dataset.kitchen;
      const q = Object.assign({}, plan, { kitchen: i, chefs: Math.min(plan.chefs, KITCHEN[i].maxChefs) });
      const why = tryPlan(q); say(why ? why + "." : `${KITCHEN[i].name} kitchen selected.`, why ? "bad" : "");
    }));
    ctx.root.querySelectorAll("[data-dec]").forEach((b) => b.addEventListener("click", () => bump(b.dataset.dec, -1)));
    ctx.root.querySelectorAll("[data-inc]").forEach((b) => b.addEventListener("click", () => bump(b.dataset.inc, 1)));
    ctx.root.querySelectorAll("[data-dish]").forEach((b) => b.addEventListener("click", () => {
      if (phase !== "plan") return;
      const d = b.dataset.dish;
      lastDish = d;
      const q = JSON.parse(JSON.stringify(plan));
      if (q.menu.includes(d)) q.menu = q.menu.filter((x) => x !== d); else q.menu.push(d);
      const why = tryPlan(q);
      say(why ? why + "." : q.menu.length < 3 ? "Pick at least 3 dishes." : "", why || q.menu.length < 3 ? "bad" : "");
    }));
    $("open").addEventListener("click", () => openDay());
    const t0 = ctx.now();
    ctx.interval(() => {
      if (phase !== "plan") return;
      const left = cfg.planMs - (ctx.now() - t0);
      ctx.setStatus("Plan · " + mmss(left));
      if (left <= 0) { plan = restFix(plan); openDay(); }
    }, 250);

    function openDay(instant) {
      if (phase !== "plan") return;
      if (restValid(plan, budget)) { say(restValid(plan, budget) + ".", "bad"); return; }
      phase = "sim";
      refresh();
      const r = restSim(day, plan, true);
      ctx.setStatus("Service");
      $("planner").style.display = "none";
      const cap = plan.tables * 4, tr = r.trace;
      const qmax = Math.max(1, ...tr.map((x) => x.queue));
      $("result").innerHTML = `<div class="${P}-res" data-test="day">
        <div class="${P}-bar"><div class="dg-eyebrow">Service · ${plan.tables} tables, ${plan.chefs} chefs, ${plan.waiters} waiters</div><b class="dg-mono" data-test="clock">11:00</b></div>
        <div class="${P}-live"><div><span>Seated</span><b data-l="seated">0</b></div><div><span>Queue</span><b data-l="queue">0</b></div><div><span>Served</span><b data-l="served">0</b></div><div><span>Left unhappy</span><b data-l="left">0</b></div></div>
        <div class="${P}-day" data-test="daychart">${tr.map(() => "<i></i>").join("")}</div>
        <div class="${P}-axis"><span>11:00</span><span>17:00</span><span>23:00</span></div>
        <div data-test="pnl"></div></div>`;
      const bars = [...ctx.root.querySelectorAll(`.${P}-day i`)];
      const paint = (t) => {
        const k = Math.min(tr.length - 1, Math.floor(t * (tr.length - 1)));
        const x = tr[k];
        $("clock").textContent = hhmm(x.m);
        for (const key of ["seated", "queue", "served", "left"]) ctx.root.querySelector(`[data-l="${key}"]`).textContent = x[key];
        bars.forEach((b, j) => {
          if (j > k) { b.style.height = "0"; return; }
          const y = tr[j];
          b.style.height = Math.round(Math.min(1, y.seated / cap) * 100) + "%";
          b.className = y.queue > 0 && y.queue >= qmax * 0.5 ? "q" : "";
        });
      };
      const done = () => {
        paint(1);
        const rows = [
          ["Revenue (food, drinks, tips)", r.revenue], ["Ingredients", -r.cogs], ["Wages", -r.wages],
          [`Kitchen and tables (${Math.round(DEPR * 100)}% of $${U.fmt(KITCHEN[plan.kitchen].cost + plan.tables * RCOST.table)})`, -r.depreciation],
          ["Menu setup", -r.menuCost], ["Marketing", -r.marketing],
        ];
        const pnl = `<table class="dg-table"><tbody>${rows.map(([a, v]) => `<tr><td>${a}</td><td class="num ${v < 0 ? "dg-bad" : ""}">${money(v)}</td></tr>`).join("")}
          <tr class="tot"><td>Profit</td><td class="num ${r.profit < 0 ? "dg-bad" : "dg-good"}">${money(r.profit)}</td></tr>
          <tr><td>Reputation (${r.stars.toFixed(1)} / 5 from ${r.served + r.unhappy} reviews)</td><td class="num">${r.repBonus >= 0 ? "+" : ""}${U.fmt(r.repBonus)}</td></tr>
          <tr><td>Base</td><td class="num">5,000</td></tr>
          <tr class="tot"><td>Score</td><td class="num dg-gold">${U.fmt(r.score)}</td></tr></tbody></table>`;
        $("pnl").innerHTML = `<div class="${P}-big" data-test="final">${U.fmt(r.score)}<small>points · ${r.served} groups served · ${r.unhappy} left unhappy · ${r.walked} never came</small></div>${pnl}`;
        ctx.setStatus("Final · " + U.fmt(r.score));
        ctx.progress(r.score);
        ctx.timeout(() => ctx.end({ score: r.score, detail: `<p class="dg-note">Profit ${money(r.profit)}, reviews ${r.stars.toFixed(1)}/5, ${r.served} groups served.</p>` }), 700);
      };
      if (ctx.reducedMotion || instant) { done(); return; }
      const s0 = ctx.now();
      const step = (now) => { const t = Math.min(1, (now - s0) / cfg.simMs); if (t >= 1) { done(); return; } paint(t); ctx.raf(step); };
      paint(0); ctx.raf(step);
    }
    refresh();
    say(`$${U.fmt(budget)} to set up. The projection updates as you plan.`, "");
    ctx.setStatus("Plan · " + mmss(cfg.planMs));
    ctx.test = {
      state: () => ({ phase, plan: JSON.parse(JSON.stringify(plan)), proj: restSim(day, plan), spend: restSpend(plan) }),
      setPlan(obj) { if (phase !== "plan") return "not planning"; const q = Object.assign(JSON.parse(JSON.stringify(plan)), JSON.parse(JSON.stringify(obj))); const why = restValid(q, budget); if (why) return why; plan = q; refresh(); return ""; },
      optimise(skill) { const r = restOptimise(day, U.rng("ui-rest:" + ctx.seed + ":" + skill), skill, 400); plan = r.plan; refresh(); return r.score; },
      finish: (instant) => openDay(instant !== false),
    };
  }
  function REST_RULES(mode) {
    const c = restConfig(mode);
    return [
      `Everyone gets the same $10,000 and the same seeded day of 100 groups (${c.planMs / 1000} s to plan).`,
      `Groups come if your menu, prices and marketing appeal to them, then leave if they wait longer than their patience.`,
      `Tables seat 4. Chefs cook one order at a time; bigger kitchens cook faster and fit more chefs. Waiters take orders, serve and bill.`,
      `Profit = revenue − ingredients − wages − menu setup − marketing − 35% of kitchen and table cost.`,
      `Score = 5,000 + profit + reputation bonus (±900 per review star above or below 3). Never below 0.`,
    ];
  }

  /* ====================================================================================
     Registration
     ==================================================================================== */
  DG.registerGame({
    id: "base", name: "Base Duel", category: "battle", kind: "race", formats: FORMATS.slice(),
    skill: 9, luck: 1, cashEligible: true, duration: "3 min (mix 45 s)", pack: "builder",
    blurb: "Build a base on a fixed budget, then hold it against the same zombie waves as your rival.",
    rules: [
      "Build phase: spend a fixed gold budget on walls, towers and spike traps. Sell for a full refund.",
      "Zombies take the shortest path to your core; towers and walls reroute them, but you can never seal it.",
      "Identical seeded waves: Walkers, fast Runners, armoured wall-smashing Brutes and tower-spitting Spitters.",
      "During waves, throw Firebombs and repair. Between waves, spend gold from kills.",
      "Score = 1,000 per wave survived + 5 × base HP + 10 per kill + unspent gold ÷ 10.",
    ],
    scoreLabel: "points", formatScore: (n) => U.fmt(n),
    play: basePlay,
    bot: (seed, skill, rng, mode) => baseBot(seed, skill, rng, mode === "mix" ? "mix" : "full"),
    _lab: BASE_LAB,
  });
  DG.registerGame({
    id: "city", name: "City Duel", category: "builder", kind: "race", formats: FORMATS.slice(),
    skill: 9, luck: 0, cashEligible: true, duration: "95 s (mix 40 s)", pack: "builder",
    blurb: "Same plot, same budget: zone homes, jobs, power and services into the happiest, richest city.",
    rules: [
      "Everyone builds on the same seeded plot with the same budget. Bulldozing refunds in full.",
      "Homes need jobs, energy and water; parks, schools, hospitals, police and shops nearby make them happy.",
      "Factories and power plants pollute nearby homes; transit cuts traffic; police cut crime.",
      "Watch the live projection: every placement changes the score.",
      "City score = people (population × happiness) + money (daily revenue) + growth.",
    ],
    scoreLabel: "city pts", formatScore: (n) => (Math.round(n * 10) / 10).toFixed(1),
    play: cityPlay,
    bot: (seed, skill, rng, mode) => cityBot(seed, skill, rng, mode === "mix" ? "mix" : "full"),
    _lab: CITY_LAB,
  });
  DG.registerGame({
    id: "restaurant", name: "Restaurant Duel", category: "builder", kind: "race", formats: FORMATS.slice(),
    skill: 8, luck: 1, cashEligible: true, duration: "65 s (mix 35 s)", pack: "builder",
    blurb: "Same $10,000, same 100 customers: set up the kitchen, staff, menu and prices for the best day.",
    rules: [
      "You and your rival get the same budget and the same seeded day of 100 customer groups.",
      "Choose kitchen, tables, chefs, waiters, a 3–5 dish menu, a price level and marketing.",
      "Read the forecast: each customer type likes different dishes, pays differently and waits differently.",
      "Then the day plays out: slow service and bad menus send people away unhappy.",
      "Score = 5,000 + profit + reputation bonus.",
    ],
    scoreLabel: "points", formatScore: (n) => U.fmt(n),
    play: restaurantPlay,
    bot: (seed, skill, rng, mode) => restBot(seed, skill, rng, mode === "mix" ? "mix" : "full"),
    _lab: REST_LAB,
  });
})();
