package labexp.semente.adapter.in.web;

import java.util.List;
import java.util.UUID;
import labexp.semente.application.port.in.ConsultarHistorico;
import labexp.semente.domain.AlteracaoTarefa;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HistoricoController {

    public record AlteracaoResponse(String campo, String valorAnterior, String valorNovo, String timestamp) {
        static AlteracaoResponse de(AlteracaoTarefa a) {
            return new AlteracaoResponse(a.campo(), a.valorAnterior(), a.valorNovo(), a.momento().toString());
        }
    }

    private final ConsultarHistorico consultar;

    public HistoricoController(ConsultarHistorico consultar) {
        this.consultar = consultar;
    }

    @GetMapping("/tarefas/{id}/historico")
    public List<AlteracaoResponse> historico(@PathVariable UUID id) {
        return consultar.historico(id).stream().map(AlteracaoResponse::de).toList();
    }
}
