package labexp.semente.adapter.out.persistence;

import java.util.List;
import labexp.semente.application.port.out.AvisoRepositorio;
import labexp.semente.domain.Aviso;
import labexp.semente.domain.ContextoEmpresa;
import org.springframework.stereotype.Component;

@Component
class AvisoRepositorioJpa implements AvisoRepositorio {

    private final AvisoJpaRepository jpa;

    AvisoRepositorioJpa(AvisoJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public void salvar(Aviso aviso) {
        jpa.save(AvisoEntity.de(aviso));
    }

    @Override
    public List<Aviso> listar() {
        return jpa.findByEmpresaOrderByCriadoEmAscTarefaIdAsc(ContextoEmpresa.atual()).stream()
                .map(AvisoEntity::paraDominio).toList();
    }
}
