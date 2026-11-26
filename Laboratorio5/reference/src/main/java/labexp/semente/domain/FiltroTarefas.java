package labexp.semente.domain;

public record FiltroTarefas(StatusTarefa status, String responsavel, boolean ordenarPorVencimento) {

    public static final FiltroTarefas NENHUM = new FiltroTarefas(null, null, false);
}
