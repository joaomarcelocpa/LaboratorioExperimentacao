package labexp.semente.domain;

public enum Papel {
    GESTOR,
    COLABORADOR;

    public static Papel de(String valor) {
        return valor != null && valor.strip().equalsIgnoreCase("gestor") ? GESTOR : COLABORADOR;
    }

    public boolean podeAlterarTarefas() {
        return this == GESTOR;
    }
}
