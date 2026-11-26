package labexp.semente.application.port.out;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.domain.FiltroTarefas;
import labexp.semente.domain.Tarefa;

public interface TarefaRepositorio {
    Tarefa salvar(Tarefa tarefa);

    Optional<Tarefa> buscar(UUID id);

    List<Tarefa> listar();

    List<Tarefa> listar(FiltroTarefas filtro);

    /** Insercao em lote de tarefas novas. */
    void inserir(List<Tarefa> tarefas);

    List<Tarefa> pendentesVencidasAte(Instant instante);

    boolean excluir(UUID id);
}
