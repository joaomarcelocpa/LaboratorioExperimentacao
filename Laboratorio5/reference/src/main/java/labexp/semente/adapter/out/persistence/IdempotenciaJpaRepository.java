package labexp.semente.adapter.out.persistence;

import org.springframework.data.jpa.repository.JpaRepository;

interface IdempotenciaJpaRepository extends JpaRepository<IdempotenciaEntity, String> {
}
