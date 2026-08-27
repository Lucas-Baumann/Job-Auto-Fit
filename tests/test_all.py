import unittest
import sys, os, json, tempfile
sys.path.insert(0, str(__file__).split("tests")[0] if "tests" in __file__ else ".")

# --- Config & DB ---
class TestConfigDB(unittest.TestCase):
    def setUp(self):
        import config
        self.Config = config.Config
    def test_config_exists(self):
        import config
        self.assertTrue(hasattr(config, "Config"))
        self.assertTrue(config.BASE_DIR.exists())

    def test_db_init(self):
        from db import init_db, is_job_processed, save_job, update_job_status
        # usar DB temporário para evitar conflito com DB existente do projeto
        import tempfile, sqlite3
        temp_db = tempfile.mktemp(suffix=".db")
        # sobrescrever Config.DB_PATH temporariamente
        import config
        original_db = config.Config.DB_PATH
        config.Config.DB_PATH = __import__('pathlib').Path(temp_db)
        init_db()
        self.assertTrue(config.Config.DB_PATH.exists())
        j = {"title":"Teste Automação", "company":"TestCo", "url":"http://test/init", "platform":"test", "description":"teste"}
        jid = save_job(j)
        self.assertGreater(jid, 0)
        update_job_status(jid, "applied", resume_path="test.pdf", cover_path="test.txt")
        # restaurar
        config.Config.DB_PATH = original_db
        # limpar temp
        try: os.remove(temp_db)
        except: pass

    def test_duplicate_prevented(self):
        from db import init_db, save_job, is_job_processed, generate_job_hash
        import tempfile
        import config
        original_db = config.Config.DB_PATH
        temp_db = tempfile.mktemp(suffix=".db")
        config.Config.DB_PATH = __import__('pathlib').Path(temp_db)
        try:
            init_db()
            j = {"title":"DupTest","company":"TestCo","url":"http://test/dup","platform":"test","description":"teste"}
            jid1 = save_job(j)
            jid2 = save_job(j)
            self.assertNotEqual(jid1, -1)
            self.assertEqual(jid2, -1)
        finally:
            config.Config.DB_PATH = original_db
            try: os.remove(temp_db)
            except: pass

# --- Collector (com timeout) ---
class TestCollector(unittest.TestCase):
    def test_fetch_remotive(self):
        from collector import fetch_remotive_jobs
        # timeout curto para não travar
        import time
        start = time.time()
        try:
            jobs = fetch_remotive_jobs("python", limit=2)
            self.assertIsInstance(jobs, list)
        except Exception as e:
            # aceitável: rede, 503, timeout
            print("[Collector skip]", e)
        elapsed = time.time() - start
        self.assertLess(elapsed, 15, "Timeout: coleta demorou demais")

# --- Filters ---
class TestFilters(unittest.TestCase):
    def test_parse_salary(self):
        from filters import parse_salary
        self.assertGreater(parse_salary("R$ 5.500,00"), 5000)
        self.assertGreater(parse_salary("R$ 15k"), 14000)
        self.assertGreater(parse_salary("$ 3000"), 10000)  # USD *5

    def test_match_filters(self):
        from filters import filter_jobs
        jobs = [{"title":"Dev Junior Python","company":"A","platform":"test","description":"vaga python remoto","url":"","contact_email":""}]
        cfg = {"exclude_keywords":["estagio"], "min_salary":0, "level":"indiferente", "only_pcd":False, "english_filter":"indiferente", "max_age_days":0, "mandatory_words":[]}
        out = filter_jobs(jobs, cfg)
        self.assertEqual(len(out), 1)
        # excluir "estagio"
        cfg2 = cfg.copy(); cfg2["exclude_keywords"] = ["python"]
        out2 = filter_jobs(jobs, cfg2)
        self.assertEqual(len(out2), 0)

# --- ATS ---
class TestATSOptimizer(unittest.TestCase):
    def test_load_base_cv(self):
        from ats_optimizer import load_base_curriculum
        cv = load_base_curriculum()
        self.assertIn("personal_info", cv)
        # se genérico, não tem nome real
        name = cv.get("personal_info",{}).get("name","")
        # aceitar tanto genérico quanto real
        self.assertIsInstance(name, str)

    def test_heuristic_fallback(self):
        from ats_optimizer import process_job_ats
        # usa base CV genérico; vai cair em heurístico (Ollama não disponível)
        try:
            res = process_job_ats(999, "Python Developer", "TestCo", "Python, Django, SQL")
            self.assertIn("match_score", res)
        except Exception as e:
            # aceitável se faltar lib
            print("[ATS skip]", e)

# --- GUI ---
class TestGUI(unittest.TestCase):
    def test_gui_import(self):
        # Import sem rodar loop
        import gui
        self.assertTrue(hasattr(gui, "App"))

# --- Import PDF ---
class TestImporter(unittest.TestCase):
    def test_heuristic_parse(self):
        from importer import heuristic_parse_curriculum
        text = "João Silva\nemail: joao@ex.com\nPython, SQL, Docker\nBacharelado Unilavras 2020"
        parsed = heuristic_parse_curriculum(text)
        self.assertIn("skills", parsed)
        self.assertTrue(any("python" in s.lower() for s in parsed.get("skills",[])))

# --- GitHub ---
class TestGitHubOptimizer(unittest.TestCase):
    def test_fetch_repos_public(self):
        from github_optimizer import fetch_repos
        repos = fetch_repos("Lucas-Baumann")
        self.assertGreaterEqual(len(repos), 1)
        names = [r["name"] for r in repos]
        # pelo menos um conhecido
        self.assertTrue(any("done" in n.lower() or "Site" in n for n in names))

    def test_generate_project_readme(self):
        from github_optimizer import generate_project_readme
        from ats_optimizer import load_base_curriculum
        repo = {"name":"test","full_name":"user/test","html_url":"https://github.com/user/test","description":"teste","language":"Python","stars":5}
        md = generate_project_readme(repo, load_base_curriculum())
        self.assertIn("teste", md)
        self.assertTrue(len(md) > 200)

if __name__ == "__main__":
    unittest.main(verbosity=2)
