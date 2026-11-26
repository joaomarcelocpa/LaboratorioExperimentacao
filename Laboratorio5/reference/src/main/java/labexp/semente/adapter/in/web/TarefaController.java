package labexp.semente.adapter.in.web;

import java.net.URI;
import java.util.List;
import java.util.UUID;
import labexp.semente.application.port.in.AtualizarTarefa;
import labexp.semente.application.port.in.ConcluirTarefa;
import labexp.semente.application.port.in.ConsultarTarefa;
import labexp.semente.application.port.in.CriarTarefa;
import labexp.semente.application.port.in.ExcluirTarefa;
import labexp.semente.application.port.in.ListarTarefas;
import labexp.semente.domain.FiltroTarefas;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.TarefaInvalidaException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/tarefas")
public class TarefaController {

    private final CriarTarefa criar;
    private final ListarTarefas listar;
    private final ConsultarTarefa consultar;
    private final AtualizarTarefa atualizar;
    private final ConcluirTarefa concluir;
    private final ExcluirTarefa excluir;

    public TarefaController(CriarTarefa criar, ListarTarefas listar, ConsultarTarefa consultar,
            AtualizarTarefa atualizar, ConcluirTarefa concluir, ExcluirTarefa excluir) {
        this.criar = criar;
        this.listar = listar;
        this.consultar = consultar;
        this.atualizar = atualizar;
        this.concluir = concluir;
        this.excluir = excluir;
    }

    @PostMapping
    public ResponseEntity<TarefaResponse> criar(@RequestBody TarefaRequest req,
            @RequestHeader(value = "Idempotency-Key", required = false) String chave) {
        TarefaResponse r = TarefaResponse.de(criar.criar(req.paraDados(), chave));
        return ResponseEntity.created(URI.create("/tarefas/" + r.id())).body(r);
    }

    @GetMapping
    public List<TarefaResponse> listar(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String responsavel,
            @RequestParam(required = false) String ordenar,
            @RequestParam(required = false) String ordem,
            @RequestParam(required = false) String ordenarPor,
            @RequestParam(required = false) String sort) {
        boolean porVencimento = java.util.stream.Stream.of(ordenar, ordem, ordenarPor, sort)
                .anyMatch(v -> v != null && v.strip().toLowerCase().startsWith("vencimento"));
        FiltroTarefas filtro = new FiltroTarefas(parseStatus(status),
                responsavel == null || responsavel.isBlank() ? null : responsavel.strip(), porVencimento);
        return listar.listar(filtro).stream().map(TarefaResponse::de).toList();
    }

    private static StatusTarefa parseStatus(String valor) {
        if (valor == null || valor.isBlank()) {
            return null;
        }
        String n = java.text.Normalizer.normalize(valor.strip(), java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "").toUpperCase();
        if (n.startsWith("PEND")) {
            return StatusTarefa.PENDENTE;
        }
        if (n.startsWith("CONC")) {
            return StatusTarefa.CONCLUIDA;
        }
        throw new TarefaInvalidaException("status invalido: " + valor);
    }

    @GetMapping("/{id}")
    public TarefaResponse consultar(@PathVariable UUID id) {
        return TarefaResponse.de(consultar.consultar(id));
    }

    @PutMapping("/{id}")
    public TarefaResponse atualizar(@PathVariable UUID id, @RequestBody TarefaRequest req) {
        return TarefaResponse.de(atualizar.atualizar(id, req.paraDados()));
    }

    @PostMapping("/{id}/concluir")
    public TarefaResponse concluir(@PathVariable UUID id) {
        return TarefaResponse.de(concluir.concluir(id));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> excluir(@PathVariable UUID id) {
        excluir.excluir(id);
        return ResponseEntity.noContent().build();
    }
}
