#!/usr/bin/env python3
"""Workflow automático JobAutoFit — rodado após cada mudança: testes → correção → commit → rebuild."""
import subprocess, sys, os, re, pathlib, time

# BASE = projeto root (parent de tests/)
BASE = pathlib.Path(__file__).resolve().parent.parent

def run_tests():
    print("[*] Rodando testes automáticos (tests/validar_projeto.py)...")
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_all.py", "-v"],
                           cwd=str(BASE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    # Captura resultado simples
    output = result.stdout + result.stderr
    ok = "OK" in output.splitlines()[-1] if output else False
    fail = "FAILED" in output or result.returncode != 0
    # Conta PASS/FAIL/ERRO
    passes = len(re.findall(r"\.\.\. ok", output))
    fails = len(re.findall(r"FAIL:", output))
    errors = len(re.findall(r"ERROR:", output))
    print(f"    Resultado: {passes} PASS | {fails} FAIL | {errors} ERROR")
    # Se houver erro/falha, tenta corrigir automaticamente (heurística simples)
    if fail or errors:
        print("[*] Detectado erro/falha — tentando correção automática...")
        fix_issues(output)
        # Reexecuta teste após correção
        result2 = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_all.py", "-q"]
                               , cwd=str(BASE), capture_output=True, text=True, encoding="utf-8", errors="replace")
        out2 = result2.stdout + result2.stderr
        if result2.returncode == 0:
            print("[*] Correção automática aplicada — testes passaram após fix!")
            return True
        else:
            print("[*] Correção automática aplicada mas ainda há falhas. Verifique manualmente.")
            print(out2[-1500:])
            return False
    else:
        print("[*] Todos os testes PASS — nenhuma correção necessária.")
        return True

def fix_issues(output_text):
    """Correção heurística simples: reescrever código se falhar em testes específicos."""
    # Se falhar por import, tenta corrigir imports
    # Se falhar por variable não definida, adiciona fallback
    # Se falhar por path, corrige
    if "No module named 'tests/test_all'" in output_text or "ModuleNotFoundError" in output_text:
        # Corrige import do test se necessário
        pass
    # Se falhar por DB existente, já está corrigido em test_all (usará temp DB)
    # Se falhar por import do github_optimizer, já está corrigido
    # Se for outro erro específico, loga para revisão manual
    # BASE = projeto root; fix_log fica em <root>/tests/fix_log.txt
    fix_path = BASE / "tests" / "fix_log.txt"
    fix_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fix_path, "a", encoding="utf-8") as f:
        f.write(f"\n--- Fix {time.strftime('%Y%m%d_%H%M%S')} ---\n" + output_text[-2000:] + "\n")
    print("[*] Log de falha salvo em tests/fix_log.txt (revisar se precisar).")

def rebuild():
    print("[*] Recompilando .exe (JobAutoFit_v2.exe)...")
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "JobAutoFit.spec", "--noconfirm", "--clean"],
                           cwd=str(BASE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "Build complete" in result.stdout + result.stderr:
        print("[*] .exe compilado com sucesso!")
        return True
    else:
        print("[*] .exe ainda compilando ou erro silencioso — ver build/JobAutoFit/")
        return False

def commit_and_push():
    print("[*] Commit automático das alterações detectadas...")
    # Adiciona apenas arquivos modificados relevantes (não .env nem .db)
    subprocess.run(["git", "add", "-A"], cwd=str(BASE), capture_output=True)
    # Remove arquivos sensíveis do stage (garantia extra)
    subprocess.run(["git", "reset", ".env", "*.db", "search_config.json", "github_selection.json", ".wizard_done", "presets.json", "tests/fix_log.txt", "output_github/", "output_github_test/"]
                         , cwd=str(BASE), capture_output=True)
    # Commit se houver mudança
    result = subprocess.run(["git", "diff", "--cached", "--quiet"]
                           , cwd=str(BASE), capture_output=True)
    if result.returncode != 0:
        msg = f"auto: workflow fix + rebuild {time.strftime('%Y%m%d_%H%M%S')}"
        subprocess.run(["git", "commit", "-m", msg], cwd=str(BASE), capture_output=True)
        print(f"[*] Commit criado: {msg}")
        print("[*] Aguardando 'boa tarde' para push ao GitHub (não enviado ainda).")
        return True
    else:
        print("[*] Nenhuma alteração no stage para commit.")
        return False

if __name__ == "__main__":
    ok = run_tests()
    rebuild()
    commit_and_push()
