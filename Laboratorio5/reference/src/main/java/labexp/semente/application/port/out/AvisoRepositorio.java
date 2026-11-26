package labexp.semente.application.port.out;

import java.util.List;
import labexp.semente.domain.Aviso;

public interface AvisoRepositorio {
    void salvar(Aviso aviso);

    List<Aviso> listar();
}
