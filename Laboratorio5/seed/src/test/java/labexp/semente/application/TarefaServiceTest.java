package labexp.semente.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.application.port.in.DadosTarefa;
import labexp.semente.application.port.in.TarefaNaoEncontradaException;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.application.service.TarefaService;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;
import labexp.semente.domain.TarefaInvalidaException;
import org.junit.jupiter.api.Test;

class TarefaServiceTest {

    private static final Instant VENC = Instant.parse("2026-12-01T15:00:00Z");

    static class RepositorioEmMemoria implements TarefaRepositorio {
        final List<Tarefa> tarefas = new ArrayList<>();

        public Tarefa salvar(Tarefa t) {
            tarefas.removeIf(x -> x.id().equals(t.id()));
            tarefas.add(t);
            return t;
        }

        public Optional<Tarefa> buscar(UUID id) {
            return tarefas.stream().filter(x -> x.id().equals(id)).findFirst();
        }

        public List<Tarefa> listar() {
            return tarefas.stream()
                    .sorted(Comparator.comparing(Tarefa::criadaEm).thenComparing(Tarefa::id))
                    .toList();
        }

        public boolean excluir(UUID id) {
            return tarefas.removeIf(x -> x.id().equals(id));
        }
    }

    private final RepositorioEmMemoria repo = new RepositorioEmMemoria();
    private final TarefaService servico = new TarefaService(repo);

    private Tarefa criar(String titulo) {
        return servico.criar(new DadosTarefa(titulo, null, "ana", VENC));
    }

    @Test
    void criaESalva() {
        Tarefa t = criar("Pagar");
        assertEquals(t, repo.buscar(t.id()).orElseThrow());
    }

    @Test
    void listaNaOrdemDeCriacao() throws InterruptedException {
        Tarefa a = criar("a");
        Thread.sleep(2);
        Tarefa b = criar("b");
        assertEquals(List.of(a, b), servico.listar());
    }

    @Test
    void consultaInexistenteLancaNaoEncontrada() {
        assertThrows(TarefaNaoEncontradaException.class, () -> servico.consultar(UUID.randomUUID()));
    }

    @Test
    void atualizaCamposEditaveisSemMudarStatus() {
        Tarefa t = criar("a");
        Tarefa concluida = servico.concluir(t.id());
        Tarefa a = servico.atualizar(t.id(), new DadosTarefa("novo", "d", "bia", VENC.plusSeconds(1)));
        assertEquals("novo", a.titulo());
        assertEquals("bia", a.responsavel());
        assertEquals(concluida.status(), a.status());
    }

    @Test
    void atualizarInexistenteLancaNaoEncontrada() {
        assertThrows(TarefaNaoEncontradaException.class,
                () -> servico.atualizar(UUID.randomUUID(), new DadosTarefa("x", null, "ana", VENC)));
    }

    @Test
    void concluiTarefa() {
        Tarefa t = criar("a");
        assertEquals(StatusTarefa.CONCLUIDA, servico.concluir(t.id()).status());
    }

    @Test
    void concluirDuasVezesNaoMuda() {
        Tarefa t = criar("a");
        assertEquals(servico.concluir(t.id()), servico.concluir(t.id()));
    }

    @Test
    void concluirInexistenteLancaNaoEncontrada() {
        assertThrows(TarefaNaoEncontradaException.class, () -> servico.concluir(UUID.randomUUID()));
    }

    @Test
    void excluiEDepoisLancaNaoEncontrada() {
        Tarefa t = criar("a");
        servico.excluir(t.id());
        assertEquals(0, repo.tarefas.size());
        assertThrows(TarefaNaoEncontradaException.class, () -> servico.excluir(t.id()));
    }

    @Test
    void criarComTituloVazioPropagaTarefaInvalida() {
        assertThrows(TarefaInvalidaException.class, () -> criar(" "));
    }
}
