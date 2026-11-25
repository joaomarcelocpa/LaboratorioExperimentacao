package labexp.semente.adapter.in.web;

import labexp.semente.domain.Tarefa;

public record TarefaResponse(
        String id,
        String titulo,
        String descricao,
        String responsavel,
        String vencimento,
        String status,
        String criadaEm) {

    static TarefaResponse de(Tarefa t) {
        return new TarefaResponse(t.id().toString(), t.titulo(), t.descricao(), t.responsavel(),
                t.vencimento().toString(), t.status().name(), t.criadaEm().toString());
    }
}
