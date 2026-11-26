package labexp.semente.adapter.out.persistence;

import java.util.Optional;
import java.util.UUID;
import labexp.semente.application.port.out.NotificacaoRepositorio;
import labexp.semente.domain.StatusNotificacao;
import org.springframework.stereotype.Component;

@Component
class NotificacaoRepositorioJpa implements NotificacaoRepositorio {

    private final NotificacaoJpaRepository jpa;

    NotificacaoRepositorioJpa(NotificacaoJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public void salvar(UUID tarefaId, StatusNotificacao status) {
        jpa.save(NotificacaoEntity.de(tarefaId, status));
    }

    @Override
    public Optional<StatusNotificacao> buscar(UUID tarefaId) {
        return jpa.findById(tarefaId).map(NotificacaoEntity::status);
    }
}
