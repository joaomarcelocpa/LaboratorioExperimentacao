package labexp.semente.adapter.out.persistence;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.domain.StatusTarefa;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

interface TarefaJpaRepository extends JpaRepository<TarefaEntity, UUID>, JpaSpecificationExecutor<TarefaEntity> {

    List<TarefaEntity> findAllByEmpresaOrderByCriadaEmAscIdAsc(String empresa);

    Optional<TarefaEntity> findByIdAndEmpresa(UUID id, String empresa);

    boolean existsByIdAndEmpresa(UUID id, String empresa);

    List<TarefaEntity> findByEmpresaAndStatusAndVencimentoBefore(String empresa, StatusTarefa status, Instant limite);
}
