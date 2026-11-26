package labexp.semente.adapter.in.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import labexp.semente.domain.Papel;
import org.springframework.http.MediaType;
import org.springframework.web.servlet.HandlerInterceptor;

public class PapelInterceptor implements HandlerInterceptor {

    static final String CABECALHO = "X-Papel";

    static Papel papelDe(HttpServletRequest req) {
        return Papel.de(req.getHeader(CABECALHO));
    }

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) throws Exception {
        if (!restrita(req) || papelDe(req).podeAlterarTarefas()) {
            return true;
        }
        res.setStatus(HttpServletResponse.SC_FORBIDDEN);
        res.setContentType(MediaType.APPLICATION_JSON_VALUE);
        res.setCharacterEncoding("UTF-8");
        res.getWriter().write("{\"erro\":\"proibido\",\"mensagem\":\"apenas gestores podem executar esta operacao\"}");
        return false;
    }

    private static boolean restrita(HttpServletRequest req) {
        String metodo = req.getMethod();
        String caminho = req.getRequestURI();
        if ("POST".equals(metodo)) {
            return caminho.equals("/tarefas") || caminho.equals("/tarefas/importacao");
        }
        return ("PUT".equals(metodo) || "DELETE".equals(metodo)) && caminho.matches("/tarefas/[^/]+");
    }
}
