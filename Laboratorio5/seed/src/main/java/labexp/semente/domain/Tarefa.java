package labexp.semente.domain;

import java.time.Instant;
import java.util.UUID;

public record Tarefa(
        UUID id,
        String titulo,
        String descricao,
        String responsavel,
        Instant vencimento,
        StatusTarefa status,
        Instant criadaEm) {

    private static final int MAX_TITULO = 120;
    private static final int MAX_DESCRICAO = 2000;
    private static final int MAX_RESPONSAVEL = 80;

    public Tarefa {
        titulo = obrigatorio(titulo, "titulo", MAX_TITULO);
        responsavel = obrigatorio(responsavel, "responsavel", MAX_RESPONSAVEL);
        if (descricao != null && descricao.length() > MAX_DESCRICAO) {
            throw new TarefaInvalidaException("descricao excede " + MAX_DESCRICAO + " caracteres");
        }
        if (vencimento == null) {
            throw new TarefaInvalidaException("vencimento e obrigatorio");
        }
    }

    public static Tarefa nova(String titulo, String descricao, String responsavel, Instant vencimento) {
        return new Tarefa(UUID.randomUUID(), titulo, descricao, responsavel, vencimento,
                StatusTarefa.PENDENTE, Instant.now());
    }

    public Tarefa atualizada(String titulo, String descricao, String responsavel, Instant vencimento) {
        return new Tarefa(id, titulo, descricao, responsavel, vencimento, status, criadaEm);
    }

    public Tarefa concluida() {
        if (status == StatusTarefa.CONCLUIDA) {
            return this;
        }
        return new Tarefa(id, titulo, descricao, responsavel, vencimento, StatusTarefa.CONCLUIDA, criadaEm);
    }

    private static String obrigatorio(String valor, String campo, int max) {
        if (valor == null || valor.isBlank()) {
            throw new TarefaInvalidaException(campo + " e obrigatorio");
        }
        String limpo = valor.strip();
        if (limpo.length() > max) {
            throw new TarefaInvalidaException(campo + " excede " + max + " caracteres");
        }
        return limpo;
    }
}
