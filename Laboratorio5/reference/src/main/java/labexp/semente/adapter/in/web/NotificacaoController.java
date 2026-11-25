package labexp.semente.adapter.in.web;

import java.util.Map;
import java.util.UUID;
import labexp.semente.application.port.in.ConsultarNotificacao;
import labexp.semente.application.port.in.ReenviarNotificacao;
import labexp.semente.domain.StatusNotificacao;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class NotificacaoController {

    private final ConsultarNotificacao consultar;
    private final ReenviarNotificacao reenviar;

    public NotificacaoController(ConsultarNotificacao consultar, ReenviarNotificacao reenviar) {
        this.consultar = consultar;
        this.reenviar = reenviar;
    }

    @GetMapping("/tarefas/{id}/notificacao")
    public Map<String, String> status(@PathVariable UUID id) {
        return corpo(consultar.notificacao(id));
    }

    @PostMapping("/tarefas/{id}/notificacao/reenviar")
    public Map<String, String> reenviar(@PathVariable UUID id) {
        return corpo(reenviar.reenviar(id));
    }

    private static Map<String, String> corpo(StatusNotificacao s) {
        return Map.of("status", s.name().toLowerCase());
    }
}
