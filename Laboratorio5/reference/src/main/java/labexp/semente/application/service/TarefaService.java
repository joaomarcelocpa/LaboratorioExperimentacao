package labexp.semente.application.service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.Set;
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
import labexp.semente.application.port.in.ImportarTarefas;
import labexp.semente.application.port.in.ListarAvisos;
import labexp.semente.application.port.in.ListarTarefas;
import labexp.semente.application.port.in.ReenviarNotificacao;
import labexp.semente.application.port.in.TarefaNaoEncontradaException;
import labexp.semente.application.port.out.AvisoRepositorio;
import labexp.semente.application.port.out.HistoricoRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio.Registro;
import labexp.semente.application.port.out.NotificacaoRepositorio;
import labexp.semente.application.port.out.NotificadorExterno;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.domain.AlteracaoTarefa;
import labexp.semente.domain.Aviso;
import labexp.semente.domain.FiltroTarefas;
import labexp.semente.domain.ResultadoImportacao;
import labexp.semente.domain.ResultadoImportacao.ErroLinha;
import labexp.semente.domain.Relatorio;
import labexp.semente.domain.StatusNotificacao;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;
import labexp.semente.domain.TarefaInvalidaException;

public final class TarefaService implements CriarTarefa, ListarTarefas, ConsultarTarefa,
        AtualizarTarefa, ConcluirTarefa, ExcluirTarefa, ConsultarHistorico, GerarRelatorio,
        ConsultarNotificacao, ReenviarNotificacao, ListarAvisos, ImportarTarefas {

    private final TarefaRepositorio repositorio;
    private final HistoricoRepositorio historico;
    private final IdempotenciaRepositorio idempotencia;
    private final NotificacaoRepositorio notificacoes;
    private final NotificadorExterno notificador;
    private final AvisoRepositorio avisos;
    private final Object travaIdempotencia = new Object();
    private final Object travaAvisos = new Object();

    public TarefaService(TarefaRepositorio repositorio, HistoricoRepositorio historico,
            IdempotenciaRepositorio idempotencia, NotificacaoRepositorio notificacoes,
            NotificadorExterno notificador, AvisoRepositorio avisos) {
        this.repositorio = repositorio;
        this.historico = historico;
        this.idempotencia = idempotencia;
        this.notificacoes = notificacoes;
        this.notificador = notificador;
        this.avisos = avisos;
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
    public List<Tarefa> listar(FiltroTarefas filtro) {
        return repositorio.listar(filtro);
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

    @Override
    public List<Aviso> avisos() {
        synchronized (travaAvisos) {
            Instant agora = Instant.now();
            Set<java.util.UUID> comAviso = avisos.listar().stream().map(Aviso::tarefaId).collect(Collectors.toSet());
            for (Tarefa t : repositorio.pendentesVencidasAte(agora)) {
                if (!comAviso.contains(t.id())) {
                    avisos.salvar(new Aviso(t.id(), t.titulo(), t.vencimento(), agora));
                }
            }
            return avisos.listar();
        }
    }

    @Override
    public ResultadoImportacao importar(String csv) {
        List<Tarefa> validas = new ArrayList<>();
        List<ErroLinha> erros = new ArrayList<>();
        String[] linhas = csv.split("\\r?\\n", -1);
        int iTitulo = 0;
        int iResponsavel = 1;
        int iVencimento = 2;
        int inicio = 0;
        if (linhas.length > 0) {
            List<String> cab = campos(linhas[0]).stream().map(TarefaService::normalizar).toList();
            if (cab.contains("titulo") && cab.contains("responsavel") && cab.contains("vencimento")) {
                iTitulo = cab.indexOf("titulo");
                iResponsavel = cab.indexOf("responsavel");
                iVencimento = cab.indexOf("vencimento");
                inicio = 1;
            }
        }
        Set<Integer> usados = new HashSet<>(List.of(iTitulo, iResponsavel, iVencimento));
        for (int i = inicio; i < linhas.length; i++) {
            if (linhas[i].isBlank()) {
                continue;
            }
            List<String> c = campos(linhas[i]);
            int numero = i + 1;
            if (c.size() <= Math.max(Math.max(iTitulo, iResponsavel), iVencimento) || usados.size() != 3) {
                erros.add(new ErroLinha(numero, "numero de colunas invalido"));
                continue;
            }
            try {
                String venc = c.get(iVencimento).strip();
                if (venc.isEmpty()) {
                    throw new TarefaInvalidaException("vencimento e obrigatorio");
                }
                Instant vencimento;
                try {
                    vencimento = Instant.parse(venc);
                } catch (java.time.format.DateTimeParseException e) {
                    throw new TarefaInvalidaException("vencimento fora do formato: " + venc);
                }
                validas.add(Tarefa.nova(c.get(iTitulo), null, c.get(iResponsavel), vencimento));
            } catch (TarefaInvalidaException e) {
                erros.add(new ErroLinha(numero, e.getMessage()));
            }
        }
        repositorio.inserir(validas);
        return new ResultadoImportacao(validas.size(), erros);
    }

    private static String normalizar(String s) {
        return java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "").strip().toLowerCase();
    }

    /** Divide uma linha CSV (virgula ou ponto e virgula), com aspas simples. */
    private static List<String> campos(String linha) {
        char sep = linha.indexOf(';') >= 0 && linha.indexOf(',') < 0 ? ';' : ',';
        List<String> r = new ArrayList<>();
        StringBuilder atual = new StringBuilder();
        boolean aspas = false;
        for (int i = 0; i < linha.length(); i++) {
            char ch = linha.charAt(i);
            if (ch == '"') {
                if (aspas && i + 1 < linha.length() && linha.charAt(i + 1) == '"') {
                    atual.append('"');
                    i++;
                } else {
                    aspas = !aspas;
                }
            } else if (ch == sep && !aspas) {
                r.add(atual.toString());
                atual.setLength(0);
            } else {
                atual.append(ch);
            }
        }
        r.add(atual.toString());
        return r;
    }
}
