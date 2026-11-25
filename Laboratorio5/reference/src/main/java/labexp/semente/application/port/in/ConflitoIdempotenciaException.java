package labexp.semente.application.port.in;

public final class ConflitoIdempotenciaException extends RuntimeException {

    public ConflitoIdempotenciaException(String chave) {
        super("a chave de idempotencia " + chave + " ja foi usada com outro conteudo");
    }
}
