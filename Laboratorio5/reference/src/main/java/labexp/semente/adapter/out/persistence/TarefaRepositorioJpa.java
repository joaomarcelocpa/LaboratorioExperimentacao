package labexp.semente.adapter.out.persistence;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import labexp.semente.application.port.out.TarefaRepositorio;
import labexp.semente.domain.ContextoEmpresa;
import labexp.semente.domain.FiltroTarefas;
import labexp.semente.domain.StatusTarefa;
import labexp.semente.domain.Tarefa;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
class TarefaRepositorioJpa implements TarefaRepositorio {

    private static final int LOTE = 500;

    private final TarefaJpaRepository jpa;

    @PersistenceContext
    private EntityManager em;

    TarefaRepositorioJpa(TarefaJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Tarefa salvar(Tarefa tarefa) {
        return jpa.save(TarefaEntity.de(tarefa)).paraDominio();
    }

    @Override
    public Optional<Tarefa> buscar(UUID id) {
        return jpa.findByIdAndEmpresa(id, ContextoEmpresa.atual()).map(TarefaEntity::paraDominio);
    }

    @Override
    public List<Tarefa> listar() {
        return jpa.findAllByEmpresaOrderByCriadaEmAscIdAsc(ContextoEmpresa.atual()).stream()
                .map(TarefaEntity::paraDominio).toList();
    }

    @Override
    public List<Tarefa> listar(FiltroTarefas f) {
        if (f == null || (f.status() == null && f.responsavel() == null && !f.ordenarPorVencimento())) {
            return listar();
        }
        String empresa = ContextoEmpresa.atual();
        Specification<TarefaEntity> spec = (root, q, cb) -> {
            List<jakarta.persistence.criteria.Predicate> p = new ArrayList<>();
            p.add(cb.equal(root.get("empresa"), empresa));
            if (f.status() != null) {
                p.add(cb.equal(root.get("status"), f.status()));
            }
            if (f.responsavel() != null) {
                p.add(cb.equal(root.get("responsavel"), f.responsavel()));
            }
            return cb.and(p.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
        Sort ordem = f.ordenarPorVencimento() ? Sort.by("vencimento", "id") : Sort.by("criadaEm", "id");
        return jpa.findAll(spec, ordem).stream().map(TarefaEntity::paraDominio).toList();
    }

    @Override
    @Transactional
    public void inserir(List<Tarefa> tarefas) {
        int n = 0;
        for (Tarefa t : tarefas) {
            em.persist(TarefaEntity.de(t));
            if (++n % LOTE == 0) {
                em.flush();
                em.clear();
            }
        }
        em.flush();
        em.clear();
    }

    @Override
    public List<Tarefa> pendentesVencidasAte(Instant instante) {
        return jpa.findByEmpresaAndStatusAndVencimentoBefore(ContextoEmpresa.atual(), StatusTarefa.PENDENTE, instante)
                .stream().map(TarefaEntity::paraDominio).toList();
    }

    @Override
    public boolean excluir(UUID id) {
        if (!jpa.existsByIdAndEmpresa(id, ContextoEmpresa.atual())) {
            return false;
        }
        jpa.deleteById(id);
        return true;
    }
}
