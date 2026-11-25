package labexp.semente.adapter.out.notificacao;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import labexp.semente.application.port.out.NotificadorExterno;
import labexp.semente.domain.Tarefa;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
class NotificadorHttp implements NotificadorExterno {

    private static final Duration PRAZO = Duration.ofMillis(500);

    private final String url;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(PRAZO).build();
    private final ObjectMapper json = new ObjectMapper();

    NotificadorHttp(@Value("${notificacao.url:}") String url) {
        this.url = url == null ? "" : url.strip();
    }

    @Override
    public boolean notificar(Tarefa t) {
        if (url.isEmpty()) {
            return false;
        }
        try {
            String corpo = json.writeValueAsString(Map.of(
                    "evento", "tarefa_concluida", "tarefaId", t.id().toString(), "titulo", t.titulo()));
            HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                    .timeout(PRAZO)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(corpo))
                    .build();
            int status = http.send(req, HttpResponse.BodyHandlers.discarding()).statusCode();
            return status >= 200 && status < 300;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        } catch (Exception e) {
            return false;
        }
    }
}
