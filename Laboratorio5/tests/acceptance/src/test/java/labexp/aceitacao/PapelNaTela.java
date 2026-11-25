package labexp.aceitacao;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

/**
 * P6 fixa o campo {@code papel-usuario} mas nao diz como o usuario troca de papel na tela.
 * O teste aceita os desenhos comuns: parametro {@code ?papel=}, campo editavel ou lista de opcoes.
 */
public final class PapelNaTela {

    private PapelNaTela() {
    }

    public static String valor(Locator campo) {
        String tag = (String) campo.evaluate("e => e.tagName.toLowerCase()");
        String v = switch (tag) {
            case "input", "textarea", "select" -> campo.inputValue();
            default -> campo.innerText();
        };
        return v.strip().toLowerCase();
    }

    /** Deixa a tela no papel pedido; falha com mensagem clara se nenhum mecanismo conhecido funcionar. */
    public static void definir(Page page, String papel) {
        if (tentar(page, papel)) {
            return;
        }
        String base = page.url().replaceAll("[?#].*$", "");
        page.navigate(base + "?papel=" + papel);
        if (tentar(page, papel)) {
            return;
        }
        Locator campo = page.getByTestId("papel-usuario");
        String tag = (String) campo.evaluate("e => e.tagName.toLowerCase()");
        try {
            if (tag.equals("select")) {
                campo.selectOption(papel);
            } else if (tag.equals("input") || tag.equals("textarea")) {
                campo.fill(papel);
                campo.press("Enter");
                campo.blur();
            }
        } catch (RuntimeException ignorado) {
            // cai na verificacao abaixo
        }
        if (!tentar(page, papel)) {
            throw new AssertionError("nao foi possivel colocar a interface no papel '" + papel
                    + "': o texto de P6 nao define como o usuario troca de papel (campo mostra '"
                    + valor(campo) + "')");
        }
    }

    private static boolean tentar(Page page, String papel) {
        try {
            Locator campo = page.getByTestId("papel-usuario");
            campo.waitFor(new Locator.WaitForOptions().setTimeout(3000));
            return valor(campo).equals(papel);
        } catch (RuntimeException e) {
            return false;
        }
    }
}
