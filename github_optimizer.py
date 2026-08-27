import requests
import json
from pathlib import Path
from datetime import datetime
from config import Config

GITHUB_API = "https://api.github.com"

def fetch_repos(username: str, token: str = "") -> list[dict]:
    """Busca repos públicos do usuário (sem token, 60 req/h; com token, 5000)."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{username}/repos?per_page=100&page={page}&sort=updated"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:300]}")
        data = r.json()
        if not data:
            break
        for repo in data:
            repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "description": repo["description"] or "",
                "language": repo["language"] or "",
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "updated_at": repo["updated_at"],
                "topics": repo.get("topics",[]),
            })
        if len(data) < 100:
            break
        page += 1
        if page > 3:  # limite 300 repos
            break
    # ordenar por estrelas desc
    repos.sort(key=lambda x: x["stars"], reverse=True)
    return repos

def generate_project_readme(repo: dict, curriculum: dict, provider: str = "") -> str:
    """Gera README bonito para repo, basado no curriculo + repo. Se provider vazio, usa template fixo."""
    # tentar via IA se configurada
    prompt = f"""
Crie um README.md bonito e profissional para o repositório GitHub "{repo['name']}" ({repo['html_url']}).
Descrição atual: "{repo['description']}" Linguagem principal: {repo['language']} Estrelas: {repo['stars']}
Use o currículo do dono para contextualizar: {json.dumps(curriculum, ensure_ascii=False)[:1000]}
Estrutura: # título com emoji, badges shields, > descrição em 1 frase, Funcionalidades (4-5 itens), Demo (deixe comentado <!-- ![Demo](docs/demo.gif) --> se não tiver imagem), Como rodar (clone, npm install, etc), Stack, Estrutura, Roadmap, Autor (Lucas Baumann, linkedin.com/in/seu-perfil).
Responda apenas com o markdown do README.
"""
    # tentar LLM já configurado em ats_optimizer
    try:
        from ats_optimizer import call_llm
        # só chama se provider compatível estiver configurado (evitar chamada sem chave)
        if Config.LLM_PROVIDER in ("gemini","openai","claude","groq","custom","ollama"):
            txt = call_llm(prompt)
            if txt and len(txt) > 200 and "heurística" not in txt.lower():
                return txt
    except: pass
    # fallback template
    lang = repo["language"] or "TypeScript"
    return f"""# {repo['name']} 

<p align="center">
  <img src="https://img.shields.io/badge/{lang.replace(' ','_')}-00BC8C?style=for-the-badge" />
  <img src="https://img.shields touchscreen" />
</p>

> {repo['description'] or 'Projeto de ' + repo['name'] + ' — desenvolvido por Lucas Baumann.'}

<p align="center">
  <a href="{repo['html_url']}"><img src="https://img.shields.io/github/stars/{repo['full_name']}?style=social" /></a>
  <img src="https://img.shields.io/github/last-commit/{repo['full_name']}?color=00BC8C" />
</p>

## ✨ Funcionalidades
- Funcionalidade principal 1
- Funcionalidade principal 2
- Interface responsiva
- Código limpo e comentado

## 📸 Demo
> <!-- Deixado vazio — me envie screenshot/GIF e eu adiciono: ![Demo](docs/demo.gif) -->

```bash
git clone {repo['html_url']}
cd {repo['name']}
# npm install / pip install conforme stack
```

## 🛠️ Stack
`{lang} • Git • GitHub`

## 👤 Autor
**Lucas Baumann** — [LinkedIn](https://linkedin.com/in/seu-perfil)

---
*Gerado por JobAutoFit — revise antes de push.*
"""

def score_repo_for_job(repo: dict, job_keywords: list[str]) -> int:
    """Score 0-100 para sugerir pins por vaga."""
    txt = (repo["name"] + " " + repo["description"] + " " + repo["language"]).lower()
    hits = sum(1 for kw in job_keywords if kw.lower() in txt)
    return min(100, hits*30 + repo["stars"]*5)

def save_drafts(repos: list[dict], out_dir: Path, curriculum: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo in repos:
        md = generate_project_readme(repo, curriculum)
        (out_dir / f"README_{repo['name']}.md").write_text(md, encoding="utf-8")
    return list(out_dir.glob("README_*.md"))

def fetch_starred_selection(username: str, token: str = "") -> list[dict]:
    """Busca starred do usuário — para sugestão."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"{GITHUB_API}/users/{username}/starred?per_page=20"
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()
    return []
