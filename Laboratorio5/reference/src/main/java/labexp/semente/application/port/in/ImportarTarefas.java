package labexp.semente.application.port.in;

import labexp.semente.domain.ResultadoImportacao;

public interface ImportarTarefas {
    ResultadoImportacao importar(String csv);
}
