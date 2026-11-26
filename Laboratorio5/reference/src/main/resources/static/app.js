const API = '/tarefas';
const form = document.getElementById('form');
const campos = {
  titulo: document.getElementById('titulo'),
  descricao: document.getElementById('descricao'),
  responsavel: document.getElementById('responsavel'),
  vencimento: document.getElementById('vencimento'),
};
const erro = document.getElementById('erro');
const cancelar = document.getElementById('cancelar');
const secao = document.getElementById('form-titulo-secao');
const lista = document.getElementById('lista');

let editando = null;

const campoEmpresa = document.getElementById('empresa');
function empresaInicial() {
  const daUrl = new URLSearchParams(location.search).get('empresa');
  if (daUrl) return daUrl;
  try { return localStorage.getItem('empresa') || ''; } catch (e) { return ''; }
}
let empresa = empresaInicial();
campoEmpresa.value = empresa;
function mudarEmpresa() {
  empresa = campoEmpresa.value.trim();
  try { localStorage.setItem('empresa', empresa); } catch (e) { /* ignora */ }
  carregar().then(carregarAvisos).catch((e) => mostrarErro(e.message));
}
campoEmpresa.addEventListener('change', mudarEmpresa);
campoEmpresa.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') mudarEmpresa(); });

const filtroStatus = document.getElementById('filtro-status');
const filtroResponsavel = document.getElementById('filtro-responsavel');
const ordenarVencimento = document.getElementById('ordenar-vencimento');
for (const c of [filtroStatus, filtroResponsavel, ordenarVencimento]) {
  c.addEventListener('change', () => carregar().catch((e) => mostrarErro(e.message)));
}

const seletorPapel = document.getElementById('papel');
const campoChave = document.getElementById('idempotency-key');
const PAPEIS = ['colaborador', 'gestor'];

function papelInicial() {
  const daUrl = new URLSearchParams(location.search).get('papel');
  if (PAPEIS.includes(daUrl)) return daUrl;
  try {
    const salvo = localStorage.getItem('papel');
    if (PAPEIS.includes(salvo)) return salvo;
  } catch (e) { /* armazenamento indisponivel */ }
  return 'colaborador';
}

let papel = papelInicial();
seletorPapel.value = papel;
const ehGestor = () => papel === 'gestor';

function novaChave() {
  campoChave.value = crypto.randomUUID();
}
novaChave();

seletorPapel.addEventListener('change', () => {
  papel = seletorPapel.value;
  try { localStorage.setItem('papel', papel); } catch (e) { /* ignora */ }
  aplicarPapel();
  
});

function aplicarPapel() {
  form.hidden = !ehGestor();
}

function mostrarErro(mensagem) {
  erro.textContent = mensagem || '';
  erro.hidden = !mensagem;
}

function paraLocal(iso) {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

async function chamar(metodo, url, corpo, extras = {}) {
  const opcoes = { method: metodo, headers: { 'X-Papel': papel, ...(empresa ? { 'X-Empresa': empresa } : {}), ...extras } };
  if (corpo instanceof Blob) {
    opcoes.body = corpo;
  } else if (corpo) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo);
  }
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 204) return null;
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.mensagem || 'erro inesperado');
  return dados;
}

function lerFormulario() {
  const local = campos.vencimento.value;
  return {
    titulo: campos.titulo.value,
    descricao: campos.descricao.value || null,
    responsavel: campos.responsavel.value,
    vencimento: local ? new Date(local).toISOString() : null,
  };
}

function limparFormulario() {
  editando = null;
  form.reset();
  secao.textContent = 'Nova tarefa';
  cancelar.hidden = true;
  mostrarErro('');
}

function iniciarEdicao(t) {
  editando = t.id;
  campos.titulo.value = t.titulo;
  campos.descricao.value = t.descricao || '';
  campos.responsavel.value = t.responsavel;
  campos.vencimento.value = paraLocal(t.vencimento);
  secao.textContent = 'Editar tarefa';
  cancelar.hidden = false;
  mostrarErro('');
}

function elemento(tag, texto, atributos = {}) {
  const e = document.createElement(tag);
  if (texto !== undefined) e.textContent = texto;
  for (const [k, v] of Object.entries(atributos)) e.setAttribute(k, v);
  return e;
}

function botao(rotulo, testid, classe, acao) {
  const b = elemento('button', rotulo, { type: 'button', 'data-testid': testid });
  if (classe) b.className = classe;
  b.addEventListener('click', () => executar(acao));
  return b;
}

async function executar(acao) {
  try {
    await acao();
    await carregar();
  } catch (e) {
    mostrarErro(e.message);
  }
}

function desenhar(t) {
  const li = elemento('li', undefined, { 'data-testid': 'tarefa-item' });
  if (t.status === 'CONCLUIDA') li.className = 'concluida';
  li.append(elemento('div', t.titulo, { class: 'titulo', 'data-testid': 'tarefa-titulo' }));

  const detalhe = elemento('div', undefined, { class: 'detalhe' });
  detalhe.append(
    elemento('span', t.responsavel, { 'data-testid': 'tarefa-responsavel' }),
    ' · ',
    elemento('span', new Date(t.vencimento).toLocaleString('pt-BR'), { 'data-testid': 'tarefa-vencimento' }),
    ' · ',
    elemento('span', t.status, { 'data-testid': 'tarefa-status' }),
  );
  li.append(detalhe);

  const acoes = elemento('div', undefined, { class: 'acoes' });
  if (ehGestor()) {
    acoes.append(botao('Editar', 'botao-editar', 'secundario', async () => iniciarEdicao(t)));
  }
  acoes.append(botao('Concluir', 'botao-concluir', 'secundario', () => chamar('POST', `${API}/${t.id}/concluir`)));
  if (ehGestor()) {
    acoes.append(botao('Excluir', 'botao-excluir', 'perigo', async () => {
      await chamar('DELETE', `${API}/${t.id}`);
      if (editando === t.id) limparFormulario();
    }));
  }
  const historico = elemento('ul', undefined, { 'data-testid': 'historico-tarefa', class: 'historico' });
  historico.hidden = true;
  acoes.append(botao('Histórico', 'botao-historico', 'secundario', async () => {
    if (historico.hidden) await preencherHistorico(historico, t.id);
    historico.hidden = !historico.hidden;
  }));
  li.append(acoes, historico);
  if (t.status === 'CONCLUIDA') li.append(blocoNotificacao(t));
  return li;
}

async function preencherHistorico(ul, id) {
  const entradas = await chamar('GET', `${API}/${id}/historico`);
  ul.replaceChildren(...entradas.map((e) => elemento('li',
    `${new Date(e.timestamp).toLocaleString('pt-BR')} · ${e.campo}: ${e.valorAnterior ?? '—'} → ${e.valorNovo ?? '—'}`,
    { 'data-testid': 'historico-entrada' })));
}

function blocoNotificacao(t) {
  const bloco = elemento('div', 'Notificação: ', { class: 'detalhe' });
  const status = elemento('span', '...', { 'data-testid': 'status-notificacao' });
  const reenviar = botao('Reenviar', 'reenviar-notificacao', 'secundario',
    () => chamar('POST', `${API}/${t.id}/notificacao/reenviar`));
  reenviar.hidden = true;
  bloco.append(status, ' ', reenviar);
  chamar('GET', `${API}/${t.id}/notificacao`).then((r) => {
    status.textContent = r.status;
    reenviar.hidden = r.status !== 'falhou';
  }).catch(() => { status.textContent = 'pendente'; });
  return bloco;
}

async function carregar() {
  const q = new URLSearchParams();
  if (filtroStatus.value) q.set('status', filtroStatus.value);
  if (filtroResponsavel.value.trim()) q.set('responsavel', filtroResponsavel.value.trim());
  if (ordenarVencimento.checked) q.set('ordenar', 'vencimento');
  const tarefas = await chamar('GET', q.toString() ? `${API}?${q}` : API);
  lista.replaceChildren(...tarefas.map(desenhar));
  await carregarRelatorio();
}

async function carregarRelatorio() {
  const r = await chamar('GET', '/relatorio/tarefas');
  const alvo = (id) => document.querySelector(`[data-testid="${id}"]`);
  alvo('relatorio-pendentes').textContent = r.pendentes;
  alvo('relatorio-concluidas').textContent = r.concluidas;
  alvo('relatorio-vencidas').textContent = r.vencidas;
  alvo('relatorio-lista-vencidas').replaceChildren(
    ...r.tarefasVencidas.map((t) => elemento('li', `${t.titulo} (${t.responsavel})`)));
  alvo('distribuicao-responsavel').replaceChildren(
    ...Object.entries(r.porResponsavel).map(([nome, total]) =>
      elemento('div', `${nome}: ${total}`, { 'data-testid': 'distribuicao-item' })));
}

form.addEventListener('submit', (evento) => {
  evento.preventDefault();
  executar(async () => {
    const corpo = lerFormulario();
    if (editando) await chamar('PUT', `${API}/${editando}`, corpo);
    else await chamar('POST', API, corpo, { 'Idempotency-Key': campoChave.value });
    limparFormulario();
    novaChave();
  });
});

cancelar.addEventListener('click', limparFormulario);



async function carregarAvisos() {
  const avisos = await chamar('GET', '/avisos');
  document.getElementById('lista-avisos').replaceChildren(...avisos.map((v) =>
    elemento('li', `${v.titulo} venceu em ${new Date(v.vencidaEm).toLocaleString('pt-BR')}`,
      { 'data-testid': 'aviso-item' })));
}

const resultadoImportacao = document.getElementById('resultado-importacao');
document.getElementById('importar-confirmar').addEventListener('click', async () => {
  const arquivo = document.getElementById('importar-csv').files[0];
  if (!arquivo) { resultadoImportacao.textContent = 'Escolha um arquivo CSV.'; return; }
  resultadoImportacao.textContent = 'Importando...';
  try {
    const r = await chamar('POST', `${API}/importacao`, arquivo, { 'Content-Type': 'text/csv' });
    const linhas = r.erros.map((e) => `Linha ${e.linha}: ${e.motivo}`);
    resultadoImportacao.replaceChildren(
      elemento('p', `${r.importadas} tarefas importadas, ${r.totalErros} linhas com erro.`),
      ...linhas.map((l) => elemento('div', l, { 'data-testid': 'erro-importacao' })));
    await carregar();
  } catch (e) {
    resultadoImportacao.textContent = e.message;
  }
});

aplicarPapel();
carregar().catch((e) => mostrarErro(e.message));
carregarAvisos().catch(() => {});
setInterval(() => carregarAvisos().catch(() => {}), 2000);
