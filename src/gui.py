import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from config import Config
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)
from gui_tabs.perfil import PerfilTabMixin
from gui_tabs.busca import BuscaTabMixin
from gui_tabs.ia import IATabMixin
from gui_tabs.execucao import ExecucaoTabMixin
from gui_tabs.dashboard import DashboardTabMixin
from gui_tabs.historico import HistoricoTabMixin
from gui_tabs.perfil_github import PerfilGithubTabMixin

class App(tb.Window, PerfilTabMixin, BuscaTabMixin, IATabMixin, ExecucaoTabMixin, DashboardTabMixin, HistoricoTabMixin, PerfilGithubTabMixin):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("JobAutoFit — Automação Completa (Gupy / LinkedIn / ATS)")
        self.geometry("1280x820"); self.minsize(1200,750)
        self.curriculum=load_curriculum(); self.env=load_env_dict(); self.search_cfg=load_search_config()
        try:
            # garante que jobs.db exista com o schema atual (colunas/tabelas novas) antes de
            # qualquer leitura do Dashboard/Histórico — antes só main.py chamava init_db()
            from db import init_db as _init_db
            _init_db()
        except Exception: pass
        # vars perfil
        self.var_name=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("name",""))
        self.var_email=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("email",""))
        self.var_phone=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("phone",""))
        self.var_location=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("location",""))
        self.var_linkedin=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("linkedin",""))
        self.var_github=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("github",""))
        # ia
        self.var_gemini_key=tk.StringVar(value=self.env.get("GEMINI_API_KEY",""))
        self.var_gemini_model=tk.StringVar(value=self.env.get("GEMINI_MODEL","gemini-flash-latest"))
        self.var_llm_provider=tk.StringVar(value=self.env.get("LLM_PROVIDER","gemini"))
        self.var_ollama_host=tk.StringVar(value=self.env.get("OLLAMA_HOST","http://localhost:11434"))
        self.var_ollama_model=tk.StringVar(value=self.env.get("OLLAMA_MODEL","llama3:latest"))
        self.var_openai_key=tk.StringVar(value=self.env.get("OPENAI_API_KEY",""))
        self.var_claude_key=tk.StringVar(value=self.env.get("CLAUDE_API_KEY",""))
        self.var_groq_key=tk.StringVar(value=self.env.get("GROQ_API_KEY",""))
        self.var_openrouter_key=tk.StringVar(value=self.env.get("OPENROUTER_API_KEY",""))
        self.var_openrouter_model=tk.StringVar(value=self.env.get("OPENROUTER_MODEL","minimax/minimax-m3:free"))
        self.var_custom_url=tk.StringVar(value=self.env.get("CUSTOM_LLM_URL",""))
        self.var_custom_key=tk.StringVar(value=self.env.get("CUSTOM_LLM_KEY",""))
        self.var_smtp_host=tk.StringVar(value=self.env.get("SMTP_HOST","smtp.gmail.com"))
        self.var_smtp_port=tk.StringVar(value=self.env.get("SMTP_PORT","587"))
        self.var_smtp_user=tk.StringVar(value=self.env.get("SMTP_USER",""))
        self.var_smtp_pass=tk.StringVar(value=self.env.get("SMTP_PASS",""))
        self.var_linkedin_email=tk.StringVar(value=self.env.get("LINKEDIN_EMAIL",""))
        self.var_linkedin_pass=tk.StringVar(value=self.env.get("LINKEDIN_PASSWORD",""))
        self.var_gupy_email=tk.StringVar(value=self.env.get("GUPY_EMAIL",""))
        self.var_gupy_pass=tk.StringVar(value=self.env.get("GUPY_PASSWORD",""))
        # busca avançada
        self.var_keywords=tk.StringVar(value=", ".join(self.search_cfg.get("keywords",[])))
        self.var_work_mode=tk.StringVar(value=self.search_cfg.get("work_mode","remoto"))
        self.var_presencial_loc=tk.StringVar(value=self.search_cfg.get("presencial_location",""))
        self.var_contract=tk.StringVar(value=self.search_cfg.get("contract_type","indiferente"))
        self.var_min_score=tk.IntVar(value=self.search_cfg.get("min_score",60))
        self.var_limit=tk.IntVar(value=self.search_cfg.get("limit_per_source",8))
        self.var_min_salary=tk.IntVar(value=self.search_cfg.get("min_salary",0))
        self.var_level=tk.StringVar(value=self.search_cfg.get("level","indiferente"))
        self.var_exclude=tk.StringVar(value=", ".join(self.search_cfg.get("exclude_keywords",[])))
        self.var_mandatory=tk.StringVar(value=", ".join(self.search_cfg.get("mandatory_words",[])))
        self.var_blocked=tk.StringVar(value=", ".join(self.search_cfg.get("blocked_companies",[])))
        self.var_fav=tk.StringVar(value=", ".join(self.search_cfg.get("favorite_companies",[])))
        self.var_max_age=tk.IntVar(value=self.search_cfg.get("max_age_days",0))
        self.var_only_pcd=tk.BooleanVar(value=self.search_cfg.get("only_pcd",False))
        self.var_english=tk.StringVar(value=self.search_cfg.get("english_filter","indiferente"))
        self.var_daily_limit=tk.IntVar(value=self.search_cfg.get("daily_limit",20))
        self.var_auto_send=tk.BooleanVar(value=self.search_cfg.get("auto_send",True))
        self.var_telegram_token=tk.StringVar(value=self.search_cfg.get("telegram_bot_token",self.env.get("TELEGRAM_BOT_TOKEN","")))
        self.var_telegram_chat=tk.StringVar(value=self.search_cfg.get("telegram_chat_id",self.env.get("TELEGRAM_CHAT_ID","")))
        self.var_schedule_enabled=tk.BooleanVar(value=self.search_cfg.get("schedule_enabled",False))
        self.var_schedule_hour=tk.StringVar(value=self.search_cfg.get("schedule_hour","08:00"))
        self.var_enable_linkedin_posts=tk.BooleanVar(value=self.search_cfg.get("enable_linkedin_posts",True))
        self.var_linkedin_posts_limit=tk.IntVar(value=self.search_cfg.get("linkedin_posts_limit", self.search_cfg.get("limit_per_source",8)))
        self.var_profile_user=tk.StringVar(value=(self.curriculum.get("personal_info",{}).get("github","").split("/")[-1].strip() if self.curriculum.get("personal_info",{}).get("github") else "Lucas-Baumann") or "Lucas-Baumann")
        self.var_profile_use_llm=tk.BooleanVar(value=True)
        self.var_github_token=tk.StringVar(value=self.env.get("GITHUB_TOKEN",""))
        self.var_dry_run=tk.BooleanVar(value=True)
        self._build_ui(); self._bind_work_mode(); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list(); self._refresh_dashboard()
        self.after(300, self._maybe_show_onboarding)

    def _maybe_show_onboarding(self):
        # primeira execução (currículo em branco, sem nome nem experiência) — evita a pessoa
        # achar que o app "travou" ou "não importou nada" olhando os campos vazios sem contexto
        pi = self.curriculum.get("personal_info",{})
        if pi.get("name") or self.curriculum.get("experiences"):
            return
        messagebox.showinfo(
            "Bem-vindo ao JobAutoFit",
            "Primeira execução — nenhum currículo carregado ainda.\n\n"
            "Passo a passo sugerido:\n"
            "1) Aba 3 (IA & Conexões) — configure uma chave de IA (Gemini/OpenRouter grátis ou Ollama local). "
            "Sem isso, o import de PDF usa um modo heurístico mais limitado.\n"
            "2) Aba 1 (Currículo) — clique em \"Importar PDF/DOCX/TXT\" para preencher automaticamente.\n"
            "3) Revise os campos preenchidos e clique em \"Salvar Tudo\"."
        )

    def _build_ui(self):
        top=tb.Frame(self,padding=10); top.pack(fill=X)
        tb.Label(top,text="JobAutoFit",font=("Segoe UI",18,"bold"),bootstyle="primary").pack(side=LEFT)
        tb.Label(top,text="  Coleta • Filtragem Avançada • ATS • Envio • Relatório • Dashboard",font=("Segoe UI",10),bootstyle="secondary").pack(side=LEFT,padx=10)
        tb.Button(top,text="Exportar",bootstyle="secondary-outline",command=self.export_config).pack(side=RIGHT,padx=5)
        tb.Button(top,text="Importar",bootstyle="secondary-outline",command=self.import_config).pack(side=RIGHT,padx=5)
        self.nb=tb.Notebook(self,bootstyle="dark"); self.nb.pack(fill=BOTH,expand=True,padx=10,pady=(0,10))
        self.tab_perfil=tb.Frame(self.nb,padding=10); self.tab_busca=tb.Frame(self.nb,padding=10); self.tab_ia=tb.Frame(self.nb,padding=10); self.tab_exec=tb.Frame(self.nb,padding=10); self.tab_dash=tb.Frame(self.nb,padding=10); self.tab_hist=tb.Frame(self.nb,padding=10); self.tab_profile=tb.Frame(self.nb,padding=10)
        self.nb.add(self.tab_perfil,text=" 1. Currículo "); self.nb.add(self.tab_busca,text=" 2. Busca & Filtros "); self.nb.add(self.tab_ia,text=" 3. IA & Conexões "); self.nb.add(self.tab_exec,text=" 4. Execução "); self.nb.add(self.tab_dash,text=" 5. Dashboard "); self.nb.add(self.tab_hist,text=" 6. Histórico "); self.nb.add(self.tab_profile,text=" 7. Perfil GitHub ")
        self._build_perfil(); self._build_busca(); self._build_ia(); self._build_exec(); self._build_dash(); self._build_hist(); self._build_profile()
        bottom=tb.Frame(self,padding=(10,0,10,10)); bottom.pack(fill=X)
        tb.Button(bottom,text="Salvar Tudo",bootstyle="success",command=self.save_all).pack(side=LEFT)
        tb.Label(bottom,text="Dica: importe PDF/DOCX do currículo na aba Currículo → Importar. Limite diário evita bloqueio no LinkedIn/Gupy.",bootstyle="secondary",font=("Segoe UI",8)).pack(side=LEFT,padx=12)
        tb.Button(bottom,text="Abrir Relatórios",bootstyle="info-outline",command=lambda:self._open_folder(BASE_DIR/"reports")).pack(side=RIGHT,padx=5)
        tb.Button(bottom,text="Preview PDF",bootstyle="info",command=self.preview_pdf).pack(side=RIGHT)

    # Perfil (com import)
    def save_all(self,silent=False):
        self.curriculum["personal_info"]={"name":self.var_name.get().strip(),"email":self.var_email.get().strip(),"phone":self.var_phone.get().strip(),"location":self.var_location.get().strip(),"linkedin":self.var_linkedin.get().strip(),"github":self.var_github.get().strip()}
        self.curriculum["summary"]=self.txt_summary.get("1.0","end").strip(); save_curriculum(self.curriculum)
        self.env.update(GEMINI_API_KEY=self.var_gemini_key.get().strip(),GEMINI_MODEL=self.var_gemini_model.get().strip() or "gemini-flash-latest",LLM_PROVIDER=self.var_llm_provider.get().strip().lower(),OLLAMA_HOST=self.var_ollama_host.get().strip(),OLLAMA_MODEL=self.var_ollama_model.get().strip(),OPENAI_API_KEY=self.var_openai_key.get().strip(),CLAUDE_API_KEY=self.var_claude_key.get().strip(),GROQ_API_KEY=self.var_groq_key.get().strip(),OPENROUTER_API_KEY=self.var_openrouter_key.get().strip(),OPENROUTER_MODEL=self.var_openrouter_model.get().strip(),CUSTOM_LLM_URL=self.var_custom_url.get().strip(),CUSTOM_LLM_KEY=self.var_custom_key.get().strip(),GITHUB_TOKEN=self.var_github_token.get().strip(),SMTP_HOST=self.var_smtp_host.get().strip(),SMTP_PORT=self.var_smtp_port.get().strip(),SMTP_USER=self.var_smtp_user.get().strip(),SMTP_PASS=self.var_smtp_pass.get().strip(),LINKEDIN_EMAIL=self.var_linkedin_email.get().strip(),LINKEDIN_PASSWORD=self.var_linkedin_pass.get().strip(),GUPY_EMAIL=self.var_gupy_email.get().strip(),GUPY_PASSWORD=self.var_gupy_pass.get().strip(),WORK_MODE=self.var_work_mode.get().strip(),PRESENCIAL_LOCATION=self.var_presencial_loc.get().strip(),CONTRACT_TYPE=self.var_contract.get().strip(),TELEGRAM_BOT_TOKEN=self.var_telegram_token.get().strip(),TELEGRAM_CHAT_ID=self.var_telegram_chat.get().strip(),DAILY_LIMIT=str(int(self.var_daily_limit.get())))
        save_env_dict(self.env)
        cfg={"keywords":[k.strip() for k in self.var_keywords.get().split(",") if k.strip()],"work_mode":self.var_work_mode.get(),"presencial_location":self.var_presencial_loc.get().strip(),"contract_type":self.var_contract.get(),"min_score":int(self.var_min_score.get()),"limit_per_source":int(self.var_limit.get()),"min_salary":int(self.var_min_salary.get()),"level":self.var_level.get(),"exclude_keywords":[k.strip() for k in self.var_exclude.get().split(",") if k.strip()],"mandatory_words":[k.strip() for k in self.var_mandatory.get().split(",") if k.strip()],"blocked_companies":[k.strip() for k in self.var_blocked.get().split(",") if k.strip()],"favorite_companies":[k.strip() for k in self.var_fav.get().split(",") if k.strip()],"max_age_days":int(self.var_max_age.get()),"only_pcd":bool(self.var_only_pcd.get()),"english_filter":self.var_english.get(),"daily_limit":int(self.var_daily_limit.get()),"telegram_bot_token":self.var_telegram_token.get().strip(),"telegram_chat_id":self.var_telegram_chat.get().strip(),"schedule_enabled":bool(self.var_schedule_enabled.get()),"schedule_hour":self.var_schedule_hour.get().strip(),"enable_linkedin_posts":bool(self.var_enable_linkedin_posts.get()),"linkedin_posts_limit":int(self.var_linkedin_posts_limit.get()),"auto_send":bool(self.var_auto_send.get())}
        save_search_config(cfg); self.search_cfg=cfg
        if not silent: messagebox.showinfo("Salvo","Salvo em curriculum_base.json, .env, search_config.json")
        try: self.log_text.insert(tk.END,"[Save] ok\n"); self.log_text.see(tk.END)
        except: pass
    def export_config(self):
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile=f"jobautofit_backup_{datetime.now().strftime('%Y%m%d')}.json")
        if not p: return
        data={"curriculum":self.curriculum,"search_config":self.search_cfg,"env":{k:self.env.get(k,"") for k in ["GEMINI_API_KEY","LLM_PROVIDER","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"]}}
        Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); messagebox.showinfo("Exportar",f"Salvo em {p}")
    def import_config(self):
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not p: return
        try:
            data=json.loads(Path(p).read_text(encoding="utf-8"))
            if "curriculum" in data:
                self.curriculum=data["curriculum"]; save_curriculum(self.curriculum)
                pi=self.curriculum.get("personal_info",{}); self.var_name.set(pi.get("name","")); self.var_email.set(pi.get("email","")); self.var_phone.set(pi.get("phone","")); self.var_location.set(pi.get("location","")); self.var_linkedin.set(pi.get("linkedin","")); self.var_github.set(pi.get("github","")); self.txt_summary.delete("1.0",tk.END); self.txt_summary.insert("1.0",self.curriculum.get("summary","")); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list()
            if "search_config" in data:
                sc=data["search_config"]; self.var_keywords.set(", ".join(sc.get("keywords",[]))); self.var_work_mode.set(sc.get("work_mode","remoto")); self.var_presencial_loc.set(sc.get("presencial_location","")); self.var_contract.set(sc.get("contract_type","indiferente")); self.var_min_score.set(sc.get("min_score",60)); self.var_limit.set(sc.get("limit_per_source",8)); self.var_min_salary.set(sc.get("min_salary",0)); self.var_level.set(sc.get("level","indiferente")); self.var_exclude.set(", ".join(sc.get("exclude_keywords",[]))); self.var_mandatory.set(", ".join(sc.get("mandatory_words",[]))); self.var_blocked.set(", ".join(sc.get("blocked_companies",[]))); self.var_fav.set(", ".join(sc.get("favorite_companies",[]))); self.var_max_age.set(sc.get("max_age_days",0)); self.var_only_pcd.set(sc.get("only_pcd",False)); self.var_english.set(sc.get("english_filter","indiferente")); self.var_daily_limit.set(sc.get("daily_limit",20)); self.var_telegram_token.set(sc.get("telegram_bot_token","")); self.var_telegram_chat.set(sc.get("telegram_chat_id","")); save_search_config(sc)
            messagebox.showinfo("Importar","Importado com sucesso!")
        except Exception as e: messagebox.showerror("Importar",str(e))


if __name__=="__main__":
    App().mainloop()
