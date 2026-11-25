package labexp.semente.application.port.out;

import java.util.Optional;
import java.util.UUID;

public interface IdempotenciaRepositorio {

    record Registro(String chave, String impressao, UUID tarefaId) {
    }

    Optional<Registro> buscar(String chave);

    void salvar(Registro registro);
}
