package labexp.semente.adapter.out.persistence;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import labexp.semente.application.port.out.IdempotenciaRepositorio.Registro;

@Entity
@Table(name = "chave_idempotencia")
class IdempotenciaEntity {

    @Id
    private String chave;

    private String impressao;

    @Column(name = "tarefa_id")
    private UUID tarefaId;

    protected IdempotenciaEntity() {
    }

    static IdempotenciaEntity de(Registro r) {
        IdempotenciaEntity e = new IdempotenciaEntity();
        e.chave = r.chave();
        e.impressao = r.impressao();
        e.tarefaId = r.tarefaId();
        return e;
    }

    Registro paraRegistro() {
        return new Registro(chave, impressao, tarefaId);
    }
}
