"""
Profile Generator — cria README de perfil GitHub na estética perfeita (Lucas-Baumann:3bfe1b0)
- Analisa perfil antigo (via raw github) + curriculum + repos via API
- Usa template fixo dark (tokyonight) + summary-cards (não vercel) + snake picture
- LLM opcional reescreve bio/resumo mantendo veracidade
"""
import json
import os
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from config import Config
from ats_optimizer import call_llm
from logutil import log_print

def _parse_llm_json(resp: str) -> dict:
    """Extrai o objeto JSON da resposta da IA. Modelos gratuitos/pequenos costumam envolver o
    JSON em texto explicativo mesmo quando instruídos a não fazer isso — um json.loads() direto
    quebra nesse caso (era o que acontecia aqui antes, e o erro só ia pro console, que nem
    existe no .exe sem janela — a IA falhava silenciosamente e caía pro heurístico genérico)."""
    clean = resp.replace("```json", "").replace("```", "").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]
    return json.loads(clean)

TEMPLATE = """<div align="center">

![{name}](https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=22&pause=1000&color=00BC8C&center=true&vCenter=true&width=600&lines={typing_lines})

</div>

<p align="center">
  <a href="{linkedin}"><img src="https://img.shields.io/badge/-LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="mailto:{email}"><img src="https://img.shields.io/badge/-Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"></a>
  <a href="https://github.com/{username}"><img src="https://img.shields.io/badge/-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
  <img src="https://komarev.com/ghpvc/?username={username}&label=Profile+views&color=00bc8c&style=flat" alt="Profile views">
</p>

<h3 align="center">🛠️ Stack principal</h3>

<p align="center">
  <a href="https://skillicons.dev"><img src="https://skillicons.dev/icons?i={skillicons}" alt="Skills" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React_Native-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React Native" />
  <img src="https://img.shields.io/badge/Expo-000020?style=for-the-badge&logo=expo&logoColor=white" alt="Expo" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/REST_API-00BC8C?style=for-the-badge&logo=fastapi&logoColor=white" alt="REST API" />
</p>

---

<h3 align="center">📊 Resumo</h3>

<div align="center">
  <img src="https://img.shields.io/badge/Repos%20p%C3%BAblicos-{public_repos}-00BC8C?style=flat" alt="Repos" />
  <img src="https://img.shields.io/github/followers/{username}?label=Seguidores&style=flat&color=00BC8C" alt="Seguidores" />
  <img src="https://img.shields.io/badge/Estrelas-{total_stars}-00BC8C?style=flat" alt="Estrelas" />
</div>

---

<h3 align="center">📈 GitHub Stats</h3>

<div align="center">
  <img src="https://github-profile-summary-cards.vercel.app/api/cards/stats?username={username}&theme=tokyonight" height="150" alt="GitHub Stats" />
  <img src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username={username}&theme=tokyonight" height="150" alt="Top Langs" />
  <br/>
  <img src="https://github-readme-streak-stats.herokuapp.com/?user={username}&theme=tokyonight&hide_border=true&background=0d1117&ring=00BC8C&currStreakLabel=00BC8C" height="150" alt="Streak" />
</div>

---

<h3 align="center">🚀 Projetos em destaque</h3>

<div align="center">

<a href="https://github.com/{username}/done-flow"><img src="https://img.shields.io/badge/done--flow-React%20Native-61DAFB?style=for-the-badge&logo=react" alt="done-flow" /></a>
<a href="https://github.com/{username}/Site-para-adocao-de-animais"><img src="https://img.shields.io/badge/Site%20Ado%C3%A7%C3%A3o-React%20TS-3178C6?style=for-the-badge&logo=typescript" alt="Site Adoção" /></a>
<a href="https://github.com/{username}/Job-Auto-Fit"><img src="https://img.shields.io/badge/Job--Auto--Fit-Python-3776AB?style=for-the-badge&logo=python" alt="Job-Auto-Fit" /></a>

</div>

<p align="center">
  <b>done-flow</b> — App de tarefas com categorias (React Native + Expo, TypeScript) • <b>Site Amigos Peludos</b> — Web completa para canil (React + TS, filtros, formulários) • <b>Job-Auto-Fit</b> — Automação de currículos Gupy/LinkedIn com IA + relatórios<br/>
  <sub>{projects_sub}</sub>
</p>

---

<h3 align="center">💼 Experiência rápida</h3>

<p align="center">
  {experience_line}<br/>
  <a href="{linkedin}">LinkedIn →</a>
</p>

---

<h3 align="center">📫 Contato</h3>

<p align="center">
  <a href="{linkedin}"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" /></a>
  <a href="mailto:{email}"><img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" /></a>
  <span> • {location} • {phone}</span>
</p>

<p align="center">
  <i>{bio_line}</i>
</p>

---

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/{username}/{username}/output/github-contribution-grid-snake-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/{username}/{username}/output/github-contribution-grid-snake.svg">
    <img alt="github contribution grid snake animation" src="https://raw.githubusercontent.com/{username}/{username}/output/github-contribution-grid-snake.svg">
  </picture>
</p>
"""

SNAKE_WORKFLOW = """name: Generate Snake Game
on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
  push:
    branches: [main]
jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: Platane/snk@v3
        with:
          github_user_name: {username}
          outputs: |
            dist/github-contribution-grid-snake.svg
            dist/github-contribution-grid-snake-dark.svg?palette=github-dark
      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
"""

def fetch_github_user(username: str) -> Dict:
    try:
        r = requests.get(f"https://api.github.com/users/{username}", timeout=10, headers={"Accept":"application/vnd.github.v3+json"})
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Profile] erro fetch user: {e}")
    return {}

def fetch_repos(username: str, limit: int = 100) -> List[Dict]:
    try:
        r = requests.get(f"https://api.github.com/users/{username}/repos?per_page={limit}&sort=updated", timeout=10)
        if r.status_code == 200:
            return r.json()
    except: pass
    return []

def fetch_old_readme(username: str) -> str:
    for branch in ["main","master"]:
        try:
            url = f"https://raw.githubusercontent.com/{username}/{username}/{branch}/README.md"
            r = requests.get(url, timeout=8)
            if r.status_code == 200 and len(r.text) > 50:
                return r.text
        except: pass
    return ""

def analyze_old_readme(text: str) -> Dict[str, str]:
    if not text:
        return {"status":"vazio","issues":"README não encontrado — será criado do zero","suggestions":"Usar template completo"}
    issues=[]
    if "skillicons" not in text.lower(): issues.append("sem skillicons/stack")
    if "github-readme-stats" not in text.lower() and "profile-summary-cards" not in text.lower(): issues.append("sem GitHub Stats")
    if "snake" not in text.lower(): issues.append("sem snake game")
    if "komarev" not in text.lower(): issues.append("sem contador views")
    if "linkedin" not in text.lower(): issues.append("sem LinkedIn")
    return {"status":"encontrado","len":str(len(text)), "issues": "; ".join(issues) if issues else "ok", "preview": text[:500]}

def _skillicons_from_curriculum(curriculum: dict, username: str) -> str:
    # mapeia skills para skillicons ids
    skills = [s.lower() for s in curriculum.get("skills",[])]
    mapping = {"react":"react","react native":"react","typescript":"ts","javascript":"js","vue":"vue","nextjs":"nextjs","html":"html","css":"css","php":"php",".net":"dotnet","c#":"cs","node":"nodejs","mysql":"mysql","postgres":"postgres","postgresql":"postgres","python":"py","docker":"docker","git":"git"}
    ids=set(["react","ts","js"])
    for s in skills:
        for k,v in mapping.items():
            if k in s:
                ids.add(v)
    # sempre inclui base
    ids.update(["vue","nextjs","html","css","php","dotnet","cs","nodejs","mysql","postgres","git","github"])
    # limita a 16
    return ",".join(sorted(ids)[:16])

def generate_profile_readme(username: str, curriculum: dict, old_readme: str = "", use_llm: bool = True) -> Tuple[str, Dict]:
    """Gera README de perfil na estética perfeita. Retorna (markdown, info)."""
    user_data = fetch_github_user(username)
    repos = fetch_repos(username)
    public_repos = user_data.get("public_repos", len(repos) if repos else 10)
    followers = user_data.get("followers", 0)
    total_stars = sum(r.get("stargazers_count",0) for r in repos) if repos else 4

    # skillicons
    skillicons = _skillicons_from_curriculum(curriculum, username)

    # typing lines a partir de curriculum
    pos = curriculum.get("experiences",[{}])[0].get("position","Desenvolvedor")
    name = curriculum.get("personal_info",{}).get("name","Seu Nome")
    loc = curriculum.get("personal_info",{}).get("location","Sua Cidade")
    # tenta LLM para bio curta
    typing_lines = f"Desenvolvedor+{pos.replace(' ','+')};TypeScript+|+JavaScript+|+PHP;{loc.replace(' ','+')}+•+Remoto;Construindo+apps+que+usam+de+verdade"
    bio_line = "Aberto a oportunidades remotas — vamos conversar?"
    experience_line = " • ".join(f"{e.get('company','Empresa')} ({e.get('period','')})" for e in curriculum.get("experiences",[])[:4]) or "Empresa Atual • Empresa Anterior"
    projects_sub = "Selecione fork/star nos 3 projetos em destaque — badges for-the-badge garantidos via shields.io"

    llm_used = False
    llm_error = None
    if use_llm and (Config.OPENROUTER_API_KEY or Config.GEMINI_API_KEY or Config.OPENAI_API_KEY):
        try:
            prompt = f"""
Você é especialista em branding GitHub. Reescreva bio curta para README de perfil,
mantendo veracidade do currículo e perfil antigo.

TEMPLATE ESTÉTICA: dark tokyonight, typing-svg, skillicons, stats summary-cards, pins shields, snake picture.

CURRICULO: {json.dumps(curriculum, ensure_ascii=False, indent=2)[:2000]}

PERFIL ANTIGO (primeiros 800 chars):
{old_readme[:800]}

Retorne JSON exato:
{{"typing_lines":"Linha1;Linha2;Linha3;Linha4","bio_line":"1 frase","experience_line":"1 linha","projects_sub":"1 linha"}}
Sem markdown, apenas JSON.
"""
            resp = call_llm(prompt)
            if resp:
                data = _parse_llm_json(resp)
                typing_lines = data.get("typing_lines", typing_lines)
                bio_line = data.get("bio_line", bio_line)
                experience_line = data.get("experience_line", experience_line)
                projects_sub = data.get("projects_sub", projects_sub)
                llm_used = True
            else:
                llm_error = "IA não retornou resposta (call_llm veio vazio — ver logs/jobautofit.log)"
        except Exception as e:
            llm_error = str(e)
            log_print(f"[Profile] LLM falhou, usando heurístico: {e}")
    elif use_llm:
        llm_error = "Nenhuma chave de IA configurada (Gemini/OpenAI/OpenRouter)"

    pinfo = curriculum.get("personal_info",{})
    md = TEMPLATE.format(
        name=pinfo.get("name", name),
        typing_lines=typing_lines,
        linkedin=pinfo.get("linkedin","https://linkedin.com/in/seu-perfil"),
        email=pinfo.get("email","seu@email.com"),
        username=username,
        skillicons=skillicons,
        public_repos=public_repos,
        total_stars=total_stars,
        projects_sub=projects_sub,
        experience_line=experience_line,
        location=pinfo.get("location", loc),
        phone=pinfo.get("phone","(00) 00000-0000"),
        bio_line=bio_line
    )
    info = {"public_repos": public_repos, "followers": followers, "total_stars": total_stars, "skillicons": skillicons, "repos_analyzed": len(repos), "llm_used": llm_used, "llm_error": llm_error}
    return md, info

def write_profile_output(username: str, markdown: str, workflow: str = ""):
    out_dir = Config.BASE_DIR / "output_github"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"README_{username}.md").write_text(markdown, encoding="utf-8")
    (out_dir / "snake.yml").write_text(SNAKE_WORKFLOW.format(username=username), encoding="utf-8")
    return str(out_dir / f"README_{username}.md")

# ── Repositórios ──
REPO_TEMPLATE = """# {repo_name}

{badges}

> {description}

## 🚀 Stack
{stack_bullets}

## ✨ Funcionalidades
{features}

## 📦 Instalação
```bash
{install_cmd}
```

## ▶️ Uso
```bash
{usage_cmd}
```

## 📸 Preview
<!-- Substitua por seu GIF/screenshot: docs/demo.gif -->
<!-- ![Demo](docs/demo.gif) -->

{sub_extra}

---
<sub>Gerado por JobAutoFit — estética dark tokyonight + shields + análise do README antigo + currículo</sub>
"""

def fetch_repo_readme(username: str, repo: str) -> str:
    for branch in ["main","master","dev"]:
        try:
            url = f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/README.md"
            r = requests.get(url, timeout=8)
            if r.status_code == 200 and len(r.text) > 30:
                return r.text
        except: pass
    # tenta via API contents
    try:
        r = requests.get(f"https://api.github.com/repos/{username}/{repo}/readme", timeout=8, headers={"Accept":"application/vnd.github.v3.raw"})
        if r.status_code == 200 and len(r.text) > 30:
            return r.text
    except: pass
    return ""

def fetch_repo_languages(username: str, repo: str) -> List[str]:
    try:
        r = requests.get(f"https://api.github.com/repos/{username}/{repo}/languages", timeout=8)
        if r.status_code == 200:
            data = r.json()
            # ordena por bytes
            return sorted(data.keys(), key=lambda k: data[k], reverse=True)[:6]
    except: pass
    return []

def check_repo_has_readme(username: str, repo: str) -> bool:
    return bool(fetch_repo_readme(username, repo))

def generate_repo_readme(username: str, repo: str, curriculum: dict, old_readme: str = "", use_llm: bool = True) -> Tuple[str, Dict]:
    """Gera README de repo atrativo na estética dark, analisando projeto. Retorna (md, info)."""
    # metadados
    repo_data={}
    langs=[]
    try:
        r = requests.get(f"https://api.github.com/repos/{username}/{repo}", timeout=8)
        if r.status_code == 200:
            repo_data = r.json()
            langs = fetch_repo_languages(username, repo)
    except: pass
    description = repo_data.get("description") or f"Projeto {repo} — {repo_data.get('language','')}"
    language_main = repo_data.get("language") or (langs[0] if langs else "JavaScript")
    stars = repo_data.get("stargazers_count", 0)
    topics = repo_data.get("topics") or []

    # heurística install/usage por linguagem (só o comando — não inventa framework/lib que o
    # repo pode nem usar, como acontecia antes ao assumir "React Native / Expo" pra qualquer JS/TS)
    lang_low = language_main.lower() if language_main else ""
    if "typescript" in lang_low or "javascript" in lang_low:
        install_cmd = "npm install"
        usage_cmd = "npm run dev  # ou npm start, conforme o script definido no package.json"
    elif "python" in lang_low:
        install_cmd = "pip install -r requirements.txt"
        usage_cmd = "python main.py"
    elif "php" in lang_low:
        install_cmd = "composer install"
        usage_cmd = "php artisan serve  # ou php -S localhost:8000"
    else:
        install_cmd = f"git clone https://github.com/{username}/{repo}.git\ncd {repo}"
        usage_cmd = "veja docs/"

    # stack a partir das linguagens reais do repo (API languages), não de um chute fixo por linguagem principal
    stack_items = list(langs[:5]) if langs else ([language_main] if language_main else [])
    stack_bullets = "\n".join(f"- {s}" for s in stack_items) if stack_items else f"- {language_main or 'Ver repositório'}"

    badges = f"[![Stars](https://img.shields.io/github/stars/{username}/{repo}?style=flat&color=00BC8C)](https://github.com/{username}/{repo}) [![Language](https://img.shields.io/github/languages/top/{username}/{repo}?color=00BC8C)](https://github.com/{username}/{repo}) [![Last Commit](https://img.shields.io/github/last-commit/{username}/{repo}?color=00BC8C)](https://github.com/{username}/{repo}/commits)"
    # sem IA, usa topics do GitHub (se o repo tiver) em vez de frases genéricas tipo "pronto para portfolio"
    features = ("\n".join(f"- {t.replace('-', ' ').replace('_', ' ').capitalize()}" for t in topics[:5])
                if topics else "- Ver código-fonte do repositório para detalhes de funcionalidades")
    sub_extra = ""

    llm_used = False
    llm_error = None
    if use_llm and (Config.OPENROUTER_API_KEY or Config.GEMINI_API_KEY or Config.OPENAI_API_KEY):
        try:
            prompt = f"""
Você é especialista em READMEs de repositórios para portfolio. Reestruture o README mantendo veracidade.

REPO: {username}/{repo}
DESCRIÇÃO ATUAL: {description}
LINGUAGEM PRINCIPAL: {language_main}
LINGUAGENS: {langs}
TOPICS/TAGS: {topics}
README ANTIGO (800 chars):
{old_readme[:800]}

CURRICULO (para contexto de autor):
{json.dumps(curriculum, ensure_ascii=False, indent=2)[:1200]}

TEMPLATE: badges shields + stack bullets + instalação + uso + preview placeholder
Retorne JSON exato: {{"description":"1 frase","features":"- bullet\\n- bullet\\n- bullet","stack_bullets":"- ...","install_cmd":"...","usage_cmd":"...","sub_extra":"1 frase opcional"}}
Sem markdown, apenas JSON.
"""
            resp = call_llm(prompt)
            if resp:
                data = _parse_llm_json(resp)
                description = data.get("description", description)
                features = data.get("features", features)
                stack_bullets = data.get("stack_bullets", stack_bullets)
                install_cmd = data.get("install_cmd", install_cmd)
                usage_cmd = data.get("usage_cmd", usage_cmd)
                sub_extra = data.get("sub_extra", "")
                llm_used = True
            else:
                llm_error = "IA não retornou resposta (call_llm veio vazio — ver logs/jobautofit.log)"
        except Exception as e:
            llm_error = str(e)
            log_print(f"[Repo] LLM falhou {repo}: {e}")
    elif use_llm:
        llm_error = "Nenhuma chave de IA configurada (Gemini/OpenAI/OpenRouter)"

    md = REPO_TEMPLATE.format(repo_name=repo, badges=badges, description=description, stack_bullets=stack_bullets, features=features, install_cmd=install_cmd, usage_cmd=usage_cmd, sub_extra=sub_extra)
    info = {"repo": repo, "language": language_main, "stars": stars, "has_old": bool(old_readme), "langs": langs, "llm_used": llm_used, "llm_error": llm_error}
    return md, info

def write_repo_output(username: str, repo: str, markdown: str) -> str:
    out_dir = Config.BASE_DIR / "output_github"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"README_{repo}.md"
    path.write_text(markdown, encoding="utf-8")
    return str(path)

def _git_push_file(username: str, repo: str, token: str, file_content: str, target_path: str, commit_msg: str, extra_files: Dict[str,str]=None, author_name: str = None, author_email: str = None) -> str:
    """Clona repo, sobrescreve arquivo, commit e push. Retorna mensagem."""
    if not token:
        raise ValueError("GITHUB_TOKEN não informado — crie em github.com/settings/tokens (classic, scope repo)")
    tmpdir = tempfile.mkdtemp(prefix="gh_push_")
    try:
        # token no URL (sem log)
        safe_user = requests.utils.quote(username)
        # usa token como user:oauth
        clone_url = f"https://{token}@github.com/{username}/{repo}.git"
        # clone shallow
        subprocess.run(["git","clone","--depth","1",clone_url, tmpdir], check=True, capture_output=True, text=True, timeout=30)
        # identidade do commit: nome/e-mail do próprio usuário (currículo) em vez de um nome
        # genérico de "bot" — assim o commit aparece com a autoria real no histórico do GitHub
        git_name = author_name or username
        git_email = author_email or f"{username}@users.noreply.github.com"
        subprocess.run(["git","-C",tmpdir,"config","user.name",git_name], check=True)
        subprocess.run(["git","-C",tmpdir,"config","user.email",git_email], check=True)
        # escreve arquivo principal
        dest = Path(tmpdir) / target_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(file_content, encoding="utf-8")
        # arquivos extras (ex: workflow)
        if extra_files:
            for rel, content in extra_files.items():
                p = Path(tmpdir) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
        # add
        to_add = [target_path] + list(extra_files.keys() if extra_files else [])
        subprocess.run(["git","-C",tmpdir,"add"] + to_add, check=True)
        # commit (se nada mudou, ignora)
        result = subprocess.run(["git","-C",tmpdir,"diff","--cached","--quiet"])
        if result.returncode == 0:
            return "sem alterações — já está atualizado"
        subprocess.run(["git","-C",tmpdir,"commit","-m",commit_msg], check=True, capture_output=True, text=True)
        # push
        subprocess.run(["git","-C",tmpdir,"push","origin","HEAD:main"], check=True, capture_output=True, text=True, timeout=30)
        return "push ok"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e))[:600]
        # esconde token
        err = err.replace(token, "***")
        raise RuntimeError(err)
    finally:
        try: shutil.rmtree(tmpdir, ignore_errors=True)
        except: pass

def push_profile_readme(username: str, token: str, markdown: str, workflow: str = None, author_name: str = None, author_email: str = None) -> str:
    extra = {".github/workflows/snake.yml": SNAKE_WORKFLOW.format(username=username)} if workflow is None else {}
    # workflow já está em SNAKE_WORKFLOW, sempre inclui
    extra = {".github/workflows/snake.yml": SNAKE_WORKFLOW.format(username=username)}
    return _git_push_file(username, username, token, markdown, "README.md", "docs: atualiza README perfil via JobAutoFit", extra_files=extra, author_name=author_name, author_email=author_email)

def push_repo_readme(username: str, repo: str, token: str, markdown: str, author_name: str = None, author_email: str = None) -> str:
    return _git_push_file(username, repo, token, markdown, "README.md", f"docs: atualiza README via JobAutoFit — {repo}", author_name=author_name, author_email=author_email)
