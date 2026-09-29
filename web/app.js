/* =========================================================================
   FHE-RAG · web explainer — animation engine (backed by the REAL pipeline)
   Every value shown comes from /api/run and /api/space (web/app.py), which
   run the real embeddings, real CKKS encryption, real homomorphic dot
   products on the real server, and real decryption. No mock data.
   ========================================================================= */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);

  const svg = (id, size, filled) =>
    `<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${filled ? "currentColor" : "none"}" stroke="${filled ? "none" : "currentColor"}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><use href="#${id}"/></svg>`;

  // ---- formatters ----
  const fmtNum = (x) => (x < 0 ? "−" : "") + Math.abs(x).toFixed(2);
  const vecStr = (arr) => arr.slice(0, 3).map(fmtNum).join("  ") + "  …";
  const hexStr = (hex) => (hex.match(/.{1,4}/g) || [hex]).slice(0, 3).join(" ") + " ▮▮ …";
  const fmtBytes = (n) => (n < 1024 ? `${n} B` : `${Math.round(n / 1024)} KB`);
  const short = (t, n = 30) => (t.length > n ? t.slice(0, n) + "…" : t);

  // Una única lista de preguntas, compartida por la demo y la viz de vectores,
  // para que "la misma pregunta" dé exactamente el mismo resultado en las dos.
  const QUERIES = [
    "¿Qué me permite hacer el FHE?",
    "¿Para qué sirve el esquema CKKS?",
    "¿Qué es el bootstrapping en FHE?",
    "¿Se puede recuperar el texto original de un embedding?",
    "presión arterial del paciente",
    "crecimiento de los ingresos interanual",
  ];

  // =========================================================================
  // MAIN ANIMATION
  // =========================================================================
  const stage = $("stage"), packet = $("packet"), tiles = $("tiles"),
        dbrows = $("dbrows"), eye = $("eye"), seePanel = $("seePanel"), results = $("results");
  const AT_CLIENT = "18%", AT_SERVER = "60%";

  let DATA = null;            // from /api/run
  let SCRIPTS = { plain: [], fhe: [] };
  let mode = "fhe", step = 0, playing = false, timer = null;

  const see = (tone, head, body) => ({ tone, head, body });
  const base = { tiles: false, encrypt: false, packet: null, db: [], results: null,
                 eye: "blind", see: see("neutral", "Lo que el servidor puede leer", "— aún nada —"), narr: "" };
  const St = (o) => Object.assign({}, base, o);

  function buildScripts(D) {
    const top3 = D.ranking.slice(0, 3);           // los 3 más relevantes (winner = idx 0)
    const winner = short(D.ranking[0].text, 34);
    const sizeNote = `texto ${fmtBytes(D.plain_bytes)} → ciphertext ${fmtBytes(D.query_cipher_bytes)} (~${D.expansion}× más grande)`;
    const qHex = hexStr(D.query_cipher_hex), qVec = vecStr(D.query_vector_preview);

    const rows = (m, n, opts = {}) => top3.slice(0, n).map((d, i) => {
      const r = { mode: m, text: m === "plain" ? vecStr(d.vector_preview) : hexStr(d.cipher_hex), hit: !!opts.hit && i === 0 };
      if (opts.scored) r.score = m === "plain" ? d.score.toFixed(2) : "cipher";
      return r;
    });

    const PLAIN = [
      St({ narr: "En tu <b>máquina (cliente)</b> tienes un documento en claro." }),
      St({ tiles: true, narr: "Lo conviertes en un <b>embedding real</b>: 384 números que capturan su significado." }),
      St({ packet: { face: "plain", txt: qVec }, tiles: true, eye: "sees",
        see: see("red", "El servidor recibe el vector EN CLARO", `${qVec} · reconstruible al texto con embedding inversion`),
        narr: "Sin cifrar, el embedding <b>viaja tal cual</b> hasta el servidor." }),
      St({ db: rows("plain", 1), eye: "sees",
        see: see("red", "El servidor lo guarda legible", `Fila 1: ${vecStr(top3[0].vector_preview)}`),
        narr: "El <b>servidor</b> lo guarda <b>tal cual</b> en su base de datos (KB)." }),
      St({ db: rows("plain", 3), eye: "sees",
        see: see("red", "La KB es una copia legible de tus datos", "Los 13 vectores en claro quedan en el servidor"),
        narr: "Repite con los 13 documentos: la KB del servidor es una <b>copia legible</b> de tus datos." }),
      St({ db: rows("plain", 3), packet: { face: "plain", txt: qVec }, eye: "sees",
        see: see("red", "También ve tu consulta", `Consulta en claro: ${qVec}`),
        narr: "Tu <b>consulta</b> se convierte en vector y también viaja <b>sin cifrar</b>." }),
      St({ db: rows("plain", 3, { hit: true, scored: true }), eye: "sees",
        see: see("red", "El servidor lo ve TODO", `Consulta + vectores + scores + ganador («${winner}»)`),
        narr: "Calcula la similitud sobre <b>números en claro</b>: ve un score por documento y el ranking." }),
      St({ db: rows("plain", 3, { hit: true, scored: true }), packet: { face: "plain", txt: "ranking" }, eye: "sees",
        see: see("red", "Ya conoce el ranking y el ganador", "Te devuelve el resultado que él mismo ordenó"),
        narr: "Te devuelve el ranking — que el servidor <b>ya calculó y vio</b>." }),
      St({ db: rows("plain", 3, { hit: true, scored: true }), packet: { face: "plain", txt: "ranking", at: "client" },
        results: { locked: false }, eye: "sees",
        see: see("red", "El ranking llega a tu máquina", "…pero el servidor lo vio todo por el camino"),
        narr: "El ranking llega a tu máquina." }),
      St({ db: rows("plain", 3, { hit: true, scored: true }), results: { locked: false, chosen: true }, eye: "sees",
        see: see("red", "Confidencialidad: rota", "El servidor vio documentos, consulta, scores y resultado."),
        narr: `Eliges «${winner}» — pero el servidor ha <b>visto todo</b>.` }),
    ];

    const FHE = [
      St({ narr: "En tu <b>máquina (cliente)</b> tienes un documento en claro. La clave secreta vive aquí." }),
      St({ tiles: true, narr: "Lo conviertes en un <b>embedding real</b>: los mismos 384 números." }),
      St({ tiles: true, encrypt: true, see: see("green", "Aún nada", "El cifrado ocurre en el cliente, antes de salir."),
        narr: "Lo <b>ciframos con tu clave secreta</b> (CKKS). Los números pasan a ser <b>ciphertext</b> ilegible." }),
      St({ packet: { face: "cipher", txt: qHex }, eye: "blind",
        see: see("green", "El servidor recibe bytes ilegibles", `${qHex} · ${sizeNote}`),
        narr: "Solo el <b>ciphertext</b> viaja por la red." }),
      St({ db: rows("cipher", 1), eye: "blind",
        see: see("green", "Guarda ciphertext, no puede leerlo", `Fila 1: ${hexStr(top3[0].cipher_hex)}`),
        narr: "El <b>servidor</b> guarda ciphertext en su KB. Nunca ve el texto ni el vector." }),
      St({ db: rows("cipher", 3), eye: "blind",
        see: see("green", "La KB es solo ruido cifrado", "13 ciphertexts almacenados · ilegibles sin la clave"),
        narr: "Con los 13 documentos, la KB del servidor es <b>solo ruido cifrado</b>." }),
      St({ db: rows("cipher", 3), packet: { face: "cipher", txt: qHex }, eye: "blind",
        see: see("green", "La consulta también llega cifrada", `Consulta: ${qHex}`),
        narr: "La <b>consulta</b> se cifra en el cliente antes de enviarse." }),
      St({ db: rows("cipher", 3, { scored: true }), eye: "blind",
        see: see("green", "Opera a ciegas", "Multiplica ciphertexts → scores CIFRADOS · no sabe cuál es mayor"),
        narr: "El servidor hace el <b>producto punto homomórfico</b>: opera sobre cifrado y obtiene <b>scores cifrados</b>." }),
      St({ db: rows("cipher", 3, { scored: true }), packet: { face: "cipher", txt: "scores ▮▮" }, eye: "blind",
        see: see("green", "Devuelve scores cifrados", "El ranking sigue oculto para el servidor"),
        narr: "El servidor te devuelve los scores — <b>todavía cifrados</b>." }),
      St({ db: rows("cipher", 3, { scored: true }), packet: { face: "cipher", txt: "scores ▮▮", at: "client" },
        results: { locked: true }, eye: "blind",
        see: see("green", "Llegan cifrados a tu máquina", "El servidor no supo el ranking"),
        narr: "Llegan a tu máquina, <b>aún cifrados</b>." }),
      St({ db: rows("cipher", 3, { scored: true }), results: { locked: false, decrypting: true }, eye: "blind",
        see: see("green", "Solo tú ves el ranking", `Descifras con tu clave: scores reales y ranking`),
        narr: "Los <b>descifras con tu clave</b>: este es el ranking real." }),
      St({ db: rows("cipher", 3, { scored: true }), results: { locked: false, chosen: true }, eye: "blind",
        see: see("green", "El servidor no vio nada", `Solo tú sabes que gana «${winner}».`),
        narr: `Eliges «${winner}». El servidor <b>nunca supo</b> cuál ganó.` }),
    ];
    return { plain: PLAIN, fhe: FHE };
  }

  const steps = () => SCRIPTS[mode] || [];

  function renderResults(r) {
    if (!r || !DATA) { results.style.opacity = "0"; results.innerHTML = ""; return; }
    results.style.opacity = "1";
    results.className = "node results" + (r.locked ? " locked" : "") + (r.decrypting ? " dec" : "");
    const head = r.locked
      ? `${svg("i-lock", 14)} Respuesta cifrada — aún ilegible`
      : (mode === "plain"
          ? `${svg("i-check", 14)} Ranking recibido del servidor`
          : `${svg("i-check", 14)} Ranking descifrado en tu máquina`);
    const top = DATA.ranking.slice(0, 4);
    const rowsHtml = r.locked
      ? top.map((d) => `<div class="rank-row"><span class="pos">·</span><span class="lab">${short(d.text)}</span><span class="sc"><span class="lk">${svg("i-lock", 11)}</span> ▮▮</span></div>`).join("")
      : top.map((d, i) => `<div class="rank-row${i === 0 ? " win" : ""}"><span class="pos">${i + 1}</span><span class="lab">${short(d.text)}</span><span class="sc">${d.score.toFixed(4)}</span></div>`).join("");
    const chosen = (!r.locked && r.chosen) ? `<div class="chosen">${svg("i-check", 13)} Elegido: ${short(DATA.ranking[0].text, 30)}</div>` : "";
    results.innerHTML = `<div class="rhead">${head}</div><div class="rank">${rowsHtml}</div>${chosen}`;
    if (r.decrypting) { results.classList.remove("decrypting"); void results.offsetWidth; results.classList.add("decrypting"); }
  }

  function apply(state, animate) {
    if (state.tiles && DATA) {
      tiles.style.opacity = "1";
      tiles.innerHTML = DATA.query_vector_preview.slice(0, 5).map((x) => `<span class="tile">${fmtNum(x)}</span>`).join("") + `<span class="tile">…</span>`;
      if (state.encrypt && animate) { tiles.classList.remove("encrypting"); void tiles.offsetWidth; tiles.classList.add("encrypting"); }
    } else { tiles.style.opacity = "0"; }

    if (state.packet) {
      const face = state.packet.face;
      packet.innerHTML = `<span class="face ${face === "plain" ? "face-plain" : "face-cipher"}" style="display:inline-flex">${svg(face === "plain" ? "i-doc" : "i-lock", 14)} ${state.packet.txt}</span>`;
      packet.style.left = state.packet.at === "client" ? AT_CLIENT : AT_SERVER;
      packet.classList.remove("hidden");
    } else { packet.classList.add("hidden"); }

    dbrows.innerHTML = state.db.map((r) => {
      const lock = r.mode === "cipher" ? `<span class="lk">${svg("i-lock", 11)}</span>` : "";
      const score = r.score ? `<span class="rscore">${r.score === "cipher" ? svg("i-lock", 11) + " ▮▮" : r.score + (r.hit ? " ★" : "")}</span>` : "";
      return `<div class="dbrow ${r.mode}${r.hit ? " hit" : ""}"><span class="rtxt">${lock}${r.text}</span>${score}</div>`;
    }).join("");

    renderResults(state.results);

    eye.className = "eye " + state.eye;
    eye.innerHTML = svg(state.eye === "sees" ? "i-eye" : "i-eyeoff", 16) + ` <span>El servidor ve: ${state.eye === "sees" ? "TODO" : "nada legible"}</span>`;

    seePanel.dataset.tone = state.see.tone;
    $("seeHead").innerHTML = svg(state.see.tone === "red" ? "i-eye" : "i-eyeoff", 18) + ` <span>${state.see.head}</span>`;
    $("seeBody").textContent = state.see.body;
    $("narrTx").innerHTML = state.narr;

    // the full answer only appears once the animation reaches the final reveal
    if (state.results && state.results.chosen) renderAnswer();
    else $("answer").innerHTML = "";
  }

  function renderDots() {
    $("dots").innerHTML = steps().map((_, i) => `<i class="${i === step ? "on" : ""}"></i>`).join("");
  }

  function renderAnswer() {
    if (!DATA || !DATA.ranking) { $("answer").innerHTML = ""; return; }
    const top = DATA.ranking[0], more = DATA.ranking.slice(1, 3);
    $("answer").innerHTML =
      `<div class="a-head">${svg("i-doc", 16)} Respuesta recuperada para «${DATA.query}»</div>` +
      `<div class="a-top"><span class="a-rank">#1</span><div class="a-text">${top.text}</div><span class="a-sc">${top.score.toFixed(4)}</span></div>` +
      `<details><summary>Ver los siguientes documentos más relevantes</summary><div class="a-more">` +
      more.map((d, i) => `<div class="m-row"><span class="m-pos">#${i + 2}</span><span>${d.text}</span><span class="m-sc">${d.score.toFixed(4)}</span></div>`).join("") +
      `</div></details>`;
  }

  function render(animate) {
    const list = steps();
    const hasData = !!DATA && list.length > 0;
    ["btnPlay", "btnPrev", "btnNext", "btnReplay"].forEach((b) => { $(b).disabled = !hasData; });
    if (!hasData) {
      $("narrTx").innerHTML = DATA ? "…" : "Cargando el pipeline real… (cifrando e indexando los documentos)";
      $("dots").innerHTML = "";
      return;
    }
    step = Math.max(0, Math.min(list.length - 1, step));
    stage.dataset.mode = mode; stage.dataset.step = String(step);
    apply(list[step], animate);
    $("narrNo").textContent = String(step + 1);
    $("btnPrev").disabled = step === 0;
    $("btnNext").disabled = step === list.length - 1;
    renderDots();
  }

  function goTo(i, a) { step = i; render(a); }
  function stop() { playing = false; if (timer) clearTimeout(timer); timer = null; $("playTx").textContent = "Reproducir"; $("btnPlay").querySelector("svg").outerHTML = svg("i-play", 18, true); }
  function tick() { if (!playing) return; if (step >= steps().length - 1) { stop(); return; } goTo(step + 1, true); timer = setTimeout(tick, 2600); }
  function play() { if (playing) { stop(); return; } if (!DATA) return; if (step >= steps().length - 1) goTo(0, false); playing = true; $("playTx").textContent = "Pausa"; $("btnPlay").querySelector("svg").outerHTML = svg("i-pause", 18); timer = setTimeout(tick, 700); }
  function setMode(m) { if (m === mode) return; stop(); mode = m; step = 0; $("modePlain").setAttribute("aria-pressed", String(m === "plain")); $("modeFhe").setAttribute("aria-pressed", String(m === "fhe")); render(false); }

  $("btnPlay").addEventListener("click", play);
  $("btnPrev").addEventListener("click", () => { stop(); goTo(Math.max(0, step - 1), false); });
  $("btnNext").addEventListener("click", () => { stop(); goTo(step + 1, true); });
  $("btnReplay").addEventListener("click", () => { stop(); goTo(0, false); });
  $("modePlain").addEventListener("click", () => setMode("plain"));
  $("modeFhe").addEventListener("click", () => setMode("fhe"));
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === "ArrowRight") { stop(); goTo(step + 1, true); }
    else if (e.key === "ArrowLeft") { stop(); goTo(Math.max(0, step - 1), false); }
    else if (e.key === " " && DATA) { e.preventDefault(); play(); }
  });

  // ---- backend wiring ----
  function setStatus(kind, txt) { $("liveStatus").className = "status " + kind; $("liveTx").textContent = txt; }

  async function loadRun(q) {
    setStatus("loading", "Ejecutando en el backend…");
    $("runBtn").disabled = true;
    try {
      const r = await fetch("/api/run?q=" + encodeURIComponent(q));
      if (r.status === 503) { setStatus("loading", "Preparando el pipeline…"); setTimeout(() => loadRun(q), 1200); return; }
      DATA = await r.json();
      SCRIPTS = buildScripts(DATA);
      stop(); step = 0;
      // deep-link ?mode=&step= (útil para saltar a un punto en la charla)
      const p = new URLSearchParams(location.search);
      if (p.get("mode") === "plain" || p.get("mode") === "fhe") mode = p.get("mode");
      $("modePlain").setAttribute("aria-pressed", String(mode === "plain"));
      $("modeFhe").setAttribute("aria-pressed", String(mode === "fhe"));
      const qs = parseInt(p.get("step"), 10);
      if (!Number.isNaN(qs)) step = qs;
      render(false);
      setStatus("live", `Pipeline real · ${DATA.docs.length} docs · ciphertext ${fmtBytes(DATA.query_cipher_bytes)}`);
    } catch (e) {
      setStatus("err", "Backend no disponible — ejecuta ./run.sh ui");
    } finally { $("runBtn").disabled = false; }
  }

  $("runSelect").innerHTML = QUERIES.map((q, i) => `<option value="${q.replace(/"/g, "&quot;")}"${i === 0 ? " selected" : ""}>${q}</option>`).join("");
  $("runSelect").addEventListener("change", () => loadRun($("runSelect").value));
  $("runBtn").addEventListener("click", () => loadRun($("runSelect").value));

  render(false); // loading placeholder until data arrives

  // =========================================================================
  // VECTOR SEARCH viz — animated, real similarities from /api/space
  // Points come from the real 2D projection, then decluttered so labels don't
  // overlap; the query sits at the similarity-weighted centre of the docs.
  // The animation: docs appear -> your question drops in -> similarity is
  // "measured" (lines + growth) -> the ranking sorts. All sims are real.
  // =========================================================================
  const VW = 440, VH = 300, PAD = 34;
  const CAT = { "Cripto / FHE": "#6E8BFF", "Salud": "#E7B15A", "Negocio": "#B58BFF" };
  let vsSpace = null, vsTimers = [];
  const clearVs = () => { vsTimers.forEach(clearTimeout); vsTimers = []; };

  function vsLayout(S) {
    const pts = S.docs.map((d) => ({ x: d.x, y: d.y * (VH / 320), cat: d.cat, text: d.text }));
    const fit = () => {
      const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
      const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
      pts.forEach((p) => {
        p.x = PAD + (p.x - x0) / ((x1 - x0) || 1) * (VW - 2 * PAD);
        p.y = PAD + (p.y - y0) / ((y1 - y0) || 1) * (VH - 2 * PAD);
      });
    };
    fit(); // spread to fill the canvas first
    for (let k = 0; k < 120; k++) { // then push overlapping points apart
      for (let i = 0; i < pts.length; i++)
        for (let j = i + 1; j < pts.length; j++) {
          let dx = pts[j].x - pts[i].x, dy = pts[j].y - pts[i].y, d = Math.hypot(dx, dy) || 0.01;
          if (d < 40) { const p = (40 - d) / 2, ux = dx / d, uy = dy / d; pts[i].x -= ux * p; pts[i].y -= uy * p; pts[j].x += ux * p; pts[j].y += uy * p; }
        }
      pts.forEach((p) => { p.x = Math.max(PAD, Math.min(VW - PAD, p.x)); p.y = Math.max(PAD, Math.min(VH - PAD, p.y)); });
    }
    const sims = S.sims || pts.map(() => 0);
    const mn = Math.min(...sims), mx = Math.max(...sims);
    const norm = sims.map((s) => (s - mn) / ((mx - mn) || 1));
    // query = similarity-weighted centroid of the documents
    let wx = 0, wy = 0, ws = 0;
    pts.forEach((p, i) => { const w = Math.pow(norm[i], 3) + 0.002; wx += p.x * w; wy += p.y * w; ws += w; });
    const order = norm.map((n, i) => [n, i]).sort((a, b) => b[0] - a[0]).map((z) => z[1]);
    return { pts, norm, sims, qx: wx / ws, qy: wy / ws, topIdx: order[0], topSet: new Set(order.slice(0, 3)) };
  }

  function buildVs(S) {
    clearVs();
    const L = vsLayout(S);
    vsSpace = S;

    // legend
    $("vsLegend").innerHTML = Object.entries(CAT).map(([k, c]) =>
      `<span><span class="dot" style="background:${c}"></span>${k}</span>`).join("");

    // lines (query -> each doc), hidden via dash offset
    $("vsLines").innerHTML = L.pts.map((p, i) => {
      const len = Math.hypot(L.qx - p.x, L.qy - p.y);
      const top = i === L.topIdx;
      return `<line id="vl${i}" class="vs-line" x1="${L.qx.toFixed(1)}" y1="${L.qy.toFixed(1)}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}" stroke="${top ? "#54D389" : "#9FB0D0"}" stroke-width="${top ? 2.2 : 1}" stroke-dasharray="${len.toFixed(1)}" stroke-dashoffset="${len.toFixed(1)}" stroke-opacity="0" stroke-linecap="round"/>`;
    }).join("");

    // dots (hidden at r=2), with hover title
    $("vsDots").innerHTML = L.pts.map((p, i) =>
      `<g><title>${p.text}</title><circle id="vd${i}" class="vs-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2" fill="${CAT[p.cat] || "#9FB0D0"}" fill-opacity="0" stroke="#0A0C11" stroke-width="1"/></g>`).join("");

    // label only the best match on the canvas (the rest live in the ranking panel)
    $("vsLabels").innerHTML = L.pts.map((p, i) => {
      if (i !== L.topIdx) return "";
      const t = short(p.text, 26), w = t.length * 5.0 + 12, right = p.x > VW - 130;
      const lx = right ? p.x - w - 6 : p.x + 10, ly = p.y + 4;
      return `<g id="vlb${i}" class="vs-label" style="opacity:0"><rect x="${lx - 3}" y="${ly - 10}" width="${w}" height="15" rx="4" fill="#15241a" stroke="rgba(84,211,137,0.5)"/><text x="${lx + 2}" y="${ly + 1}" font-family="Inter,sans-serif" font-size="9" fill="#a6f0c6">★ ${t}</text></g>`;
    }).join("");

    // query marker (flies in)
    const tri = `M${L.qx.toFixed(1)} ${(L.qy - 8).toFixed(1)} L${(L.qx + 6.5).toFixed(1)} ${(L.qy + 5).toFixed(1)} L${(L.qx - 6.5).toFixed(1)} ${(L.qy + 5).toFixed(1)} Z`;
    $("vsQuery").innerHTML =
      `<g id="vqm" class="vs-qmark" style="opacity:0;transform:translateY(-16px)">` +
      `<circle cx="${L.qx.toFixed(1)}" cy="${L.qy.toFixed(1)}" r="14" fill="#6E8BFF" fill-opacity="0.16"/>` +
      `<path d="${tri}" fill="#6E8BFF" stroke="#0A0C11" stroke-width="1"/>` +
      `<rect x="${(L.qx + 9).toFixed(1)}" y="${(L.qy - 20).toFixed(1)}" width="72" height="14" rx="4" fill="#6E8BFF" fill-opacity="0.16"/>` +
      `<text x="${(L.qx + 14).toFixed(1)}" y="${(L.qy - 10).toFixed(1)}" font-family="Inter,sans-serif" font-size="8.5" font-weight="600" fill="#8AA0FF">tu pregunta</text></g>`;

    // ranking rows (bars start at 0)
    if (S.ranking) {
      const mx = S.ranking[0].sim || 1;
      $("vsRankRows").innerHTML = S.ranking.slice(0, 5).map((d, i) =>
        `<div class="vr-row${i === 0 ? " top" : ""}"><span class="vr-pos">${i + 1}</span><span class="vr-lab" title="${d.text}">${short(d.text, 20)}</span>` +
        `<span class="vr-track"><span class="vr-bar" data-w="${Math.max(4, (d.sim / mx) * 100).toFixed(1)}" style="width:0"></span></span>` +
        `<span class="vr-sc">${d.sim.toFixed(3)}</span></div>`).join("");
    }
    $("vsCaption").innerHTML = "Midiendo la similitud de tu pregunta con cada documento…";

    runVs(L, S);
  }

  function runVs(L, S) {
    const at = (t, fn) => vsTimers.push(setTimeout(fn, t));
    // phase A: docs appear (staggered)
    at(30, () => L.pts.forEach((p, i) => {
      const c = $("vd" + i); if (!c) return;
      c.style.transitionDelay = (i * 22) + "ms";
      c.setAttribute("r", "5"); c.setAttribute("fill-opacity", "0.85");
    }));
    // phase B: the question drops in
    at(720, () => { const q = $("vqm"); if (q) { q.style.opacity = "1"; q.style.transform = "translateY(0)"; } });
    // phase C: measure — lines draw, relevant dots grow, top labels show
    at(1250, () => {
      L.pts.forEach((p, i) => {
        const ln = $("vl" + i), c = $("vd" + i);
        if (ln) { ln.setAttribute("stroke-dashoffset", "0"); ln.setAttribute("stroke-opacity", i === L.topIdx ? "0.9" : (0.08 + L.norm[i] * 0.4).toFixed(2)); }
        if (c) { c.style.transitionDelay = "0ms"; c.setAttribute("r", (5 + L.norm[i] * 7).toFixed(1)); }
      });
      const wl = $("vlb" + L.topIdx); if (wl) wl.style.opacity = "1";
    });
    // phase D: ranking sorts + caption
    at(1850, () => {
      document.querySelectorAll("#vsRankRows .vr-bar").forEach((b) => { b.style.width = b.dataset.w + "%"; });
      if (S.ranking) $("vsCaption").innerHTML = `Tu pregunta se parece más a <b>«${short(S.ranking[0].text, 44)}»</b> — es el mayor producto punto (${S.ranking[0].sim.toFixed(3)}).`;
    });
  }

  async function loadSpace(q, idx) {
    $("vsCaption").textContent = "Calculando embeddings reales…";
    try {
      const r = await fetch("/api/space?q=" + encodeURIComponent(q));
      if (r.status === 503) { setTimeout(() => loadSpace(q, idx), 1200); return; }
      buildVs(await r.json());
      Array.from($("vsQueries").children).forEach((b, i) => b.setAttribute("aria-pressed", String(i === idx)));
    } catch (e) { $("vsCaption").textContent = "Backend no disponible — ejecuta ./run.sh ui"; }
  }

  $("vsQueries").innerHTML = QUERIES.map((q, i) =>
    `<button class="vs-q" aria-pressed="${i === 0}">${q}</button>`).join("");
  Array.from($("vsQueries").children).forEach((b, i) => b.addEventListener("click", () => loadSpace(QUERIES[i], i)));
  $("vsReplay").addEventListener("click", () => { if (vsSpace) buildVs(vsSpace); });

  // Scale the fixed-layout stage down to fit narrow screens, so the demo is
  // always fully visible (no cut-off) however small the window gets.
  function fitStage() {
    const wrap = document.querySelector(".stage-scroll");
    if (!wrap || !stage) return;
    const scale = Math.min(1, wrap.clientWidth / 840);
    stage.style.transform = `scale(${scale})`;
    wrap.style.height = Math.round(470 * scale) + "px";
  }
  window.addEventListener("resize", fitStage);
  fitStage();
  requestAnimationFrame(fitStage);

  // =========================================================================
  // boot: wait for the backend, then load defaults
  // =========================================================================
  async function boot() {
    for (let i = 0; i < 200; i++) {
      try {
        const h = await (await fetch("/api/health")).json();
        if (h.error) { setStatus("err", "Error del backend: " + h.error); return; }
        if (h.ready) break;
        setStatus("loading", "Preparando el pipeline real… (cifrando e indexando)");
      } catch (e) { setStatus("err", "Abre la web con ./run.sh ui (backend no accesible)"); return; }
      await new Promise((res) => setTimeout(res, 700));
    }
    await loadRun(QUERIES[0]);
    await loadSpace(QUERIES[0], 0);
  }
  boot();
})();
