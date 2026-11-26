package labexp.semente.application.port.in;

import java.util.List;
import java.util.UUID;
import labexp.semente.domain.AlteracaoTarefa;

public interface ConsultarHistorico {
    List<AlteracaoTarefa> historico(UUID tarefaId);
}
