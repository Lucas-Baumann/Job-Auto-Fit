import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class Tooltip:
    """Tooltip simples ao passar mouse em ícone ⓘ"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
    def show(self, _):
        if self.tip: return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + 18
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tip, text=self.text, bg="#2b2b2b", fg="#e0e0e0", relief=SOLID, borderwidth=1,
                       font=("Segoe UI", 8), wraplength=300, justify=LEFT, padx=8, pady=6)
        lbl.pack()
    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None

def info_icon(parent, tooltip_text):
    lbl = tb.Label(parent, text=" ⓘ", font=("Segoe UI", 9, "bold"), bootstyle="info", cursor="hand2")
    Tooltip(lbl, tooltip_text)
    return lbl

BASE_DIR = Path(__file__).resolve().parent
CURRICULUM_PATH = BASE_DIR / "curriculum_base.json"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
SEARCH_CONFIG_PATH = BASE_DIR / "search_config.json"
DB_PATH = BASE_DIR / "jobs.db"

def load_curriculum():
    if CURRICULUM_PATH.exists():
        return json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    return {"personal_info":{"name":"","email":"","phone":"","location":"","linkedin":"","github":""},"summary":"","skills":[],"experiences":[],"education":[],"languages":[]}
def save_curriculum(d): CURRICULUM_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2),encoding="utf-8")
def load_env_dict():
    d={}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line: continue
            k,v=line.split("=",1); d[k.strip()]=v.strip()
    return d
def save_env_dict(d):
    lines=[]
    if ENV_EXAMPLE.exists():
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k=line.split("=",1)[0].strip()
                lines.append(f"{k}={d[k]}" if k in d else line)
            else: lines.append(line)
        existing={l.split("=",1)[0].strip() for l in lines if "=" in l and not l.strip().startswith("#")}
        for k,v in d.items():
            if k not in existing: lines.append(f"{k}={v}")
    else:
        for k,v in d.items(): lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines),encoding="utf-8")
def load_search_config():
    if SEARCH_CONFIG_PATH.exists():
        try: return json.loads(SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))
        except: pass
    return {"keywords":["Desenvolvedor Python","Python Developer"],"work_mode":"remoto","presencial_location":"","contract_type":"indiferente","min_score":60,"limit_per_source":8,"min_salary":0,"level":"indiferente","exclude_keywords":[],"mandatory_words":[],"blocked_companies":[],"favorite_companies":[],"max_age_days":0,"only_pcd":False,"english_filter":"indiferente","daily_limit":20,"telegram_bot_token":"","telegram_chat_id":"","schedule_enabled":False,"schedule_hour":"08:00","enable_linkedin_posts":True,"linkedin_posts_limit":8}
def save_search_config(c): SEARCH_CONFIG_PATH.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding="utf-8")

class App(tb.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("JobAutoFit — Automação Completa (Gupy / LinkedIn / ATS)")
        self.geometry("1280x820"); self.minsize(1200,750)
        self.curriculum=load_curriculum(); self.env=load_env_dict(); self.search_cfg=load_search_config()
        # vars perfil
        self.var_name=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("name",""))
        self.var_email=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("email",""))
        self.var_phone=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("phone",""))
        self.var_location=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("location",""))
        self.var_linkedin=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("linkedin",""))
        self.var_github=tk.StringVar(value=self.curriculum.get("personal_info",{}).get("github",""))
        # ia
        self.var_gemini_key=tk.StringVar(value=self.env.get("GEMINI_API_KEY",""))
        self.var_llm_provider=tk.StringVar(value=self.env.get("LLM_PROVIDER","gemini"))
        self.var_ollama_host=tk.StringVar(value=self.env.get("OLLAMA_HOST","http://localhost:11434"))
        self.var_ollama_model=tk.StringVar(value=self.env.get("OLLAMA_MODEL","llama3:latest"))
        self.var_openai_key=tk.StringVar(value=self.env.get("OPENAI_API_KEY",""))
        self.var_claude_key=tk.StringVar(value=self.env.get("CLAUDE_API_KEY",""))
        self.var_groq_key=tk.StringVar(value=self.env.get("GROQ_API_KEY",""))
        self.var_openrouter_key=tk.StringVar(value=self.env.get("OPENROUTER_API_KEY",""))
        self.var_openrouter_model=tk.StringVar(value=self.env.get("OPENROUTER_MODEL","meta-llama/llama-3.1-8b-instruct:free"))
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
    def _build_perfil(self):
        f=self.tab_perfil
        card=tb.Labelframe(f,text="Dados Pessoais",padding=10,bootstyle="info"); card.pack(fill=X,pady=5)
        grid=tb.Frame(card); grid.pack(fill=X)
        for c in range(4): grid.columnconfigure(c,weight=1)
        tb.Label(grid,text="Nome completo").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_name).grid(row=0,column=1,sticky=EW,padx=5,pady=3,columnspan=3)
        tb.Label(grid,text="E-mail").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_email).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(grid,text="Telefone").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_phone).grid(row=1,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(grid,text="Localização").grid(row=2,column=0,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_location).grid(row=2,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(grid,text="LinkedIn URL").grid(row=2,column=2,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_linkedin).grid(row=2,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(grid,text="GitHub / Portfólio").grid(row=3,column=0,sticky=W,padx=5,pady=3); tb.Entry(grid,textvariable=self.var_github).grid(row=3,column=1,sticky=EW,padx=5,pady=3,columnspan=2)
        tb.Button(grid,text="Importar PDF/DOCX/TXT",bootstyle="warning-outline",command=self.import_cv_file).grid(row=3,column=3,padx=5,pady=3,sticky=EW)
        card2=tb.Labelframe(f,text="Resumo Profissional (IA reescreve mantendo contexto)",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        self.txt_summary=tk.Text(card2,height=4,wrap="word",bg="#2b2b2b",fg="#e0e0e0",insertbackground="white"); self.txt_summary.pack(fill=X); self.txt_summary.insert("1.0",self.curriculum.get("summary",""))
        cols=tb.Frame(f); cols.pack(fill=BOTH,expand=True,pady=5)
        for i in range(3): cols.columnconfigure(i,weight=1)
        self.card_skills=tb.Labelframe(cols,text="Skills (ATS)",padding=8,bootstyle="success"); self.card_skills.grid(row=0,column=0,sticky=NSEW,padx=5)
        self.lst_skills=tk.Listbox(self.card_skills,height=8,bg="#1e1e1e",fg="white"); self.lst_skills.pack(fill=BOTH,expand=True)
        row=tb.Frame(self.card_skills); row.pack(fill=X,pady=4)
        self.ent_skill=tb.Entry(row); self.ent_skill.pack(side=LEFT,fill=X,expand=True,padx=(0,5)); self.ent_skill.bind("<Return>",lambda e:self.add_skill())
        tb.Button(row,text="+",width=4,bootstyle="success",command=self.add_skill).pack(side=LEFT); tb.Button(row,text="–",width=4,bootstyle="danger-outline",command=self.del_skill).pack(side=LEFT,padx=2)
        self.card_exp=tb.Labelframe(cols,text="Experiências",padding=8,bootstyle="warning"); self.card_exp.grid(row=0,column=1,sticky=NSEW,padx=5)
        self.lst_exp=tk.Listbox(self.card_exp,height=8,bg="#1e1e1e",fg="white"); self.lst_exp.pack(fill=BOTH,expand=True); self.lst_exp.bind("<Double-Button-1>",lambda e:self.edit_exp())
        btns=tb.Frame(self.card_exp); btns.pack(fill=X,pady=4)
        tb.Button(btns,text="Adicionar",bootstyle="warning",command=self.add_exp).pack(side=LEFT,fill=X,expand=True,padx=1); tb.Button(btns,text="Editar",bootstyle="secondary",command=self.edit_exp).pack(side=LEFT,fill=X,expand=True,padx=1); tb.Button(btns,text="Remover",bootstyle="danger-outline",command=self.del_exp).pack(side=LEFT,fill=X,expand=True,padx=1)
        self.card_edu=tb.Labelframe(cols,text="Formação",padding=8,bootstyle="info"); self.card_edu.grid(row=0,column=2,sticky=NSEW,padx=5)
        self.lst_edu=tk.Listbox(self.card_edu,height=8,bg="#1e1e1e",fg="white"); self.lst_edu.pack(fill=BOTH,expand=True); self.lst_edu.bind("<Double-Button-1>",lambda e:self.edit_edu())
        btns2=tb.Frame(self.card_edu); btns2.pack(fill=X,pady=4)
        tb.Button(btns2,text="Adicionar",bootstyle="info",command=self.add_edu).pack(side=LEFT,fill=X,expand=True,padx=1); tb.Button(btns2,text="Editar",bootstyle="secondary",command=self.edit_edu).pack(side=LEFT,fill=X,expand=True,padx=1); tb.Button(btns2,text="Remover",bootstyle="danger-outline",command=self.del_edu).pack(side=LEFT,fill=X,expand=True,padx=1)
    def _refresh_skills_list(self):
        self.lst_skills.delete(0,tk.END)
        for s in self.curriculum.get("skills",[]): self.lst_skills.insert(tk.END,s)
    def add_skill(self):
        v=self.ent_skill.get().strip()
        if v: self.curriculum.setdefault("skills",[]).append(v); self.ent_skill.delete(0,tk.END); self._refresh_skills_list()
    def del_skill(self):
        sel=self.lst_skills.curselection()
        if sel: self.curriculum["skills"].pop(sel[0]); self._refresh_skills_list()
    def _refresh_exp_list(self):
        self.lst_exp.delete(0,tk.END)
        for e in self.curriculum.get("experiences",[]): self.lst_exp.insert(tk.END,f"{e.get('position','')} @ {e.get('company','')} ({e.get('period','')})")
    def _exp_dialog(self,data=None):
        top=tb.Toplevel(self); top.title("Experiência"); top.geometry("560x360"); top.transient(self); top.grab_set()
        vals=data or {"company":"","position":"","period":"","highlights":[]}
        v_company=tk.StringVar(value=vals.get("company","")); v_position=tk.StringVar(value=vals.get("position","")); v_period=tk.StringVar(value=vals.get("period",""))
        tb.Label(top,text="Empresa").pack(anchor=W,padx=10,pady=(10,0)); tb.Entry(top,textvariable=v_company).pack(fill=X,padx=10)
        tb.Label(top,text="Cargo").pack(anchor=W,padx=10,pady=(8,0)); tb.Entry(top,textvariable=v_position).pack(fill=X,padx=10)
        tb.Label(top,text="Período").pack(anchor=W,padx=10,pady=(8,0)); tb.Entry(top,textvariable=v_period).pack(fill=X,padx=10)
        tb.Label(top,text="Destaques (um por linha)").pack(anchor=W,padx=10,pady=(8,0)); txt=tk.Text(top,height=6,bg="#1e1e1e",fg="white"); txt.pack(fill=BOTH,expand=True,padx=10); txt.insert("1.0","\n".join(vals.get("highlights",[])))
        result={}
        def ok(): result.update(company=v_company.get().strip(),position=v_position.get().strip(),period=v_period.get().strip(),highlights=[l.strip() for l in txt.get("1.0","end").splitlines() if l.strip()]); top.destroy()
        tb.Button(top,text="Salvar",bootstyle="success",command=ok).pack(pady=10); self.wait_window(top); return result if result else None
    def add_exp(self):
        d=self._exp_dialog()
        if d and d.get("company"): self.curriculum.setdefault("experiences",[]).append(d); self._refresh_exp_list()
    def edit_exp(self):
        sel=self.lst_exp.curselection()
        if not sel: return
        idx=sel[0]; d=self._exp_dialog(self.curriculum["experiences"][idx])
        if d: self.curriculum["experiences"][idx]=d; self._refresh_exp_list()
    def del_exp(self):
        sel=self.lst_exp.curselection()
        if sel: self.curriculum["experiences"].pop(sel[0]); self._refresh_exp_list()
    def _refresh_edu_list(self):
        self.lst_edu.delete(0,tk.END)
        for e in self.curriculum.get("education",[]): self.lst_edu.insert(tk.END,f"{e.get('degree','')} - {e.get('institution','')} ({e.get('year','')})")
    def _edu_dialog(self,data=None):
        top=tb.Toplevel(self); top.title("Formação"); top.geometry("480x220"); top.transient(self); top.grab_set()
        vals=data or {"degree":"","institution":"","year":""}; v_degree=tk.StringVar(value=vals.get("degree","")); v_inst=tk.StringVar(value=vals.get("institution","")); v_year=tk.StringVar(value=vals.get("year",""))
        tb.Label(top,text="Curso / Título").pack(anchor=W,padx=10,pady=(10,0)); tb.Entry(top,textvariable=v_degree).pack(fill=X,padx=10)
        tb.Label(top,text="Instituição").pack(anchor=W,padx=10,pady=(8,0)); tb.Entry(top,textvariable=v_inst).pack(fill=X,padx=10)
        tb.Label(top,text="Ano / Período").pack(anchor=W,padx=10,pady=(8,0)); tb.Entry(top,textvariable=v_year).pack(fill=X,padx=10)
        result={}
        def ok(): result.update(degree=v_degree.get().strip(),institution=v_inst.get().strip(),year=v_year.get().strip()); top.destroy()
        tb.Button(top,text="Salvar",bootstyle="success",command=ok).pack(pady=10); self.wait_window(top); return result if result else None
    def add_edu(self):
        d=self._edu_dialog()
        if d and d.get("degree"): self.curriculum.setdefault("education",[]).append(d); self._refresh_edu_list()
    def edit_edu(self):
        sel=self.lst_edu.curselection()
        if not sel: return
        d=self._edu_dialog(self.curriculum["education"][sel[0]])
        if d: self.curriculum["education"][sel[0]]=d; self._refresh_edu_list()
    def del_edu(self):
        sel=self.lst_edu.curselection()
        if sel: self.curriculum["education"].pop(sel[0]); self._refresh_edu_list()
    def import_cv_file(self):
        p=filedialog.askopenfilename(filetypes=[("PDF/DOCX/TXT","*.pdf *.docx *.txt"),("Todos","*.*")])
        if not p: return
        try:
            # salvar IA config atual antes de verificar (usuário pode ter testado OK mas não salvado)
            try: self.save_all(silent=True)
            except: pass
            from importer import import_file_to_curriculum
            from config import Config
            # verificar IA tanto via Config (salvo) quanto via GUI vars (atual)
            has_llm_cfg = any([Config.GEMINI_API_KEY, Config.OPENAI_API_KEY, Config.CLAUDE_API_KEY, Config.GROQ_API_KEY, Config.OPENROUTER_API_KEY, Config.CUSTOM_LLM_KEY]) or Config.LLM_PROVIDER=="ollama"
            has_llm_gui = any([self.var_gemini_key.get().strip(), self.var_openai_key.get().strip(), self.var_claude_key.get().strip(), self.var_groq_key.get().strip(), self.var_openrouter_key.get().strip(), self.var_custom_key.get().strip()])
            has_llm = has_llm_cfg or has_llm_gui
            if not has_llm:
                self._log("[Import] Sem IA configurada → usando heurístico. Para melhor análise de experiências/formação, configure OpenRouter/Gemini na aba 3.")
            parsed=import_file_to_curriculum(Path(p))
            # merge personal_info (inclui location)
            for k in ["name","email","phone","linkedin","github","location"]:
                if parsed.get("personal_info",{}).get(k): self.curriculum.setdefault("personal_info",{})[k]=parsed["personal_info"][k]
            if parsed.get("skills"): self.curriculum["skills"]=list(dict.fromkeys(self.curriculum.get("skills",[])+parsed["skills"]))
            if parsed.get("summary") and not self.txt_summary.get("1.0","end").strip(): 
                self.txt_summary.delete("1.0",tk.END); self.txt_summary.insert("1.0",parsed["summary"])
            elif parsed.get("summary"):
                # se já tem resumo, mostra mas não sobrescreve automaticamente
                pass
            # experiências e formação (novo)
            if parsed.get("experiences"):
                self.curriculum["experiences"]=parsed["experiences"]
            if parsed.get("education"):
                self.curriculum["education"]=parsed["education"]
            if parsed.get("languages"):
                self.curriculum["languages"]=parsed["languages"]
            # refresh UI
            pi=self.curriculum.get("personal_info",{})
            self.var_name.set(pi.get("name","")); self.var_email.set(pi.get("email","")); self.var_phone.set(pi.get("phone","")); self.var_location.set(pi.get("location","")); self.var_linkedin.set(pi.get("linkedin","")); self.var_github.set(pi.get("github",""))
            self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list()
            # mensagem com aviso sobre IA
            exp_count=len(parsed.get("experiences",[]))
            edu_count=len(parsed.get("education",[]))
            msg=f"Importado de {Path(p).name}\nExperiências: {exp_count} | Formação: {edu_count} | Skills: {len(parsed.get('skills',[]))}\nRevise os campos antes de salvar."
            if not has_llm:
                msg+="\n\n⚠ Sem IA configurada — análise heurística. Com IA (aba 3 → OpenRouter/Gemini) a extração de experiências/formação é 100% precisa e preenche automaticamente."
                messagebox.showwarning("Importar — IA recomendada",msg)
            else:
                messagebox.showinfo("Importar",msg + "\n\n✓ IA usada para melhor análise.")
        except Exception as e: messagebox.showerror("Importar",str(e))
    def suggest_mandatory(self):
        skills = self.curriculum.get("skills", [])
        if not skills:
            messagebox.showwarning("Sugerir", "Adicione skills no currículo primeiro (aba Currículo).")
            return
        sug = ", ".join(skills[:8])
        self.var_mandatory.set(sug)
        self._log(f"[Sugestão] Palavras obrigatórias preenchidas: {sug}")

    # Busca avançada
    def _build_busca(self):
        f=self.tab_busca
        # scroll
        canvas=tk.Canvas(f,bg="#222222",highlightthickness=0); sb=tb.Scrollbar(f,orient=VERTICAL,command=canvas.yview); canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT,fill=Y); canvas.pack(side=LEFT,fill=BOTH,expand=True)
        inner=tb.Frame(canvas); canvas.create_window((0,0),window=inner,anchor="nw")
        inner.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # scroll com roda do mouse (fix: antes não detectava)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        # Windows
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # Linux
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        # garante foco ao entrar na aba
        inner.bind("<Enter>", lambda e: canvas.focus_set())
        card=tb.Labelframe(inner,text="Palavras-chave (vírgula)",padding=10,bootstyle="primary"); card.pack(fill=X,pady=5)
        tb.Entry(card,textvariable=self.var_keywords).pack(fill=X)
        tb.Label(card,text="Ex: Desenvolvedor Python, Backend, Django, FastAPI, AWS",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W,pady=(4,0))
        grid=tb.Frame(inner); grid.pack(fill=X,pady=5)
        grid.columnconfigure(1,weight=1); grid.columnconfigure(3,weight=1)
        tb.Label(grid,text="Regime").grid(row=0,column=0,sticky=W,padx=5,pady=4); cb=tb.Combobox(grid,textvariable=self.var_work_mode,values=["remoto","presencial","hibrido","indiferente"],state="readonly",width=16); cb.grid(row=0,column=1,sticky=W,padx=5,pady=4); cb.bind("<<ComboboxSelected>>",lambda e:self._bind_work_mode())
        tb.Label(grid,text="Contrato").grid(row=0,column=2,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_contract,values=["clt","pj","indiferente"],state="readonly",width=16).grid(row=0,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Nível").grid(row=1,column=0,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_level,values=["indiferente","estagio","junior","pleno","senior"],state="readonly",width=16).grid(row=1,column=1,sticky=W,padx=5,pady=4)
        info_icon(grid, "Filtra por senioridade no título/descrição.\nIndiferente = não filtra").grid(row=1,column=0,sticky=E,padx=(60,0))
        tb.Label(grid,text="Inglês").grid(row=1,column=2,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_english,values=["indiferente","sim","nao"],state="readonly",width=16).grid(row=1,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Salário mínimo (R$)").grid(row=2,column=0,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=0,to=50000,textvariable=self.var_min_salary,width=16, increment=500).grid(row=2,column=1,sticky=W,padx=5,pady=4)
        info_icon(grid, "Extrai R$ do texto da vaga. Se não achar salário, não filtra.").grid(row=2,column=0,sticky=E,padx=(110,0))
        tb.Label(grid,text="Idade max vaga (dias, 0=ignorar)").grid(row=2,column=2,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=0,to=60,textvariable=self.var_max_age,width=16).grid(row=2,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Limite diário envios").grid(row=3,column=0,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=1,to=100,textvariable=self.var_daily_limit,width=16).grid(row=3,column=1,sticky=W,padx=5,pady=4)
        info_icon(grid, "Máximo de vagas processadas por dia.\n>30 = alto risco de softban no LinkedIn (erro 999/429, IP bloqueado 15min-24h).\nRecomendado: 15-20.").grid(row=3,column=0,sticky=E,padx=(120,0))
        tb.Checkbutton(grid,text="Apenas vagas PCD",variable=self.var_only_pcd,bootstyle="round-toggle").grid(row=3,column=2,sticky=W,padx=5,pady=4)
        info_icon(grid, "Só passa vaga com 'PCD'/'pessoa com deficiência' no texto").grid(row=3,column=2,sticky=E,padx=(130,0))
        # aviso dinâmico de ban — sempre visível quando em risco
        self.lbl_ban_warning=tb.Label(inner, text="", font=("Segoe UI", 8, "bold"), bootstyle="danger", wraplength=900, justify=LEFT)
        self.lbl_ban_warning.pack(fill=X, pady=(2,4))
        self.frame_presencial=tb.Labelframe(inner,text="Localização Presencial / Híbrido",padding=10,bootstyle="warning"); self.frame_presencial.pack(fill=X,pady=5)
        tb.Label(self.frame_presencial,text="Cidade/Estado ex: São Paulo, SP").pack(anchor=W); tb.Entry(self.frame_presencial,textvariable=self.var_presencial_loc).pack(fill=X,pady=4)
        card2=tb.Labelframe(inner,text="Palavras-chave avançadas",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        r=tb.Frame(card2); r.pack(fill=X); tb.Label(r,text="Excluir vagas que contenham (vírgula)").pack(side=LEFT); info_icon(r, "Se título/descrição contiver qualquer termo aqui, vaga é descartada.\nEx: estágio, temporário, banco de talentos").pack(side=LEFT)
        tb.Entry(card2,textvariable=self.var_exclude).pack(fill=X,pady=2)
        r2=tb.Frame(card2); r2.pack(fill=X,pady=(6,0)); tb.Label(r2,text="Palavras obrigatórias (pelo menos uma, vírgula)").pack(side=LEFT); info_icon(r2, "Vaga só passa se contiver PELO MENOS UMA dessas palavras.\nNÃO é preenchido automaticamente — você define.\nDica: use 'Sugerir do currículo' para preencher com suas skills.").pack(side=LEFT)
        tb.Entry(card2,textvariable=self.var_mandatory).pack(fill=X,pady=2)
        tb.Button(card2,text="Sugerir do currículo (preenche com suas skills)",bootstyle="info-outline",command=self.suggest_mandatory).pack(anchor=W,pady=2)
        r3=tb.Frame(card2); r3.pack(fill=X,pady=(6,0)); tb.Label(r3,text="Empresas bloqueadas (vírgula)").pack(side=LEFT); info_icon(r3, "Empresas que você NÃO quer — vagas delas são ignoradas.\nEx: Empresa X, Consultoria Y").pack(side=LEFT)
        tb.Entry(card2,textvariable=self.var_blocked).pack(fill=X,pady=2)
        r4=tb.Frame(card2); r4.pack(fill=X,pady=(6,0)); tb.Label(r4,text="Empresas favoritas (destaca no relatório, vírgula)").pack(side=LEFT); info_icon(r4, "Apenas destaca no relatório HTML, não filtra.\nUse para priorizar visualmente.").pack(side=LEFT)
        tb.Entry(card2,textvariable=self.var_fav).pack(fill=X,pady=2)
        card3=tb.Labelframe(inner,text="Parâmetros ATS",padding=10,bootstyle="success"); card3.pack(fill=X,pady=5)
        row=tb.Frame(card3); row.pack(fill=X)
        tb.Label(row,text="Score mínimo %").pack(side=LEFT,padx=5); tb.Scale(row,from_=0,to=100,variable=self.var_min_score,length=200,bootstyle="success").pack(side=LEFT,padx=5); tb.Label(row,textvariable=self.var_min_score,width=4).pack(side=LEFT)
        tb.Label(row,text="Vagas/fonte").pack(side=LEFT,padx=(20,5)); tb.Spinbox(row,from_=1,to=30,textvariable=self.var_limit,width=6).pack(side=LEFT)
        info_icon(row, "Vagas por fonte (Gupy/LinkedIn/Remotive).\n>12 por fonte = risco de 429/softban. Recomendado: 8-10.\nO LinkedIn Jobs Guest bloqueia com muitas req/seg.").pack(side=LEFT)
        # LinkedIn posts de recrutadores
        card_posts=tb.Labelframe(inner,text="LinkedIn — Posts de Recrutadores (nova fonte)",padding=10,bootstyle="warning"); card_posts.pack(fill=X,pady=5)
        row_posts=tb.Frame(card_posts); row_posts.pack(fill=X)
        tb.Checkbutton(row_posts,text="Buscar também posts de recrutadores no LinkedIn",variable=self.var_enable_linkedin_posts,bootstyle="round-toggle").pack(side=LEFT,padx=5)
        info_icon(row_posts, "Ativa coleta em posts/feed de recrutadores no LinkedIn (ex: 'Estamos contratando').\nFiltra por sinais de recrutador (Recruiter/RH/Talent) + keywords de vaga.\nSem login usa scraping guest (frágil, pode pegar poucos). Com login + Playwright é mais confiável.\nExpande automaticamente: Python Developer → 'Python Developer vaga contratando hiring'").pack(side=LEFT)
        row_posts2=tb.Frame(card_posts); row_posts2.pack(fill=X,pady=4)
        tb.Label(row_posts2,text="Limite posts/keyword").pack(side=LEFT,padx=5); tb.Spinbox(row_posts2,from_=1,to=20,textvariable=self.var_linkedin_posts_limit,width=6).pack(side=LEFT,padx=5)
        info_icon(row_posts2, "Limite de posts por keyword.\n>10 sem login (guest) = falha/authwall garantida. Com login + Playwright suporta 10-15.\nCada post = 1 request + 1 detalhe, respeita daily_limit.").pack(side=LEFT)
        tb.Label(row_posts2,text="Requer PLAYWRIGHT + login para melhor taxa. Delay + daily_limit evitam softban.",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT,padx=10)
        # agendamento
        card4=tb.Labelframe(inner,text="Agendamento + Notificações",padding=10,bootstyle="secondary"); card4.pack(fill=X,pady=5)
        tb.Checkbutton(card4,text="Ativar agendamento diário",variable=self.var_schedule_enabled,bootstyle="round-toggle").pack(anchor=W,pady=2)
        row2=tb.Frame(card4); row2.pack(fill=X,pady=4)
        tb.Label(row2,text="Horário (HH:MM)").pack(side=LEFT,padx=5); tb.Entry(row2,textvariable=self.var_schedule_hour,width=10).pack(side=LEFT,padx=5)
        tb.Button(row2,text="Agendar",bootstyle="secondary-outline",command=self.setup_schedule).pack(side=LEFT,padx=5)
        tb.Label(card4,text="Telegram (opcional): crie bot no @BotFather e informe token + chat_id",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W,pady=(6,0))
        row3=tb.Frame(card4); row3.pack(fill=X,pady=4)
        tb.Label(row3,text="Bot Token").pack(side=LEFT,padx=5); tb.Entry(row3,textvariable=self.var_telegram_token,width=36,show="*").pack(side=LEFT,padx=5,fill=X,expand=True)
        tb.Label(row3,text="Chat ID").pack(side=LEFT,padx=5); tb.Entry(row3,textvariable=self.var_telegram_chat,width=16).pack(side=LEFT,padx=5)
        tb.Button(row3,text="Testar Telegram",bootstyle="info-outline",command=self.test_telegram).pack(side=LEFT,padx=5)
        # hooks para aviso de ban dinâmico
        for v in (self.var_limit, self.var_daily_limit, self.var_linkedin_posts_limit):
            try: v.trace_add("write", lambda *_: self._check_ban_risk())
            except: pass
        try: self.var_enable_linkedin_posts.trace_add("write", lambda *_: self._check_ban_risk())
        except: pass
        self.after(500, self._check_ban_risk)
    def _check_ban_risk(self, *_):
        if not hasattr(self, 'lbl_ban_warning'): return
        msgs=[]
        try: lim = int(self.var_limit.get())
        except: lim=8
        try: daily = int(self.var_daily_limit.get())
        except: daily=20
        try: posts_lim = int(self.var_linkedin_posts_limit.get())
        except: posts_lim=8
        enable_posts = bool(self.var_enable_linkedin_posts.get()) if hasattr(self, 'var_enable_linkedin_posts') else False
        has_login = bool(self.var_linkedin_email.get().strip() and self.var_linkedin_pass.get().strip()) if hasattr(self, 'var_linkedin_email') else False
        if lim > 12:
            msgs.append(f"Vagas/fonte={lim} (>12) → risco 429/softban LinkedIn/Gupy")
        elif lim > 10:
            msgs.append(f"Vagas/fonte={lim} (>10) → moderado risco de bloqueio")
        if daily > 30:
            msgs.append(f"Limite diário={daily} (>30) → alto risco softban 999 (IP bloqueado 15min-24h)")
        elif daily > 20:
            msgs.append(f"Limite diário={daily} (>20) → risco elevado, recomendado 15-20")
        if enable_posts:
            if not has_login and posts_lim > 8:
                msgs.append(f"Posts={posts_lim} sem login → guest falha/authwall (use login+Playwright ou ≤8)")
            elif posts_lim > 12:
                msgs.append(f"Posts={posts_lim} (>12) → mesmo com login, risco de bloqueio")
        if msgs:
            self.lbl_ban_warning.config(text="⚠ " + " | ".join(msgs), bootstyle="danger")
        else:
            self.lbl_ban_warning.config(text="✓ Limites seguros — ritmo humano, baixo risco de ban", bootstyle="success")
    def _bind_work_mode(self):
        mode=self.var_work_mode.get()
        if mode in ("presencial","hibrido"): self.frame_presencial.pack(fill=X,pady=5)
        else: self.frame_presencial.pack_forget()
    def setup_schedule(self):
        if not self.var_schedule_enabled.get(): messagebox.showinfo("Agendamento","Ative a opção primeiro."); return
        hour=self.var_schedule_hour.get().strip()
        if not re.match(r"^\d{2}:\d{2}$",hour): messagebox.showwarning("Agendamento","Formato HH:MM ex: 08:00"); return
        self.save_all(silent=True); messagebox.showinfo("Agendamento",f"Agendamento salvo para {hour} diário.\nDeixe a GUI aberta — ela dispara automaticamente.\nOu use Task Scheduler com: python main.py")
        self._schedule_loop()
    def _schedule_loop(self):
        if not self.var_schedule_enabled.get(): return
        now=datetime.now().strftime("%H:%M")
        if now==self.var_schedule_hour.get().strip():
            self._log(f"[Agendamento] Disparando execução automática às {now}")
            self.run_automation()
        self.after(60000, self._schedule_loop)
    def test_telegram(self):
        token=self.var_telegram_token.get().strip(); chat=self.var_telegram_chat.get().strip()
        if not token or not chat: messagebox.showwarning("Telegram","Informe token e chat_id"); return
        try:
            import requests
            r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":"JobAutoFit: teste OK ✔️"},timeout=8)
            if r.status_code==200: messagebox.showinfo("Telegram","Mensagem enviada!")
            else: messagebox.showerror("Telegram",r.text[:400])
        except Exception as e: messagebox.showerror("Telegram",str(e))

    # IA
    def _build_ia(self):
        f=self.tab_ia
        card=tb.Labelframe(f,text="Provedor IA (gratuito ou pago) — campo OPCIONAL",padding=10,bootstyle="success"); card.pack(fill=X,pady=5)
        row_prov=tb.Frame(card); row_prov.pack(fill=X)
        tb.Label(row_prov,text="Provedor").pack(side=LEFT,padx=5); self.combo_llm=tb.Combobox(row_prov,textvariable=self.var_llm_provider,values=["gemini","ollama","openai","claude","groq","openrouter","custom"],state="readonly",width=16); self.combo_llm.pack(side=LEFT,padx=5)
        info_icon(row_prov, "Escolha a IA que reescreve seu currículo/Carta para o ATS.\n• gemini = gratuito (aistudio.google.com)\n• ollama = local gratuito\n• openai/claude/groq = pago\n• openrouter = free tier (openrouter.ai/keys) :free").pack(side=LEFT)
        self.btn_test_gemini=tb.Button(row_prov,text="Testar Conexão",bootstyle="success-outline",command=self.test_gemini); self.btn_test_gemini.pack(side=LEFT,padx=5)
        self.lbl_ai_status=tb.Label(card,text="",font=("Segoe UI",8,"bold")); self.lbl_ai_status.pack(anchor=W,pady=(6,0))
        tb.Label(card,text="Gemini gratuito: aistudio.google.com/app/apikey — deixe em branco para heurístico.",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W)
        # container dinâmico — mostra só o provider selecionado
        self.frame_ia_dynamic=tb.Frame(card); self.frame_ia_dynamic.pack(fill=X,pady=6)
        self.frame_gemini=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_gemini,text="Gemini Key").pack(side=LEFT,padx=5); self.ent_gemini=tb.Entry(self.frame_gemini,textvariable=self.var_gemini_key,show="*",width=40); self.ent_gemini.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_gemini, "Chave gratuita do Google Gemini. Deixe em branco para heurístico.").pack(side=LEFT)
        def toggle(): self.ent_gemini.config(show="" if self.ent_gemini.cget("show")=="*" else "*"); btn_show.config(text="Ocultar" if self.ent_gemini.cget("show")=="" else "Mostrar")
        btn_show=tb.Button(self.frame_gemini,text="Mostrar",bootstyle="secondary-outline",command=toggle,width=8); btn_show.pack(side=LEFT,padx=5)
        self.frame_ollama=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_ollama,text="Ollama Host").pack(side=LEFT,padx=5); self.ent_ollama_host=tb.Entry(self.frame_ollama,textvariable=self.var_ollama_host,width=28); self.ent_ollama_host.pack(side=LEFT,padx=5)
        info_icon(self.frame_ollama, "IA local gratuita. Instale em ollama.com e rode 'ollama run llama3'").pack(side=LEFT)
        tb.Label(self.frame_ollama,text="Modelo").pack(side=LEFT,padx=5); self.ent_ollama_model=tb.Entry(self.frame_ollama,textvariable=self.var_ollama_model,width=18); self.ent_ollama_model.pack(side=LEFT,padx=5)
        self.frame_openai=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_openai,text="OpenAI Key").pack(side=LEFT,padx=5); self.ent_openai=tb.Entry(self.frame_openai,textvariable=self.var_openai_key,show="*",width=40); self.ent_openai.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_openai, "platform.openai.com/api-keys — pago, modelo gpt-4o-mini").pack(side=LEFT)
        self.frame_claude=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_claude,text="Claude Key").pack(side=LEFT,padx=5); self.ent_claude=tb.Entry(self.frame_claude,textvariable=self.var_claude_key,show="*",width=40); self.ent_claude.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_claude, "console.anthropic.com — pago, modelo claude-3-haiku").pack(side=LEFT)
        self.frame_groq=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_groq,text="Groq Key").pack(side=LEFT,padx=5); self.ent_groq=tb.Entry(self.frame_groq,textvariable=self.var_groq_key,show="*",width=40); self.ent_groq.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_groq, "console.groq.com — gratuito/pago, rápido").pack(side=LEFT)
        self.frame_openrouter=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_openrouter,text="OpenRouter Key").pack(side=LEFT,padx=5); self.ent_openrouter=tb.Entry(self.frame_openrouter,textvariable=self.var_openrouter_key,show="*",width=28); self.ent_openrouter.pack(side=LEFT,padx=5)
        info_icon(self.frame_openrouter, "openrouter.ai/keys → Free tier :free sem cartão").pack(side=LEFT)
        tb.Label(self.frame_openrouter,text="Modelo").pack(side=LEFT,padx=5); self.combo_openrouter_model=tb.Combobox(self.frame_openrouter,textvariable=self.var_openrouter_model,values=["google/gemma-4-26b-a4b-it:free","google/gemma-4-31b-it:free","nvidia/nemotron-3.5-lightning:free","liquid/lfm-2.5-2.6b:free","inclusionai/ling-3.0-flash-fin:free","nvidia/nemotron-3-super-120b-a12b:free","minimax/minimax-m2.7:free","nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"],width=36); self.combo_openrouter_model.pack(side=LEFT,padx=5)
        tb.Button(self.frame_openrouter,text="↗ Lista free",bootstyle="info-outline",width=10,command=lambda: webbrowser.open("https://openrouter.ai/models?max_price=0")).pack(side=LEFT,padx=5)
        info_icon(self.frame_openrouter, "Digite manualmente o slug :free visto na lista (copie de openrouter.ai/models?max_price=0). Lista muda; se 404, tente outro.").pack(side=LEFT)
        self.frame_custom=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_custom,text="Custom URL").pack(side=LEFT,padx=5); self.ent_custom_url=tb.Entry(self.frame_custom,textvariable=self.var_custom_url,width=38); self.ent_custom_url.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_custom, "Ex: https://api.deepseek.com/v1/chat/completions").pack(side=LEFT)
        tb.Label(self.frame_custom,text="Custom Key").pack(side=LEFT,padx=5); self.ent_custom_key=tb.Entry(self.frame_custom,textvariable=self.var_custom_key,show="*",width=22); self.ent_custom_key.pack(side=LEFT,padx=5)
        # trace para habilitar/desabilitar
        self.var_gemini_key.trace_add("write", lambda *_: self._update_ai_state())
        self.var_openrouter_key.trace_add("write", lambda *_: self._update_ai_state())
        self.var_llm_provider.trace_add("write", lambda *_: self._update_ai_state())
        self.after(300, self._update_ai_state)
        card2=tb.Labelframe(f,text="E-mail SMTP (envio automático, opcional)",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        hdr2=tb.Frame(card2); hdr2.pack(fill=X); tb.Label(hdr2,text="Envia currículos automaticamente por e-mail quando a vaga divulga e-mail de contato",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT); info_icon(hdr2, "SMTP = protocolo de envio de e-mail.\nGmail: smtp.gmail.com:587 + Senha de App (myaccount.google.com > Segurança > Senhas de app).\nOutlook: smtp.office365.com:587\nSe deixar vazio, o sistema só gera PDFs e relatório (não envia).").pack(side=LEFT,padx=4)
        g=tb.Frame(card2); g.pack(fill=X, pady=(6,0)); g.columnconfigure(1,weight=1); g.columnconfigure(3,weight=1)
        tb.Label(g,text="Host").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_host).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Porta").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_port,width=8).grid(row=0,column=3,sticky=W,padx=5,pady=3)
        tb.Label(g,text="Usuário").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_user).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Senha / App Pass").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(card2,text="Se vazio, não envia e-mail — apenas gera PDFs.",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W, pady=(4,0))
        card3=tb.Labelframe(f,text="LinkedIn / Gupy (automação navegador, opcional)",padding=10,bootstyle="warning"); card3.pack(fill=X,pady=5)
        hdr3=tb.Frame(card3); hdr3.pack(fill=X); tb.Label(hdr3,text="Playwright preenche formulários com ritmo humano; CAPTCHA/teste pausa para você",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT); info_icon(hdr3, "Automação de navegador real (Playwright).\nLinkedIn Easy Apply e Gupy: abre Chromium visível, clica em Candidatar-se e anexa PDF.\nPrecisa login. Deixe vazio para modo manual (só relatório).").pack(side=LEFT,padx=4)
        g2=tb.Frame(card3); g2.pack(fill=X); g2.columnconfigure(1,weight=1); g2.columnconfigure(3,weight=1)
        tb.Label(g2,text="LinkedIn Email").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_email).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_pass,show="*").grid(row=0,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Gupy Email").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_email).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)

    def _update_ai_state(self, *_):
        p = self.var_llm_provider.get()
        has_gemini = bool(self.var_gemini_key.get().strip())
        has_openai = bool(self.var_openai_key.get().strip())
        has_claude = bool(self.var_claude_key.get().strip())
        has_groq = bool(self.var_groq_key.get().strip())
        has_openrouter = bool(self.var_openrouter_key.get().strip())
        has_custom = bool(self.var_custom_url.get().strip() and self.var_custom_key.get().strip())
        if p == "gemini": ai_available = has_gemini
        elif p == "openai": ai_available = has_openai
        elif p == "claude": ai_available = has_claude
        elif p == "groq": ai_available = has_groq
        elif p == "openrouter": ai_available = has_openrouter
        elif p == "custom": ai_available = has_custom
        elif p == "ollama": ai_available = True
        else: ai_available = False
        if hasattr(self, 'btn_test_gemini'):
            need_key = {"gemini": has_gemini, "openai": has_openai, "claude": has_claude, "groq": has_groq, "openrouter": has_openrouter, "custom": has_custom, "ollama": True}.get(p, False)
            self.btn_test_gemini.config(state=NORMAL if need_key else DISABLED, bootstyle="success-outline" if need_key else "secondary")
        # habilitar apenas campos do provedor ativo
        if hasattr(self, 'ent_gemini'): self.ent_gemini.config(state=NORMAL if p=="gemini" else DISABLED)
        if hasattr(self, 'ent_openai'): self.ent_openai.config(state=NORMAL if p=="openai" else DISABLED)
        if hasattr(self, 'ent_claude'): self.ent_claude.config(state=NORMAL if p=="claude" else DISABLED)
        if hasattr(self, 'ent_groq'): self.ent_groq.config(state=NORMAL if p=="groq" else DISABLED)
        if hasattr(self, 'ent_openrouter'): 
            s_or = NORMAL if p=="openrouter" else DISABLED
            self.ent_openrouter.config(state=s_or)
            if hasattr(self, 'combo_openrouter_model'): self.combo_openrouter_model.config(state=s_or)
        if hasattr(self, 'ent_ollama_host'):
            s = NORMAL if p=="ollama" else DISABLED
            self.ent_ollama_host.config(state=s); self.ent_ollama_model.config(state=s)
        if hasattr(self, 'ent_custom_url'):
            s2 = NORMAL if p=="custom" else DISABLED
            self.ent_custom_url.config(state=s2); self.ent_custom_key.config(state=s2)
        # mostra só frame do provider selecionado (dropdown único dinâmico)
        if hasattr(self, 'frame_gemini'):
            for f in [self.frame_gemini, self.frame_ollama, self.frame_openai, self.frame_claude, self.frame_groq, self.frame_openrouter, self.frame_custom]:
                try: f.pack_forget()
                except: pass
            if p=="gemini": self.frame_gemini.pack(fill=X, pady=2)
            elif p=="ollama": self.frame_ollama.pack(fill=X, pady=2)
            elif p=="openai": self.frame_openai.pack(fill=X, pady=2)
            elif p=="claude": self.frame_claude.pack(fill=X, pady=2)
            elif p=="groq": self.frame_groq.pack(fill=X, pady=2)
            elif p=="openrouter": self.frame_openrouter.pack(fill=X, pady=2)
            elif p=="custom": self.frame_custom.pack(fill=X, pady=2)
        if hasattr(self, 'lbl_ai_status'):
            if ai_available:
                self.lbl_ai_status.config(text=f"✓ IA habilitada ({p}) — reestruturação ATS e carta com IA ativas", bootstyle="success")
            else:
                self.lbl_ai_status.config(text=f"○ IA desabilitada — preencha a chave de '{p}' acima para ativar (opcional). Sem chave usa heurístico e funções com IA ficam cinza.", bootstyle="secondary")
        for attr in ["btn_preview_ai"]:
            if hasattr(self, attr):
                try: getattr(self, attr).config(state=NORMAL if ai_available else DISABLED)
                except: pass
        if hasattr(self, 'lbl_exec_ai'):
            if ai_available:
                self.lbl_exec_ai.config(text=f"IA pronta ({p}) — currículos serão reestruturados com palavras-chave da vaga", bootstyle="success")
            else:
                self.lbl_exec_ai.config(text="IA desabilitada — execução usará heurístico (sem reestruturação por IA). Preencha a chave para habilitar.", bootstyle="secondary")

    def test_gemini(self):
        p=self.var_llm_provider.get()
        if p=="openrouter":
            key=self.var_openrouter_key.get().strip()
            model=self.var_openrouter_model.get().strip() or "meta-llama/llama-3.1-8b-instruct:free"
            if not key: messagebox.showwarning("OpenRouter","Informe a key em openrouter.ai/keys"); return
            try:
                import requests
                headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json","HTTP-Referer":"https://github.com/Lucas-Baumann/Job-Auto-Fit","X-Title":"JobAutoFit"}
                payload={"model": model, "messages":[{"role":"user","content":"Responda apenas OK"}],"max_tokens":20}
                r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers=headers,json=payload,timeout=20)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    messagebox.showinfo("OpenRouter",f"{model}: {txt[:200]}")
                else:
                    # tenta fallback gemini flash free
                    messagebox.showerror("OpenRouter",f"{r.status_code}: {r.text[:400]}\nDica: verifique modelo :free e créditos em openrouter.ai/activity")
            except Exception as e: messagebox.showerror("OpenRouter",str(e))
            return
        key=self.var_gemini_key.get().strip()
        if not key: messagebox.showwarning("Gemini","Informe a key"); return
        try:
            import google.generativeai as genai
            genai.configure(api_key=key); m=genai.GenerativeModel("gemini-1.5-flash"); r=m.generate_content("Responda OK")
            messagebox.showinfo("Gemini",r.text[:200])
        except Exception as e: messagebox.showerror("Gemini",str(e))

    # Execução
    def _build_exec(self):
        f=self.tab_exec
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Checkbutton(top,text="dry-run (só PDFs + relatório)",variable=self.var_dry_run,bootstyle="round-toggle").pack(side=LEFT,padx=5)
        self.btn_run=tb.Button(top,text="▶ Iniciar Automação",bootstyle="success",width=20,command=self.run_automation); self.btn_run.pack(side=RIGHT,padx=5)
        self.btn_stop=tb.Button(top,text="■ Parar",bootstyle="danger-outline",command=self.stop_automation,state=DISABLED); self.btn_stop.pack(side=RIGHT,padx=5)
        self.progress=tb.Progressbar(f,mode="indeterminate",bootstyle="success-striped"); self.progress.pack(fill=X,pady=6)
        log_frame=tb.Frame(f); log_frame.pack(fill=BOTH,expand=True,pady=5)
        self.log_text=tk.Text(log_frame,height=18,wrap="word",bg="#0f0f0f",fg="#d0d0d0",insertbackground="white",font=("Consolas",9)); self.log_text.pack(side=LEFT,fill=BOTH,expand=True)
        sb=tb.Scrollbar(log_frame,orient=VERTICAL,command=self.log_text.yview); sb.pack(side=RIGHT,fill=Y); self.log_text.configure(yscrollcommand=sb.set)
        self.log=type("o",(),{"text":self.log_text})()
        self._log("Pronto. Clique em Iniciar.\n")
        row=tb.Frame(f); row.pack(fill=X,pady=5)
        tb.Button(row,text="Abrir último HTML",bootstyle="info",command=self.open_last_report).pack(side=LEFT,padx=5)
        tb.Button(row,text="Pasta OUTPUT",bootstyle="secondary",command=lambda:self._open_folder(BASE_DIR/"output")).pack(side=LEFT,padx=5)
        self.btn_preview_ai=tb.Button(row,text="Preview ATS c/ IA (reestrutura)",bootstyle="warning-outline",command=self.preview_pdf); self.btn_preview_ai.pack(side=LEFT,padx=5)
        tb.Button(row,text="Limpar log",bootstyle="secondary-outline",command=lambda:self.log.text.delete("1.0",tk.END)).pack(side=RIGHT)
        self.lbl_exec_ai=tb.Label(f,text="",font=("Segoe UI",8)); self.lbl_exec_ai.pack(anchor=W, pady=(2,0))
    def _log(self,msg): self.log.text.insert(tk.END,msg+("\n" if not msg.endswith("\n") else "")); self.log.text.see(tk.END); self.update_idletasks()
    def _open_folder(self,p):
        try:
            if sys.platform.startswith("win"): os.startfile(str(p))
            else: subprocess.Popen(["xdg-open",str(p)])
        except Exception as e: messagebox.showerror("Erro",str(e))
    def open_last_report(self):
        reps=sorted((BASE_DIR/"reports").glob("*.html"),key=lambda x:x.stat().st_mtime,reverse=True)
        if not reps: messagebox.showinfo("Relatório","Nenhum relatório ainda."); return
        webbrowser.open(reps[0].as_uri())
    def preview_pdf(self):
        try:
            self.save_all(silent=True)
            from ats_optimizer import generate_ats_pdf
            out=BASE_DIR/"output"/"_preview_cv.pdf"; generate_ats_pdf(self.curriculum,out); webbrowser.open(out.as_uri()); self._log(f"[Preview] {out}")
        except Exception as e: messagebox.showerror("Preview",str(e))
    def run_automation(self):
        if not self.var_name.get().strip(): messagebox.showwarning("Validação","Informe nome"); self.nb.select(self.tab_perfil); return
        self.save_all(silent=True); self.btn_run.config(state=DISABLED); self.btn_stop.config(state=NORMAL); self.progress.start(12); self._log("\n=== Iniciando ===")
        kws=[k.strip() for k in self.var_keywords.get().split(",") if k.strip()] or ["Desenvolvedor Python"]
        loc="Brasil" if self.var_work_mode.get()=="remoto" else (self.var_presencial_loc.get().strip() or "Brasil")
        cmd=[sys.executable,str(BASE_DIR/"main.py"),"--keywords",*kws,"--location",loc,"--min-score",str(int(self.var_min_score.get()))]
        if self.var_dry_run.get(): cmd.append("--dry-run")
        self._log(f"Comando: {' '.join(cmd)}"); self.proc=None; self.stop_requested=False
        def target():
            try:
                self.proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",cwd=str(BASE_DIR))
                for line in self.proc.stdout:
                    if self.stop_requested:
                        try: self.proc.terminate()
                        except: pass
                        break
                    self._log(line.rstrip())
                self.proc.wait()
                self._log("\n=== Finalizado ===" if not self.stop_requested else "\n=== Parado ===")
            except Exception as e: self._log(str(e))
            finally: self.progress.stop(); self.btn_run.config(state=NORMAL); self.btn_stop.config(state=DISABLED); self._refresh_hist(); self._refresh_dashboard()
        threading.Thread(target=target,daemon=True).start()
    def stop_automation(self):
        self.stop_requested=True
        try: self.proc.terminate()
        except: pass
        self._log("[Stop] solicitado")

    # Dashboard
    def _build_dash(self):
        f=self.tab_dash
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_dashboard).pack(side=RIGHT)
        self.dash_cards=tb.Frame(f); self.dash_cards.pack(fill=X,pady=5)
        # cards serão labels
        self.lbl_total=tb.Label(self.dash_cards,text="0 vagas",font=("Segoe UI",14,"bold"),bootstyle="primary"); self.lbl_total.pack(side=LEFT,padx=10)
        self.lbl_high=tb.Label(self.dash_cards,text="0 high match",font=("Segoe UI",12),bootstyle="success"); self.lbl_high.pack(side=LEFT,padx=10)
        self.lbl_today=tb.Label(self.dash_cards,text="0 hoje",font=("Segoe UI",12),bootstyle="info"); self.lbl_today.pack(side=LEFT,padx=10)
        # bars por status
        self.frame_bars=tb.Labelframe(f,text="Distribuição por status / plataforma",padding=10); self.frame_bars.pack(fill=BOTH,expand=True,pady=5)
        self.bars_text=tk.Text(self.frame_bars,height=12,bg="#1e1e1e",fg="#d0d0d0",font=("Consolas",9)); self.bars_text.pack(fill=BOTH,expand=True)
    def _refresh_dashboard(self):
        try:
            if not DB_PATH.exists(): return
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT COUNT(*) c FROM jobs"); total=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE match_score>=60"); high=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE date(created_at)=date('now')"); today=cur.fetchone()["c"]
            self.lbl_total.config(text=f"{total} vagas totais"); self.lbl_high.config(text=f"{high} match≥60%"); self.lbl_today.config(text=f"{today} hoje")
            cur.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status"); rows=cur.fetchall()
            cur.execute("SELECT platform, COUNT(*) c FROM jobs GROUP BY platform"); rows2=cur.fetchall()
            con.close()
            txt=f"Por status:\n"
            for r in rows: txt+=f"  {r['status']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            txt+="\nPor plataforma:\n"
            for r in rows2: txt+=f"  {r['platform']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            self.bars_text.delete("1.0",tk.END); self.bars_text.insert("1.0",txt)
        except Exception as e: pass

    # Histórico
    def _build_hist(self):
        f=self.tab_hist
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Label(top,text="Histórico (jobs.db) — duplo clique abre vaga").pack(side=LEFT,padx=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_hist).pack(side=RIGHT,padx=5)
        cols=("vaga","empresa","local","match","status","plataforma")
        self.tree=tb.Treeview(f,columns=cols,show="headings",bootstyle="dark",height=14)
        for c in cols: self.tree.heading(c,text=c.capitalize())
        self.tree.column("vaga",width=260); self.tree.column("empresa",width=160); self.tree.column("local",width=140); self.tree.column("match",width=60,anchor=CENTER); self.tree.column("status",width=110,anchor=CENTER); self.tree.column("plataforma",width=90,anchor=CENTER)
        self.tree.pack(fill=BOTH,expand=True,pady=5); self.tree.bind("<Double-Button-1>",self._on_hist_dbl); self._refresh_hist()
    def _refresh_hist(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            if not DB_PATH.exists(): return
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT title,company,location,match_score,status,platform FROM jobs ORDER BY id DESC LIMIT 300")
            for r in cur.fetchall(): self.tree.insert("",tk.END,values=(r["title"],r["company"],r["location"],f"{r['match_score'] or 0}%",r["status"],r["platform"]))
            con.close()
        except: pass
    def _on_hist_dbl(self,ev):
        sel=self.tree.selection()
        if not sel: return
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); cur=con.cursor(); idx=self.tree.index(sel[0]); cur.execute("SELECT url FROM jobs ORDER BY id DESC LIMIT 1 OFFSET ?",(idx,)); row=cur.fetchone()
            if row and row[0]: webbrowser.open(row[0])
            con.close()
        except: pass

    # Perfil GitHub
    def _build_profile(self):
        f=self.tab_profile
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Label(top,text="Username GitHub").pack(side=LEFT,padx=5); tb.Entry(top,textvariable=self.var_profile_user,width=24).pack(side=LEFT,padx=5)
        tb.Checkbutton(top,text="Usar IA para reescrever bio",variable=self.var_profile_use_llm,bootstyle="round-toggle").pack(side=LEFT,padx=10)
        info_icon(top,"Se ativado e IA configurada (aba 3), reescreve bio/linhas typing com seu currículo + perfil antigo. Sem IA usa heurístico.").pack(side=LEFT)
        token_row=tb.Frame(f); token_row.pack(fill=X,pady=4)
        tb.Label(token_row,text="GitHub Token (repo scope)").pack(side=LEFT,padx=5); self.ent_github_token=tb.Entry(token_row,textvariable=self.var_github_token,show="*",width=40); self.ent_github_token.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(token_row,"Crie em github.com/settings/tokens (classic) com scope 'repo' — necessário para push direto. Deixe vazio para só gerar local.").pack(side=LEFT)
        tb.Button(token_row,text="Salvar",bootstyle="secondary-outline",width=8,command=lambda:self.save_all(silent=True)).pack(side=LEFT,padx=5)
        btns=tb.Frame(f); btns.pack(fill=X,pady=5)
        tb.Button(btns,text="🔍 Analisar perfil antigo",bootstyle="info-outline",command=self.analyze_profile).pack(side=LEFT,padx=5)
        tb.Button(btns,text="✨ Gerar README Perfil",bootstyle="success",command=self.generate_profile).pack(side=LEFT,padx=5)
        tb.Button(btns,text="🚀 Gerar e Push Perfil",bootstyle="success",command=self.generate_and_push_profile).pack(side=LEFT,padx=5)
        tb.Button(btns,text="📂 Abrir output_github",bootstyle="secondary-outline",command=lambda:self._open_folder(BASE_DIR/"output_github")).pack(side=LEFT,padx=5)
        tb.Button(btns,text="📋 Copiar workflow snake",bootstyle="secondary-outline",command=self.copy_snake_workflow).pack(side=LEFT,padx=5)
        self.txt_profile_log=tk.Text(f,height=8,bg="#1e1e1e",fg="#d0d0d0",font=("Consolas",9),wrap="word"); self.txt_profile_log.pack(fill=BOTH,expand=True,pady=5)
        self.txt_profile_log.insert("1.0","Pronto. Informe username e clique Analisar. O gerador usa a estética perfeita (dark tokyonight + summary-cards + snake picture) e analisa seu README antigo se existir.\n")
        row=tb.Frame(f); row.pack(fill=X,pady=4)
        tb.Label(row,text="Após gerar: copie output_github/README_<user>.md → repo <user>/<user> → commit → push. Snake: copie output_github/snake.yml → <user>/<user>/.github/workflows/",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT)
        # Repositórios
        card_repos=tb.Labelframe(f,text="Repositórios — selecione com ⭐ para reformular README",padding=8,bootstyle="warning"); card_repos.pack(fill=BOTH,expand=True,pady=5)
        top_repos=tb.Frame(card_repos); top_repos.pack(fill=X)
        tb.Button(top_repos,text="🔍 Buscar Repos do Perfil",bootstyle="info-outline",command=self.fetch_profile_repos).pack(side=LEFT,padx=5)
        tb.Button(top_repos,text="✨ Reformular Selecionados (⭐)",bootstyle="warning",command=self.generate_selected_repos).pack(side=LEFT,padx=5)
        tb.Button(top_repos,text="🚀 Push Selecionados",bootstyle="success",command=self.push_selected_repos).pack(side=LEFT,padx=5)
        tb.Button(top_repos,text="📂 Abrir saída",bootstyle="secondary-outline",command=lambda:self._open_folder(BASE_DIR/"output_github")).pack(side=LEFT,padx=5)
        tb.Label(top_repos,text="  Clique na linha para ⭐/desmarcar • Gera README otimizado dark por projeto",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT,padx=5)
        cols_repos=("star","repo","lang","stars","readme")
        self.tree_repos=tb.Treeview(card_repos,columns=cols_repos,show="headings",height=7,bootstyle="warning")
        for c,t,w in [("star","⭐",30),("repo","Repositório",200),("lang","Lang",80),("stars","★",50),("readme","README?",80)]:
            self.tree_repos.heading(c,text=t); self.tree_repos.column(c,width=w,anchor=CENTER if c in ("star","stars","readme") else W)
        self.tree_repos.pack(fill=BOTH,expand=True,pady=5)
        self.tree_repos.bind("<ButtonRelease-1>", lambda e: self.after(100, self.toggle_repo_star))
        self.repos_cache=[]
        self.repos_starred=set()
        # carrega seleção persistida
        try:
            sel_path=BASE_DIR/"github_selection.json"
            if sel_path.exists(): self.repos_starred=set(json.loads(sel_path.read_text(encoding="utf-8")))
        except: pass

    def analyze_profile(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        self.txt_profile_log.insert(tk.END,f"\n[Análise] Buscando {user}...\n"); self.txt_profile_log.see(tk.END); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, fetch_github_user, fetch_repos, analyze_old_readme
            old=fetch_old_readme(user)
            info=analyze_old_readme(old)
            udata=fetch_github_user(user)
            repos=fetch_repos(user)
            total_stars=sum(r.get("stargazers_count",0) for r in repos)
            self.txt_profile_log.insert(tk.END,f"  Usuário: {udata.get('name','')} | Repos: {udata.get('public_repos', len(repos))} | Seguidores: {udata.get('followers',0)} | Estrelas totais: {total_stars}\n")
            self.txt_profile_log.insert(tk.END,f"  README antigo: {info.get('status')} | len={info.get('len','0')} | issues: {info.get('issues')}\n")
            if old:
                self.txt_profile_log.insert(tk.END,f"  Preview antigo (500 chars):\n{info.get('preview','')[:500]}\n")
            else:
                self.txt_profile_log.insert(tk.END,"  Nenhum README encontrado em github.com/{user}/{user} — será criado do zero.\n")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Análise",str(e))

    def generate_profile(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Geração] Gerando README para {user} (IA={'sim' if use_llm else 'não'})...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, generate_profile_readme, write_profile_output
            old=fetch_old_readme(user)
            md, info = generate_profile_readme(user, self.curriculum, old, use_llm=use_llm)
            path=write_profile_output(user, md)
            self.txt_profile_log.insert(tk.END,f"  ✓ Gerado em {path}\n  Repos: {info['public_repos']} | Estrelas: {info['total_stars']} | Skillicons: {info['skillicons']}\n")
            self.txt_profile_log.insert(tk.END,"  Próximo: abra output_github, copie README_<user>.md para seu repo de perfil e snake.yml para .github/workflows/\n")
            # preview no log
            self.txt_profile_log.insert(tk.END,f"\n--- Preview (primeiras 800 chars) ---\n{md[:800]}\n")
            self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Perfil",f"README gerado em {path}\nSnake workflow em output_github/snake.yml")
            webbrowser.open((Path(path)).as_uri())
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Geração",str(e))

    def copy_snake_workflow(self):
        try:
            from pathlib import Path as _P
            src=_P(BASE_DIR/"output_github"/"snake.yml")
            if not src.exists():
                messagebox.showwarning("Snake","Gere o README primeiro (cria snake.yml)")
                return
            self.txt_profile_log.insert(tk.END,f"[Snake] Workflow em {src} — copie para https://github.com/{self.var_profile_user.get()}/{self.var_profile_user.get()}/.github/workflows/\n")
            webbrowser.open(src.as_uri())
        except Exception as e: messagebox.showerror("Snake",str(e))

    def fetch_profile_repos(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Repos","Informe username"); return
        self.txt_profile_log.insert(tk.END,f"\n[Repos] Buscando repos de {user}...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_repos, fetch_repo_readme
            repos=fetch_repos(user)
            # limpa tree
            for i in self.tree_repos.get_children(): self.tree_repos.delete(i)
            self.repos_cache=repos
            for r in sorted(repos, key=lambda x: x.get("stargazers_count",0), reverse=True)[:30]:
                name=r.get("name","")
                lang=r.get("language") or "-"
                stars=r.get("stargazers_count",0)
                has_readme="sim" if fetch_repo_readme(user, name) else "não"
                star="⭐" if name in self.repos_starred else ""
                self.tree_repos.insert("", "end", values=(star, name, lang, stars, has_readme))
            self.txt_profile_log.insert(tk.END,f"  {len(repos)} repos encontrados (mostrando até 30 ordenados por ★). Clique na linha para ⭐.\n")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro repos: {e}\n"); messagebox.showerror("Repos",str(e))

    def toggle_repo_star(self):
        sel=self.tree_repos.selection()
        if not sel: return
        vals=self.tree_repos.item(sel[0],"values")
        if not vals: return
        repo=vals[1]
        if repo in self.repos_starred:
            self.repos_starred.remove(repo)
            self.tree_repos.item(sel[0], values=("", vals[1], vals[2], vals[3], vals[4]))
        else:
            self.repos_starred.add(repo)
            self.tree_repos.item(sel[0], values=("⭐", vals[1], vals[2], vals[3], vals[4]))
        # persiste
        try: (BASE_DIR/"github_selection.json").write_text(json.dumps(sorted(self.repos_starred), ensure_ascii=False, indent=2), encoding="utf-8")
        except: pass
        self.txt_profile_log.insert(tk.END,f"[⭐] {'+'+repo if repo in self.repos_starred else '-'+repo} | total ⭐: {len(self.repos_starred)}\n"); self.txt_profile_log.see(tk.END)

    def generate_selected_repos(self):
        user=self.var_profile_user.get().strip()
        if not self.repos_starred: messagebox.showwarning("Repos","Selecione ao menos 1 repo com ⭐ (clique na linha)"); return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Repos] Reformulando {len(self.repos_starred)} repos com IA={'sim' if use_llm else 'não'}...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_repo_readme, generate_repo_readme, write_repo_output
            for repo in sorted(self.repos_starred):
                self.txt_profile_log.insert(tk.END,f"  → {repo} ..."); self.update_idletasks()
                old=fetch_repo_readme(user, repo)
                md, info = generate_repo_readme(user, repo, self.curriculum, old, use_llm=use_llm)
                path=write_repo_output(user, repo, md)
                has = "tinha README" if info["has_old"] else "sem README"
                self.txt_profile_log.insert(tk.END,f" ✓ {path} ({has}, {info['language']}, {info['langs']})\n")
                self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Repos",f"{len(self.repos_starred)} READMEs gerados em output_github/README_<repo>.md\nRevise antes de copiar para cada repo.")
            self._open_folder(BASE_DIR/"output_github")
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Repos",str(e))

    def generate_and_push_profile(self):
        user=self.var_profile_user.get().strip()
        token=self.var_github_token.get().strip() or self.env.get("GITHUB_TOKEN","")
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        if not token: messagebox.showwarning("Token","Informe GitHub Token (repo) para push"); return
        if not messagebox.askyesno("Push Perfil",f"Gerar README para {user}/{user} e fazer push direto?\nIsso sobrescreve o README remoto."):
            return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Perfil Push] Gerando e enviando para {user}/{user}...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, generate_profile_readme, push_profile_readme
            old=fetch_old_readme(user)
            md, info = generate_profile_readme(user, self.curriculum, old, use_llm=use_llm)
            # salva local primeiro
            from profile_generator import write_profile_output
            write_profile_output(user, md)
            self.txt_profile_log.insert(tk.END,"  Gerado local, fazendo push...\n"); self.update_idletasks()
            msg=push_profile_readme(user, token, md)
            self.txt_profile_log.insert(tk.END,f"  ✓ {msg} — https://github.com/{user}/{user}\n")
            messagebox.showinfo("Perfil",f"Push ok em https://github.com/{user}/{user}")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro push: {e}\n"); messagebox.showerror("Push Perfil",str(e))

    def push_selected_repos(self):
        user=self.var_profile_user.get().strip()
        token=self.var_github_token.get().strip() or self.env.get("GITHUB_TOKEN","")
        if not self.repos_starred: messagebox.showwarning("Repos","Selecione ao menos 1 repo com ⭐"); return
        if not token: messagebox.showwarning("Token","Informe GitHub Token (repo)"); return
        if not messagebox.askyesno("Push Repos",f"Fazer push de {len(self.repos_starred)} READMEs para GitHub?\nRepos: {', '.join(sorted(self.repos_starred))}"):
            return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Repos Push] {len(self.repos_starred)} repos...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_repo_readme, generate_repo_readme, push_repo_readme
            for repo in sorted(self.repos_starred):
                self.txt_profile_log.insert(tk.END,f"  → {repo} gerando..."); self.update_idletasks()
                old=fetch_repo_readme(user, repo)
                md, info = generate_repo_readme(user, repo, self.curriculum, old, use_llm=use_llm)
                # write local
                from profile_generator import write_repo_output
                write_repo_output(user, repo, md)
                self.txt_profile_log.insert(tk.END," push..."); self.update_idletasks()
                msg=push_repo_readme(user, repo, token, md)
                self.txt_profile_log.insert(tk.END,f" {msg}\n"); self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Repos","Push concluído! Verifique no GitHub.")
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Push Repos",str(e))

    # Save/export
    def save_all(self,silent=False):
        self.curriculum["personal_info"]={"name":self.var_name.get().strip(),"email":self.var_email.get().strip(),"phone":self.var_phone.get().strip(),"location":self.var_location.get().strip(),"linkedin":self.var_linkedin.get().strip(),"github":self.var_github.get().strip()}
        self.curriculum["summary"]=self.txt_summary.get("1.0","end").strip(); save_curriculum(self.curriculum)
        self.env.update(GEMINI_API_KEY=self.var_gemini_key.get().strip(),LLM_PROVIDER=self.var_llm_provider.get().strip().lower(),OLLAMA_HOST=self.var_ollama_host.get().strip(),OLLAMA_MODEL=self.var_ollama_model.get().strip(),OPENAI_API_KEY=self.var_openai_key.get().strip(),CLAUDE_API_KEY=self.var_claude_key.get().strip(),GROQ_API_KEY=self.var_groq_key.get().strip(),OPENROUTER_API_KEY=self.var_openrouter_key.get().strip(),OPENROUTER_MODEL=self.var_openrouter_model.get().strip(),CUSTOM_LLM_URL=self.var_custom_url.get().strip(),CUSTOM_LLM_KEY=self.var_custom_key.get().strip(),GITHUB_TOKEN=self.var_github_token.get().strip(),SMTP_HOST=self.var_smtp_host.get().strip(),SMTP_PORT=self.var_smtp_port.get().strip(),SMTP_USER=self.var_smtp_user.get().strip(),SMTP_PASS=self.var_smtp_pass.get().strip(),LINKEDIN_EMAIL=self.var_linkedin_email.get().strip(),LINKEDIN_PASSWORD=self.var_linkedin_pass.get().strip(),GUPY_EMAIL=self.var_gupy_email.get().strip(),GUPY_PASSWORD=self.var_gupy_pass.get().strip(),WORK_MODE=self.var_work_mode.get().strip(),PRESENCIAL_LOCATION=self.var_presencial_loc.get().strip(),CONTRACT_TYPE=self.var_contract.get().strip(),TELEGRAM_BOT_TOKEN=self.var_telegram_token.get().strip(),TELEGRAM_CHAT_ID=self.var_telegram_chat.get().strip(),DAILY_LIMIT=str(int(self.var_daily_limit.get())))
        save_env_dict(self.env)
        cfg={"keywords":[k.strip() for k in self.var_keywords.get().split(",") if k.strip()],"work_mode":self.var_work_mode.get(),"presencial_location":self.var_presencial_loc.get().strip(),"contract_type":self.var_contract.get(),"min_score":int(self.var_min_score.get()),"limit_per_source":int(self.var_limit.get()),"min_salary":int(self.var_min_salary.get()),"level":self.var_level.get(),"exclude_keywords":[k.strip() for k in self.var_exclude.get().split(",") if k.strip()],"mandatory_words":[k.strip() for k in self.var_mandatory.get().split(",") if k.strip()],"blocked_companies":[k.strip() for k in self.var_blocked.get().split(",") if k.strip()],"favorite_companies":[k.strip() for k in self.var_fav.get().split(",") if k.strip()],"max_age_days":int(self.var_max_age.get()),"only_pcd":bool(self.var_only_pcd.get()),"english_filter":self.var_english.get(),"daily_limit":int(self.var_daily_limit.get()),"telegram_bot_token":self.var_telegram_token.get().strip(),"telegram_chat_id":self.var_telegram_chat.get().strip(),"schedule_enabled":bool(self.var_schedule_enabled.get()),"schedule_hour":self.var_schedule_hour.get().strip(),"enable_linkedin_posts":bool(self.var_enable_linkedin_posts.get()),"linkedin_posts_limit":int(self.var_linkedin_posts_limit.get())}
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
