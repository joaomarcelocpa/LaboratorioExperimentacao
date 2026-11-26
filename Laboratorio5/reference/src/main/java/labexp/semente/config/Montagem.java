package labexp.semente.config;

import labexp.semente.application.port.out.AvisoRepositorio;
import labexp.semente.application.port.out.HistoricoRepositorio;
import labexp.semente.application.port.out.IdempotenciaRepositorio;
import labexp.semente.application.port.out.NotificacaoRepositorio;
import labexp.semente.application.port.out.NotificadorExterno;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.application.service.TarefaService;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@Configuration
@EntityScan("labexp.semente.adapter.out.persistence")
@EnableJpaRepositories("labexp.semente.adapter.out.persistence")
public class Montagem {

    @Bean
    TarefaService tarefaService(TarefaRepositorio repositorio, HistoricoRepositorio historico,
            IdempotenciaRepositorio idempotencia, NotificacaoRepositorio notificacoes,
            NotificadorExterno notificador, AvisoRepositorio avisos) {
        return new TarefaService(repositorio, historico, idempotencia, notificacoes, notificador, avisos);
    }
}
