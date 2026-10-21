(function () {
  'use strict';

  // ---------- formatação (pt-BR) ----------------------------------------------------------
  const nfs = {};
  const nf = (a, b) => nfs[a + '-' + b] || (nfs[a + '-' + b] = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: a, maximumFractionDigits: b }));
  const FMT = {
    int: (v) => nf(0, 0).format(v),
    d1: (v) => nf(1, 1).format(v),
    d2: (v) => nf(2, 2).format(v),
    d3: (v) => nf(3, 3).format(v),
    abs2: (v) => nf(2, 2).format(Math.abs(v)),
    pct0: (v) => nf(0, 0).format(v * 100) + '%',
    pct1: (v) => nf(1, 1).format(v * 100) + '%',
    pp1: (v) => nf(1, 1).format(v) + ' p.p.',
    s2: (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + nf(2, 2).format(Math.abs(v)),
    dias1: (v) => nf(1, 1).format(v / 24),
    h1: (v) => nf(1, 1).format(v),
  };
  // célula vazia vale ausente (NaN), nunca zero: Number('') seria 0 e entraria como Elite, 0% etc.
  const N = (x) => (x === '' || x == null ? NaN : Number(x));
  const rows = (id) => { const d = dash.data(id); return d && d.status === 'ok' ? d.data : null; };
  const colors = () => dash.colors;

  // ---------- números marcados ---------------------------------------------------------------
  function parseWhere(w) {
    const o = {};
    if (!w) return o;
    w.split('&').forEach((p) => { const i = p.indexOf('='); o[decodeURIComponent(p.slice(0, i))] = decodeURIComponent(p.slice(i + 1)); });
    return o;
  }
  function fillMarks(root) {
    root.querySelectorAll('[data-fmt]').forEach((el) => {
      const r = rows(el.dataset.source);
      if (!r) { el.textContent = '—'; return; }
      const w = parseWhere(el.dataset.where);
      const row = r.find((x) => Object.keys(w).every((k) => String(x[k]) === w[k]));
      if (el.dataset.fmt === 'txt') { el.textContent = row && row[el.dataset.field] ? row[el.dataset.field] : '—'; return; }
      const v = row ? N(row[el.dataset.field]) : NaN;
      el.textContent = Number.isFinite(v) ? FMT[el.dataset.fmt](v) : '—';
    });
  }

  // ---------- utilitários de desenho --------------------------------------------------------------
  const NS = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => e.setAttribute(k, v));
    if (parent) parent.appendChild(e);
    return e;
  }
  function htmlEl(tag, cls, text, parent) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function makeSvg(el, h) {
    el.replaceChildren();
    const w = Math.max(280, el.clientWidth || 600);
    const svg = svgEl('svg', { viewBox: `0 0 ${w} ${h}`, width: '100%', role: 'img' });
    el.appendChild(svg);
    return { svg, w, h };
  }
  const tipFor = (el) => {
    let t = el.querySelector('.px-tip');
    if (!t) { t = htmlEl('div', 'px-tip', ''); t.hidden = true; el.appendChild(t); }
    return t;
  };
  function showTip(el, ev, html) {
    const t = tipFor(el);
    t.replaceChildren();
    html.forEach((part, i) => { if (i) t.appendChild(document.createElement('br')); const s = htmlEl('span', null, part[0]); t.appendChild(s); if (part[1]) t.appendChild(document.createTextNode(' ' + part[1])); });
    t.hidden = false;
    const r = el.getBoundingClientRect();
    let x = ev.clientX - r.left + 12, y = ev.clientY - r.top - 8;
    if (x + t.offsetWidth > r.width) x = ev.clientX - r.left - t.offsetWidth - 12;
    t.style.left = Math.max(0, x) + 'px';
    t.style.top = Math.max(0, y) + 'px';
  }
  const hideTip = (el) => { const t = el.querySelector('.px-tip'); if (t) t.hidden = true; };
  function placeholder(el, ok) {
    el.classList.toggle('dash-skeleton', !ok);
    if (!ok) el.replaceChildren();
    return ok;
  }

  // ---------- predefinições ---------------------------------------------------------------------------
  const CLASSES = ['Elite', 'High', 'Medium', 'Low'];
  const HIST = {
    freq: { cols: ['freq_release'], names: ['releases por semana'], log: true, bins: 26, ticks: [0.1, 0.25, 1, 7], tl: ['0,1', '0,25', '1', '7'],
      bands: [[0, 1 / 4.34, 'Low'], [1 / 4.34, 1, 'Medium'], [1, 7, 'High'], [7, 1e9, 'Elite']], xl: 'releases por semana (escala log)', med: FMT.d2, unit: ' /sem' },
    lt: { cols: ['lt_release_h', 'lt_commit_h'], names: ['(a) por release', '(b) por commit'], div: 24, log: true, bins: 26, ticks: [0.1, 1, 7, 30, 365], tl: ['0,1', '1', '7', '30', '365'],
      bands: [[0, 1, 'Elite'], [1, 7, 'High'], [7, 30, 'Medium'], [30, 1e9, 'Low']], xl: 'dias entre o commit e a release (escala log)', med: FMT.d1, unit: ' dias' },
    cfra: { cols: ['cfr_a'], names: ['CFR de CI (a)'], log: false, dom: [0, 1], bins: 20, ticks: [0, 0.15, 0.3, 0.45, 0.6, 0.8, 1], tl: ['0', '15%', '30%', '45%', '60%', '80%', '100%'],
      bands: [[0, 0.15, 'Elite'], [0.15, 0.3, 'High'], [0.3, 0.45, 'Medium'], [0.45, 1.01, 'Low']], xl: 'proporção de falhas', med: FMT.pct1, unit: '' },
    cfrb: { cols: ['cfr_b'], names: ['CFR por release (b)'], log: false, dom: [0, 1], bins: 20, ticks: [0, 0.15, 0.3, 0.45, 0.6, 0.8, 1], tl: ['0', '15%', '30%', '45%', '60%', '80%', '100%'],
      bands: [[0, 0.15, 'Elite'], [0.15, 0.3, 'High'], [0.3, 0.45, 'Medium'], [0.45, 1.01, 'Low']], xl: 'proporção de releases seguidas de corretiva', med: FMT.pct1, unit: '' },
    rec: { cols: ['recuperacao_h'], names: ['tempo de recuperação'], log: true, bins: 28, ticks: [0.1, 1, 24, 168, 1000], tl: ['0,1 h', '1 h', '1 dia', '1 sem', '1000 h'],
      bands: [[0, 1, 'Elite'], [1, 24, 'High'], [24, 168, 'Medium'], [168, 1e9, 'Low']], xl: 'horas até o CI voltar ao verde (escala log)', med: FMT.h1, unit: ' h' },
    rework: { cols: ['rework_rate'], names: ['rework rate'], log: false, dom: [0, 1.0001], bins: 20, ticks: [0, 0.25, 0.5, 0.75, 1], tl: ['0', '25%', '50%', '75%', '100%'],
      bands: null, xl: 'releases corretivas ÷ releases avaliadas', med: FMT.pct1, unit: '' },
  };

  // ---------- histograma ------------------------------------------------------------------------------------
  function hist(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const P = HIST[el.dataset.preset];
    const div = P.div || 1;
    const series = P.cols.map((c) => r.map((x) => N(x[c]) / div).filter((v) => Number.isFinite(v) && (!P.log || v > 0)));
    const all = series.flat();
    const H = 250, m = { l: 40, r: 12, t: 22, b: 50 };
    const { svg, w } = makeSvg(el, H);
    const iw = w - m.l - m.r, ih = H - m.t - m.b;
    let x0, x1;
    if (P.dom) { [x0, x1] = P.dom; } else { x0 = Math.min(...all) * 0.85; x1 = Math.max(...all) * 1.15; }
    const x = P.log ? d3.scaleLog().domain([x0, x1]).range([0, iw]) : d3.scaleLinear().domain([x0, x1]).range([0, iw]);
    const th = d3.range(1, P.bins).map((i) => (P.log ? x0 * Math.pow(x1 / x0, i / P.bins) : x0 + ((x1 - x0) * i) / P.bins));
    const bins = series.map((s) => d3.bin().domain([x0, x1]).thresholds(th)(s));
    const ymax = Math.max(1, ...bins.flat().map((b) => b.length));
    const y = d3.scaleLinear().domain([0, ymax]).nice().range([ih, 0]);
    const g = svgEl('g', { transform: `translate(${m.l},${m.t})` }, svg);

    if (P.bands) {
      P.bands.forEach(([a, b, name], i) => {
        const xa = Math.max(0, x(Math.max(a, x0 * 0.0001 || a))), xb = Math.min(iw, x(Math.min(b, x1)));
        if (!(b > x0) || !(a < x1)) return;
        const xs = a <= x0 ? 0 : x(a), xe = b >= x1 ? iw : x(b);
        svgEl('rect', { x: xs, y: 0, width: Math.max(0, xe - xs), height: ih, style: `fill: color-mix(in srgb, var(--color-fg) ${i % 2 ? 7 : 3}%, transparent)` }, g);
        const t = svgEl('text', { x: (xs + xe) / 2, y: -8, 'text-anchor': 'middle' }, g);
        t.textContent = name;
      });
    }
    // grade e eixo y
    y.ticks(4).forEach((t) => {
      svgEl('line', { x1: 0, x2: iw, y1: y(t), y2: y(t), style: 'stroke: var(--px-chart-grid); stroke-width: 1' }, g);
      const tx = svgEl('text', { x: -6, y: y(t) + 4, 'text-anchor': 'end' }, g); tx.textContent = FMT.int(t);
    });
    const cs = colors();
    bins.forEach((bs, si) => {
      bs.forEach((b) => {
        if (!b.length) return;
        const bx0 = x(b.x0), bx1 = x(b.x1);
        const pad = 1;
        const rect = svgEl('rect', { x: bx0 + pad / 2, y: y(b.length), width: Math.max(1, bx1 - bx0 - pad), height: ih - y(b.length), rx: 2,
          style: si === 0 ? `fill: ${cs[0]}; opacity: ${bins.length > 1 ? 0.45 : 0.9}` : `fill: none; stroke: ${cs[1]}; stroke-width: 2` }, g);
        rect.addEventListener('mousemove', (ev) => showTip(el, ev, [[b.length + ' repositórios', ''], [P.names[si], `${P.log ? FMT.d2(b.x0) : FMT.d2(b.x0)} a ${FMT.d2(b.x1)}`]]));
        rect.addEventListener('mouseleave', () => hideTip(el));
      });
    });
    // mediana(s)
    series.forEach((s, si) => {
      const med = d3.median(s);
      const mx = x(med);
      svgEl('line', { x1: mx, x2: mx, y1: 0, y2: ih, style: `stroke: ${cs[si === 0 ? 0 : 1]}; stroke-width: 2; stroke-dasharray: 5 4` }, g);
      const left = si === 1 || mx > iw * 0.72;
      const t = svgEl('text', { x: mx + (left ? -5 : 5), y: 14 + si * 14, 'text-anchor': left ? 'end' : 'start', class: 'lbl-strong' }, g);
      t.textContent = `mediana ${series.length > 1 ? P.names[si].slice(0, 3) + ' ' : ''}${P.med(med)}${P.unit}`;
    });
    // eixo x
    svgEl('line', { x1: 0, x2: iw, y1: ih, y2: ih, style: 'stroke: var(--px-chart-axis)' }, g);
    P.ticks.forEach((t, i) => {
      if (t < x0 || t > x1) return;
      svgEl('line', { x1: x(t), x2: x(t), y1: ih, y2: ih + 4, style: 'stroke: var(--px-chart-axis)' }, g);
      const tx = svgEl('text', { x: x(t), y: ih + 17, 'text-anchor': 'middle' }, g); tx.textContent = P.tl[i];
    });
    const xl = svgEl('text', { x: iw / 2, y: ih + 38, 'text-anchor': 'middle' }, g); xl.textContent = P.xl;
    if (series.length > 1) {
      const lg = htmlEl('div', 'px-legend', null);
      P.names.forEach((n, i) => { const s = htmlEl('span', null, null, lg); const sw = htmlEl('i', null, null, s); sw.style.background = i ? 'transparent' : cs[0]; sw.style.border = i ? `2px solid ${cs[1]}` : '0'; s.appendChild(document.createTextNode(n)); });
      el.appendChild(lg);
    }
  }

  // ---------- dispersão (RQ 05) -----------------------------------------------------------------------------------
  function scatter(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const ycol = el.dataset.y;
    const pts = r.map((d) => ({ repo: d.repo, x: N(d.freq_release), y: N(d[ycol]) })).filter((d) => d.x > 0 && Number.isFinite(d.y));
    const H = 290, m = { l: 44, r: 12, t: 12, b: 48 };
    const { svg, w } = makeSvg(el, H);
    const iw = w - m.l - m.r, ih = H - m.t - m.b;
    const x = d3.scaleLog().domain([d3.min(pts, (d) => d.x) * 0.8, d3.max(pts, (d) => d.x) * 1.2]).range([0, iw]);
    const y = d3.scaleLinear().domain([0, 1]).range([ih, 0]);
    const g = svgEl('g', { transform: `translate(${m.l},${m.t})` }, svg);
    [0, 0.25, 0.5, 0.75, 1].forEach((t) => {
      svgEl('line', { x1: 0, x2: iw, y1: y(t), y2: y(t), style: 'stroke: var(--px-chart-grid)' }, g);
      const tx = svgEl('text', { x: -6, y: y(t) + 4, 'text-anchor': 'end' }, g); tx.textContent = FMT.pct0(t);
    });
    [0.1, 0.25, 1, 7].forEach((t, i) => {
      if (t < x.domain()[0] || t > x.domain()[1]) return;
      svgEl('line', { x1: x(t), x2: x(t), y1: ih, y2: ih + 4, style: 'stroke: var(--px-chart-axis)' }, g);
      const tx = svgEl('text', { x: x(t), y: ih + 17, 'text-anchor': 'middle' }, g); tx.textContent = ['0,1', '0,25', '1', '7'][i];
    });
    svgEl('line', { x1: 0, x2: iw, y1: ih, y2: ih, style: 'stroke: var(--px-chart-axis)' }, g);
    const xl = svgEl('text', { x: iw / 2, y: ih + 38, 'text-anchor': 'middle' }, g); xl.textContent = 'releases por semana (escala log)';
    const yl = svgEl('text', { x: -ih / 2, y: -34, 'text-anchor': 'middle', transform: 'rotate(-90)' }, g); yl.textContent = el.dataset.ylabel;
    const c = colors()[el.dataset.color ? Number(el.dataset.color) : 0];
    pts.forEach((p) => {
      const dot = svgEl('circle', { cx: x(p.x), cy: y(p.y), r: 3.4, style: `fill: ${c}; opacity: .55; stroke: var(--color-bg); stroke-width: .5` }, g);
      dot.addEventListener('mousemove', (ev) => showTip(el, ev, [[p.repo, ''], ['frequência', FMT.d2(p.x) + ' /sem'], [el.dataset.ylabel, FMT.pct1(p.y)]]));
      dot.addEventListener('mouseleave', () => hideTip(el));
    });
  }

  // ---------- barras em HTML ---------------------------------------------------------------------------------------------
  function drawBars(el, items, opt) {
    opt = opt || {};
    el.replaceChildren();
    const max = opt.max || Math.max(...items.map((i) => i.value), 1e-9);
    const box = htmlEl('div', 'px-bars', null, el);
    items.forEach((it) => {
      const row = htmlEl('div', 'px-bar', null, box);
      htmlEl('div', 't', it.label, row);
      const tr = htmlEl('div', 'tr', null, row);
      const fi = htmlEl('div', 'fi', null, tr);
      fi.style.width = Math.max(0, Math.min(100, (it.value / max) * 100)) + '%';
      fi.style.background = it.color || colors()[0];
      if (opt.ref != null) { const rl = htmlEl('div', null, null, tr); rl.style.cssText = `position:absolute;top:0;bottom:0;width:2px;background:var(--color-fg);left:${(opt.ref / max) * 100}%`; }
      htmlEl('div', 'n', it.text, row);
      row.title = it.tip || '';
    });
    if (opt.note) htmlEl('div', 'px-legend', opt.note, el);
  }
  const byMetric = (r) => Object.fromEntries(r.map((x) => [x.metrica, x]));

  const BARS = {
    faixas(el, r) {
      const cs = colors(); const col = [cs[2], cs[0], cs[1], cs[3]];
      drawBars(el, r.map((x, i) => ({ label: x.faixa, value: N(x.repositorios), text: `${FMT.int(N(x.repositorios))} · ${FMT.pct0(N(x.pct))}`, color: col[i] })));
    },
    freq_variantes(el, r) {
      const m = byMetric(r);
      drawBars(el, [['freq_release', 'Releases'], ['freq_release_pre', 'Releases + pré-releases'], ['freq_tag', 'Tags']].map(([k, l], i) => ({ label: l, value: N(m[k].mediana), text: FMT.d2(N(m[k].mediana)) + ' /sem', color: colors()[i] })), { max: 1, ref: 0.25, note: 'Linha: corte entre Medium e Low (1 por mês).' });
    },
    lt_medianas(el, r) {
      const m = byMetric(r);
      drawBars(el, [['lt_release_h', '(a) por release'], ['lt_commit_h', '(b) por commit'], ['lt_commit_sem_bots_h', '(b) sem commits de bots']].map(([k, l], i) => ({ label: l, value: N(m[k].mediana) / 24, text: FMT.d1(N(m[k].mediana) / 24) + ' dias', color: colors()[i] })), { max: 10, ref: 7, note: 'Linha: 7 dias, o limite superior da hipótese (faixa High).' });
    },
    cfr_variantes(el, r) {
      const m = byMetric(r);
      drawBars(el, [['cfr_a', 'Oficial (a)'], ['cfr_a_bruto', 'Bruto, com tentativas anteriores'], ['cfr_a_sem_flaky', 'Sem falhas flaky']].map(([k, l], i) => ({ label: l, value: N(m[k].mediana), text: FMT.pct1(N(m[k].mediana)), color: colors()[i] })), { max: 0.25, ref: 0.10, note: 'Linha: 10%, o início da faixa prevista na hipótese (10% a 25%).' });
    },
    cfr_comparacao(el, r) {
      const m = byMetric(r);
      drawBars(el, [['cfr_a', 'CFR de CI (a)'], ['cfr_b', 'CFR por release (b)'], ['cfr_c', 'CFR por issues de bug (c)']].map(([k, l], i) => ({ label: l, value: N(m[k].mediana), text: FMT.pct1(N(m[k].mediana)), color: colors()[i] })), { max: 0.5, note: 'Mediana entre repositórios. O (c) existe em menos repositórios (os que têm issues com label de bug).' });
    },
    heuristica(el, r) {
      drawBars(el, r.map((x) => ({ label: x.variante === 'v5' ? 'v5 (adotada)' : x.variante, value: N(x.f1), text: `F1 ${FMT.d2(N(x.f1))}`, tip: `precisão ${FMT.d3(N(x.precisao))} · recall ${FMT.d3(N(x.recall))}`, color: x.variante === 'v5' ? colors()[0] : 'var(--px-chart-muted)' })), { max: 1, ref: 0.7, note: 'Linha: F1 de 0,70, o limiar do enunciado. Precisão da v5: 0,48; recall: 0,97.' });
    },
    kappa(el, r) {
      const nm = { tipo_projeto: 'Tipo do projeto', entregas_reais: 'Releases são entregas?', corretiva: 'Release corretiva' };
      drawBars(el, r.map((x, i) => ({ label: nm[x.dimensao] || x.dimensao, value: N(x.kappa), text: `κ ${FMT.d2(N(x.kappa))} · ${x.interpretacao}`, color: colors()[i] })), { max: 1, note: 'Kappa de Fleiss entre os 3 avaliadores, antes do desempate. Escala de 0 a 1.' });
    },
    rec_classes(el, r) {
      const v = r.map((x) => N(x.recuperacao_h)).filter(Number.isFinite);
      const cuts = [['Elite (< 1 h)', (a) => a < 1], ['High (1 h a 1 dia)', (a) => a >= 1 && a < 24], ['Medium (1 dia a 1 sem)', (a) => a >= 24 && a < 168], ['Low (≥ 1 sem)', (a) => a >= 168]];
      const cs = colors(); const col = [cs[2], cs[0], cs[1], cs[3]];
      drawBars(el, cuts.map(([l, f], i) => { const n = v.filter(f).length; return { label: l, value: n, text: `${FMT.int(n)} · ${FMT.pct0(n / v.length)}`, color: col[i] }; }));
    },
    grupo_freq(el, r) {
      const f = r.filter((x) => x.fator === el.dataset.fator);
      const ordem = el.dataset.fator === 'idade' ? f : f.slice().sort((a, b) => N(b.freq_release) - N(a.freq_release));
      const rot = (x) => (x.fator === 'idade' ? `${x.grupo} (${FMT.d1(N(x.idade_min))} a ${FMT.d1(N(x.idade_max))} anos)` : `${x.grupo} (n=${x.n})`);
      drawBars(el, ordem.map((x, i) => ({ label: rot(x), value: N(x.freq_release), text: FMT.d2(N(x.freq_release)) + ' /sem', color: colors()[el.dataset.fator === 'idade' ? 1 : 0] })), { note: 'Mediana de releases por semana em cada grupo.' });
    },
    rq08b_freq(el, r) {
      drawBars(el, r.map((x, i) => ({ label: x.trimestre.replace('Q', ' T'), value: N(x.mediana), text: FMT.d2(N(x.mediana)) + ' /sem', tip: `IQR ${FMT.d2(N(x.q1))} a ${FMT.d2(N(x.q3))}`, color: colors()[0] })), { note: 'Mediana entre repositórios. Só descritivo, sem teste.' });
    },
    rq08b_lt(el, r) {
      drawBars(el, r.map((x) => ({ label: x.trimestre.replace('Q', ' T'), value: N(x.mediana_h) / 24, text: FMT.d1(N(x.mediana_h) / 24) + ' dias', tip: `${x.n_repos} repositórios`, color: colors()[1] })), { note: 'Lead time (a) por trimestre de publicação. Só descritivo, sem teste.' });
    },
    rq08a(el, r) {
      const m = byMetric(r);
      drawBars(el, [['rework_rate', 'Rework rate (sem limite de dias)'], ['rework_rate_7d', 'Rework rate em 7 dias'], ['cfr_b', 'CFR por release (b)']].map(([k, l], i) => ({ label: l, value: N(m[k].mediana), text: FMT.pct1(N(m[k].mediana)), color: colors()[i] })), { max: 1, note: 'Mediana entre repositórios.' });
    },
  };
  function bars(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    BARS[el.dataset.preset](el, r);
  }

  // ---------- funil de seleção ----------------------------------------------------------------------------------------------------
  function funnel(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const by = Object.fromEntries(r.map((x) => [x.etapa, x]));
    const e = (k) => N(by[k].entraram);
    const items = [
      ['Candidatos da busca', e('duplicata')],
      ['Sem duplicatas e forks', e('arquivado')],
      ['Sem repositórios arquivados', e('sem_push_na_janela')],
      ['Com push na janela', e('nao_examinados')],
      ['Examinados pelos filtros', e('usa_actions')],
      ['Usam GitHub Actions', e('min_releases')],
      ['5 ou mais releases na janela', e('min_runs')],
      ['50 ou mais runs válidos (amostra)', e('min_runs') - N(by.min_runs.sairam)],
    ];
    const top = items[0][1], lmax = Math.log10(top);
    const cs = colors();
    drawBars(el, items.map(([l, v], i) => ({ label: l, value: Math.log10(v), text: FMT.int(v), color: i === items.length - 1 ? cs[2] : cs[0] })), { max: lmax, note: 'Largura em escala logarítmica. A seleção para quando a amostra fecha, então só uma fração dos candidatos chega aos filtros caros.' });
  }

  // ---------- classes DORA da C1 -----------------------------------------------------------------------------------------------------------
  function classesC1(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const cs = colors(); const col = { Elite: cs[2], High: cs[0], Medium: cs[1], Low: cs[3] };
    const by = Object.fromEntries(r.map((x) => [x.classe, x]));
    drawBars(el, CLASSES.map((c) => ({ label: c, value: N(by[c].repositorios), text: `${FMT.int(N(by[c].repositorios))} · ${FMT.pct0(N(by[c].pct))}`, color: col[c] })));
  }

  // ---------- RQ 06: tamanho de efeito por teste ---------------------------------------------------------------------------------
  function dots(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const FL = { linguagem_top: 'Linguagem', estrelas_q: 'Estrelas', contribuidores_q: 'Contribuidores', idade_q: 'Idade', tipo_projeto: 'Tipo do projeto' };
    const ML = { freq_release: 'frequência', lt_commit_h: 'lead time (b)', cfr_a: 'CFR (a)', cfr_b: 'CFR (b)', recuperacao_h: 'recuperação' };
    const data = r.map((d) => ({ f: FL[d.fator] || d.fator, m: ML[d.metrica] || d.metrica, e: N(d.epsilon2), p: N(d.p_ajustado), n: N(d.n_total) }));
    const rowH = 19, H = data.length * rowH + 52, mL = 150, mR = 14, mT = 20;
    const { svg, w } = makeSvg(el, H);
    const iw = w - mL - mR;
    const xmax = Math.max(0.2, d3.max(data, (d) => d.e) * 1.08);
    const x = d3.scaleLinear().domain([0, xmax]).range([0, iw]);
    const g = svgEl('g', { transform: `translate(${mL},${mT})` }, svg);
    const ih = data.length * rowH;
    [0, 0.05, 0.1, 0.15, 0.2].forEach((t) => {
      if (t > xmax) return;
      svgEl('line', { x1: x(t), x2: x(t), y1: 0, y2: ih, style: 'stroke: var(--px-chart-grid)' }, g);
      const tx = svgEl('text', { x: x(t), y: ih + 15, 'text-anchor': 'middle' }, g); tx.textContent = FMT.d2(t);
    });
    const rx = x(0.06);
    svgEl('line', { x1: rx, x2: rx, y1: -6, y2: ih, style: 'stroke: var(--px-chart-reference); stroke-width: 1.5; stroke-dasharray: 5 4' }, g);
    const rt = svgEl('text', { x: rx + 4, y: -8, class: 'lbl-strong' }, g); rt.textContent = 'ε² = 0,06 (hipótese)';
    const xl = svgEl('text', { x: iw / 2, y: ih + 33, 'text-anchor': 'middle' }, g); xl.textContent = 'tamanho de efeito (ε²)';
    const cs = colors();
    let last = null;
    data.forEach((d, i) => {
      const cy = i * rowH + rowH / 2;
      if (d.f !== last) { svgEl('line', { x1: -mL, x2: iw, y1: i * rowH, y2: i * rowH, style: 'stroke: var(--px-chart-grid)' }, g); last = d.f; }
      const sig = d.p < 0.05;
      const lab = svgEl('text', { x: -8, y: cy + 4, 'text-anchor': 'end', class: sig ? 'lbl-strong' : '' }, g); lab.textContent = `${d.f} · ${d.m}`;
      svgEl('line', { x1: 0, x2: x(d.e), y1: cy, y2: cy, style: `stroke: ${sig ? cs[0] : 'var(--px-chart-muted)'}; stroke-width: 2; opacity: .6` }, g);
      const c = svgEl('circle', { cx: x(d.e), cy, r: 5, style: sig ? `fill: ${cs[0]}` : 'fill: var(--color-bg); stroke: var(--px-chart-muted); stroke-width: 1.5' }, g);
      c.addEventListener('mousemove', (ev) => showTip(el, ev, [[`${d.f} · ${d.m}`, ''], ['ε²', FMT.d3(d.e)], ['p ajustado (Holm)', d.p < 0.001 ? '< 0,001' : FMT.d3(d.p)], ['n', FMT.int(d.n)]]));
      c.addEventListener('mouseleave', () => hideTip(el));
    });
    const lg = htmlEl('div', 'px-legend', null, el);
    const s1 = htmlEl('span', null, null, lg); const i1 = htmlEl('i', null, null, s1); i1.style.background = cs[0]; s1.appendChild(document.createTextNode('significativo após Holm (p < 0,05)'));
    const s2 = htmlEl('span', null, null, lg); const i2 = htmlEl('i', null, null, s2); i2.style.cssText = 'border:1.5px solid var(--px-chart-muted);border-radius:50%'; s2.appendChild(document.createTextNode('não significativo'));
  }

  // ---------- linha com faixa (RQ 08b) --------------------------------------------------------------------------------------------
  function lineband(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    const metric = el.dataset.metric, scale = N(el.dataset.scale || 1);
    const d = r.filter((x) => x.metrica === metric).map((x) => ({ mes: x.mes, n: N(x.n), med: N(x.mediana) * scale, q1: N(x.q1) * scale, q3: N(x.q3) * scale }));
    const H = 230, m = { l: 42, r: 12, t: 14, b: 46 };
    const { svg, w } = makeSvg(el, H);
    const iw = w - m.l - m.r, ih = H - m.t - m.b;
    const x = d3.scalePoint().domain(d.map((q) => q.mes)).range([0, iw]).padding(0.2);
    const ymax = d3.max(d, (q) => q.q3) * 1.1;
    const y = d3.scaleLinear().domain([0, ymax]).nice().range([ih, 0]);
    const g = svgEl('g', { transform: `translate(${m.l},${m.t})` }, svg);
    y.ticks(4).forEach((t) => {
      svgEl('line', { x1: 0, x2: iw, y1: y(t), y2: y(t), style: 'stroke: var(--px-chart-grid)' }, g);
      const tx = svgEl('text', { x: -6, y: y(t) + 4, 'text-anchor': 'end' }, g); tx.textContent = FMT.int(t) + (el.dataset.unit || '');
    });
    const cs = colors();
    const area = d3.area().x((q) => x(q.mes)).y0((q) => y(q.q1)).y1((q) => y(q.q3));
    svgEl('path', { d: area(d), style: `fill: ${cs[0]}; opacity: .2` }, g);
    const line = d3.line().x((q) => x(q.mes)).y((q) => y(q.med));
    svgEl('path', { d: line(d), style: `fill: none; stroke: ${cs[0]}; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round` }, g);
    d.forEach((q, i) => {
      const c = svgEl('circle', { cx: x(q.mes), cy: y(q.med), r: 3.5, style: `fill: ${cs[0]}` }, g);
      c.addEventListener('mousemove', (ev) => showTip(el, ev, [[q.mes, ''], ['mediana', FMT.d1(q.med) + (el.dataset.unit || '')], ['IQR', `${FMT.d1(q.q1)} a ${FMT.d1(q.q3)}`], ['repositórios', FMT.int(q.n)]]));
      c.addEventListener('mouseleave', () => hideTip(el));
      if (i % 2 === 0 || d.length < 7) {
        const t = svgEl('text', { x: x(q.mes), y: ih + 16, 'text-anchor': 'end', transform: `rotate(-35 ${x(q.mes)} ${ih + 16})` }, g); t.textContent = q.mes;
      }
    });
    svgEl('line', { x1: 0, x2: iw, y1: ih, y2: ih, style: 'stroke: var(--px-chart-axis)' }, g);
    const lg = htmlEl('div', 'px-legend', null, el);
    const s = htmlEl('span', null, null, lg); const i = htmlEl('i', null, null, s); i.style.background = cs[0]; s.appendChild(document.createTextNode('mediana mensal entre repositórios; a faixa é o IQR'));
  }

  // ---------- barras verticais agrupadas (RQ 07) -------------------------------------------------------------------------------------------
  function cols(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    el.replaceChildren();
    const by = Object.fromEntries(r.map((x) => [x.classe, x]));
    const combos = ['C1', 'C2', 'C3'];
    const max = Math.max(...r.flatMap((x) => combos.map((c) => N(x[c]))));
    const cs = colors();
    const box = htmlEl('div', 'px-cols', null, el);
    CLASSES.forEach((cl) => {
      const g = htmlEl('div', 'g', null, box);
      const bars = htmlEl('div', 'bars', null, g);
      combos.forEach((c, i) => {
        const b = htmlEl('div', 'b', null, bars);
        const v = N(by[cl][c]);
        b.style.height = (v / max) * 100 + '%'; b.style.background = cs[i];
        htmlEl('em', null, FMT.int(v), b);
        b.title = `${c}: ${v}`;
      });
      htmlEl('div', 'gl', cl, g);
    });
    const lg = htmlEl('div', 'px-legend', null, el);
    combos.forEach((c, i) => { const s = htmlEl('span', null, null, lg); const ic = htmlEl('i', null, null, s); ic.style.background = cs[i]; s.appendChild(document.createTextNode({ C1: 'C1 · release, lead time (a), CFR (a)', C2: 'C2 · release + pré, (b), CFR (b)', C3: 'C3 · tag, (b), CFR (a)' }[c])); });
  }

  // ---------- RQ 07: o que mudou por métrica ------------------------------------------------------------------------------------------------
  function metricChange(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    el.replaceChildren();
    const ML = { freq: 'Unidade de deploy', lead_time: 'Lead time', cfr: 'CFR' };
    const cs = colors();
    const box = htmlEl('div', 'px-bars', null, el);
    ['cfr', 'lead_time', 'freq'].forEach((met, mi) => {
      const rs = r.filter((x) => x.metrica === met);
      const vals = rs.map((x) => N(x.pct_nota_mudou));
      const mx = Math.max(...vals);
      const row = htmlEl('div', 'px-bar', null, box);
      htmlEl('div', 't', ML[met], row);
      const tr = htmlEl('div', 'tr', null, row);
      const fi = htmlEl('div', 'fi', null, tr);
      fi.style.width = mx * 100 + '%'; fi.style.background = cs[mi === 0 ? 3 : mi === 1 ? 1 : 0];
      htmlEl('div', 'n', mx === 0 ? '0%' : FMT.pct0(mx), row);
      row.title = rs.map((x) => `${x.par}: ${FMT.pct1(N(x.pct_nota_mudou))}`).join(' · ');
    });
  }

  // ---------- RQ 07: matriz de transição ----------------------------------------------------------------------------------------------------------
  let pairSel = 'C1xC2';
  function heat(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    el.replaceChildren();
    const pills = htmlEl('div', 'px-tabs2', null, el);
    ['C1xC2', 'C1xC3', 'C2xC3'].forEach((p) => {
      const b = htmlEl('button', 'px-pill', p.replace('x', ' → '), pills);
      b.type = 'button'; b.setAttribute('aria-pressed', String(p === pairSel));
      b.addEventListener('click', () => { pairSel = p; heat(el); });
    });
    const [a, b2] = pairSel.split('x');
    const d = r.filter((x) => x.par === pairSel);
    const get = (de, para) => N((d.find((x) => x.de === de && x.para === para) || {}).n || 0);
    const max = Math.max(...d.map((x) => N(x.n)), 1);
    const grid = htmlEl('div', 'px-heat', null, el);
    grid.style.gridTemplateColumns = 'minmax(3.2rem, auto) repeat(4, minmax(0, 1fr))';
    grid.style.marginTop = '12px';
    const corner = htmlEl('div', 'c h', `${a} ↓ · ${b2} →`, grid); corner.style.fontSize = '10px';
    CLASSES.forEach((c) => htmlEl('div', 'c h', c, grid));
    const cs = colors();
    CLASSES.forEach((de, i) => {
      htmlEl('div', 'c h', de, grid);
      CLASSES.forEach((para, j) => {
        const v = get(de, para);
        const cell = htmlEl('div', 'c', FMT.int(v), grid);
        const diag = i === j;
        cell.style.background = `color-mix(in srgb, ${diag ? 'var(--color-ok)' : cs[3]} ${Math.round(8 + (v / max) * 52)}%, transparent)`;
        cell.title = `${de} em ${a} → ${para} em ${b2}: ${v}`;
      });
    });
    htmlEl('div', 'px-legend', 'Linhas: classe na primeira combinação. Colunas: classe na segunda. A diagonal (verde) é quem não mudou.', el).style.marginTop = '10px';
  }

  // ---------- RQ 08b: direção das tendências -----------------------------------------------------------------------------------------------------------
  function seg(el) {
    const r = rows(el.dataset.source);
    if (!placeholder(el, !!r)) return;
    el.replaceChildren();
    const by = Object.fromEntries(r.map((x) => [x.metrica, x]));
    const nm = { cfr_a: 'CFR de CI (a)', recuperacao_h: 'Tempo de recuperação' };
    const cs = colors();
    const box = htmlEl('div', 'px-seg', null, el);
    const ok = 'var(--color-ok)', bad = 'var(--color-bad)', mut = 'var(--px-chart-muted)';
    [['cfr_a', ''], ['cfr_a', '_holm'], ['recuperacao_h', ''], ['recuperacao_h', '_holm']].forEach(([m, suf]) => {
      const x = by[m]; const n = N(x.testados);
      const row = htmlEl('div', 'row', null, box);
      htmlEl('div', null, `${nm[m]}${suf ? ' · com Holm' : ''}`, row);
      const st = htmlEl('div', 'st', null, row);
      [['melhora', x['melhora' + suf], ok], ['sem_tendencia', x['sem_tendencia' + suf], mut], ['piora', x['piora' + suf], bad]].forEach(([k, v, c]) => {
        const sp = htmlEl('span', null, N(v) > 0 && N(v) / n > 0.04 ? FMT.int(N(v)) : '', st);
        sp.style.width = (N(v) / n) * 100 + '%'; sp.style.background = c;
        sp.title = `${k.replace('_', ' ')}: ${FMT.int(N(v))} de ${FMT.int(n)} (${FMT.pct1(N(v) / n)})`;
      });
    });
    const lg = htmlEl('div', 'px-legend', null, el);
    [['melhora', ok], ['sem tendência', mut], ['piora', bad]].forEach(([l, c]) => { const s = htmlEl('span', null, null, lg); const i = htmlEl('i', null, null, s); i.style.background = c; s.appendChild(document.createTextNode(l)); });
    lg.style.marginTop = '10px';
  }

  const CHARTS = { hist, scatter, bars, funnel, classes: classesC1, dots, lineband, cols, metricchange: metricChange, heat, seg };
  function drawChart(el) { const f = CHARTS[el.dataset.chart]; if (f) f(el); }

  // ---------- abas ----------------------------------------------------------------------------------------------------------------------------------------------
  const tabs = Array.from(document.querySelectorAll('.px-tab'));
  const host = document.getElementById('px-pages');
  function page(id) {
    let p = document.getElementById('pg-' + id);
    if (!p) {
      const tpl = document.getElementById('tpl-' + id);
      p = document.createElement('section');
      p.className = 'px-page'; p.id = 'pg-' + id; p.hidden = true;
      p.appendChild(tpl.content.cloneNode(true));
      host.appendChild(p);
      p.querySelectorAll('[data-go]').forEach((b) => b.addEventListener('click', () => show(b.dataset.go)));
    }
    return p;
  }
  function show(id) {
    if (!document.getElementById('tpl-' + id)) id = 'geral';
    const p = page(id);
    host.querySelectorAll('.px-page').forEach((x) => { x.hidden = x !== p; });
    tabs.forEach((t) => t.setAttribute('aria-selected', String(t.dataset.tab === id)));
    try { dash.setLink(id); } catch (e) { /* fora do painel */ }
    render();
    window.scrollTo({ top: 0 });
  }
  function render() {
    const cur = host.querySelector('.px-page:not([hidden])');
    if (!cur) return;
    fillMarks(document.querySelector('.px'));
    cur.querySelectorAll('[data-chart]').forEach(drawChart);
  }
  tabs.forEach((t) => t.addEventListener('click', () => show(t.dataset.tab)));
  tabs.forEach((t) => t.addEventListener('keydown', (ev) => {
    const i = tabs.indexOf(t);
    if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') { const n = tabs[(i + (ev.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; n.focus(); ev.preventDefault(); }
  }));
  dash.onData(render);
  window.addEventListener('hashchange', () => { const id = location.hash.replace('#', ''); if (id) show(id); });
  const first = (location.hash || '').replace('#', '');
  show(first || 'geral');
})();
