"""Testes do harness com Claude Code falso e medidor falso: nada aqui gasta o plano nem precisa de Docker."""
import subprocess
import sys
from pathlib import Path

import pytest

from analysis import schema
from harness import agente, csvpassos, medicao, pedidos, workspace
from harness.config import Config, LAB
from harness.executar import Contexto, principal, rodar_cadeia, tipo_do_pedido

FAKE = Path(__file__).resolve().parent / "harness_fake_claude.py"


def cfg_de_teste(tmp_path, **extra) -> Config:
    cfg = Config.do_ambiente(container=False, work_root=tmp_path / "work", resultados=tmp_path / "res",
                             claude=[sys.executable, str(FAKE)], timeout_s=20, **extra)
    return cfg


@pytest.fixture
def env_fake(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CLAUDE_PROMPTS", str(tmp_path / "prompts.txt"))
    monkeypatch.setenv("FAKE_CLAUDE_ESTADO", str(tmp_path / "estado"))
    return tmp_path


def prompts_recebidos(tmp_path) -> list[str]:
    arq = tmp_path / "prompts.txt"
    return [p for p in arq.read_text(encoding="utf-8").split("\x00") if p] if arq.exists() else []


class MedidorFalso:
    def __init__(self, builds=None):
        self.builds = list(builds or [])
        self.chamadas_build = 0
        self.workspaces = []

    def construir(self, ws):
        self.chamadas_build += 1
        return self.builds.pop(0) if self.builds else True

    def subir(self, ws):
        self.workspaces.append(ws)
        return True

    def descer(self, ws=None):
        pass

    def regressao(self):
        return {"RegTest.a": True, "RegTest.b": True, "RegTest.c": True}

    def aceitacao(self, pedido):
        return {f"{pedido}Test.x": True, f"{pedido}Test.y": True}

    def produto(self, ws, commit="HEAD"):
        return {"arch_violations": 0, "cycles": 0, "files_touched": 3, "modules_touched": 2, "max_ccn": 4,
                "dup_pct": 1.5, "loc": 900, "doc_drift": 0, "detalhe": {"fonte": "falso"}}


def contexto(tmp_path, pedidos_ids, builds=None) -> Contexto:
    cfg = cfg_de_teste(tmp_path)
    return Contexto(cfg, MedidorFalso(builds), tmp_path / "res" / "passos.csv", pedidos_ids,
                    agora=lambda: "2026-12-01T10:00:00Z")


# ---------------------------------------------------------------------------------------------------- pedidos
@pytest.mark.parametrize("pedido", ["P1", "P3", "P5", "P9", "P10"])
def test_agente_so_recebe_o_molde(pedido):
    texto = pedidos.texto_do_pedido(Config.do_ambiente(), pedido)
    for marca in ("[CONTEXTO]", "[NECESSIDADE]", "[COMPORTAMENTO PARA O USUÁRIO]", "[CRITÉRIOS DE ACEITAÇÃO]", "[SAÍDA]"):
        assert marca in texto
    for proibido in ("Tipo:", "Cabe na arquitetura", "Tensiona a arquitetura", "Rastreio", "caso de teste",
                     "Ordem no piloto", "Ordem na coleta", "issue B2", "Contrato do stub (para escrita"):
        assert proibido not in texto, proibido
    assert not any(l.startswith(">") for l in texto.splitlines())


def test_minimo_observavel_vai_ao_agente_mas_o_rastreio_nao():
    texto = pedidos.texto_do_pedido(Config.do_ambiente(), "P3")
    assert "empresa-input" in texto and "X-Empresa" in texto
    assert "Mínimo observável" in texto
    assert "empresaBNaoVeTarefasDaEmpresaA" not in texto


def test_incremental_envia_so_o_pedido_do_passo_e_regenerado_acumula():
    cfg = Config.do_ambiente()
    ids = ["P1", "P2", "P3"]
    inc3 = pedidos.prompt_do_passo(cfg, "incremental", ids, 3)
    reg3 = pedidos.prompt_do_passo(cfg, "regenerado", ids, 3)
    assert inc3 == pedidos.texto_do_pedido(cfg, "P3")
    assert "PEDIDO" not in inc3
    for i in ids:
        assert pedidos.texto_do_pedido(cfg, i) in reg3
    assert reg3.index("PEDIDO 1") < reg3.index("PEDIDO 2") < reg3.index("PEDIDO 3")
    assert pedidos.prompt_do_passo(cfg, "regenerado", ids, 1) == pedidos.prompt_do_passo(cfg, "incremental", ids, 1)


def test_tipo_vem_do_arquivo_e_nunca_do_prompt():
    cfg = Config.do_ambiente()
    assert tipo_do_pedido(cfg, "P1") == "cabe"
    assert tipo_do_pedido(cfg, "P3") == "tensiona"
    with pytest.raises(pedidos.PedidoInexistente):
        pedidos.arquivo(cfg, "P99")
    with pytest.raises(pedidos.PedidoInexistente):
        pedidos.arquivo(cfg, "../P1")


# ---------------------------------------------------------------------------------------------------- agente
@pytest.mark.parametrize("comando,esperado", [
    ("mvn -B test", True), ("./mvnw verify", True), ("mvn -q package", True), ("mvn package -DskipTests", False),
    ("mvn -B -q -DskipTests package", False), ("mvn test -Dtest=FooTest", True), ("ls src", False),
    ("curl localhost:8080/health", False), ("pytest -q", True),
])
def test_agent_ran_tests(comando, esperado):
    assert agente.comando_roda_testes(comando) is esperado


def test_comando_nao_interativo_e_com_versao_e_modelo_fixados(tmp_path):
    cfg = cfg_de_teste(tmp_path)
    cmd = agente.montar_comando(cfg, "faca X")
    assert cmd[len(cfg.claude)] == "-p" and "faca X" in cmd
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-5-5"
    assert cmd[cmd.index("--output-format") + 1] == "stream-json" and "--verbose" in cmd
    assert "--no-session-persistence" in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert "--max-turns" not in cmd
    assert agente.ambiente_do_agente(cfg)["DISABLE_AUTOUPDATER"] == "1"
    assert agente.ambiente_do_agente(cfg)["ANTHROPIC_MODEL"] == "claude-sonnet-5-5"


def test_max_turns_so_quando_a_versao_suporta(tmp_path, monkeypatch):
    cfg = cfg_de_teste(tmp_path, max_turns=30)
    assert "--max-turns" not in agente.montar_comando(cfg, "x")
    monkeypatch.setenv("FAKE_HAS_MAX_TURNS", "1")
    cmd = agente.montar_comando(cfg, "x")
    assert cmd[cmd.index("--max-turns") + 1] == "30"


def test_container_monta_so_o_workspace(tmp_path):
    cfg = cfg_de_teste(tmp_path)
    cmd = agente.comando_em_container(cfg, tmp_path / "ws", "nome", ["claude", "-p", "x"])
    assert cmd.count("-v") == 1 and cmd[cmd.index("-v") + 1] == f"{tmp_path / 'ws'}:/work"
    assert "--rm" in cmd and "--cap-drop" in cmd and "no-new-privileges" in cmd
    juntos = " ".join(cmd)
    assert "acceptance" not in juntos and "reference" not in juntos


def test_executar_le_tokens_custo_turnos_e_grava_transcript(tmp_path, env_fake, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_TESTES", "1")
    monkeypatch.setenv("FAKE_CLAUDE_MODO", "cache")
    ws = tmp_path / "ws"
    ws.mkdir()
    cfg = cfg_de_teste(tmp_path)
    r = agente.executar(cfg, ws, "pedido", tmp_path / "t" / "um.jsonl")
    assert r.ok and r.motivo == "ok"
    assert r.tokens_in == 100 + 1000 + 10000 and r.tokens_out == 50
    assert r.cost_usd == 0.25 and r.turns == 7 and r.agent_ran_tests == 1
    assert (ws / "feito.txt").read_text() == "pedido"
    assert r.transcript.exists()
    with pytest.raises(FileExistsError):
        agente.executar(cfg, ws, "pedido", tmp_path / "t" / "um.jsonl")


@pytest.mark.parametrize("modo,motivo", [("erro", "erro_do_agente"), ("sem_resultado", "erro_do_agente")])
def test_falhas_do_agente(tmp_path, env_fake, monkeypatch, modo, motivo):
    monkeypatch.setenv("FAKE_CLAUDE_MODO", modo)
    ws = tmp_path / "ws"
    ws.mkdir()
    r = agente.executar(cfg_de_teste(tmp_path), ws, "p", tmp_path / "t.jsonl")
    assert not r.ok and r.motivo == motivo


def test_tempo_esgotado(tmp_path, env_fake, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODO", "dormir")
    ws = tmp_path / "ws"
    ws.mkdir()
    cfg = cfg_de_teste(tmp_path)
    cfg.timeout_s = 1
    r = agente.executar(cfg, ws, "p", tmp_path / "t.jsonl")
    assert not r.ok and r.motivo == "tempo_esgotado"


# ---------------------------------------------------------------------------------------------------- workspace
def test_workspace_um_commit_por_passo_mesmo_se_o_agente_commitar(tmp_path, monkeypatch):
    base = workspace.preparar(LAB / "seed", tmp_path / "work" / "ws")
    ws = tmp_path / "work" / "ws"
    assert workspace.contar_commits(ws) == 1
    assert not (ws / "target").exists()
    (ws / "novo.txt").write_text("a")
    subprocess.run(["git", "-c", "user.name=a", "-c", "user.email=a@a", "add", "-A"], cwd=ws, check=True)
    subprocess.run(["git", "-c", "user.name=a", "-c", "user.email=a@a", "commit", "-q", "-m", "do agente"],
                   cwd=ws, check=True)
    (ws / "solto.txt").write_text("b")
    workspace.fechar_passo(ws, base, "passo 1")
    assert workspace.contar_commits(ws) == 2
    assert (ws / "novo.txt").exists() and (ws / "solto.txt").exists()


def test_restaurar_volta_ao_mesmo_estado(tmp_path):
    ws = tmp_path / "work" / "ws"
    base = workspace.preparar(LAB / "seed", ws)
    (ws / "lixo.txt").write_text("x")
    (ws / "pom.xml").write_text("quebrado")
    workspace.restaurar(ws, base, tmp_path / "work")
    assert not (ws / "lixo.txt").exists()
    assert "quebrado" not in (ws / "pom.xml").read_text()


def test_restaurar_recusa_pasta_fora_da_area_de_trabalho(tmp_path):
    ws = tmp_path / "fora" / "ws"
    base = workspace.preparar(LAB / "seed", ws)
    with pytest.raises(workspace.IsolamentoViolado):
        workspace.restaurar(ws, base, tmp_path / "work")


def test_isolamento_barra_testes_ocultos_no_workspace(tmp_path):
    ws = tmp_path / "work" / "ws"
    workspace.preparar(LAB / "seed", ws)
    (ws / "tests" / "acceptance").mkdir(parents=True)
    with pytest.raises(workspace.IsolamentoViolado):
        workspace.verificar_isolamento(ws)
    # workspace dentro das pastas ocultas tambem e barrado
    with pytest.raises(workspace.IsolamentoViolado):
        workspace.verificar_isolamento(LAB / "tests" / "acceptance" / "ws")
    with pytest.raises(workspace.IsolamentoViolado):
        workspace.verificar_isolamento(LAB / "reference")


# ---------------------------------------------------------------------------------------------------- medicao e csv
RELATORIO = """<testsuite><testcase classname="A" name="ok"/><testcase classname="A" name="falha"><failure/></testcase>
<testcase classname="A" name="erro"><error/></testcase><testcase classname="A" name="pulado"><skipped/></testcase></testsuite>"""


def test_ler_relatorios_surefire(tmp_path):
    (tmp_path / "TEST-A.xml").write_text(RELATORIO)
    assert medicao.ler_relatorios(tmp_path) == {"A.ok": True, "A.falha": False, "A.erro": False}


def test_regressao_e_flaky_pelas_duas_rodadas():
    r1 = {"a": True, "b": False, "c": False, "d": True}
    r2 = {"a": True, "b": False, "c": True, "d": True}
    # b falha nas duas (regressao), c difere entre as rodadas (flaky)
    assert medicao.contar_rodadas(r1, r2) == {"total": 4, "failed": 1, "flaky": 1}


def test_suite_de_aceitacao_vazia_nao_passa_em_silencio():
    class SemTestes(MedidorFalso):
        def aceitacao(self, pedido):
            return {}

    with pytest.raises(medicao.ErroDeInfra):
        medicao.medir_testes(SemTestes(), "P1")


def test_csv_so_acrescenta_e_segue_o_esquema(tmp_path):
    caminho = tmp_path / "p.csv"
    base = {n: None for n in schema.NOMES}
    base.update(chain_id=1, mode="incremental", step=0)
    csvpassos.anexar(caminho, base)
    with pytest.raises(csvpassos.LinhaDuplicada):
        csvpassos.anexar(caminho, base)
    with pytest.raises(ValueError):
        csvpassos.anexar(caminho, {**base, "step": 1, "inventada": 1})
    assert caminho.read_text().splitlines()[0].split(",") == list(schema.NOMES)


# ---------------------------------------------------------------------------------------------------- cadeia completa
def _cadeia(tmp_path, modo, ids, builds=None, **env):
    ctx = contexto(tmp_path, ids, builds)
    resultado = rodar_cadeia(ctx, 1, modo)
    return ctx, resultado


def test_cadeia_incremental_gera_uma_linha_por_passo_e_valida_no_esquema(tmp_path, env_fake, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_COMMIT", "1")
    ctx, resultado = _cadeia(tmp_path, "incremental", ["P1", "P2"])
    assert resultado == "completa"
    linhas = csvpassos.da_cadeia(ctx.saida, 1, "incremental")
    assert [l["step"] for l in linhas] == ["0", "1", "2"]
    assert [l["request_id"] for l in linhas] == ["P0", "P1", "P2"]
    assert [l["request_type"] for l in linhas] == ["semente", "cabe", "cabe"]
    assert all(l["status"] == "ok" and l["tool_version"] == "2.1.323" for l in linhas)
    assert linhas[0]["tokens_in"] == "" and linhas[0]["acc_total"] == "0"
    assert linhas[1]["tokens_in"] == "100" and linhas[1]["turns"] == "7" and linhas[1]["reg_total"] == "3"
    assert linhas[1]["acc_total"] == "2" and linhas[1]["flaky"] == "0"
    assert schema.validar(schema.carregar(ctx.saida)) == []
    # um commit por passo (mais o da semente), mesmo com o falso agente commitando por conta propria
    assert workspace.contar_commits(ctx.cfg.work_root / "incremental-c01" / "ws") == 3
    # cada passo usa o prompt so do seu pedido
    p = prompts_recebidos(tmp_path)
    assert len(p) == 2 and "Aviso de vencimento" not in p[1] and "filtrar a lista" in p[1]
    assert len(list((ctx.cfg.resultados / "transcripts").glob("*.jsonl"))) == 2
    assert (ctx.cfg.resultados / "execucoes.jsonl").exists()


def test_cadeia_regenerado_parte_da_semente_com_pedidos_acumulados(tmp_path, env_fake):
    ctx, resultado = _cadeia(tmp_path, "regenerado", ["P1", "P2", "P3"])
    assert resultado == "completa"
    assert schema.validar(schema.carregar(ctx.saida)) == []
    p = prompts_recebidos(tmp_path)
    assert [x.count("PEDIDO ") for x in p] == [0, 2, 3]
    assert "PEDIDO 1" in p[2] and "PEDIDO 3" in p[2]
    base = ctx.cfg.work_root / "regenerado-c01"
    for passo in (1, 2, 3):
        ws = base / f"ws-p{passo}"
        assert workspace.contar_commits(ws) == 2  # semente + commit do passo
        assert (ws / "feito.txt").read_text() == p[passo - 1]


def test_nova_tentativa_depois_de_falha_sem_feedback(tmp_path, env_fake, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODO", "primeira_falha")
    ctx, resultado = _cadeia(tmp_path, "incremental", ["P1"])
    assert resultado == "completa"
    p = prompts_recebidos(tmp_path)
    assert len(p) == 2 and p[0] == p[1]  # mesmo prompt, sem o erro anterior
    passo1 = csvpassos.da_cadeia(ctx.saida, 1, "incremental")[1]
    assert passo1["retry"] == "1" and passo1["run_ok"] == "1" and passo1["status"] == "ok"
    assert len(list((ctx.cfg.resultados / "transcripts").glob("*.jsonl"))) == 2
    assert schema.validar(schema.carregar(ctx.saida)) == []


def test_duas_falhas_terminam_a_cadeia_e_censuram(tmp_path, env_fake, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODO", "erro")
    ctx, resultado = _cadeia(tmp_path, "incremental", ["P1", "P2", "P3"])
    assert resultado == "censurada"
    linhas = csvpassos.da_cadeia(ctx.saida, 1, "incremental")
    assert [l["step"] for l in linhas] == ["0", "1"]  # nada depois da falha
    f = linhas[1]
    assert f["status"] == "falha" and f["retry"] == "1" and f["run_ok"] == "0" and f["build_ok"] == "0"
    assert f["reg_total"] == "" and f["loc"] == ""
    assert len(prompts_recebidos(tmp_path)) == 2
    assert schema.validar(schema.carregar(ctx.saida)) == []
    # retomar uma cadeia censurada nao executa nada
    assert rodar_cadeia(ctx, 1, "incremental") == "ja_completa"
    assert len(prompts_recebidos(tmp_path)) == 2


def test_build_quebrado_apos_a_nova_tentativa_e_falha_de_passo(tmp_path, env_fake):
    # builds: semente ok, passo 1 tentativa 1 quebra, tentativa 2 quebra
    ctx, resultado = _cadeia(tmp_path, "incremental", ["P1", "P2"], builds=[True, False, False])
    assert resultado == "censurada"
    f = csvpassos.da_cadeia(ctx.saida, 1, "incremental")[1]
    assert f["status"] == "falha" and f["run_ok"] == "1" and f["build_ok"] == "0" and f["retry"] == "1"
    assert schema.validar(schema.carregar(ctx.saida)) == []


def test_retomar_cadeia_completa_nao_executa_nem_sobrescreve(tmp_path, env_fake):
    ctx, _ = _cadeia(tmp_path, "incremental", ["P1"])
    antes = ctx.saida.read_text()
    assert rodar_cadeia(ctx, 1, "incremental") == "ja_completa"
    assert ctx.saida.read_text() == antes
    assert len(prompts_recebidos(tmp_path)) == 1


def test_retomar_cadeia_parcial_continua_do_proximo_passo(tmp_path, env_fake):
    ids = ["P1", "P2"]
    ctx1, _ = _cadeia(tmp_path, "incremental", ids[:1])
    ctx2 = contexto(tmp_path, ids)
    assert rodar_cadeia(ctx2, 1, "incremental") == "completa"
    assert [l["step"] for l in csvpassos.da_cadeia(ctx2.saida, 1, "incremental")] == ["0", "1", "2"]
    assert len(prompts_recebidos(tmp_path)) == 2


# ---------------------------------------------------------------------------------------------------- CLI
def test_piloto_sem_executar_so_mostra_o_plano(tmp_path, capsys):
    rc = principal(["piloto", "--saida", str(tmp_path / "x.csv")])
    saida = capsys.readouterr().out
    assert rc == 0 and "24 execucao(oes)" in saida and "nada foi executado" in saida
    assert not (tmp_path / "x.csv").exists()


def test_carregar_env_nao_sobrescreve_e_tolera_quebras(tmp_path):
    from harness.config import carregar_env
    arq = tmp_path / ".env"
    arq.write_text("# comentario\nA=do_arquivo\nB=parte1 \n  \nC=\"entre aspas\"\nD=\nE=sem igual\nLINHA_SEM_IGUAL\n")
    arq.chmod(0o600)
    destino = {"A": "ja_exportada"}
    carregadas = carregar_env(arq, destino)
    assert destino["A"] == "ja_exportada"
    assert destino["B"] == "parte1"
    assert destino["C"] == "entreaspas"
    assert "D" not in destino
    assert set(carregadas) == {"B", "C", "E"}


def test_carregar_env_sem_arquivo(tmp_path):
    from harness.config import carregar_env
    assert carregar_env(tmp_path / "nao-existe", {}) == []
