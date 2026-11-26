package labexp.semente.adapter.out.persistence;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface HistoricoJpaRepository extends JpaRepository<HistoricoEntity, Long> {

    List<HistoricoEntity> findByTarefaIdOrderByIdDesc(UUID tarefaId);
}
