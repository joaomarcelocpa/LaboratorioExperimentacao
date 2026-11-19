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

function mostrarErro(mensagem) {
  erro.textContent = mensagem || '';
  erro.hidden = !mensagem;
}

function paraLocal(iso) {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

async function chamar(metodo, url, corpo) {
  const opcoes = { method: metodo, headers: {} };
  if (corpo) {
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
  acoes.append(
    botao('Editar', 'botao-editar', 'secundario', async () => iniciarEdicao(t)),
    botao('Concluir', 'botao-concluir', 'secundario', () => chamar('POST', `${API}/${t.id}/concluir`)),
    botao('Excluir', 'botao-excluir', 'perigo', async () => {
      await chamar('DELETE', `${API}/${t.id}`);
      if (editando === t.id) limparFormulario();
    }),
  );
  li.append(acoes);
  return li;
}

async function carregar() {
  const tarefas = await chamar('GET', API);
  lista.replaceChildren(...tarefas.map(desenhar));
}

form.addEventListener('submit', (evento) => {
  evento.preventDefault();
  executar(async () => {
    const corpo = lerFormulario();
    if (editando) await chamar('PUT', `${API}/${editando}`, corpo);
    else await chamar('POST', API, corpo);
    limparFormulario();
  });
});

cancelar.addEventListener('click', limparFormulario);

carregar().catch((e) => mostrarErro(e.message));
