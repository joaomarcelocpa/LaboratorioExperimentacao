package labexp.semente.application.service;

import java.util.List;
import java.util.UUID;
import labexp.semente.application.port.in.AtualizarTarefa;
import labexp.semente.application.port.in.ConcluirTarefa;
import labexp.semente.application.port.in.ConsultarTarefa;
import labexp.semente.application.port.in.CriarTarefa;
import labexp.semente.application.port.in.DadosTarefa;
import labexp.semente.application.port.in.ExcluirTarefa;
import labexp.semente.application.port.in.ListarTarefas;
import labexp.semente.application.port.in.TarefaNaoEncontradaException;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.domain.Tarefa;

public final class TarefaService implements CriarTarefa, ListarTarefas, ConsultarTarefa,
        AtualizarTarefa, ConcluirTarefa, ExcluirTarefa {

    private final TarefaRepositorio repositorio;

    public TarefaService(TarefaRepositorio repositorio) {
        this.repositorio = repositorio;
    }

    @Override
    public Tarefa criar(DadosTarefa d) {
        return repositorio.salvar(Tarefa.nova(d.titulo(), d.descricao(), d.responsavel(), d.vencimento()));
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
        return repositorio.salvar(atual.atualizada(d.titulo(), d.descricao(), d.responsavel(), d.vencimento()));
    }

    @Override
    public Tarefa concluir(UUID id) {
        return repositorio.salvar(consultar(id).concluida());
    }

    @Override
    public void excluir(UUID id) {
        if (!repositorio.excluir(id)) {
            throw new TarefaNaoEncontradaException(id);
        }
    }
}
