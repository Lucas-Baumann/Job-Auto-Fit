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
PRESETS_PATH = BASE_DIR / "presets.json"
def load_presets():
    if PRESETS_PATH.exists():
        try: return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        except: return {}
    return {}
def save_presets(d): PRESETS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

class App(tb.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("JobAutoFit — Automação Completa (Gupy / LinkedIn / ATS)")
        self.geometry("1280x820"); self.minsize(1200,750)
        # abrir em tela cheia (maximizado) — solicitado
        try:
            self.state('zoomed')
        except:
            try: self.attributes('-zoomed', True)
            except: pass
        # fallback centralizar se não maximizou
        self.update_idletasks()
        try:
            if self.state() != 'zoomed':
                sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
                x = (sw - 1280)//2; y = (sh - 820)//2 - 20
                self.geometry(f"1280x820+{max(0,x)}+{max(0,y)}")
        except: pass
        # ícone da janela (.ico)
        try:
            ico = BASE_DIR / "logo.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass
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
        self.var_github_user = tk.StringVar(value=(self.curriculum.get("personal_info",{}).get("github","").split("/")[-1].strip() if self.curriculum.get("personal_info",{}).get("github") else self.env.get("GITHUB_USER","Lucas-Baumann") or "Lucas-Baumann"))
        self.var_github_token = tk.StringVar(value=self.env.get("GITHUB_TOKEN",""))
        self.github_repos = []
        self.github_starred = set()
        try:
            sel_path = BASE_DIR / "github_selection.json"
            if sel_path.exists():
                self.github_starred = set(json.loads(sel_path.read_text(encoding="utf-8")))
        except: pass
        self.var_dry_run=tk.BooleanVar(value=True)
        self._build_ui(); self._bind_work_mode(); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list(); self._refresh_dashboard()
        # atalhos
        self.bind("<Control-s>", lambda e: self.save_all())
        self.bind("<Control-S>", lambda e: self.save_all())
        self.bind("<F5>", lambda e: (self._refresh_dashboard(), self._refresh_hist()))
        self.bind("<Escape>", lambda e: self.stop_automation())
        self.after(600, self.show_wizard)

    def _build_ui(self):
        top=tb.Frame(self,padding=10); top.pack(fill=X)
        # logo + título
        try:
            from PIL import Image, ImageTk
            ico_path = BASE_DIR / "logo.ico"
            if ico_path.exists():
                img = Image.open(str(ico_path))
                img = img.resize((36,36), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                tb.Label(top, image=self.logo_img).pack(side=LEFT, padx=(0,6))
        except Exception:
            pass
        tb.Label(top,text="JobAutoFit",font=("Segoe UI",18,"bold"),bootstyle="primary").pack(side=LEFT)
        self.lbl_subtitle = tb.Label(top,text="  Coleta • Filtragem Avançada • ATS • Envio • Relatório • Dashboard",font=("Segoe UI",10,"bold"),bootstyle="light")
        self.lbl_subtitle.pack(side=LEFT,padx=10)
        # stepper visual
        self.lbl_stepper = tb.Label(top, text="① Currículo → ② Busca → ③ IA → ④ Execução → ⑤ Dashboard", font=("Segoe UI", 8, "bold"), bootstyle="light")
        self.lbl_stepper.pack(side=LEFT, padx=12)
        self.btn_theme = tb.Button(top, text="☀ Claro", bootstyle="light-outline", width=8, command=self.toggle_theme)
        self.btn_theme.pack(side=RIGHT, padx=5)
        self.btn_export_top = tb.Button(top,text="Exportar",bootstyle="light-outline",command=self.export_config)
        self.btn_export_top.pack(side=RIGHT,padx=5)
        self.btn_import_top = tb.Button(top,text="Importar",bootstyle="light-outline",command=self.import_config)
        self.btn_import_top.pack(side=RIGHT,padx=5)
        self.nb=tb.Notebook(self,bootstyle="dark"); self.nb.pack(fill=BOTH,expand=True,padx=10,pady=(0,10))
        self.tab_perfil=tb.Frame(self.nb,padding=10); self.tab_busca=tb.Frame(self.nb,padding=10); self.tab_ia=tb.Frame(self.nb,padding=10); self.tab_exec=tb.Frame(self.nb,padding=10); self.tab_dash=tb.Frame(self.nb,padding=10); self.tab_hist=tb.Frame(self.nb,padding=10); self.tab_github=tb.Frame(self.nb,padding=10)
        self.nb.add(self.tab_perfil,text=" 1. Currículo "); self.nb.add(self.tab_busca,text=" 2. Busca & Filtros "); self.nb.add(self.tab_ia,text=" 3. IA & Conexões "); self.nb.add(self.tab_exec,text=" 4. Execução "); self.nb.add(self.tab_dash,text=" 5. Dashboard "); self.nb.add(self.tab_hist,text=" 6. Histórico "); self.nb.add(self.tab_github,text=" 7. GitHub ⭐ ")
        self._build_perfil(); self._build_busca(); self._build_ia(); self._build_exec(); self._build_dash(); self._build_hist(); self._build_github()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._update_stepper())
        self._update_stepper()
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
        tb.Label(grid,text="E-mail").grid(row=1,column=0,sticky=W,padx=5,pady=3); self.ent_email = tb.Entry(grid,textvariable=self.var_email); self.ent_email.grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        self.var_email.trace_add("write", lambda *_: self._validate_email())
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
            from importer import import_file_to_curriculum
            parsed=import_file_to_curriculum(Path(p))
            # merge
            for k in ["name","email","phone","linkedin","github"]:
                if parsed.get("personal_info",{}).get(k): self.curriculum.setdefault("personal_info",{})[k]=parsed["personal_info"][k]
            if parsed.get("skills"): self.curriculum["skills"]=list(dict.fromkeys(self.curriculum.get("skills",[])+parsed["skills"]))
            if parsed.get("summary") and not self.txt_summary.get("1.0","end").strip(): self.txt_summary.delete("1.0",tk.END); self.txt_summary.insert("1.0",parsed["summary"])
            # refresh
            self.var_name.set(self.curriculum["personal_info"].get("name","")); self.var_email.set(self.curriculum["personal_info"].get("email","")); self.var_phone.set(self.curriculum["personal_info"].get("phone","")); self.var_linkedin.set(self.curriculum["personal_info"].get("linkedin","")); self.var_github.set(self.curriculum["personal_info"].get("github",""))
            self._refresh_skills_list(); messagebox.showinfo("Importar",f"Importado de {Path(p).name}\nRevise os campos antes de salvar.")
        except Exception as e: messagebox.showerror("Importar",str(e))
    def suggest_mandatory(self):
        skills = self.curriculum.get("skills", [])
        if not skills:
            messagebox.showwarning("Sugerir", "Adicione skills no currículo primeiro (aba Currículo).")
            return
        sug = ", ".join(skills[:8])
        self.var_mandatory.set(sug)
        self._log(f"[Sugestão] Palavras obrigatórias preenchidas: {sug}")
    def _refresh_presets_combo(self):
        presets = load_presets()
        self.combo_presets["values"] = list(presets.keys())
    def save_preset(self):
        name = self.var_preset_name.get().strip()
        if not name:
            messagebox.showwarning("Preset", "Digite um nome para o preset")
            return
        self.save_all(silent=True)
        presets = load_presets()
        presets[name] = self.search_cfg
        save_presets(presets)
        self._refresh_presets_combo()
        self.show_toast(f"Preset '{name}' salvo")
    def load_preset(self):
        name = self.combo_presets.get().strip()
        if not name:
            messagebox.showwarning("Preset", "Selecione um preset")
            return
        presets = load_presets()
        cfg = presets.get(name)
        if not cfg:
            messagebox.showerror("Preset", "Preset não encontrado")
            return
        # aplicar
        self.var_keywords.set(", ".join(cfg.get("keywords", [])))
        self.var_work_mode.set(cfg.get("work_mode", "remoto"))
        self.var_presencial_loc.set(cfg.get("presencial_location", ""))
        self.var_contract.set(cfg.get("contract_type", "indiferente"))
        self.var_min_score.set(cfg.get("min_score", 60))
        self.var_limit.set(cfg.get("limit_per_source", 8))
        self.var_min_salary.set(cfg.get("min_salary", 0))
        self.var_level.set(cfg.get("level", "indiferente"))
        self.var_exclude.set(", ".join(cfg.get("exclude_keywords", [])))
        self.var_mandatory.set(", ".join(cfg.get("mandatory_words", [])))
        self.var_blocked.set(", ".join(cfg.get("blocked_companies", [])))
        self.var_fav.set(", ".join(cfg.get("favorite_companies", [])))
        self.var_max_age.set(cfg.get("max_age_days", 0))
        self.var_only_pcd.set(cfg.get("only_pcd", False))
        self.var_english.set(cfg.get("english_filter", "indiferente"))
        self.var_daily_limit.set(cfg.get("daily_limit", 20))
        self._bind_work_mode()
        self._update_chips()
        self.show_toast(f"Preset '{name}' carregado")
    def delete_preset(self):
        name = self.combo_presets.get().strip()
        if not name:
            return
        presets = load_presets()
        if name in presets:
            del presets[name]
            save_presets(presets)
            self._refresh_presets_combo()
            self.combo_presets.set("")
            self.show_toast(f"Preset '{name}' excluído")
    def _update_chips(self):
        for w in self.frame_chips.winfo_children():
            w.destroy()
        kws = [k.strip() for k in self.var_keywords.get().split(",") if k.strip()]
        for kw in kws[:10]:
            btn = tb.Button(self.frame_chips, text=f"{kw} ✕", bootstyle="info-outline", width=12, command=lambda k=kw: self._remove_chip(k))
            btn.pack(side=LEFT, padx=2, pady=2)
            Tooltip(btn, f"Clique para remover '{kw}'")
    def _remove_chip(self, kw):
        kws = [k.strip() for k in self.var_keywords.get().split(",") if k.strip() and k.strip().lower() != kw.lower()]
        self.var_keywords.set(", ".join(kws))

    # Busca avançada
    def _build_busca(self):
        f=self.tab_busca
        # scroll - ScrollableFrame robusto
        bg = "#222222" if self.style.theme.name=="darkly" else "#f8f9fa"
        container = tb.Frame(f)
        container.pack(fill=BOTH, expand=True)
        canvas=tk.Canvas(container,bg=bg,highlightthickness=0, highlightbackground=bg)
        sb=tb.Scrollbar(container,orient=VERTICAL,command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT,fill=Y)
        canvas.pack(side=LEFT,fill=BOTH,expand=True)
        inner=tb.Frame(canvas)
        win_id = canvas.create_window((0,0),window=inner,anchor="nw")
        def _on_inner_config(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # inner sempre com mesma largura do canvas
            try: canvas.itemconfig(win_id, width=canvas.winfo_width())
            except: pass
        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        # tornar canvas focável para setas/espaço
        canvas.configure(takefocus=True)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        # scroll handlers
        def _on_mousewheel(event):
            try:
                if self.nb.index(self.nb.select()) != self.nb.index(self.tab_busca):
                    return "break"
                delta = 0
                if event.delta:
                    delta = int(-1*(event.delta/120))
                elif event.num==4:
                    delta = -3
                elif event.num==5:
                    delta = 3
                if delta:
                    canvas.yview_scroll(delta, "units")
                return "break"
            except: pass
        def _on_keys(event):
            if self.nb.index(self.nb.select()) != self.nb.index(self.tab_busca):
                return
            if event.keysym in ("Down", "Next", "space"):
                canvas.yview_scroll(3, "units"); return "break"
            elif event.keysym in ("Up", "Prior"):
                canvas.yview_scroll(-3, "units"); return "break"
        # bind em todos os níveis - recursivo + global fallback
        def _bind_all(_):
            self.bind_all("<MouseWheel>", _on_mousewheel, add="+")
            self.bind_all("<Button-4>", _on_mousewheel, add="+")
            self.bind_all("<Button-5>", _on_mousewheel, add="+")
            canvas.bind_all("<Up>", _on_keys, add="+")
            canvas.bind_all("<Down>", _on_keys, add="+")
            canvas.bind_all("<Prior>", _on_keys, add="+")
            canvas.bind_all("<Next>", _on_keys, add="+")
            canvas.bind_all("<space>", _on_keys, add="+")
        def _unbind_all(_):
            try:
                self.unbind_all("<MouseWheel>"); self.unbind_all("<Button-4>"); self.unbind_all("<Button-5>")
                canvas.unbind_all("<Up>"); canvas.unbind_all("<Down>"); canvas.unbind_all("<Prior>"); canvas.unbind_all("<Next>"); canvas.unbind_all("<space>")
            except: pass
        f.bind("<Enter>", _bind_all)
        f.bind("<Leave>", _unbind_all)
        # também bind direto no canvas/inner para garantir
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(seq, _on_mousewheel, add="+")
            inner.bind(seq, _on_mousewheel, add="+")
        # bind recursivo em todos os children futuros (após criar)
        def _bind_recursive(widget):
            for child in widget.winfo_children():
                try:
                    child.bind("<MouseWheel>", _on_mousewheel, add="+")
                    child.bind("<Button-4>", _on_mousewheel, add="+")
                    child.bind("<Button-5>", _on_mousewheel, add="+")
                    _bind_recursive(child)
                except: pass
        self.after(500, lambda: _bind_recursive(inner))
        self.after(800, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
        # guardar para troca de tema
        self._busca_canvas = canvas; self._busca_inner = inner
        # nota informativa: SMTP e Credenciais estão abaixo — role para ver
        info_box = tb.Labelframe(inner, text="Dica: role para baixo para ver SMTP e LinkedIn/Gupy", padding=6, bootstyle="secondary"); info_box.pack(fill=X, pady=4)
        tb.Label(info_box, text="A aba IA (dinâmica) mostra só o campo do provedor selecionado. SMTP e automação Playwright estão sempre visíveis abaixo no scroll. Se usar 'gemini' sem chave, o sistema usa heurístico (não quebra). Se usar 'openrouter', use chave gratuita de openrouter.ai/keys.", font=("Segoe UI",8), bootstyle="secondary", wraplength=1000).pack(anchor=W)
        # Presets
        preset_frame = tb.Labelframe(inner, text="Presets de busca", padding=10, bootstyle="secondary")
        preset_frame.pack(fill=X, pady=5)
        self.var_preset_name = tk.StringVar()
        self.combo_presets = tb.Combobox(preset_frame, state="readonly", width=28)
        self.combo_presets.pack(side=LEFT, padx=5)
        tb.Entry(preset_frame, textvariable=self.var_preset_name, width=22).pack(side=LEFT, padx=5)
        info_icon(preset_frame, "Salve combinações: ex 'Python Remoto CLT 8k'\nCarrega todos os filtros de uma vez").pack(side=LEFT)
        tb.Button(preset_frame, text="Salvar preset", bootstyle="success-outline", command=self.save_preset).pack(side=LEFT, padx=5)
        tb.Button(preset_frame, text="Carregar", bootstyle="info-outline", command=self.load_preset).pack(side=LEFT, padx=2)
        tb.Button(preset_frame, text="Excluir", bootstyle="danger-outline", command=self.delete_preset).pack(side=LEFT, padx=2)
        self._refresh_presets_combo()
        card=tb.Labelframe(inner,text="Palavras-chave (vírgula)",padding=10,bootstyle="primary"); card.pack(fill=X,pady=5)
        tb.Entry(card,textvariable=self.var_keywords).pack(fill=X)
        tb.Label(card,text="Ex: Desenvolvedor Python, Backend, Django, FastAPI, AWS",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W,pady=(4,0))
        self.frame_chips = tb.Frame(card); self.frame_chips.pack(fill=X, pady=4)
        self.var_keywords.trace_add("write", lambda *_: self._update_chips())
        self.after(300, self._update_chips)
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
        # scroll container para não cortar SMTP/LinkedIn
        bg = "#2b2b2b" if self.style.theme.name=="darkly" else "#ffffff"
        container = tb.Frame(f)
        container.pack(fill=BOTH, expand=True)
        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        sb = tb.Scrollbar(container, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        inner = tb.Frame(canvas)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(takefocus=True)
        def _on_mousewheel(event):
            try:
                if self.nb.index(self.nb.select()) != self.nb.index(self.tab_ia):
                    return "break"
                delta = int(-1*(event.delta/120)) if event.delta else (-3 if event.num==4 else 3)
                if delta: canvas.yview_scroll(delta, "units")
                return "break"
            except: pass
        def _bind_all(_): self.bind_all("<MouseWheel>", _on_mousewheel); self.bind_all("<Button-4>", _on_mousewheel); self.bind_all("<Button-5>", _on_mousewheel)
        def _unbind_all(_): 
            try: self.unbind_all("<MouseWheel>"); self.unbind_all("<Button-4>"); self.unbind_all("<Button-5>")
            except: pass
        f.bind("<Enter>", _bind_all); f.bind("<Leave>", _unbind_all)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(seq, _on_mousewheel, add="+")
            inner.bind(seq, _on_mousewheel, add="+")
        self._ia_canvas = canvas; self._ia_inner = inner
        # card provedor
        card=tb.Labelframe(inner,text="Provedor IA — campo OPCIONAL (selecione 1)",padding=10,bootstyle="success"); card.pack(fill=X,pady=5)
        row=tb.Frame(card); row.pack(fill=X)
        tb.Label(row,text="Provedor").pack(side=LEFT,padx=5)
        self.combo_llm=tb.Combobox(row,textvariable=self.var_llm_provider,values=["gemini","openrouter","ollama","openai","claude","groq","custom"],state="readonly",width=14); self.combo_llm.pack(side=LEFT,padx=5)
        info_icon(row, "Escolha 1 IA que reescreve seu currículo/Carta.\n• gemini = gratuito (recomendado)\n• openrouter = gratuito com várias IAs (recomendado)\n• ollama = local gratuito\n• openai/claude/groq = pago").pack(side=LEFT)
        self.btn_test_gemini=tb.Button(row,text="Testar Conexão",bootstyle="success-outline",command=self.test_gemini); self.btn_test_gemini.pack(side=RIGHT,padx=5)
        self.lbl_ai_status=tb.Label(card,text="",font=("Segoe UI",8,"bold")); self.lbl_ai_status.pack(anchor=W,pady=(6,0))
        # frame dinâmico - só mostra o campo do provedor selecionado
        self.frame_ia_dynamic = tb.Frame(card)
        self.frame_ia_dynamic.pack(fill=X, pady=6)
        # trace para reconstruir campo único
        self.var_llm_provider.trace_add("write", lambda *_: (self._rebuild_ia_fields(), self._update_ai_state()))
        for v in [self.var_gemini_key, self.var_openrouter_key, self.var_ollama_host, self.var_openai_key, self.var_claude_key, self.var_groq_key, self.var_custom_url]:
            try: v.trace_add("write", lambda *_: self._update_ai_state())
            except: pass
        self.after(300, lambda: (self._rebuild_ia_fields(), self._update_ai_state()))
        # SMTP
        card2=tb.Labelframe(inner,text="E-mail SMTP (envio automático, opcional)",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        hdr2=tb.Frame(card2); hdr2.pack(fill=X); tb.Label(hdr2,text="Envia currículos automaticamente por e-mail quando a vaga divulga e-mail de contato",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT); info_icon(hdr2, "SMTP = protocolo de envio de e-mail.\nGmail: smtp.gmail.com:587 + Senha de App (myaccount.google.com > Segurança > Senhas de app).\nOutlook: smtp.office365.com:587\nSe deixar vazio, o sistema só gera PDFs e relatório (não envia).").pack(side=LEFT,padx=4)
        g=tb.Frame(card2); g.pack(fill=X, pady=(6,0)); g.columnconfigure(1,weight=1); g.columnconfigure(3,weight=1)
        tb.Label(g,text="Host").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_host).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Porta").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_port,width=8).grid(row=0,column=3,sticky=W,padx=5,pady=3)
        tb.Label(g,text="Usuário").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_user).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Senha / App Pass").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(card2,text="Se vazio, não envia e-mail — apenas gera PDFs.",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W, pady=(4,0))
        # LinkedIn/Gupy
        card3=tb.Labelframe(inner,text="LinkedIn / Gupy (automação navegador, opcional)",padding=10,bootstyle="warning"); card3.pack(fill=X,pady=5)
        hdr3=tb.Frame(card3); hdr3.pack(fill=X); tb.Label(hdr3,text="Playwright preenche formulários com ritmo humano; CAPTCHA/teste pausa para você",font=("Segoe UI",8),bootstyle="secondary").pack(side=LEFT); info_icon(hdr3, "Automação de navegador real (Playwright).\nLinkedIn Easy Apply e Gupy: abre Chromium visível, clica em Candidatar-se e anexa PDF.\nPrecisa login. Deixe vazio para modo manual (só relatório).").pack(side=LEFT,padx=4)
        g2=tb.Frame(card3); g2.pack(fill=X); g2.columnconfigure(1,weight=1); g2.columnconfigure(3,weight=1)
        tb.Label(g2,text="LinkedIn Email").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_email).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_pass,show="*").grid(row=0,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Gupy Email").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_email).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)

    def _rebuild_ia_fields(self):
        # limpa e recria apenas o campo do provedor selecionado
        for w in self.frame_ia_dynamic.winfo_children(): w.destroy()
        p = self.var_llm_provider.get()
        # helper para criar entry com mostrar/ocultar
        def make_key_row(parent, label, var, info, placeholder=""):
            frm = tb.Frame(parent); frm.pack(fill=X, pady=2)
            tb.Label(frm, text=label, width=14, anchor=W).pack(side=LEFT, padx=5)
            ent = tb.Entry(frm, textvariable=var, show="*", width=42)
            ent.pack(side=LEFT, padx=5, fill=X, expand=True)
            if placeholder and not var.get(): ent.insert(0, placeholder)
            info_icon(frm, info).pack(side=LEFT, padx=4)
            def toggle(): ent.config(show="" if ent.cget("show")=="*" else "*"); btn.config(text="Ocultar" if ent.cget("show")=="" else "Mostrar")
            btn = tb.Button(frm, text="Mostrar", bootstyle="secondary-outline", width=7, command=toggle); btn.pack(side=LEFT, padx=5)
            # guardar refs para _update_ai_state desabilitar se necessário
            if p=="gemini": self.ent_gemini = ent
            elif p=="openrouter": self.ent_openrouter = ent
            elif p=="openai": self.ent_openai = ent
            elif p=="claude": self.ent_claude = ent
            elif p=="groq": self.ent_groq = ent
            elif p=="custom": self.ent_custom_key = ent
            return ent
        if p == "gemini":
            make_key_row(self.frame_ia_dynamic, "Gemini Key", self.var_gemini_key, "Gratuito: aistudio.google.com/app/apikey\nDeixe vazio para heurístico")
            tb.Label(self.frame_ia_dynamic, text="Recomendado gratuito: Gemini ou OpenRouter. Sem chave usa heurístico e funções ficam cinza.", font=("Segoe UI",8), bootstyle="secondary").pack(anchor=W, pady=(4,0))
        elif p == "openrouter":
            make_key_row(self.frame_ia_dynamic, "OpenRouter Key", self.var_openrouter_key, "Gratuito: openrouter.ai/keys\nAgrupa Gemini/Claude/Llama gratuitos. Recomendado!")
            # dropdown de modelo (o usuário escolhe qual modelo gratuito usar)
            frm_model = tb.Frame(self.frame_ia_dynamic); frm_model.pack(fill=X, pady=2)
            tb.Label(frm_model, text="Modelo:").pack(side=LEFT, padx=5)
            # Lista oficial de modelos gratuitos OpenRouter (confirmada pelo usuário: openrouter.ai/keys, variante free)
            openrouter_free_models = [
                "inclusionai/ling-3.0-flash-fin:free",
                "nvidia/nemotron-3.5-lightning:free",
                "thinkingmachines/inkling-small:free",
                "thinkingmachines/inkling:free",
                "z-ai/glm-5.2:free",
                "nvidia/nemotron-3-ultra-550b-a55b:free",
                "google/gemma-4-31b-it:free",
            ]
            self.combo_openrouter_model = tb.Combobox(frm_model, textvariable=self.var_openrouter_model, values=openrouter_free_models, state="readonly", width=42)
            self.combo_openrouter_model.pack(side=LEFT, padx=5, fill=X, expand=True)
            info_icon(frm_model, "Escolha o modelo gratuito do OpenRouter.\nCada um consome a mesma chave universal.").pack(side=LEFT, padx=4)
            tb.Label(self.frame_ia_dynamic, text="OpenRouter — chave universal gratuita (openrouter.ai/keys). Modelos confirmados pelo usuário (free): inclusionai/ling-3.0-flash-fin, nvidia/nemotron-3.5-lightning, thinkingmachines/inkling-small, thinkingmachines/inkling, z-ai/glm-5.2, nvidia/nemotron-3-ultra-550b-a55b, google/gemma-4-31b-it. Modelo padrão: inclusionai/ling-3.0-flash-fin:free", font=("Segoe UI",8), bootstyle="secondary").pack(anchor=W, pady=(2,0))
        elif p == "ollama":
            frm = tb.Frame(self.frame_ia_dynamic); frm.pack(fill=X, pady=2)
            tb.Label(frm, text="Ollama Host", width=14, anchor=W).pack(side=LEFT, padx=5)
            self.ent_ollama_host = tb.Entry(frm, textvariable=self.var_ollama_host, width=28); self.ent_ollama_host.pack(side=LEFT, padx=5)
            info_icon(frm, "IA local gratuita. Instale ollama.com e rode 'ollama run llama3'").pack(side=LEFT)
            tb.Label(frm, text="Modelo").pack(side=LEFT, padx=5)
            self.ent_ollama_model = tb.Entry(frm, textvariable=self.var_ollama_model, width=18); self.ent_ollama_model.pack(side=LEFT, padx=5)
        elif p == "openai":
            make_key_row(self.frame_ia_dynamic, "OpenAI Key", self.var_openai_key, "platform.openai.com/api-keys — pago gpt-4o-mini")
        elif p == "claude":
            make_key_row(self.frame_ia_dynamic, "Claude Key", self.var_claude_key, "console.anthropic.com — pago claude-3-haiku")
        elif p == "groq":
            make_key_row(self.frame_ia_dynamic, "Groq Key", self.var_groq_key, "console.groq.com — rápido")
        elif p == "custom":
            frm = tb.Frame(self.frame_ia_dynamic); frm.pack(fill=X, pady=2)
            tb.Label(frm, text="Custom URL", width=14, anchor=W).pack(side=LEFT, padx=5)
            self.ent_custom_url = tb.Entry(frm, textvariable=self.var_custom_url, width=38); self.ent_custom_url.pack(side=LEFT, padx=5, fill=X, expand=True)
            info_icon(frm, "Ex: https://api.deepseek.com/v1/chat/completions").pack(side=LEFT, padx=4)
            make_key_row(self.frame_ia_dynamic, "Custom Key", self.var_custom_key, "Chave do provedor custom")
        # garantir refs para quem não foi recriado ainda
        for attr in ["ent_gemini","ent_openrouter","ent_ollama_host","ent_openai","ent_claude","ent_groq","ent_custom_url"]:
            if not hasattr(self, attr):
                try: setattr(self, attr, tb.Entry(self.frame_ia_dynamic))
                except: pass

    def show_toast(self, msg, duration=2500):
        t = tb.Toplevel(self)
        t.overrideredirect(True)
        # posição canto inferior direito
        t.geometry(f"320x50+{self.winfo_rootx()+self.winfo_width()-340}+{self.winfo_rooty()+self.winfo_height()-80}")
        t.attributes("-topmost", True)
        frm = tb.Frame(t, bootstyle="success", padding=10)
        frm.pack(fill=BOTH, expand=True)
        tb.Label(frm, text=msg, bootstyle="inverse-success").pack()
        t.after(duration, t.destroy)

    def toggle_theme(self):
        cur = self.style.theme.name
        new = "flatly" if cur == "darkly" else "darkly"
        self.style.theme_use(new)
        self.btn_theme.config(text="🌙 Escuro" if new=="flatly" else "☀ Claro")
        # ajustar contraste do header conforme tema
        if new == "flatly":
            self.lbl_subtitle.config(bootstyle="secondary")
            self.lbl_stepper.config(bootstyle="secondary")
            self.btn_theme.config(bootstyle="secondary-outline")
            self.btn_export_top.config(bootstyle="secondary-outline")
            self.btn_import_top.config(bootstyle="secondary-outline")
        else:
            self.lbl_subtitle.config(bootstyle="light")
            self.lbl_stepper.config(bootstyle="light")
            self.btn_theme.config(bootstyle="light-outline")
            self.btn_export_top.config(bootstyle="light-outline")
            self.btn_import_top.config(bootstyle="light-outline")
        # atualizar fundos hard-coded para modo claro realista
        try:
            is_dark = new == "darkly"
            bg_canvas = "#222222" if is_dark else "#ffffff"
            bg_list = "#1e1e1e" if is_dark else "#ffffff"
            fg_list = "white" if is_dark else "black"
            bg_text = "#2b2b2b" if is_dark else "#ffffff"
            fg_text = "#e0e0e0" if is_dark else "#212529"
            if hasattr(self, '_busca_canvas'):
                self._busca_canvas.config(bg=bg_canvas)
            for attr in ["lst_skills","lst_exp","lst_edu","tree","bars_text","log_text","txt_summary"]:
                if hasattr(self, attr):
                    w = getattr(self, attr)
                    try:
                        # Treeview handle separately (ttk)
                        if attr == "tree":
                            # ttk Treeview theme já cuida, mas forçar
                            pass
                        elif isinstance(w, tk.Text):
                            w.config(bg=bg_text, fg=fg_text, insertbackground=fg_text)
                        elif isinstance(w, tk.Listbox):
                            w.config(bg=bg_list, fg=fg_list)
                    except: pass
        except: pass
        self._update_stepper()
        self.show_toast(f"Tema {new} ativado")

    def _validate_email(self, *_):
        import re
        email = self.var_email.get().strip()
        if not email:
            try: self.ent_email.config(bootstyle="secondary")
            except: pass
            return
        ok = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None
        try:
            self.ent_email.config(bootstyle="success" if ok else "danger")
        except: pass
        if hasattr(self, 'lbl_email_hint'):
            self.lbl_email_hint.config(text="✓ válido" if ok else "✗ e-mail inválido — borda vermelha", bootstyle="success" if ok else "danger")

    def show_wizard(self):
        # só mostra na primeira vez
        flag = BASE_DIR / ".wizard_done"
        if flag.exists():
            return
        top = tb.Toplevel(self)
        top.title("Bem-vindo ao JobAutoFit")
        top.geometry("520x360")
        # posicionar no canto superior direito do app
        self.update_idletasks()
        try:
            ax = self.winfo_rootx(); ay = self.winfo_rooty(); aw = self.winfo_width()
            wx = ax + aw - 540  # 520 + margem
            wy = ay + 60
            # garantir dentro da tela
            sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
            wx = max(0, min(wx, sw - 540)); wy = max(0, min(wy, sh - 380))
            top.geometry(f"520x360+{wx}+{wy}")
        except: pass
        top.transient(self)
        top.grab_set()
        tb.Label(top, text=" Bem-vindo! Vamos configurar em 4 passos:", font=("Segoe UI", 12, "bold")).pack(pady=12)
        steps = [
            "1. Aba Currículo → Importar PDF/DOCX ou preencher dados",
            "2. Aba Busca & Filtros → definir palavras-chave e regime",
            "3. Aba IA & Conexões → testar Gemini/Ollama (opcional)",
            "4. Aba Execução → Iniciar Automação e ver relatório"
        ]
        for s in steps:
            tb.Label(top, text=s, anchor=W).pack(fill=X, padx=20, pady=4)
        tb.Label(top, text="Dica: passe o mouse no ⓘ para ajuda de cada campo.", font=("Segoe UI", 8), bootstyle="secondary").pack(pady=8)
        def close():
            flag.write_text("done")
            top.destroy()
            self.nb.select(self.tab_perfil)
        tb.Button(top, text="Começar", bootstyle="success", command=close).pack(pady=12)
        self.wait_window(top)

    def _update_stepper(self, *_):
        try:
            idx = self.nb.index(self.nb.select())
            steps = ["① Currículo", "② Busca", "③ IA", "④ Execução", "⑤ Dashboard", "⑥ Histórico", "⑦ GitHub"]
            txt = " → ".join([f"[{s}]" if i==idx else s for i,s in enumerate(steps)])
            self.lbl_stepper.config(text=txt)
        except Exception:
            pass

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
        # habilitar apenas campos do provedor ativo (para modo dinâmico, só o visível existe)
        if hasattr(self, 'ent_gemini'): 
            try: self.ent_gemini.config(state=NORMAL if p=="gemini" else DISABLED)
            except: pass
        if hasattr(self, 'ent_openai'): 
            try: self.ent_openai.config(state=NORMAL if p=="openai" else DISABLED)
            except: pass
        if hasattr(self, 'ent_claude'): 
            try: self.ent_claude.config(state=NORMAL if p=="claude" else DISABLED)
            except: pass
        if hasattr(self, 'ent_groq'): 
            try: self.ent_groq.config(state=NORMAL if p=="groq" else DISABLED)
            except: pass
        if hasattr(self, 'ent_openrouter'): 
            try: self.ent_openrouter.config(state=NORMAL if p=="openrouter" else DISABLED)
            except: pass
        if hasattr(self, 'ent_ollama_host'):
            s = NORMAL if p=="ollama" else DISABLED
            try: self.ent_ollama_host.config(state=s); self.ent_ollama_model.config(state=s)
            except: pass
        if hasattr(self, 'ent_custom_url'):
            s2 = NORMAL if p=="custom" else DISABLED
            try: self.ent_custom_url.config(state=s2); self.ent_custom_key.config(state=s2)
            except: pass
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
        # testa o provedor selecionado
        p=self.var_llm_provider.get()
        key_map={"gemini":self.var_gemini_key.get().strip(),"openrouter":self.var_openrouter_key.get().strip(),"openai":self.var_openai_key.get().strip(),"claude":self.var_claude_key.get().strip(),"groq":self.var_groq_key.get().strip(),"custom":self.var_custom_key.get().strip(),"ollama":"ok"}
        key=key_map.get(p,"")
        if p!="ollama" and not key: messagebox.showwarning("IA", f"Informe a chave de '{p}'"); return
        try:
            if p=="gemini":
                import google.generativeai as genai
                genai.configure(api_key=key); m=genai.GenerativeModel("gemini-1.5-flash"); r=m.generate_content("Responda OK")
                messagebox.showinfo("Gemini", r.text[:200])
            elif p=="openrouter":
                from ats_optimizer import _call_openai_compat
                ans=_call_openai_compat("Responda apenas OK", key, "https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.1-8b-instruct:free")
                messagebox.showinfo("OpenRouter", ans[:400] if ans else "Sem resposta — verifique chave/modelo free")
            elif p=="ollama":
                import requests; r=requests.get(f"{self.var_ollama_host.get().strip()}/api/tags", timeout=5); messagebox.showinfo("Ollama", f"OK — {r.status_code}" if r.status_code==200 else r.text[:300])
            else:
                # openai/claude/groq/custom via call_llm
                from ats_optimizer import call_llm
                # forçar provider temporário
                import config; old=config.Config.LLM_PROVIDER; config.Config.LLM_PROVIDER=p
                # injetar chave temporária se necessário
                if p=="openai": config.Config.OPENAI_API_KEY=key
                elif p=="claude": config.Config.CLAUDE_API_KEY=key
                elif p=="groq": config.Config.GROQ_API_KEY=key
                elif p=="custom": config.Config.CUSTOM_LLM_KEY=key
                ans=call_llm("Responda apenas OK")
                config.Config.LLM_PROVIDER=old
                messagebox.showinfo(p, ans[:400] if ans else "Sem resposta")
        except Exception as e: messagebox.showerror(p, str(e))

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
        self.bars_text=tk.Text(self.frame_bars,height=6,bg="#1e1e1e",fg="#d0d0d0",font=("Consolas",9)); self.bars_text.pack(fill=BOTH,expand=False)
        # gráfico funil matplotlib
        self.fig_frame = tb.Frame(self.frame_bars); self.fig_frame.pack(fill=BOTH, expand=True, pady=6)
        tb.Label(self.frame_bars, text="Funil: coleta → filtro → match≥60 → enviado (gerado via filters + ATS)", font=("Segoe UI",8), bootstyle="secondary").pack(anchor=W)
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
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE status IN ('applied','prepared')")
            sent_row = cur.fetchone()
            sent = sent_row["c"] if sent_row else 0
            con.close()
            txt=f"Por status:\n"
            for r in rows: txt+=f"  {r['status']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            txt+="\nPor plataforma:\n"
            for r in rows2: txt+=f"  {r['platform']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            self.bars_text.delete("1.0",tk.END); self.bars_text.insert("1.0",txt)
            # matplotlib funil
            try:
                for w in self.fig_frame.winfo_children(): w.destroy()
                import matplotlib
                matplotlib.use("Agg")
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                # funil: total → high → enviados
                stages = ["Coletadas", "Match ≥60%", "Enviadas"]
                vals = [total or 0, high or 0, sent or 0]
                fig = Figure(figsize=(6,2), dpi=100)
                fig.patch.set_facecolor("#2b2b2b")
                ax = fig.add_subplot(111)
                ax.set_facecolor("#2b2b2b")
                ax.bar(stages, vals, color=["#375a7f","#00bc8c","#f39c12"])
                ax.tick_params(colors="white", labelsize=8)
                for spine in ax.spines.values(): spine.set_color("white")
                ax.set_title("Funil", color="white", fontsize=9)
                for i, v in enumerate(vals): ax.text(i, v+0.3, str(v), ha="center", color="white", fontsize=8)
                canvas = FigureCanvasTkAgg(fig, master=self.fig_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=BOTH, expand=True)
            except Exception as e:
                # fallback sem matplotlib
                pass
        except Exception as e: pass

    # Histórico
    def _build_hist(self):
        f=self.tab_hist
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Label(top,text="Histórico (jobs.db) — duplo clique abre vaga").pack(side=LEFT,padx=5)
        tb.Button(top,text="Exportar CSV",bootstyle="success-outline",command=self._export_hist_csv).pack(side=RIGHT,padx=5)
        tb.Button(top,text="Perguntas IA",bootstyle="warning-outline",command=self._hist_interview).pack(side=RIGHT,padx=5)
        tb.Button(top,text="Diff ATS",bootstyle="info-outline",command=self._hist_diff).pack(side=RIGHT,padx=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_hist).pack(side=RIGHT,padx=5)
        # filtro
        filt = tb.Frame(f); filt.pack(fill=X, pady=5)
        tb.Label(filt, text="Filtro:").pack(side=LEFT, padx=5)
        self.var_hist_filter = tk.StringVar()
        ent = tb.Entry(filt, textvariable=self.var_hist_filter, width=40)
        ent.pack(side=LEFT, padx=5, fill=X, expand=True)
        ent.bind("<KeyRelease>", lambda e: self._refresh_hist())
        info_icon(filt, "Filtra por vaga/empresa/status. Clique no cabeçalho para ordenar. Botão direito: menu").pack(side=LEFT, padx=5)
        cols=("vaga","empresa","local","match","status","plataforma")
        self.tree=tb.Treeview(f,columns=cols,show="headings",bootstyle="dark",height=14)
        for c in cols:
            self.tree.heading(c,text=c.capitalize(), command=lambda _c=c: self._sort_tree(_c, False))
        self.tree.column("vaga",width=260); self.tree.column("empresa",width=160); self.tree.column("local",width=140); self.tree.column("match",width=60,anchor=CENTER); self.tree.column("status",width=110,anchor=CENTER); self.tree.column("plataforma",width=90,anchor=CENTER)
        self.tree.pack(fill=BOTH,expand=True,pady=5)
        self.tree.bind("<Double-Button-1>",self._on_hist_dbl)
        # menu contexto
        self.hist_menu = tk.Menu(self, tearoff=0)
        self.hist_menu.add_command(label="Abrir vaga", command=self._hist_open)
        self.hist_menu.add_command(label="Copiar link", command=self._hist_copy)
        self.hist_menu.add_separator()
        self.hist_menu.add_command(label="Diff ATS (original vs vaga)", command=self._hist_diff)
        self.hist_menu.add_command(label="Gerar perguntas entrevista (IA)", command=self._hist_interview)
        self.hist_menu.add_separator()
        self.hist_menu.add_command(label="Excluir", command=self._hist_delete)
        self.hist_menu.add_command(label="Adicionar nota", command=self._hist_note)
        self.tree.bind("<Button-3>", self._show_hist_menu)
        self._hist_sort_reverse = {}
        self._refresh_hist()
    def _build_github(self):
        f=self.tab_github
        top=tb.Frame(f); top.pack(fill=X, pady=5)
        tb.Label(top, text="GitHub User:").pack(side=LEFT, padx=5)
        tb.Entry(top, textvariable=self.var_github_user, width=20).pack(side=LEFT, padx=5)
        info_icon(top, "Seu username do GitHub (ex: seu-usuario)\nUsado para buscar repos públicos").pack(side=LEFT)
        tb.Label(top, text="Token (opcional):").pack(side=LEFT, padx=(15,5))
        tb.Entry(top, textvariable=self.var_github_token, show="*", width=22).pack(side=LEFT, padx=5)
        info_icon(top, "Token aumenta limite de 60→5000 req/h e vê privados.\nGere em github.com/settings/tokens (sem escopo para públicos)").pack(side=LEFT)
        tb.Button(top, text="Buscar Repos", bootstyle="info", command=self._github_fetch).pack(side=LEFT, padx=8)
        tb.Label(f, text="Clique na estrela ⭐ para marcar os repos que quer reestruturar o README. Depois clique em Gerar.", font=("Segoe UI",8), bootstyle="secondary").pack(anchor=W, pady=4)
        cols=("star","repo","lang","stars","desc")
        self.github_tree=tb.Treeview(f, columns=cols, show="headings", bootstyle="dark", height=14)
        self.github_tree.heading("star", text="⭐"); self.github_tree.heading("repo", text="Repositório"); self.github_tree.heading("lang", text="Lang"); self.github_tree.heading("stars", text="★"); self.github_tree.heading("desc", text="Descrição")
        self.github_tree.column("star", width=40, anchor=CENTER); self.github_tree.column("repo", width=200); self.github_tree.column("lang", width=90, anchor=CENTER); self.github_tree.column("stars", width=50, anchor=CENTER); self.github_tree.column("desc", width=400)
        # cor para estrelados — fundo amarelo escuro + estrela dourada
        self.github_tree.tag_configure("starred", background="#4a3f00", foreground="#FFD700")
        self.github_tree.tag_configure("normal", background="", foreground="")
        self.github_tree.pack(fill=BOTH, expand=True, pady=5)
        self.github_tree.bind("<Button-1>", self._github_toggle_star)
        self.github_tree.bind("<Double-Button-1>", self._github_open)
        # menu
        self.github_menu=tk.Menu(self, tearoff=0)
        self.github_menu.add_command(label="Abrir no GitHub", command=self._github_open)
        self.github_menu.add_command(label="Alternar ⭐", command=lambda: self._github_toggle_star(None))
        self.github_tree.bind("<Button-3>", lambda e: self.github_menu.post(e.x_root, e.y_root))
        btns=tb.Frame(f); btns.pack(fill=X, pady=5)
        tb.Button(btns, text="Gerar READMEs para ⭐ estrelados", bootstyle="success", command=self._github_generate).pack(side=LEFT, padx=5)
        tb.Button(btns, text="Preview README Perfil", bootstyle="info-outline", command=self._github_preview_profile).pack(side=LEFT, padx=5)
        tb.Button(btns, text="Abrir pasta output_github", bootstyle="secondary", command=lambda: self._open_folder(BASE_DIR/"output_github")).pack(side=LEFT, padx=5)
        tb.Label(btns, text="Selecione com ⭐ e gere drafts em output_github/ para revisar antes do push", font=("Segoe UI",8), bootstyle="secondary").pack(side=LEFT, padx=10)
        # carregar se já tiver repos em cache? tentar fetch silencioso se já tiver seleção
        if self.github_starred:
            self.after(800, lambda: self._github_fetch(silent=True))

    def _github_fetch(self, silent=False):
        user=self.var_github_user.get().strip()
        if not user:
            if not silent: messagebox.showwarning("GitHub", "Informe o username")
            return
        try:
            from github_optimizer import fetch_repos
            token=self.var_github_token.get().strip()
            self._log_hist = getattr(self, "_log", lambda x: None)
            # usar thread para não travar
            def do_fetch():
                try:
                    repos=fetch_repos(user, token)
                    self.github_repos=repos
                    self.after(0, lambda: self._github_populate())
                    if not silent:
                        self.after(0, lambda: self.show_toast(f"{len(repos)} repos encontrados"))
                except Exception as e:
                    if not silent:
                        self.after(0, lambda: messagebox.showerror("GitHub", str(e)))
            import threading; threading.Thread(target=do_fetch, daemon=True).start()
        except Exception as e:
            if not silent: messagebox.showerror("GitHub", str(e))
    def _github_populate(self):
        for i in self.github_tree.get_children(): self.github_tree.delete(i)
        for r in self.github_repos:
            is_starred = r["name"] in self.github_starred
            star="★" if is_starred else "☆"
            tags=(r["name"], "starred") if is_starred else (r["name"], "normal")
            self.github_tree.insert("", "end", values=(star, r["name"], r["language"], r["stars"], r["description"][:80]), tags=tags)
    def _github_toggle_star(self, event):
        # identificar linha clicada
        try:
            # se clicou no cabeçalho, ignora
            region=self.github_tree.identify("region", event.x, event.y) if event else "cell"
            if region=="heading": return
            iid=self.github_tree.identify_row(event.y) if event else (self.github_tree.selection()[0] if self.github_tree.selection() else None)
            if not iid: return
            # coluna star?
            col=self.github_tree.identify_column(event.x) if event else "#1"
            # alternar estrela para a linha
            vals=self.github_tree.item(iid, "values")
            repo_name=self.github_tree.item(iid, "tags")[0] if self.github_tree.item(iid, "tags") else vals[1]
            if repo_name in self.github_starred:
                self.github_starred.remove(repo_name)
            else:
                self.github_starred.add(repo_name)
            # salvar
            try: (BASE_DIR/"github_selection.json").write_text(json.dumps(sorted(list(self.github_starred)), ensure_ascii=False, indent=2), encoding="utf-8")
            except: pass
            self._github_populate()
            # manter seleção
            for child in self.github_tree.get_children():
                if self.github_tree.item(child, "tags")[0]==repo_name:
                    self.github_tree.selection_set(child)
                    break
        except: pass
    def _github_open(self, event=None):
        sel=self.github_tree.selection()
        if not sel: return
        repo=self.github_tree.item(sel[0], "tags")[0]
        webbrowser.open(f"https://github.com/{self.var_github_user.get().strip()}/{repo}")
    def _github_generate(self):
        if not self.github_starred:
            messagebox.showwarning("GitHub", "Selecione com ⭐ pelo menos 1 repo")
            return
        try:
            from github_optimizer import save_drafts
            import pathlib
            # filtrar repos estrelados
            selected=[r for r in self.github_repos if r["name"] in self.github_starred]
            if not selected:
                # se não tem cache, buscar das estreladas via nome
                selected=[{"name":n, "full_name":f"{self.var_github_user.get().strip()}/{n}", "html_url":f"https://github.com/{self.var_github_user.get().strip()}/{n}", "description":"", "language":"", "stars":0} for n in self.github_starred]
            out_dir=BASE_DIR/"output_github"
            # garantir curriculum atualizado
            self.save_all(silent=True)
            cur=self.curriculum
            files=save_drafts(selected, out_dir, cur)
            messagebox.showinfo("GitHub", f"{len(files)} READMEs gerados em output_github/\nRevise antes de copiar para cada repo.")
            self._open_folder(out_dir)
            self.show_toast(f"{len(files)} READMEs gerados")
        except Exception as e: messagebox.showerror("GitHub", str(e))
    def _github_preview_profile(self):
        try:
            p=BASE_DIR/"PROFILE_README_EXPERIMENTAL.md"
            if p.exists(): webbrowser.open(p.as_uri())
            else: messagebox.showinfo("Preview", "PROFILE_README_EXPERIMENTAL.md não encontrado — gere via módulo GitHub primeiro")
        except Exception as e: messagebox.showerror("Preview", str(e))
    def _refresh_hist(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            if not DB_PATH.exists(): return
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT title,company,location,match_score,status,platform,url FROM jobs ORDER BY id DESC LIMIT 500")
            rows = cur.fetchall()
            con.close()
            filt = self.var_hist_filter.get().lower().strip() if hasattr(self, 'var_hist_filter') else ""
            for r in rows:
                vals = (r["title"],r["company"],r["location"],f"{r['match_score'] or 0}%",r["status"],r["platform"])
                if filt and filt not in " ".join([str(v).lower() for v in vals]):
                    continue
                self.tree.insert("",tk.END,values=vals, tags=(r["url"] or "",))
        except Exception as e:
            pass
    def _sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        # tratar match %
        try:
            if col=="match":
                l.sort(key=lambda x: int(x[0].replace("%","") or 0), reverse=reverse)
            else:
                l.sort(key=lambda x: x[0].lower(), reverse=reverse)
        except:
            l.sort(reverse=reverse)
        for idx, (val, k) in enumerate(l):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))
    def _show_hist_menu(self, ev):
        try:
            iid = self.tree.identify_row(ev.y)
            if iid:
                self.tree.selection_set(iid)
                self.hist_menu.post(ev.x_root, ev.y_root)
        except: pass
    def _hist_open(self): self._on_hist_dbl(None)
    def _hist_copy(self):
        sel=self.tree.selection()
        if not sel: return
        url = self.tree.item(sel[0], "tags")
        if url and url[0]:
            self.clipboard_clear(); self.clipboard_append(url[0]); self.show_toast("Link copiado")
    def _hist_delete(self):
        sel=self.tree.selection()
        if not sel or not messagebox.askyesno("Excluir", "Excluir vaga do histórico?"): return
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); cur=con.cursor()
            # pega url do item
            url = self.tree.item(sel[0], "tags")
            if url and url[0]:
                cur.execute("DELETE FROM jobs WHERE url=?", (url[0],))
                con.commit()
            con.close()
            self.tree.delete(sel[0])
            self.show_toast("Excluído")
            self._refresh_dashboard()
        except Exception as e: messagebox.showerror("Erro", str(e))
    def _hist_note(self):
        sel=self.tree.selection()
        if not sel: return
        url = self.tree.item(sel[0], "tags")
        if not url or not url[0]: return
        # simples: armazena nota em arquivo .notes
        from tkinter.simpledialog import askstring
        note = askstring("Nota", "Anotação para esta vaga (ex: 'enviei por e-mail'):")
        if note is not None:
            # salva em arquivo lateral
            notes_path = BASE_DIR / "job_notes.json"
            notes = {}
            if notes_path.exists():
                try: notes = json.loads(notes_path.read_text(encoding="utf-8"))
                except: notes={}
            notes[url[0]] = note
            notes_path.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
            self.show_toast("Nota salva")
    def _hist_diff(self):
        sel=self.tree.selection()
        if not sel: messagebox.showwarning("Diff", "Selecione uma vaga"); return
        url=self.tree.item(sel[0],"tags")
        if not url or not url[0]: return
        # buscar job no db
        try:
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT description, title, company FROM jobs WHERE url=?", (url[0],))
            row=cur.fetchone(); con.close()
            if not row: return
            desc=row["description"] or ""
            # diff simples: skills do currículo vs palavras da vaga
            skills=self.curriculum.get("skills",[])
            found=[s for s in skills if s.lower() in desc.lower()]
            missing=[s for s in skills if s.lower() not in desc.lower()]
            top=tb.Toplevel(self); top.title(f"Diff ATS — {row['title']} @ {row['company']}"); top.geometry("700x500"); top.transient(self); top.grab_set()
            tb.Label(top, text=f"Vaga: {row['title']} @ {row['company']}", font=("Segoe UI",10,"bold")).pack(pady=6, anchor=W, padx=10)
            txt=tk.Text(top, wrap="word", bg="#1e1e1e", fg="#d0d0d0", font=("Consolas",9)); txt.pack(fill=BOTH, expand=True, padx=10, pady=5)
            txt.insert("1.0", f"Resumo original:\n{self.curriculum.get('summary','')[:600]}\n\n--- SKILLS ENCONTRADAS NA VAGA ({len(found)}) ---\n" + ", ".join(found) + f"\n\n--- SKILLS NÃO ENCONTRADAS ({len(missing)}) ---\n" + ", ".join(missing) + f"\n\n--- DESCRIÇÃO (trecho) ---\n{desc[:1200]}")
            txt.config(state=DISABLED)
            tb.Button(top, text="Fechar", bootstyle="secondary", command=top.destroy).pack(pady=8)
            # histórico PDFs: listar
            pdfs = list((BASE_DIR/"output").glob("*.pdf"))
            if pdfs: tb.Label(top, text=f"{len(pdfs)} PDFs em output/ — último: {sorted(pdfs, key=lambda x: x.stat().st_mtime)[-1].name}", font=("Segoe UI",8), bootstyle="secondary").pack()
        except Exception as e: messagebox.showerror("Diff", str(e))
    def _hist_interview(self):
        sel=self.tree.selection()
        if not sel: messagebox.showwarning("Entrevista", "Selecione uma vaga"); return
        url=self.tree.item(sel[0],"tags")
        if not url or not url[0]: return
        # verificar IA
        p=self.var_llm_provider.get()
        has_key=bool(self.var_gemini_key.get().strip() or self.var_openai_key.get().strip() or self.var_claude_key.get().strip() or self.var_groq_key.get().strip() or self.var_custom_key.get().strip() or p=="ollama")
        if not has_key and p=="gemini":
            messagebox.showwarning("IA", "Configure uma chave de IA na aba 3 para gerar perguntas")
            return
        try:
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT description, title, company FROM jobs WHERE url=?", (url[0],))
            row=cur.fetchone(); con.close()
            if not row: return
            from ats_optimizer import call_llm
            prompt=f"Gere 8 perguntas de entrevista técnicas e comportamentais para a vaga '{row['title']}' na empresa '{row['company']}'. Descrição: {row['description'][:2000]}. Responda em português, numeradas, com dica curta de como responder."
            ans=call_llm(prompt)
            if not ans or "heurística" in ans.lower():
                # fallback sem IA
                ans="1. Fale sobre sua experiência com as tecnologias citadas na vaga.\n2. Como você resolveria um bug crítico em produção?\n3. Exemplo de projeto desafiador e aprendizado.\n4. Como trabalha em equipe remota?\n5. Como prioriza tarefas com prazo curto?\n(Configure IA para perguntas personalizadas)"
            top=tb.Toplevel(self); top.title(f"Perguntas Entrevista — {row['title']}"); top.geometry("700x500"); top.transient(self); top.grab_set()
            tb.Label(top, text=f"Perguntas para: {row['title']} @ {row['company']}", font=("Segoe UI",10,"bold")).pack(pady=6)
            txt=tk.Text(top, wrap="word", bg="#1e1e1e", fg="#d0d0d0", font=("Segoe UI",10)); txt.pack(fill=BOTH, expand=True, padx=10, pady=5)
            txt.insert("1.0", ans); txt.config(state=DISABLED)
            tb.Button(top, text="Copiar", bootstyle="info-outline", command=lambda: (self.clipboard_clear(), self.clipboard_append(ans), self.show_toast("Copiado"))).pack(side=LEFT, padx=20, pady=8)
            tb.Button(top, text="Fechar", bootstyle="secondary", command=top.destroy).pack(side=RIGHT, padx=20, pady=8)
        except Exception as e: messagebox.showerror("Entrevista", str(e))
    def _export_hist_csv(self):
        try:
            import csv, sqlite3
            p=filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile=f"historico_{datetime.now().strftime('%Y%m%d')}.csv")
            if not p: return
            con=sqlite3.connect(str(DB_PATH)); cur=con.cursor()
            cur.execute("SELECT title,company,location,match_score,status,platform,url,created_at FROM jobs ORDER BY id DESC")
            rows=cur.fetchall(); con.close()
            with open(p,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["vaga","empresa","local","match","status","plataforma","url","data"])
                w.writerows(rows)
            # webhook opcional
            webhook=self.search_cfg.get("webhook_url","")
            if webhook:
                try:
                    import requests; requests.post(webhook, json={"event":"export_csv","count":len(rows)}, timeout=5)
                except: pass
            self.show_toast(f"CSV exportado: {len(rows)} vagas")
            self._open_folder(Path(p).parent)
        except Exception as e: messagebox.showerror("Export", str(e))
    def _on_hist_dbl(self,ev):
        sel=self.tree.selection()
        if not sel: return
        try:
            url = self.tree.item(sel[0], "tags")
            if url and url[0]: webbrowser.open(url[0])
            else:
                # fallback antigo
                import sqlite3; con=sqlite3.connect(str(DB_PATH)); cur=con.cursor(); idx=self.tree.index(sel[0]); cur.execute("SELECT url FROM jobs ORDER BY id DESC LIMIT 1 OFFSET ?",(idx,)); row=cur.fetchone()
                if row and row[0]: webbrowser.open(row[0])
                con.close()
        except: pass

    # Save/export
    def save_all(self,silent=False):
        self.curriculum["personal_info"]={"name":self.var_name.get().strip(),"email":self.var_email.get().strip(),"phone":self.var_phone.get().strip(),"location":self.var_location.get().strip(),"linkedin":self.var_linkedin.get().strip(),"github":self.var_github.get().strip()}
        self.curriculum["summary"]=self.txt_summary.get("1.0","end").strip(); save_curriculum(self.curriculum)
        self.env.update(GEMINI_API_KEY=self.var_gemini_key.get().strip(),LLM_PROVIDER=self.var_llm_provider.get().strip().lower(),OLLAMA_HOST=self.var_ollama_host.get().strip(),OLLAMA_MODEL=self.var_ollama_model.get().strip(),OPENAI_API_KEY=self.var_openai_key.get().strip(),CLAUDE_API_KEY=self.var_claude_key.get().strip(),GROQ_API_KEY=self.var_groq_key.get().strip(),OPENROUTER_API_KEY=self.var_openrouter_key.get().strip(),CUSTOM_LLM_URL=self.var_custom_url.get().strip(),CUSTOM_LLM_KEY=self.var_custom_key.get().strip(),GITHUB_USER=self.var_github_user.get().strip(),GITHUB_TOKEN=self.var_github_token.get().strip(),SMTP_HOST=self.var_smtp_host.get().strip(),SMTP_PORT=self.var_smtp_port.get().strip(),SMTP_USER=self.var_smtp_user.get().strip(),SMTP_PASS=self.var_smtp_pass.get().strip(),LINKEDIN_EMAIL=self.var_linkedin_email.get().strip(),LINKEDIN_PASSWORD=self.var_linkedin_pass.get().strip(),GUPY_EMAIL=self.var_gupy_email.get().strip(),GUPY_PASSWORD=self.var_gupy_pass.get().strip(),WORK_MODE=self.var_work_mode.get().strip(),PRESENCIAL_LOCATION=self.var_presencial_loc.get().strip(),CONTRACT_TYPE=self.var_contract.get().strip(),TELEGRAM_BOT_TOKEN=self.var_telegram_token.get().strip(),TELEGRAM_CHAT_ID=self.var_telegram_chat.get().strip(),DAILY_LIMIT=str(int(self.var_daily_limit.get())))
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
