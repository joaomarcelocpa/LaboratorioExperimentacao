package labexp.semente.domain;

public final class TarefaInvalidaException extends RuntimeException {

    public TarefaInvalidaException(String mensagem) {
        super(mensagem);
    }
}
