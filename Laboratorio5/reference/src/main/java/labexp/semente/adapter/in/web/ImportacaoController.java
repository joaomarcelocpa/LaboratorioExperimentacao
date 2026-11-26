package labexp.semente.adapter.in.web;

import java.nio.charset.StandardCharsets;
import java.util.List;
import labexp.semente.application.port.in.ImportarTarefas;
import labexp.semente.domain.ResultadoImportacao;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ImportacaoController {

    public record ErroResponse(int linha, String motivo) {
    }

    public record ImportacaoResponse(int importadas, int totalErros, List<ErroResponse> erros) {
    }

    private final ImportarTarefas importar;

    public ImportacaoController(ImportarTarefas importar) {
        this.importar = importar;
    }

    @PostMapping("/tarefas/importacao")
    public ImportacaoResponse importar(@RequestBody byte[] corpo) {
        ResultadoImportacao r = importar.importar(new String(corpo, StandardCharsets.UTF_8));
        List<ErroResponse> erros = r.erros().stream().map(e -> new ErroResponse(e.linha(), e.motivo())).toList();
        return new ImportacaoResponse(r.importadas(), erros.size(), erros);
    }
}
