package labexp.semente.adapter.out.persistence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import labexp.semente.domain.StatusNotificacao;

@Entity
@Table(name = "notificacao_tarefa")
class NotificacaoEntity {

    @Id
    @Column(name = "tarefa_id")
    private UUID tarefaId;

    @Enumerated(EnumType.STRING)
    private StatusNotificacao status;

    protected NotificacaoEntity() {
    }

    static NotificacaoEntity de(UUID tarefaId, StatusNotificacao status) {
        NotificacaoEntity e = new NotificacaoEntity();
        e.tarefaId = tarefaId;
        e.status = status;
        return e;
    }

    StatusNotificacao status() {
        return status;
    }
}
