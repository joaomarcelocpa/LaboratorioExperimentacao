package labexp.semente.adapter.out.persistence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import labexp.semente.domain.AlteracaoTarefa;

@Entity
@Table(name = "historico_tarefa")
class HistoricoEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tarefa_id")
    private UUID tarefaId;

    private String campo;

    @Column(name = "valor_anterior")
    private String valorAnterior;

    @Column(name = "valor_novo")
    private String valorNovo;

    private Instant momento;

    protected HistoricoEntity() {
    }

    static HistoricoEntity de(AlteracaoTarefa a) {
        HistoricoEntity e = new HistoricoEntity();
        e.tarefaId = a.tarefaId();
        e.campo = a.campo();
        e.valorAnterior = a.valorAnterior();
        e.valorNovo = a.valorNovo();
        e.momento = a.momento();
        return e;
    }

    AlteracaoTarefa paraDominio() {
        return new AlteracaoTarefa(tarefaId, campo, valorAnterior, valorNovo, momento);
    }
}
