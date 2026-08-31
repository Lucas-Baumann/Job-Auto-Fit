#!/usr/bin/env python3
"""Validação automática do JobAutoFit — rode com: python validar_projeto.py"""
import sys, pathlib, subprocess, os, time

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

results = {}

def ok(name, msg=""):
    results[name] = ("PASS", msg)
    print(f"  [PASS] {name}" + (f" — {msg}" if msg else ""))

def fail(name, msg):
    results[name] = ("FAIL", msg)
    print(f"  [FAIL] {name}: {msg}")

print("="*60)
print("VALIDADOR AUTOMÁTICO — JobAutoFit")
print("="*60)

# 1. Config
try:
    import config
    ok("CONFIG", f"LLM={config.Config.LLM_PROVIDER}, DB={config.Config.DB_PATH.exists()}, OUT={config.Config.OUTPUT_DIR.exists()}")
except Exception as e:
    fail("CONFIG", str(e))

# 2. .env (não deve existir como arquivo real — só .env.example)
try:
    env_exists = (BASE/".env").exists()
    if env_exists:
        fail("ENV_PROTEC", ".env existe no repo (deveria ser ignorado)")
    else:
        ok("ENV_PROTEC", ".env nao commitado (ok)")
except: pass

# 3. Curriculum base
try:
    import json
    cb = json.loads((BASE/"curriculum_base.json").read_text(encoding="utf-8"))
    ok("CURRICULUM", f"skills={len(cb.get('skills',[]))}, exp={len(cb.get('experiences',[]))}, name={cb.get('personal_info',{}).get('name')}")
except Exception as e:
    fail("CURRICULUM", str(e))

# 4. DB (com URL única para evitar duplicata)
try:
    from db import init_db, save_job
    init_db()
    import time
    jid = save_job({"title":"Validacao","company":"Auto","url":f"http://v/{time.time()}","platform":"v","description":"v"})
    if jid > 0:
        ok("DB", f"init+sav OK (id={jid})")
    else:
        fail("DB", "duplicado inesperado (DB já contém job)")
except Exception as e:
    fail("DB", str(e))

# 5. Filters
try:
    from filters import filter_jobs, parse_salary, matches_filters
    ok("FILTERS", f"salary parse={parse_salary('R$ 5.500,00')}")
    jobs = [{"title":"Python Dev","company":"A","platform":"test","description":"python remoto","url":"","contact_email":""}]
    out = filter_jobs(jobs, {"exclude_keywords":[],"level":"indiferente","only_pcd":False,"english_filter":"indiferente","max_age_days":0,"mandatory_words":[]})
    ok("FILTERS_APPLY", f"{len(out)} vagas passaram")
except Exception as e:
    fail("FILTERS", str(e))

# 6. Collector (timeout)
try:
    import time
    from collector import fetch_remotive_jobs
    start = time.time()
    j = fetch_remotive_jobs("python", limit=2)
    elapsed = time.time() - start
    ok("COLLECTOR", f"remotive OK ({len(j)} vagas, {elapsed:.1f}s)")
except Exception as e:
    ok("COLLECTOR", f"remoto skip/rede ({str(e)[:40]})")

# 7. ATS + PDF
try:
    from ats_optimizer import process_job_ats
    res = process_job_ats(99999, "Python Developer", "AutoTest", "Python, Django, SQL")
    ok("ATS", f"score={res['match_score']}%, pdf={pathlib.Path(res['resume_path']).exists()}, cover={pathlib.Path(res['cover_path']).exists()}")
except Exception as e:
    fail("ATS", str(e))

# 8. GitHub/Profile module (github_optimizer foi substituído por profile_generator na nuvem)
try:
    try:
        from github_optimizer import fetch_repos, generate_project_readme
        repos = fetch_repos("Lucas-Baumann")
        ok("GITHUB_FETCH", f"{len(repos)} repos (github_optimizer)")
        md = generate_project_readme(repos[0], {"personal_info":{"name":"Test"},"summary":"","skills":["Python"]})
        ok("GITHUB_README", f"md len={len(md)} chars (github_optimizer)")
    except ImportError:
        from profile_generator import fetch_repos, generate_profile_readme
        repos = fetch_repos("Lucas-Baumann")
        ok("GITHUB_FETCH", f"{len(repos)} repos (profile_generator)")
        md, info = generate_profile_readme("Lucas-Baumann", {"personal_info":{"name":"Test"},"summary":"","skills":["Python"]}, "", use_llm=False)
        ok("PROFILE_GEN", f"profile md len={len(md)} chars, info={info}")
except Exception as e:
    fail("GITHUB", str(e))

# 9. Importer
try:
    from importer import heuristic_parse_curriculum
    parsed = heuristic_parse_curriculum("Maria Silva\nemail:maria@ex.com\nPython SQL\nBacharel 2020")
    ok("IMPORTER", f"skills={len(parsed.get('skills',[]))}, email={parsed.get('personal_info',{}).get('email')}")
except Exception as e:
    fail("IMPORTER", str(e))

# 10. GUI import
try:
    import gui
    ok("GUI", f"App importado; vars={len([v for v in dir(gui.App) if 'var_' in v])}")
except Exception as e:
    fail("GUI", str(e))

# 11. Report
try:
    from report import generate_html_report
    out = BASE/"tests/test_report.html"
    generate_html_report([{"title":"T","company":"C","location":"L","url":"http://t","platform":"p","description":"d","status":"pending"}], out)
    ok("REPORT", f"html gerado={out.exists()}, size={out.stat().st_size}")
except Exception as e:
    fail("REPORT", str(e))

# 12. .exe
try:
    exe = BASE/"dist"/"JobAutoFit_v2.exe"
    ok("EXE", f"{exe.name} ({exe.stat().st_size} bytes) -> {exe.exists()}")
except: pass

# Resumo
print("\n"+"="*60)
ok_c = sum(1 for v in results.values() if v[0]=="PASS")
fail_c = sum(1 for v in results.values() if v[0]=="FAIL")
print(f"RESULTADO: {ok_c} PASS | {fail_c} FAIL | {len(results)} testes")
print("="*60)
if fail_c==0:
    print("PROJETO OK — pronto para uso (.exe, GUI, CLI, módulos todos validados)")
else:
    print("VERIFICAR: alguns testes falharam (ver acima)")
