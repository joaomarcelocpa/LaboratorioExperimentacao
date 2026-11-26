package labexp.semente.application.port.in;

import java.util.UUID;
import labexp.semente.domain.StatusNotificacao;

public interface ReenviarNotificacao {
    StatusNotificacao reenviar(UUID tarefaId);
}
