package labexp.semente.adapter.in.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PapelController {

    @GetMapping("/papel")
    public Map<String, String> papel(HttpServletRequest req) {
        return Map.of("papel", PapelInterceptor.papelDe(req).name().toLowerCase());
    }
}
