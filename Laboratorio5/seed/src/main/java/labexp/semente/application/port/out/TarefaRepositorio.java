package labexp.semente.application.port.out;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.domain.Tarefa;

public interface TarefaRepositorio {
    Tarefa salvar(Tarefa tarefa);

    Optional<Tarefa> buscar(UUID id);

    List<Tarefa> listar();

    boolean excluir(UUID id);
}
