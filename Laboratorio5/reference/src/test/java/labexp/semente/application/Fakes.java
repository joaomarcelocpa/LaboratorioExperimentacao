package labexp.semente.application;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.application.port.out.HistoricoRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio;
import labexp.semente.application.port.out.NotificacaoRepositorio;
import labexp.semente.application.port.out.NotificadorExterno;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.application.service.TarefaService;
import labexp.semente.domain.AlteracaoTarefa;
import labexp.semente.domain.StatusNotificacao;
import labexp.semente.domain.Tarefa;

public final class Fakes {

    private Fakes() {
    }

    public static final class Historico implements HistoricoRepositorio {
        public final List<AlteracaoTarefa> todas = new ArrayList<>();

        public void registrar(List<AlteracaoTarefa> alteracoes) {
            todas.addAll(alteracoes);
        }

        public List<AlteracaoTarefa> listar(UUID tarefaId) {
            List<AlteracaoTarefa> r = new ArrayList<>(todas.stream().filter(a -> a.tarefaId().equals(tarefaId)).toList());
            java.util.Collections.reverse(r);
            return r;
        }
    }

    public static final class Idempotencia implements IdempotenciaRepositorio {
        final Map<String, Registro> registros = new HashMap<>();

        public Optional<Registro> buscar(String chave) {
            return Optional.ofNullable(registros.get(chave));
        }

        public void salvar(Registro r) {
            registros.put(r.chave(), r);
        }
    }

    public static final class Notificacoes implements NotificacaoRepositorio {
        final Map<UUID, StatusNotificacao> status = new HashMap<>();

        public void salvar(UUID id, StatusNotificacao s) {
            status.put(id, s);
        }

        public Optional<StatusNotificacao> buscar(UUID id) {
            return Optional.ofNullable(status.get(id));
        }
    }

    public static final class Notificador implements NotificadorExterno {
        public boolean responde = true;
        public int chamadas;

        public boolean notificar(Tarefa t) {
            chamadas++;
            return responde;
        }
    }

    public static TarefaService servico(TarefaRepositorio repositorio) {
        return new TarefaService(repositorio, new Historico(), new Idempotencia(), new Notificacoes(), new Notificador());
    }
}
