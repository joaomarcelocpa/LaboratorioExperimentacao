package labexp.semente.adapter.out.persistence;

import java.util.List;
import java.util.UUID;
import labexp.semente.application.port.out.HistoricoRepositorio;
import labexp.semente.domain.AlteracaoTarefa;
import org.springframework.stereotype.Component;

@Component
class HistoricoRepositorioJpa implements HistoricoRepositorio {

    private final HistoricoJpaRepository jpa;

    HistoricoRepositorioJpa(HistoricoJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public void registrar(List<AlteracaoTarefa> alteracoes) {
        jpa.saveAll(alteracoes.stream().map(HistoricoEntity::de).toList());
    }

    @Override
    public List<AlteracaoTarefa> listar(UUID tarefaId) {
        return jpa.findByTarefaIdOrderByIdDesc(tarefaId).stream().map(HistoricoEntity::paraDominio).toList();
    }
}
