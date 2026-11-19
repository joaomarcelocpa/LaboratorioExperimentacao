package labexp.semente.application.port.in;

import java.util.List;
import labexp.semente.domain.Tarefa;

public interface ListarTarefas {
    List<Tarefa> listar();
}
