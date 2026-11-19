package labexp.regressao;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;

abstract class Base {

    static final String BASE_URL = System.getenv().getOrDefault("BASE_URL", "http://localhost:8080");
    static final String VENCIMENTO = "2026-12-01T15:00:00Z";

    final ApiClient api = new ApiClient(BASE_URL);
    private final Set<String> responsaveis = new HashSet<>();

    String responsavelUnico() {
        String r = "r-" + UUID.randomUUID();
        responsaveis.add(r);
        return r;
    }

    @AfterEach
    void limpar() {
        for (var t : api.listar().json()) {
            if (responsaveis.contains(t.get("responsavel").asText())) {
                api.excluir(t.get("id").asText());
            }
        }
    }
}
