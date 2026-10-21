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
    colors: ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3', '#937860', '#DA8BC3', '#8C8C8C'],
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
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(dash.disparar, 120); });
  window.dash = dash;
})();
