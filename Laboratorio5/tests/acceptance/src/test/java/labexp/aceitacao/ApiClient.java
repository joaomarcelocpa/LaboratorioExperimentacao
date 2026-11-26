package labexp.aceitacao;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/** Cliente HTTP minimo: so o contrato publico dos pedidos, nada da estrutura interna. */
public final class ApiClient {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();

    public record Resposta(int status, String corpo, long milissegundos) {
        public JsonNode json() {
            try {
                return MAPPER.readTree(corpo);
            } catch (Exception e) {
                throw new IllegalStateException("corpo nao e JSON (status " + status + "): " + corpo, e);
            }
        }

        public String id() {
            return json().get("id").asText();
        }
    }

    private final String base;
    private final String papel;

    private ApiClient(String base, String papel) {
        this.base = base;
        this.papel = papel;
    }

    /** Papel nulo significa "sem o cabecalho X-Papel". */
    public static ApiClient comPapel(String base, String papel) {
        return new ApiClient(base, papel);
    }

    public ApiClient papel(String novoPapel) {
        return new ApiClient(base, novoPapel);
    }

    public Resposta enviar(String metodo, String caminho, String corpo) {
        return enviar(metodo, caminho, corpo, Map.of());
    }

    public Resposta enviar(String metodo, String caminho, String corpo, Map<String, String> cabecalhos) {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + caminho)).timeout(Duration.ofSeconds(30));
        Map<String, String> todos = new LinkedHashMap<>();
        if (papel != null) {
            todos.put("X-Papel", papel);
        }
        todos.putAll(cabecalhos);
        todos.forEach(b::header);
        if (corpo == null) {
            b.method(metodo, HttpRequest.BodyPublishers.noBody());
        } else {
            b.header("Content-Type", "application/json").method(metodo, HttpRequest.BodyPublishers.ofString(corpo));
        }
        long inicio = System.nanoTime();
        try {
            HttpResponse<String> r = HTTP.send(b.build(), HttpResponse.BodyHandlers.ofString());
            return new Resposta(r.statusCode(), r.body(), (System.nanoTime() - inicio) / 1_000_000);
        } catch (Exception e) {
            throw new IllegalStateException("falha chamando " + metodo + " " + caminho, e);
        }
    }

    public static String corpo(String titulo, String descricao, String responsavel, String vencimento) {
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

    public Resposta criar(String titulo, String responsavel, String vencimento) {
        return enviar("POST", "/tarefas", corpo(titulo, null, responsavel, vencimento));
    }

    public Resposta criarComChave(String chave, String titulo, String responsavel, String vencimento) {
        return enviar("POST", "/tarefas", corpo(titulo, null, responsavel, vencimento),
                Map.of("Idempotency-Key", chave));
    }

    public Resposta listar() {
        return enviar("GET", "/tarefas", null);
    }

    public Resposta consultar(String id) {
        return enviar("GET", "/tarefas/" + id, null);
    }

    public Resposta atualizar(String id, String titulo, String responsavel, String vencimento) {
        return enviar("PUT", "/tarefas/" + id, corpo(titulo, null, responsavel, vencimento));
    }

    public Resposta concluir(String id) {
        return enviar("POST", "/tarefas/" + id + "/concluir", null);
    }

    public Resposta excluir(String id) {
        return enviar("DELETE", "/tarefas/" + id, null);
    }

    public Resposta get(String caminho) {
        return enviar("GET", caminho, null);
    }
}
