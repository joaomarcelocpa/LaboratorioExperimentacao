package labexp.semente.application.port.in;

import java.util.List;
import labexp.semente.domain.FiltroTarefas;
import labexp.semente.domain.Tarefa;

public interface ListarTarefas {
    List<Tarefa> listar(FiltroTarefas filtro);

    default List<Tarefa> listar() {
        return listar(FiltroTarefas.NENHUM);
    }
}
