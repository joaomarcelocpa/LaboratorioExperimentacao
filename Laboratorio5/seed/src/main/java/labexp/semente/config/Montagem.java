package labexp.semente.config;

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
    TarefaService tarefaService(TarefaRepositorio repositorio) {
        return new TarefaService(repositorio);
    }
}
