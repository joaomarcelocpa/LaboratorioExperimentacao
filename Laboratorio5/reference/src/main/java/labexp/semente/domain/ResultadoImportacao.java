package labexp.semente.domain;

import java.util.List;

public record ResultadoImportacao(int importadas, List<ErroLinha> erros) {

    public record ErroLinha(int linha, String motivo) {
    }
}
