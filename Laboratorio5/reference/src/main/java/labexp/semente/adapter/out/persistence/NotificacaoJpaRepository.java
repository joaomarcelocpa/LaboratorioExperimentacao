package labexp.semente.adapter.out.persistence;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface NotificacaoJpaRepository extends JpaRepository<NotificacaoEntity, UUID> {
}
