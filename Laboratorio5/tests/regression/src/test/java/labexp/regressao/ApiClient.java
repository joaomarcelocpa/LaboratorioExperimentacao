package labexp.regressao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

final class ApiClient {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    record Resposta(int status, String corpo) {
        JsonNode json() {
            try {
                return MAPPER.readTree(corpo);
            } catch (Exception e) {
                throw new IllegalStateException("corpo nao e JSON: " + corpo, e);
            }
        }

        String id() {
            return json().get("id").asText();
        }
    }

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
    private final String base;

    ApiClient(String base) {
        this.base = base;
    }

    Resposta enviar(String metodo, String caminho, String corpo) {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + caminho)).timeout(Duration.ofSeconds(30));
        if (corpo == null) {
            b.method(metodo, HttpRequest.BodyPublishers.noBody());
        } else {
            b.header("Content-Type", "application/json").method(metodo, HttpRequest.BodyPublishers.ofString(corpo));
        }
        try {
            HttpResponse<String> r = http.send(b.build(), HttpResponse.BodyHandlers.ofString());
            return new Resposta(r.statusCode(), r.body());
        } catch (Exception e) {
            throw new IllegalStateException("falha chamando " + metodo + " " + caminho, e);
        }
    }

    static String corpo(String titulo, String descricao, String responsavel, String vencimento) {
        ObjectNode n = MAPPER.createObjectNode();
        n.put("titulo", titulo);
        if (descricao != null) {
            n.put("descricao", descricao);
        }
        n.put("responsavel", responsavel);
        if (vencimento != null) {
            n.put("vencimento", vencimento);
        }
        return n.toString();
    }

    Resposta criar(String titulo, String responsavel, String vencimento) {
        return enviar("POST", "/tarefas", corpo(titulo, null, responsavel, vencimento));
    }

    Resposta listar() {
        return enviar("GET", "/tarefas", null);
    }

    Resposta consultar(String id) {
        return enviar("GET", "/tarefas/" + id, null);
    }

    Resposta atualizar(String id, String titulo, String responsavel, String vencimento) {
        return enviar("PUT", "/tarefas/" + id, corpo(titulo, null, responsavel, vencimento));
    }

    Resposta concluir(String id) {
        return enviar("POST", "/tarefas/" + id + "/concluir", null);
    }

    Resposta excluir(String id) {
        return enviar("DELETE", "/tarefas/" + id, null);
    }
}
