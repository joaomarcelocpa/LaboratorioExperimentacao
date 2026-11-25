package labexp.semente.adapter.out.persistence;

import java.util.Optional;
import labexp.semente.application.port.out.IdempotenciaRepositorio;
import org.springframework.stereotype.Component;

@Component
class IdempotenciaRepositorioJpa implements IdempotenciaRepositorio {

    private final IdempotenciaJpaRepository jpa;

    IdempotenciaRepositorioJpa(IdempotenciaJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Optional<Registro> buscar(String chave) {
        return jpa.findById(chave).map(IdempotenciaEntity::paraRegistro);
    }

    @Override
    public void salvar(Registro registro) {
        jpa.save(IdempotenciaEntity.de(registro));
    }
}
