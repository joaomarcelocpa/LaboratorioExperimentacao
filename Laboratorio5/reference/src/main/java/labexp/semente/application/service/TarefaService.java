package labexp.semente.application.service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.stream.Collectors;
import labexp.semente.application.port.in.AtualizarTarefa;
import labexp.semente.application.port.in.ConcluirTarefa;
import labexp.semente.application.port.in.ConflitoIdempotenciaException;
import labexp.semente.application.port.in.ConsultarHistorico;
import labexp.semente.application.port.in.ConsultarNotificacao;
import labexp.semente.application.port.in.ConsultarTarefa;
import labexp.semente.application.port.in.CriarTarefa;
import labexp.semente.application.port.in.DadosTarefa;
import labexp.semente.application.port.in.ExcluirTarefa;
import labexp.semente.application.port.in.GerarRelatorio;
import labexp.semente.application.port.in.ListarTarefas;
import labexp.semente.application.port.in.ReenviarNotificacao;
import labexp.semente.application.port.in.TarefaNaoEncontradaException;
import labexp.semente.application.port.out.HistoricoRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio.Registro;
import labexp.semente.application.port.out.NotificacaoRepositorio;
import labexp.semente.application.port.out.NotificadorExterno;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.domain.AlteracaoTarefa;
import labexp.semente.domain.Relatorio;
import labexp.semente.domain.StatusNotificacao;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;

public final class TarefaService implements CriarTarefa, ListarTarefas, ConsultarTarefa,
        AtualizarTarefa, ConcluirTarefa, ExcluirTarefa, ConsultarHistorico, GerarRelatorio,
        ConsultarNotificacao, ReenviarNotificacao {

    private final TarefaRepositorio repositorio;
    private final HistoricoRepositorio historico;
    private final IdempotenciaRepositorio idempotencia;
    private final NotificacaoRepositorio notificacoes;
    private final NotificadorExterno notificador;
    private final Object travaIdempotencia = new Object();

    public TarefaService(TarefaRepositorio repositorio, HistoricoRepositorio historico,
            IdempotenciaRepositorio idempotencia, NotificacaoRepositorio notificacoes,
            NotificadorExterno notificador) {
        this.repositorio = repositorio;
        this.historico = historico;
        this.idempotencia = idempotencia;
        this.notificacoes = notificacoes;
        this.notificador = notificador;
    }

    @Override
    public Tarefa criar(DadosTarefa d, String chave) {
        if (chave == null || chave.isBlank()) {
            return criarNova(d);
        }
        synchronized (travaIdempotencia) {
            String impressao = impressao(d);
            var existente = idempotencia.buscar(chave);
            if (existente.isPresent()) {
                if (!existente.get().impressao().equals(impressao)) {
                    throw new ConflitoIdempotenciaException(chave);
                }
                return repositorio.buscar(existente.get().tarefaId()).orElseGet(() -> criarNova(d));
            }
            Tarefa criada = criarNova(d);
            idempotencia.salvar(new Registro(chave, impressao, criada.id()));
            return criada;
        }
    }

    private Tarefa criarNova(DadosTarefa d) {
        return repositorio.salvar(Tarefa.nova(d.titulo(), d.descricao(), d.responsavel(), d.vencimento()));
    }

    private static String impressao(DadosTarefa d) {
        return String.join("\u0001", String.valueOf(d.titulo()), String.valueOf(d.descricao()),
                String.valueOf(d.responsavel()), String.valueOf(d.vencimento()));
    }

    @Override
    public List<Tarefa> listar() {
        return repositorio.listar();
    }

    @Override
    public Tarefa consultar(UUID id) {
        return repositorio.buscar(id).orElseThrow(() -> new TarefaNaoEncontradaException(id));
    }

    @Override
    public Tarefa atualizar(UUID id, DadosTarefa d) {
        Tarefa atual = consultar(id);
        Tarefa nova = atual.atualizada(d.titulo(), d.descricao(), d.responsavel(), d.vencimento());
        Tarefa salva = repositorio.salvar(nova);
        historico.registrar(atual.alteracoesPara(salva, Instant.now()));
        return salva;
    }

    @Override
    public Tarefa concluir(UUID id) {
        Tarefa atual = consultar(id);
        Tarefa nova = atual.concluida();
        if (nova == atual) {
            return atual;
        }
        Tarefa salva = repositorio.salvar(nova);
        historico.registrar(atual.alteracoesPara(salva, Instant.now()));
        notificar(salva);
        return salva;
    }

    private StatusNotificacao notificar(Tarefa concluida) {
        notificacoes.salvar(concluida.id(), StatusNotificacao.PENDENTE);
        boolean enviada;
        try {
            enviada = notificador.notificar(concluida);
        } catch (RuntimeException e) {
            enviada = false;
        }
        StatusNotificacao resultado = enviada ? StatusNotificacao.ENVIADA : StatusNotificacao.FALHOU;
        notificacoes.salvar(concluida.id(), resultado);
        return resultado;
    }

    @Override
    public void excluir(UUID id) {
        if (!repositorio.excluir(id)) {
            throw new TarefaNaoEncontradaException(id);
        }
    }

    @Override
    public List<AlteracaoTarefa> historico(UUID tarefaId) {
        List<AlteracaoTarefa> alteracoes = historico.listar(tarefaId);
        if (alteracoes.isEmpty() && repositorio.buscar(tarefaId).isEmpty()) {
            throw new TarefaNaoEncontradaException(tarefaId);
        }
        return alteracoes;
    }

    @Override
    public Relatorio gerar() {
        List<Tarefa> todas = repositorio.listar();
        Instant agora = Instant.now();
        long pendentes = todas.stream().filter(t -> t.status() == StatusTarefa.PENDENTE).count();
        long concluidas = todas.size() - pendentes;
        List<Tarefa> vencidas = todas.stream()
                .filter(t -> t.status() == StatusTarefa.PENDENTE && t.vencimento().isBefore(agora))
                .toList();
        Map<String, Long> porResponsavel = todas.stream()
                .collect(Collectors.groupingBy(Tarefa::responsavel, TreeMap::new, Collectors.counting()));
        return new Relatorio(pendentes, concluidas, vencidas, porResponsavel);
    }

    @Override
    public StatusNotificacao notificacao(UUID tarefaId) {
        consultar(tarefaId);
        return notificacoes.buscar(tarefaId).orElse(StatusNotificacao.PENDENTE);
    }

    @Override
    public StatusNotificacao reenviar(UUID tarefaId) {
        Tarefa t = consultar(tarefaId);
        StatusNotificacao atual = notificacoes.buscar(tarefaId).orElse(StatusNotificacao.PENDENTE);
        if (t.status() == StatusTarefa.CONCLUIDA && atual == StatusNotificacao.FALHOU) {
            return notificar(t);
        }
        return atual;
    }
}
