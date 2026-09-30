/* Reference implementations of the game contract. NOT shipped in the build — used by the
   platform's tests and as a template for game packs. */
(function () {
  const { util: U } = DG;

  /* ---- RACE example: Tap Sprint ---- */
  DG.css("sample-tap", `
    .g-tap{display:grid;gap:12px}
    .g-tap-btn{min-height:160px;border-radius:var(--r-lg);border:0;background:var(--gold);color:var(--on-gold);
      font-family:var(--f-display);font-size:48px;font-weight:900;text-transform:uppercase}`);
  DG.registerGame({
    id: "sample-tap", name: "Tap Sprint", category: "reflex", kind: "race",
    formats: ["1v1", "2v2", "ffa", "tournament", "mix"],
    skill: 6, luck: 1, cashEligible: true, duration: "10 s", pack: "samples",
    blurb: "Tap as many times as you can.", rules: ["Tap the button as fast as you can.", "One point per tap."],
    scoreLabel: "taps",
    play(ctx) {
      const DUR = ctx.mode === "mix" ? 5000 : 10000;
      let taps = 0;
      ctx.root.innerHTML = `<div class="g-tap"><button class="g-tap-btn" data-test="tap">Tap</button><p class="dg-note dg-center">Score: <b class="dg-mono" data-test="score">0</b></p></div>`;
      const btn = ctx.root.querySelector("[data-test=tap]");
      btn.addEventListener("pointerdown", (e) => { e.preventDefault(); if (ctx.signal.ended) return; taps++; ctx.root.querySelector("[data-test=score]").textContent = taps; ctx.progress(taps); });
      ctx.interval(() => {
        const left = Math.max(0, DUR - ctx.now());
        ctx.setStatus((left / 1000).toFixed(1) + "s");
        if (left <= 0) ctx.end({ score: taps, detail: `<p class="dg-note">${taps} taps.</p>` });
      }, 100);
    },
    bot(seed, skill, rng, mode) {
      const secs = mode === "mix" ? 5 : 10;
      const rate = 3 + skill * 6 + U.gauss(rng) * 0.6;
      const score = Math.max(0, Math.round(rate * secs));
      const timeline = [];
      for (let t = 1; t <= secs; t++) timeline.push([t, Math.round(score * t / secs)]);
      return { score, timeline };
    },
  });

  /* ---- VERSUS example: Nim (take 1-3, last stone wins) ---- */
  DG.registerGame({
    id: "sample-nim", name: "Nim", category: "strategy", kind: "versus",
    formats: ["1v1", "tournament"], skill: 9, luck: 0, cashEligible: true, duration: "1 min", pack: "samples",
    blurb: "Take 1–3 stones. Whoever takes the last stone wins.", rules: ["Players alternate taking 1, 2 or 3 stones.", "Taking the last stone wins."],
    play(ctx) {
      const opp = ctx.opponents[0];
      let stones = 15 + Math.floor(ctx.rng() * 6), myTurn = true;
      const render = () => {
        ctx.setStatus(stones + " left");
        ctx.root.innerHTML = `<div class="dg-stack dg-center"><div class="dg-h" style="font-size:64px" data-test="stones">${stones}</div>
          <div class="dg-row" style="justify-content:center">${[1, 2, 3].map((n) => `<button class="dg-btn primary" data-take="${n}" ${!myTurn || n > stones ? "disabled" : ""}>Take ${n}</button>`).join("")}</div>
          <p class="dg-note">${myTurn ? "Your move" : U.esc(opp.name) + " is thinking…"}</p></div>`;
        ctx.root.querySelectorAll("[data-take]").forEach((b) => b.onclick = () => take(+b.dataset.take, true));
      };
      const take = (n, mine) => {
        stones -= n;
        if (stones <= 0) return ctx.end({ outcome: mine ? "win" : "loss", myScore: mine ? 1 : 0, oppScore: mine ? 0 : 1 });
        myTurn = !mine; render();
        if (!myTurn) ctx.timeout(() => {
          const best = stones % 4 || 1;
          const n2 = ctx.rng() < opp.skill ? best : 1 + Math.floor(ctx.rng() * Math.min(3, stones));
          take(Math.min(n2, stones), false);
        }, 600);
      };
      render();
    },
  });
})();
