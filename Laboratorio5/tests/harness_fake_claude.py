#!/usr/bin/env python3
"""Claude Code falso para testar o harness SEM gastar o plano. Imita --version, --help e `-p ... stream-json`.

Controle por variaveis de ambiente:
  FAKE_CLAUDE_MODO        ok (padrao) | erro | sem_resultado | dormir | primeira_falha | cache
  FAKE_CLAUDE_ESTADO      pasta para contadores (modo primeira_falha)
  FAKE_CLAUDE_PROMPTS     arquivo onde cada prompt recebido e acrescentado (separado por \\x00)
  FAKE_CLAUDE_TESTES      1 = o transcript inclui um `mvn test` do agente
  FAKE_CLAUDE_COMMIT      1 = o falso agente faz um commit proprio (o harness deve juntar em um so)
  FAKE_HAS_MAX_TURNS      1 = o --help lista --max-turns
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if "--version" in args:
        print("2.1.323 (Claude Code)")
        return 0
    if "--help" in args:
        print("Usage: claude [options]\n  -p, --print\n  --model <model>")
        if os.environ.get("FAKE_HAS_MAX_TURNS") == "1":
            print("  --max-turns <n>")
        return 0

    prompt = args[args.index("-p") + 1]
    if os.environ.get("FAKE_CLAUDE_PROMPTS"):
        with open(os.environ["FAKE_CLAUDE_PROMPTS"], "a", encoding="utf-8") as f:
            f.write(prompt + "\x00")

    modo = os.environ.get("FAKE_CLAUDE_MODO", "ok")
    if modo == "primeira_falha":
        estado = Path(os.environ["FAKE_CLAUDE_ESTADO"])
        estado.mkdir(parents=True, exist_ok=True)
        contador = estado / "chamadas"
        n = int(contador.read_text()) + 1 if contador.exists() else 1
        contador.write_text(str(n))
        modo = "erro" if n == 1 else "ok"
    if modo == "dormir":
        time.sleep(30)
    if modo == "sem_resultado":
        return 1

    Path("feito.txt").write_text(prompt, encoding="utf-8")
    if os.environ.get("FAKE_CLAUDE_COMMIT") == "1":
        base = ["git", "-c", "user.name=a", "-c", "user.email=a@a"]
        subprocess.run([*base, "add", "-A"], check=True)
        subprocess.run([*base, "commit", "-q", "-m", "commit do agente"], check=True)

    print(json.dumps({"type": "system", "subtype": "init", "session_id": "fake"}))
    if os.environ.get("FAKE_CLAUDE_TESTES") == "1":
        print(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "mvn -B test"}}]}}))
    print("linha que nao e json")
    uso = {"input_tokens": 100, "output_tokens": 50}
    if modo == "cache":
        uso.update({"cache_creation_input_tokens": 1000, "cache_read_input_tokens": 10000})
    erro = modo == "erro"
    print(json.dumps({"type": "result", "subtype": "error_during_execution" if erro else "success",
                      "is_error": erro, "num_turns": 7, "total_cost_usd": 0.25, "session_id": "fake",
                      "usage": uso}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
