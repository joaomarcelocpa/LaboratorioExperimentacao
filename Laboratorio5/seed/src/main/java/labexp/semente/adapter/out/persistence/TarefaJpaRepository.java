package labexp.semente.adapter.out.persistence;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface TarefaJpaRepository extends JpaRepository<TarefaEntity, UUID> {

    List<TarefaEntity> findAllByOrderByCriadaEmAscIdAsc();
}
