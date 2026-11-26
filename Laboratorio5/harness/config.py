"""Configuracao do harness: caminhos, pins e limites. Tudo que muda entre maquinas vem de variaveis de ambiente."""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
PINS = LAB / "harness" / "ambiente.pins"

# Pastas que o agente nunca pode ver: testes ocultos e a implementacao de referencia.
PASTAS_OCULTAS = (LAB / "tests" / "acceptance", LAB / "reference")


ENV_ARQUIVO = LAB / ".env"


def carregar_env(caminho: Path = ENV_ARQUIVO, destino=None) -> list[str]:
    """Le .env (CHAVE=VALOR) para o ambiente SEM sobrescrever o que ja esta exportado. Devolve as chaves carregadas.

    O arquivo guarda credencial: nao e versionado (.gitignore) e avisa se outros usuarios podem le-lo.
    Espacos e quebras de linha dentro do valor sao removidos (um token colado em varias linhas continua valido).
    """
    destino = os.environ if destino is None else destino
    if not caminho.is_file():
        return []
    if caminho.stat().st_mode & 0o077:
        import sys
        print(f"aviso: {caminho} pode ser lido por outros usuarios; rode: chmod 600 {caminho}", file=sys.stderr)
    carregadas: list[str] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = "".join(valor.split()).strip("\"'")
        if valor and not destino.get(chave):
            destino[chave] = valor
            carregadas.append(chave)
    return carregadas


def ler_pins(caminho: Path = PINS) -> dict[str, str]:
    pins: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            pins[chave.strip()] = valor.strip()
    return pins


@dataclass
class Config:
    lab: Path = LAB
    work_root: Path = Path("/tmp/lab05-harness")
    resultados: Path = LAB / "results" / "pilot"
    claude: list[str] = field(default_factory=lambda: ["claude"])
    modelo: str = "claude-sonnet-5-5"
    versao_claude: str = ""
    # Limites ainda nao decididos pelo grupo (protocolo-congelado, secao 1): valores provisorios.
    timeout_s: int = 1800
    max_turns: int | None = None
    max_budget_usd: float | None = None
    container: bool = True
    imagem: str = ""
    base_url: str = "http://localhost:8080"
    espera_saude_s: int = 120
    projeto_compose: str = "lab05-harness"
    # So P9 precisa que o servico `app` receba NOTIFICACAO_URL; fora dele o override poderia quebrar o compose do agente.
    compose_override: bool = False

    @classmethod
    def do_ambiente(cls, **sobrescritas) -> "Config":
        carregar_env()
        pins = ler_pins()
        env = os.environ
        cfg = cls(
            work_root=Path(env.get("HARNESS_WORK", "/tmp/lab05-harness")),
            claude=shlex.split(env.get("HARNESS_CLAUDE", "claude")),
            modelo=pins.get("MODELO") or "claude-sonnet-5-5",
            versao_claude=pins.get("CLAUDE_CODE", ""),
            timeout_s=int(env.get("HARNESS_TIMEOUT_S", "1800")),
            max_turns=int(env["HARNESS_MAX_TURNS"]) if env.get("HARNESS_MAX_TURNS") else None,
            max_budget_usd=float(env["HARNESS_MAX_BUDGET_USD"]) if env.get("HARNESS_MAX_BUDGET_USD") else None,
            base_url=env.get("BASE_URL", "http://localhost:8080"),
        )
        cfg.imagem = env.get("HARNESS_IMAGEM") or f"lab05-agente:{cfg.versao_claude or 'dev'}"
        for k, v in sobrescritas.items():
            setattr(cfg, k, v)
        return cfg

    @property
    def seed(self) -> Path:
        return self.lab / "seed"

    def pastas_pedidos(self) -> list[Path]:
        return [self.lab / "docs" / "s01" / "pedidos", self.lab / "docs" / "s02" / "pedidos"]
