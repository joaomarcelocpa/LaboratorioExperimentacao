package labexp.semente.adapter.in.web;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import labexp.semente.domain.ContextoEmpresa;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Fixa a empresa da requisicao a partir de X-Empresa; sem o cabecalho vale a empresa padrao. */
@Component
class EmpresaFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        ContextoEmpresa.definir(req.getHeader("X-Empresa"));
        try {
            chain.doFilter(req, res);
        } finally {
            ContextoEmpresa.limpar();
        }
    }
}
