package labexp.aceitacao;

import com.fasterxml.jackson.databind.JsonNode;
import java.text.Normalizer;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Leitura tolerante de JSON. Os pedidos fixam o que deve aparecer (campo, valor anterior, contadores...)
 * mas nao os nomes das propriedades; os testes nao podem exigir um formato que o texto nao define.
 */
public final class Json {

    private Json() {
    }

    public static String normalizar(String s) {
        String semAcento = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        return semAcento.toLowerCase().replaceAll("[^a-z0-9]", "");
    }

    /** Primeiro campo (nesta ordem de apelidos) presente no objeto. */
    public static Optional<JsonNode> campo(JsonNode objeto, String... apelidos) {
        for (String apelido : apelidos) {
            for (Iterator<Map.Entry<String, JsonNode>> it = objeto.fields(); it.hasNext();) {
                var e = it.next();
                if (normalizar(e.getKey()).equals(normalizar(apelido))) {
                    return Optional.of(e.getValue());
                }
            }
        }
        return Optional.empty();
    }

    /** Campo cuja chave contem algum dos trechos (ex.: "anterior", "antigo"). */
    public static Optional<JsonNode> campoContendo(JsonNode objeto, String... trechos) {
        for (Iterator<Map.Entry<String, JsonNode>> it = objeto.fields(); it.hasNext();) {
            var e = it.next();
            String chave = normalizar(e.getKey());
            for (String trecho : trechos) {
                if (chave.contains(trecho)) {
                    return Optional.of(e.getValue());
                }
            }
        }
        return Optional.empty();
    }

    public static String texto(JsonNode n) {
        return n == null || n.isNull() ? null : n.asText();
    }

    /** A lista pode vir pura ou embrulhada em um objeto ({"historico":[...]}). */
    public static List<JsonNode> itens(JsonNode raiz) {
        if (raiz.isArray()) {
            List<JsonNode> r = new ArrayList<>();
            raiz.forEach(r::add);
            return r;
        }
        if (raiz.isObject()) {
            for (Iterator<JsonNode> it = raiz.elements(); it.hasNext();) {
                JsonNode filho = it.next();
                if (filho.isArray()) {
                    return itens(filho);
                }
            }
        }
        throw new AssertionError("esperava uma lista JSON, veio: " + raiz);
    }

    public static Instant instante(JsonNode n) {
        if (n == null || n.isNull()) {
            throw new AssertionError("timestamp ausente");
        }
        if (n.isNumber()) {
            long v = n.asLong();
            return v > 100_000_000_000L ? Instant.ofEpochMilli(v) : Instant.ofEpochSecond(v);
        }
        String s = n.asText().strip();
        try {
            return Instant.parse(s);
        } catch (Exception ignorado) {
            // tenta outros formatos ISO
        }
        try {
            return OffsetDateTime.parse(s).toInstant();
        } catch (Exception ignorado) {
            // tenta sem deslocamento
        }
        try {
            return LocalDateTime.parse(s).toInstant(ZoneOffset.UTC);
        } catch (Exception e) {
            throw new AssertionError("timestamp nao reconhecido: " + s);
        }
    }

    public static boolean pareceTimestamp(JsonNode n) {
        try {
            instante(n);
            return n.isNumber() || n.asText().matches("\\d{4}-\\d{2}-\\d{2}.*");
        } catch (AssertionError e) {
            return false;
        }
    }

    /**
     * Procura um contador pelo nome em qualquer nivel: {"pendentes":5}, {"porStatus":{"PENDENTE":5}}
     * ou [{"status":"PENDENTE","total":5}]. Uma lista conta pelo tamanho.
     */
    public static Optional<Long> contador(JsonNode raiz, String... apelidos) {
        ArrayDeque<JsonNode> fila = new ArrayDeque<>();
        fila.add(raiz);
        while (!fila.isEmpty()) {
            JsonNode atual = fila.poll();
            if (atual.isObject()) {
                var direto = campo(atual, apelidos);
                if (direto.isPresent() && valorContavel(direto.get()).isPresent()) {
                    return valorContavel(direto.get());
                }
                var rotulado = rotuloComNumero(atual, apelidos);
                if (rotulado.isPresent()) {
                    return rotulado;
                }
                atual.elements().forEachRemaining(fila::add);
            } else if (atual.isArray()) {
                atual.elements().forEachRemaining(fila::add);
            }
        }
        return Optional.empty();
    }

    private static Optional<Long> valorContavel(JsonNode v) {
        if (v.isIntegralNumber()) {
            return Optional.of(v.asLong());
        }
        if (v.isArray()) {
            return Optional.of((long) v.size());
        }
        return Optional.empty();
    }

    private static Optional<Long> rotuloComNumero(JsonNode objeto, String[] apelidos) {
        for (Iterator<JsonNode> it = objeto.elements(); it.hasNext();) {
            JsonNode valor = it.next();
            if (valor.isTextual()) {
                for (String apelido : apelidos) {
                    if (normalizar(valor.asText()).equals(normalizar(apelido))) {
                        return primeiroNumero(objeto);
                    }
                }
            }
        }
        return Optional.empty();
    }

    private static Optional<Long> primeiroNumero(JsonNode objeto) {
        var preferido = campo(objeto, "total", "quantidade", "qtd", "count", "contagem", "tarefas", "totalTarefas");
        if (preferido.isPresent() && preferido.get().isIntegralNumber()) {
            return Optional.of(preferido.get().asLong());
        }
        for (Iterator<JsonNode> it = objeto.elements(); it.hasNext();) {
            JsonNode v = it.next();
            if (v.isIntegralNumber()) {
                return Optional.of(v.asLong());
            }
        }
        return Optional.empty();
    }

    /** Total de tarefas de um responsavel, em {"ana":3} ou [{"responsavel":"ana","total":3}]. */
    public static Optional<Long> totalDoResponsavel(JsonNode raiz, String responsavel) {
        ArrayDeque<JsonNode> fila = new ArrayDeque<>();
        fila.add(raiz);
        while (!fila.isEmpty()) {
            JsonNode atual = fila.poll();
            if (atual.isObject()) {
                JsonNode porChave = atual.get(responsavel);
                if (porChave != null) {
                    var n = porChave.isIntegralNumber() ? Optional.of(porChave.asLong())
                            : porChave.isObject() ? primeiroNumero(porChave) : Optional.<Long>empty();
                    if (n.isPresent()) {
                        return n;
                    }
                }
                for (Iterator<JsonNode> it = atual.elements(); it.hasNext();) {
                    JsonNode v = it.next();
                    if (v.isTextual() && v.asText().equals(responsavel)) {
                        var n = primeiroNumero(atual);
                        if (n.isPresent()) {
                            return n;
                        }
                    }
                }
                atual.elements().forEachRemaining(fila::add);
            } else if (atual.isArray()) {
                atual.elements().forEachRemaining(fila::add);
            }
        }
        return Optional.empty();
    }
}
