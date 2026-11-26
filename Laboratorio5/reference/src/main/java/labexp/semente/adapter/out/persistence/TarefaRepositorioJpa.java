package labexp.semente.adapter.out.persistence;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.domain.Tarefa;
import org.springframework.stereotype.Component;

@Component
class TarefaRepositorioJpa implements TarefaRepositorio {

    private final TarefaJpaRepository jpa;

    TarefaRepositorioJpa(TarefaJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Tarefa salvar(Tarefa tarefa) {
        return jpa.save(TarefaEntity.de(tarefa)).paraDominio();
    }

    @Override
    public Optional<Tarefa> buscar(UUID id) {
        return jpa.findById(id).map(TarefaEntity::paraDominio);
    }

    @Override
    public List<Tarefa> listar() {
        return jpa.findAllByOrderByCriadaEmAscIdAsc().stream().map(TarefaEntity::paraDominio).toList();
    }

    @Override
    public boolean excluir(UUID id) {
        if (!jpa.existsById(id)) {
            return false;
        }
        jpa.deleteById(id);
        return true;
    }
}
