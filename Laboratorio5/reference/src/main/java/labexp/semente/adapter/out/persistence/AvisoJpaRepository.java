package labexp.semente.adapter.out.persistence;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface AvisoJpaRepository extends JpaRepository<AvisoEntity, UUID> {

    List<AvisoEntity> findByEmpresaOrderByCriadoEmAscTarefaIdAsc(String empresa);
}
