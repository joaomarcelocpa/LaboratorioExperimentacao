package labexp.semente.domain;

/** Empresa da requisicao em curso (P3). Fixada na entrada, lida pela persistencia, limpa no fim. */
public final class ContextoEmpresa {

    public static final String PADRAO = "padrao";
    private static final int MAX = 80;
    private static final ThreadLocal<String> ATUAL = new ThreadLocal<>();

    private ContextoEmpresa() {
    }

    public static String atual() {
        String e = ATUAL.get();
        return e == null ? PADRAO : e;
    }

    public static void definir(String empresa) {
        String limpa = empresa == null ? "" : empresa.strip();
        ATUAL.set(limpa.isEmpty() ? PADRAO : limpa.substring(0, Math.min(limpa.length(), MAX)));
    }

    public static void limpar() {
        ATUAL.remove();
    }
}
