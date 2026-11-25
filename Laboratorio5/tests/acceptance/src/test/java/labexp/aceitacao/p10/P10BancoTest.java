package labexp.aceitacao.p10;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;
import labexp.aceitacao.ApiClient.Resposta;
import labexp.aceitacao.Base;
import org.junit.jupiter.api.Test;

/**
 * P10: troca de banco. Os testes so usam HTTP, entao valem para qualquer banco. Qual banco esta ativo e
 * decidido por quem sobe a aplicacao (perfil h2 ou DATABASE_URL do PostgreSQL), nunca pelo teste: o mesmo
 * conjunto roda nos dois cenarios e o criterio "a suite inteira passa no perfil h2" e verificado rodando
 * P5 a P9 (e a regressao) com a aplicacao nesse perfil.
 */
class P10BancoTest extends Base {

    @Test
    void aplicacaoIniciaComH2SemErro() {
        Resposta saude = api.get("/health");
        assertEquals(200, saude.status(), saude.corpo());
        assertEquals(200, api.listar().status(), "a aplicacao responde as operacoes de tarefa");
    }

    @Test
    void crudCompletoFuncionaComH2() {
        String resp = responsavelUnico();
        Resposta criada = api.criar("Ciclo", resp, FUTURO);
        assertEquals(201, criada.status(), criada.corpo());
        assertEquals("PENDENTE", criada.json().get("status").asText());
        String id = criada.id();

        assertTrue(StreamSupport.stream(api.listar().json().spliterator(), false)
                .anyMatch(t -> t.get("id").asText().equals(id)));
        Resposta lida = api.consultar(id);
        assertEquals(200, lida.status());
        assertEquals(FUTURO, lida.json().get("vencimento").asText(), "vencimento preserva o instante");

        Resposta atualizada = api.atualizar(id, "Ciclo 2", resp, "2099-12-02T15:00:00Z");
        assertEquals(200, atualizada.status());
        assertEquals("Ciclo 2", atualizada.json().get("titulo").asText());

        Resposta concluida = api.concluir(id);
        assertEquals(200, concluida.status());
        assertEquals("CONCLUIDA", concluida.json().get("status").asText());

        assertEquals(204, api.excluir(id).status());
        assertEquals(404, api.consultar(id).status());
    }

    @Test
    void cargaEmParaleloPersisteTudo() {
        String resp = responsavelUnico();
        List<Callable<String>> cargas = new ArrayList<>();
        for (int i = 0; i < 40; i++) {
            String titulo = "carga-" + i;
            cargas.add(() -> {
                Resposta r = api.criar(titulo, resp, FUTURO);
                assertEquals(201, r.status(), r.corpo());
                return r.id();
            });
        }
        Set<String> criados = Set.copyOf(emParalelo(cargas));
        assertEquals(40, criados.size());

        Set<String> listados = StreamSupport.stream(api.listar().json().spliterator(), false)
                .filter(t -> t.get("responsavel").asText().equals(resp))
                .map(t -> t.get("id").asText())
                .collect(Collectors.toSet());
        assertEquals(criados, listados);
    }
}
