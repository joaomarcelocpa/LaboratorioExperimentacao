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
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
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
    public ResponseEntity<TarefaResponse> criar(@RequestBody TarefaRequest req) {
        TarefaResponse r = TarefaResponse.de(criar.criar(req.paraDados()));
        return ResponseEntity.created(URI.create("/tarefas/" + r.id())).body(r);
    }

    @GetMapping
    public List<TarefaResponse> listar() {
        return listar.listar().stream().map(TarefaResponse::de).toList();
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
