package labexp.aceitacao;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.AfterEach;

public abstract class Base {

    public static final String BASE_URL = System.getenv().getOrDefault("BASE_URL", "http://localhost:8080");
    public static final String FUTURO = "2099-12-01T15:00:00Z";
    public static final String PASSADO = "2020-01-01T00:00:00Z";

    /** Carga e limpeza sempre como gestor: o papel padrao pode ser restrito (P6). */
    protected final ApiClient api = ApiClient.comPapel(BASE_URL, "gestor");

    private final Set<String> responsaveis = Collections.synchronizedSet(new HashSet<>());

    protected String responsavelUnico() {
        String r = "r-" + UUID.randomUUID();
        responsaveis.add(r);
        return r;
    }

    protected String tituloUnico(String prefixo) {
        return prefixo + "-" + UUID.randomUUID();
    }

    /** Carga em paralelo pelos endpoints existentes, conforme o contrato de execucao. */
    protected static <T> List<T> emParalelo(List<Callable<T>> tarefas) {
        ExecutorService pool = Executors.newFixedThreadPool(8);
        try {
            List<Future<T>> futuros = pool.invokeAll(tarefas);
            return futuros.stream().map(f -> {
                try {
                    return f.get();
                } catch (InterruptedException | ExecutionException e) {
                    throw new IllegalStateException(e);
                }
            }).toList();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        } finally {
            pool.shutdown();
        }
    }

    /** Apaga todas as tarefas visiveis. So para testes que exigem a base vazia. */
    protected void esvaziarBase() {
        List<Callable<Integer>> exclusoes = new java.util.ArrayList<>();
        for (var t : api.listar().json()) {
            String id = t.get("id").asText();
            exclusoes.add(() -> api.excluir(id).status());
        }
        emParalelo(exclusoes);
    }

    @AfterEach
    void limpar() {
        List<Callable<Integer>> exclusoes = new java.util.ArrayList<>();
        for (var t : api.listar().json()) {
            if (responsaveis.contains(t.get("responsavel").asText())) {
                String id = t.get("id").asText();
                exclusoes.add(() -> api.excluir(id).status());
            }
        }
        emParalelo(exclusoes);
    }
}
