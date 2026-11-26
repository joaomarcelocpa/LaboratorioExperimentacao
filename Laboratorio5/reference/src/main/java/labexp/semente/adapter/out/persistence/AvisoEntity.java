package labexp.semente.adapter.out.persistence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import labexp.semente.domain.Aviso;
import labexp.semente.domain.ContextoEmpresa;

@Entity
@Table(name = "aviso")
class AvisoEntity {

    @Id
    @Column(name = "tarefa_id")
    private UUID tarefaId;

    private String empresa;
    private String titulo;

    @Column(name = "vencida_em")
    private Instant vencidaEm;

    @Column(name = "criado_em")
    private Instant criadoEm;

    protected AvisoEntity() {
    }

    static AvisoEntity de(Aviso a) {
        AvisoEntity e = new AvisoEntity();
        e.tarefaId = a.tarefaId();
        e.empresa = ContextoEmpresa.atual();
        e.titulo = a.titulo();
        e.vencidaEm = a.vencidaEm();
        e.criadoEm = a.criadoEm();
        return e;
    }

    Aviso paraDominio() {
        return new Aviso(tarefaId, titulo, vencidaEm, criadoEm);
    }
}
