// Lê os CSVs de data/ e dispara o desenho. Cada conjunto é `data/<id>.csv`; as células chegam como texto.
(function () {
  'use strict';
  const store = {}, falhas = {}, handlers = [];
  function aviso() {
    const raiz = document.getElementById('dash-root');
    const d = document.createElement('p');
    d.className = 'px-aviso';
    d.textContent = 'Não foi possível carregar ' + Object.keys(falhas).length + ' arquivo(s) de dados. ' +
      'Se abriu o index.html direto do disco, sirva a pasta: python -m http.server, dentro de dashboard/.';
    raiz.insertBefore(d, raiz.firstChild);
  }
  const dash = {
    // variáveis CSS, para a paleta acompanhar o tema sem redesenhar
    colors: ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)', 'var(--c6)', 'var(--c7)', 'var(--c8)'],
    data(id) {
      if (store[id]) return { status: 'ok', data: store[id] };
      return { status: falhas[id] ? 'error' : 'loading', data: [] };
    },
    onData(fn) { handlers.push(fn); fn(); },
    setLink(id) { try { history.replaceState(null, '', '#' + id); } catch (e) { /* sem histórico */ } },
    disparar() { handlers.forEach((h) => h()); },
    async carregar(ids) {
      await Promise.all(ids.map(async (id) => {
        try {
          const r = await fetch('data/' + id + '.csv');
          if (!r.ok) throw new Error(String(r.status));
          store[id] = d3.csvParse(await r.text());
        } catch (e) { falhas[id] = String(e); }
      }));
      if (Object.keys(falhas).length) aviso();
      dash.disparar();
    },
  };
  // tema: segue o sistema até o botão forçar um dos dois; a escolha fica no navegador
  function temaAtivo() {
    const t = document.documentElement.getAttribute('data-theme');
    if (t === 'light' || t === 'dark') return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  const botao = document.getElementById('px-theme');
  function rotular() { botao.setAttribute('aria-label', temaAtivo() === 'dark' ? 'Mudar para o tema claro' : 'Mudar para o tema escuro'); }
  if (botao) {
    rotular();
    botao.addEventListener('click', () => {
      const novo = temaAtivo() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', novo);
      try { localStorage.setItem('dashboard-theme', novo); } catch (e) { /* sem armazenamento */ }
      rotular();
    });
  }
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(dash.disparar, 120); });
  window.dash = dash;
})();
