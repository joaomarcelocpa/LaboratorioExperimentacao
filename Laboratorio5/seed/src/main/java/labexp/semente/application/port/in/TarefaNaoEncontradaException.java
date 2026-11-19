package labexp.semente.application.port.in;

import java.util.UUID;

public final class TarefaNaoEncontradaException extends RuntimeException {

    public TarefaNaoEncontradaException(UUID id) {
        super("tarefa " + id + " nao encontrada");
    }
}
