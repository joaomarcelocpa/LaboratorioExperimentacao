package labexp.regressao;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

/**
 * Desde P6 a tela comeca como colaborador, que nao ve o formulario nem editar/excluir. A regressao precisa do
 * gestor para exercitar os comportamentos anteriores. Antes de P6 nao ha campo de papel e nada muda.
 */
final class PapelNaTela {

    private PapelNaTela() {
    }

    static void comoGestorSeExistir(Page page) {
        Locator campo = page.getByTestId("papel-usuario");
        if (campo.count() == 0) {
            return;
        }
        if (ehGestor(campo)) {
            return;
        }
        String base = page.url().replaceAll("[?#].*$", "");
        page.navigate(base + "?papel=gestor");
        if (ehGestor(page.getByTestId("papel-usuario"))) {
            return;
        }
        String tag = (String) campo.evaluate("e => e.tagName.toLowerCase()");
        if (tag.equals("select")) {
            campo.selectOption("gestor");
        } else if (tag.equals("input") || tag.equals("textarea")) {
            campo.fill("gestor");
            campo.press("Enter");
        }
    }

    private static boolean ehGestor(Locator campo) {
        String tag = (String) campo.evaluate("e => e.tagName.toLowerCase()");
        String valor = switch (tag) {
            case "input", "textarea", "select" -> campo.inputValue();
            default -> campo.innerText();
        };
        return valor.strip().equalsIgnoreCase("gestor");
    }
}
