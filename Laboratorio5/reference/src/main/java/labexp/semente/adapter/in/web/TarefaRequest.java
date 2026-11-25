package labexp.semente.adapter.in.web;

import java.time.Instant;
import labexp.semente.application.port.in.DadosTarefa;

public record TarefaRequest(String titulo, String descricao, String responsavel, Instant vencimento) {

    DadosTarefa paraDados() {
        return new DadosTarefa(titulo, descricao, responsavel, vencimento);
    }
}
