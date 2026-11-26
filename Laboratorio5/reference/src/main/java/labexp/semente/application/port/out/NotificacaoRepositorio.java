package labexp.semente.application.port.out;

import java.util.Optional;
import java.util.UUID;
import labexp.semente.domain.StatusNotificacao;

public interface NotificacaoRepositorio {
    void salvar(UUID tarefaId, StatusNotificacao status);

    Optional<StatusNotificacao> buscar(UUID tarefaId);
}
