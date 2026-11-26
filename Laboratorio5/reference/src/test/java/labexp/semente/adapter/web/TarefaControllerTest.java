package labexp.semente.adapter.web;

import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.adapter.in.web.TarefaController;
import labexp.semente.adapter.in.web.TratadorDeErros;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.application.service.TarefaService;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class TarefaControllerTest {

    static class RepositorioEmMemoria implements TarefaRepositorio {
        final List<Tarefa> tarefas = new ArrayList<>();

        public Tarefa salvar(Tarefa t) {
            tarefas.removeIf(x -> x.id().equals(t.id()));
            tarefas.add(t);
            return t;
        }

        public Optional<Tarefa> buscar(UUID id) {
            return tarefas.stream().filter(x -> x.id().equals(id)).findFirst();
        }

        public List<Tarefa> listar() {
            return List.copyOf(tarefas);
        }

        public List<Tarefa> listar(labexp.semente.domain.FiltroTarefas f) {
            return listar().stream()
                    .filter(t -> f.status() == null || t.status() == f.status())
                    .filter(t -> f.responsavel() == null || t.responsavel().equals(f.responsavel()))
                    .sorted(f.ordenarPorVencimento() ? Comparator.comparing(Tarefa::vencimento) : (a, b) -> 0)
                    .toList();
        }

        public void inserir(List<Tarefa> novas) {
            tarefas.addAll(novas);
        }

        public List<Tarefa> pendentesVencidasAte(java.time.Instant limite) {
            return tarefas.stream().filter(t -> t.status() == StatusTarefa.PENDENTE && t.vencimento().isBefore(limite)).toList();
        }

        public boolean excluir(UUID id) {
            return tarefas.removeIf(x -> x.id().equals(id));
        }
    }

    private static final String VALIDO =
            "{\"titulo\":\"Pagar\",\"responsavel\":\"ana\",\"vencimento\":\"2026-12-01T15:00:00Z\"}";

    private final ObjectMapper json = new ObjectMapper();
    private MockMvc mvc;

    @BeforeEach
    void preparar() {
        TarefaService s = labexp.semente.application.Fakes.servico(new RepositorioEmMemoria());
        mvc = MockMvcBuilders.standaloneSetup(new TarefaController(s, s, s, s, s, s))
                .setControllerAdvice(new TratadorDeErros())
                .build();
    }

    private ResultActions enviar(String metodo, String url, String corpo) throws Exception {
        var req = switch (metodo) {
            case "POST" -> post(url);
            case "PUT" -> put(url);
            default -> throw new IllegalArgumentException(metodo);
        };
        return mvc.perform(req.contentType(MediaType.APPLICATION_JSON).content(corpo));
    }

    private String criarEObterId() throws Exception {
        String corpo = enviar("POST", "/tarefas", VALIDO).andReturn().getResponse().getContentAsString();
        JsonNode n = json.readTree(corpo);
        return n.get("id").asText();
    }

    private void erro400(ResultActions r) throws Exception {
        r.andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.erro").value("requisicao_invalida"))
                .andExpect(jsonPath("$.mensagem", notNullValue()));
    }

    @Test
    void postValidoDevolve201ComLocation() throws Exception {
        var r = enviar("POST", "/tarefas", VALIDO)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("PENDENTE"))
                .andReturn().getResponse();
        String id = json.readTree(r.getContentAsString()).get("id").asText();
        assertTrue(r.getHeader("Location").endsWith("/tarefas/" + id));
    }

    @Test
    void postTituloSoEspacosDevolve400() throws Exception {
        erro400(enviar("POST", "/tarefas",
                "{\"titulo\":\"   \",\"responsavel\":\"ana\",\"vencimento\":\"2026-12-01T15:00:00Z\"}"));
    }

    @Test
    void postJsonMalformadoDevolve400() throws Exception {
        erro400(enviar("POST", "/tarefas", "{nao e json"));
    }

    @Test
    void postCorpoVazioDevolve400() throws Exception {
        erro400(mvc.perform(post("/tarefas").contentType(MediaType.APPLICATION_JSON)));
    }

    @Test
    void postVencimentoInvalidoDevolve400() throws Exception {
        erro400(enviar("POST", "/tarefas",
                "{\"titulo\":\"t\",\"responsavel\":\"ana\",\"vencimento\":\"amanha\"}"));
    }

    @Test
    void vencimentoComOffsetEhNormalizadoParaUtc() throws Exception {
        enviar("POST", "/tarefas",
                "{\"titulo\":\"t\",\"responsavel\":\"ana\",\"vencimento\":\"2026-12-01T12:00:00-03:00\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.vencimento").value("2026-12-01T15:00:00Z"));
    }

    @Test
    void getIdMalformadoDevolve404() throws Exception {
        mvc.perform(get("/tarefas/nao-e-uuid"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.erro").value("nao_encontrada"));
    }

    @Test
    void getInexistenteDevolve404() throws Exception {
        mvc.perform(get("/tarefas/" + UUID.randomUUID()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.mensagem", notNullValue()));
    }

    @Test
    void putAtualizaEDevolve200() throws Exception {
        String id = criarEObterId();
        enviar("PUT", "/tarefas/" + id,
                "{\"titulo\":\"novo\",\"responsavel\":\"bia\",\"vencimento\":\"2026-12-02T15:00:00Z\"}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.titulo").value("novo"))
                .andExpect(jsonPath("$.status").value("PENDENTE"));
    }

    @Test
    void concluirDevolve200ComStatusConcluida() throws Exception {
        String id = criarEObterId();
        mvc.perform(post("/tarefas/" + id + "/concluir"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CONCLUIDA"));
    }

    @Test
    void deleteDevolve204ESegundaVezDevolve404() throws Exception {
        String id = criarEObterId();
        mvc.perform(delete("/tarefas/" + id)).andExpect(status().isNoContent());
        mvc.perform(delete("/tarefas/" + id)).andExpect(status().isNotFound());
    }
}
