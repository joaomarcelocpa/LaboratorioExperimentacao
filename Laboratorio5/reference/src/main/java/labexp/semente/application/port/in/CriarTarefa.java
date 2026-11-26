package labexp.semente.application.port.in;

import labexp.semente.domain.Tarefa;

public interface CriarTarefa {
    Tarefa criar(DadosTarefa dados, String chaveIdempotencia);

    default Tarefa criar(DadosTarefa dados) {
        return criar(dados, null);
    }
}
