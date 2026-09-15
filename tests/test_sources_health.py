#!/usr/bin/env python3
"""Health-check das fontes de vaga (src/collector.py) — rode com:
python tests/test_sources_health.py

Faz requisição REAL contra cada site (sem mock) e avisa se alguma fonte que deveria
funcionar parou de retornar vaga — sinal de que o site mudou HTML/API e o seletor
desatualizou (foi assim que descobrimos o Gupy e o InfoJobs quebrados nesta sessão,
testando manualmente vaga por vaga). Rode antes de uma busca real, ou sempre que os
resultados parecerem baixos demais, pra saber rápido qual fonte parou de funcionar.

InfoJobs entrou de volta na lista (estava fora, documentado como quebrado — a busca usava
o parâmetro de URL errado, 'palavra' em vez de 'palabra'/espanhol, e por isso ignorava
qualquer termo buscado; corrigido em fetch_infojobs_jobs).

Sai com código 0 se todas as fontes retornaram vaga, 1 se alguma falhou.
"""
import sys, pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

from collector import (
    fetch_gupy_jobs, fetch_remotive_jobs, fetch_catho_jobs, fetch_infojobs_jobs,
    fetch_programathor_jobs, fetch_vagascom_jobs, fetch_wwr_jobs, fetch_linkedin_jobs,
)

# termo genérico o bastante pra sempre ter resultado real em qualquer fonte, brasileira
# ou internacional (Remotive/We Work Remotely são sites em inglês)
FONTES = [
    ("Gupy", lambda: fetch_gupy_jobs("desenvolvedor", limit=3)),
    ("Remotive", lambda: fetch_remotive_jobs("developer", limit=3)),
    ("InfoJobs", lambda: fetch_infojobs_jobs("desenvolvedor", limit=3)),
    ("Catho", lambda: fetch_catho_jobs("desenvolvedor", limit=3)),
    ("Programathor", lambda: fetch_programathor_jobs("desenvolvedor", limit=3)),
    ("Vagas.com", lambda: fetch_vagascom_jobs("desenvolvedor", limit=3)),
    ("We Work Remotely", lambda: fetch_wwr_jobs("developer", limit=3)),
    ("LinkedIn Jobs", lambda: fetch_linkedin_jobs("desenvolvedor", limit=3)),
]

def main():
    print("=" * 60)
    print("HEALTH CHECK — Fontes de vaga (requisições reais, sem mock)")
    print("=" * 60)
    falhas = []
    for nome, fn in FONTES:
        try:
            jobs = fn()
            n = len(jobs)
            status = "PASS" if n > 0 else "FAIL"
            print(f"  [{status}] {nome}: {n} vaga(s)")
            if n == 0:
                falhas.append(nome)
        except Exception as e:
            print(f"  [FAIL] {nome}: ERRO — {e}")
            falhas.append(nome)
    print("=" * 60)
    if falhas:
        print(f"ATENÇÃO: {len(falhas)}/{len(FONTES)} fonte(s) sem retorno: {', '.join(falhas)}")
        print("Pode ser seletor/API desatualizado (site mudou) ou instabilidade momentânea da rede — rode de novo antes de investigar código.")
    else:
        print(f"OK: todas as {len(FONTES)} fontes retornaram vaga(s).")
    sys.exit(1 if falhas else 0)

if __name__ == "__main__":
    main()
