package labexp.semente.application.port.in;

import labexp.semente.domain.Tarefa;

public interface CriarTarefa {
    Tarefa criar(DadosTarefa dados);
}
