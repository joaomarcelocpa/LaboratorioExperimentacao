package labexp.semente.application.port.out;

import labexp.semente.domain.Tarefa;

public interface NotificadorExterno {
    /** Verdadeiro so quando o servico externo confirmou o recebimento dentro do prazo. */
    boolean notificar(Tarefa tarefaConcluida);
}
