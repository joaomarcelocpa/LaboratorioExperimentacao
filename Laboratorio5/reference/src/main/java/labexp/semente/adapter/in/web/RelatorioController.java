package labexp.semente.adapter.in.web;

import java.util.List;
import java.util.Map;
import labexp.semente.application.port.in.GerarRelatorio;
import labexp.semente.domain.Relatorio;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class RelatorioController {

    public record RelatorioResponse(long pendentes, long concluidas, long vencidas,
            List<TarefaResponse> tarefasVencidas, Map<String, Long> porResponsavel) {
        static RelatorioResponse de(Relatorio r) {
            return new RelatorioResponse(r.pendentes(), r.concluidas(), r.vencidas().size(),
                    r.vencidas().stream().map(TarefaResponse::de).toList(), r.porResponsavel());
        }
    }

    private final GerarRelatorio gerar;

    public RelatorioController(GerarRelatorio gerar) {
        this.gerar = gerar;
    }

    @GetMapping("/relatorio/tarefas")
    public RelatorioResponse relatorio() {
        return RelatorioResponse.de(gerar.gerar());
    }
}
