package labexp.semente.adapter.out.persistence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;

@Entity
@Table(name = "tarefa")
class TarefaEntity {

    @Id
    private UUID id;
    private String titulo;
    private String descricao;
    private String responsavel;
    private Instant vencimento;

    @Enumerated(EnumType.STRING)
    private StatusTarefa status;

    @Column(name = "criada_em")
    private Instant criadaEm;

    protected TarefaEntity() {
    }

    static TarefaEntity de(Tarefa t) {
        TarefaEntity e = new TarefaEntity();
        e.id = t.id();
        e.titulo = t.titulo();
        e.descricao = t.descricao();
        e.responsavel = t.responsavel();
        e.vencimento = t.vencimento();
        e.status = t.status();
        e.criadaEm = t.criadaEm();
        return e;
    }

    Tarefa paraDominio() {
        return new Tarefa(id, titulo, descricao, responsavel, vencimento, status, criadaEm);
    }
}
