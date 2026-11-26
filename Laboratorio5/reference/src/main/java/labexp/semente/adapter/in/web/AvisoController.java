package labexp.semente.adapter.in.web;

import java.util.List;
import labexp.semente.application.port.in.ListarAvisos;
import labexp.semente.domain.Aviso;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AvisoController {

    public record AvisoResponse(String tarefaId, String titulo, String vencidaEm, String criadoEm) {
        static AvisoResponse de(Aviso a) {
            return new AvisoResponse(a.tarefaId().toString(), a.titulo(), a.vencidaEm().toString(),
                    a.criadoEm().toString());
        }
    }

    private final ListarAvisos listar;

    public AvisoController(ListarAvisos listar) {
        this.listar = listar;
    }

    @GetMapping("/avisos")
    public List<AvisoResponse> avisos() {
        return listar.avisos().stream().map(AvisoResponse::de).toList();
    }
}
