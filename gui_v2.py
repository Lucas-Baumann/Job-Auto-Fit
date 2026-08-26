import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

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
    return {"keywords":["Desenvolvedor Python","Python Developer"],"work_mode":"remoto","presencial_location":"","contract_type":"indiferente","min_score":60,"limit_per_source":8,"min_salary":0,"level":"indiferente","exclude_keywords":[],"mandatory_words":[],"blocked_companies":[],"favorite_companies":[],"max_age_days":0,"only_pcd":False,"english_filter":"indiferente","daily_limit":20,"telegram_bot_token":"","telegram_chat_id":"","schedule_enabled":False,"schedule_hour":"08:00"}
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
        self.var_dry_run=tk.BooleanVar(value=True)
        self._build_ui(); self._bind_work_mode(); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list(); self._refresh_dashboard()

    def _build_ui(self):
        top=tb.Frame(self,padding=10); top.pack(fill=X)
        tb.Label(top,text="JobAutoFit",font=("Segoe UI",18,"bold"),bootstyle="primary").pack(side=LEFT)
        tb.Label(top,text="  Coleta • Filtragem Avançada • ATS • Envio • Relatório • Dashboard",font=("Segoe UI",10),bootstyle="secondary").pack(side=LEFT,padx=10)
        tb.Button(top,text="Exportar",bootstyle="secondary-outline",command=self.export_config).pack(side=RIGHT,padx=5)
        tb.Button(top,text="Importar",bootstyle="secondary-outline",command=self.import_config).pack(side=RIGHT,padx=5)
        self.nb=tb.Notebook(self,bootstyle="dark"); self.nb.pack(fill=BOTH,expand=True,padx=10,pady=(0,10))
        self.tab_perfil=tb.Frame(self.nb,padding=10); self.tab_busca=tb.Frame(self.nb,padding=10); self.tab_ia=tb.Frame(self.nb,padding=10); self.tab_exec=tb.Frame(self.nb,padding=10); self.tab_dash=tb.Frame(self.nb,padding=10); self.tab_hist=tb.Frame(self.nb,padding=10)
        self.nb.add(self.tab_perfil,text=" 1. Currículo "); self.nb.add(self.tab_busca,text=" 2. Busca & Filtros "); self.nb.add(self.tab_ia,text=" 3. IA & Conexões "); self.nb.add(self.tab_exec,text=" 4. Execução "); self.nb.add(self.tab_dash,text=" 5. Dashboard "); self.nb.add(self.tab_hist,text=" 6. Histórico ")
        self._build_perfil(); self._build_busca(); self._build_ia(); self._build_exec(); self._build_dash(); self._build_hist()
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
    def del_exp(self): sel=self.lst_exp.curselection(); 
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
    def del_edu(self): sel=self.lst_edu.curselection(); 
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

    # Busca avançada
    def _build_busca(self):
        f=self.tab_busca
        # scroll
        canvas=tk.Canvas(f,bg="#222222",highlightthickness=0); sb=tb.Scrollbar(f,orient=VERTICAL,command=canvas.yview); canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT,fill=Y); canvas.pack(side=LEFT,fill=BOTH,expand=True)
        inner=tb.Frame(canvas); canvas.create_window((0,0),window=inner,anchor="nw")
        inner.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        card=tb.Labelframe(inner,text="Palavras-chave (vírgula)",padding=10,bootstyle="primary"); card.pack(fill=X,pady=5)
        tb.Entry(card,textvariable=self.var_keywords).pack(fill=X)
        tb.Label(card,text="Ex: Desenvolvedor Python, Backend, Django, FastAPI, AWS",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W,pady=(4,0))
        grid=tb.Frame(inner); grid.pack(fill=X,pady=5)
        grid.columnconfigure(1,weight=1); grid.columnconfigure(3,weight=1)
        tb.Label(grid,text="Regime").grid(row=0,column=0,sticky=W,padx=5,pady=4); cb=tb.Combobox(grid,textvariable=self.var_work_mode,values=["remoto","presencial","hibrido","indiferente"],state="readonly",width=16); cb.grid(row=0,column=1,sticky=W,padx=5,pady=4); cb.bind("<<ComboboxSelected>>",lambda e:self._bind_work_mode())
        tb.Label(grid,text="Contrato").grid(row=0,column=2,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_contract,values=["clt","pj","indiferente"],state="readonly",width=16).grid(row=0,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Nível").grid(row=1,column=0,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_level,values=["indiferente","estagio","junior","pleno","senior"],state="readonly",width=16).grid(row=1,column=1,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Inglês").grid(row=1,column=2,sticky=W,padx=5,pady=4); tb.Combobox(grid,textvariable=self.var_english,values=["indiferente","sim","nao"],state="readonly",width=16).grid(row=1,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Salário mínimo (R$)").grid(row=2,column=0,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=0,to=50000,textvariable=self.var_min_salary,width=16, increment=500).grid(row=2,column=1,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Idade max vaga (dias, 0=ignorar)").grid(row=2,column=2,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=0,to=60,textvariable=self.var_max_age,width=16).grid(row=2,column=3,sticky=W,padx=5,pady=4)
        tb.Label(grid,text="Limite diário envios").grid(row=3,column=0,sticky=W,padx=5,pady=4); tb.Spinbox(grid,from_=1,to=100,textvariable=self.var_daily_limit,width=16).grid(row=3,column=1,sticky=W,padx=5,pady=4)
        tb.Checkbutton(grid,text="Apenas vagas PCD",variable=self.var_only_pcd,bootstyle="round-toggle").grid(row=3,column=2,sticky=W,padx=5,pady=4)
        self.frame_presencial=tb.Labelframe(inner,text="Localização Presencial / Híbrido",padding=10,bootstyle="warning"); self.frame_presencial.pack(fill=X,pady=5)
        tb.Label(self.frame_presencial,text="Cidade/Estado ex: São Paulo, SP").pack(anchor=W); tb.Entry(self.frame_presencial,textvariable=self.var_presencial_loc).pack(fill=X,pady=4)
        card2=tb.Labelframe(inner,text="Palavras-chave avançadas",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        tb.Label(card2,text="Excluir vagas que contenham (vírgula)").pack(anchor=W); tb.Entry(card2,textvariable=self.var_exclude).pack(fill=X,pady=2)
        tb.Label(card2,text="Palavras obrigatórias (pelo menos uma, vírgula)").pack(anchor=W,pady=(6,0)); tb.Entry(card2,textvariable=self.var_mandatory).pack(fill=X,pady=2)
        tb.Label(card2,text="Empresas bloqueadas (vírgula)").pack(anchor=W,pady=(6,0)); tb.Entry(card2,textvariable=self.var_blocked).pack(fill=X,pady=2)
        tb.Label(card2,text="Empresas favoritas (destaca no relatório, vírgula)").pack(anchor=W,pady=(6,0)); tb.Entry(card2,textvariable=self.var_fav).pack(fill=X,pady=2)
        card3=tb.Labelframe(inner,text="Parâmetros ATS",padding=10,bootstyle="success"); card3.pack(fill=X,pady=5)
        row=tb.Frame(card3); row.pack(fill=X)
        tb.Label(row,text="Score mínimo %").pack(side=LEFT,padx=5); tb.Scale(row,from_=0,to=100,variable=self.var_min_score,length=200,bootstyle="success").pack(side=LEFT,padx=5); tb.Label(row,textvariable=self.var_min_score,width=4).pack(side=LEFT)
        tb.Label(row,text="Vagas/fonte").pack(side=LEFT,padx=(20,5)); tb.Spinbox(row,from_=1,to=30,textvariable=self.var_limit,width=6).pack(side=LEFT)
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
        card=tb.Labelframe(f,text="Provedor IA (gratuito)",padding=10,bootstyle="success"); card.pack(fill=X,pady=5)
        row=tb.Frame(card); row.pack(fill=X)
        tb.Label(row,text="Provedor").pack(side=LEFT,padx=5); tb.Combobox(row,textvariable=self.var_llm_provider,values=["gemini","ollama"],state="readonly",width=12).pack(side=LEFT,padx=5)
        tb.Label(row,text="Gemini Key").pack(side=LEFT,padx=(15,5)); ent=tb.Entry(row,textvariable=self.var_gemini_key,show="*",width=38); ent.pack(side=LEFT,padx=5,fill=X,expand=True)
        def toggle(): ent.config(show="" if ent.cget("show")=="*" else "*"); btn.config(text="Ocultar" if ent.cget("show")=="" else "Mostrar")
        btn=tb.Button(row,text="Mostrar",bootstyle="secondary-outline",command=toggle,width=8); btn.pack(side=LEFT,padx=5)
        tb.Button(row,text="Testar",bootstyle="success-outline",command=self.test_gemini).pack(side=LEFT,padx=5)
        tb.Label(card,text="https://aistudio.google.com/app/apikey — deixe em branco para Ollama ou heurístico",font=("Segoe UI",8),bootstyle="secondary").pack(anchor=W,pady=(6,0))
        row2=tb.Frame(card); row2.pack(fill=X,pady=6)
        tb.Label(row2,text="Ollama Host").pack(side=LEFT,padx=5); tb.Entry(row2,textvariable=self.var_ollama_host,width=28).pack(side=LEFT,padx=5)
        tb.Label(row2,text="Modelo").pack(side=LEFT,padx=5); tb.Entry(row2,textvariable=self.var_ollama_model,width=18).pack(side=LEFT,padx=5)
        card2=tb.Labelframe(f,text="SMTP (opcional)",padding=10,bootstyle="info"); card2.pack(fill=X,pady=5)
        g=tb.Frame(card2); g.pack(fill=X); g.columnconfigure(1,weight=1); g.columnconfigure(3,weight=1)
        tb.Label(g,text="Host").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_host).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Porta").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_port,width=8).grid(row=0,column=3,sticky=W,padx=5,pady=3)
        tb.Label(g,text="Usuário").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_user).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="App Pass").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)
        card3=tb.Labelframe(f,text="LinkedIn / Gupy (Playwright opcional)",padding=10,bootstyle="warning"); card3.pack(fill=X,pady=5)
        g2=tb.Frame(card3); g2.pack(fill=X); g2.columnconfigure(1,weight=1); g2.columnconfigure(3,weight=1)
        tb.Label(g2,text="LinkedIn Email").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_email).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_linkedin_pass,show="*").grid(row=0,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Gupy Email").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_email).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g2,text="Senha").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g2,textvariable=self.var_gupy_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)
    def test_gemini(self):
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
        tb.Button(row,text="Limpar log",bootstyle="secondary-outline",command=lambda:self.log.text.delete("1.0",tk.END)).pack(side=RIGHT)
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
    def stop_automation(self): self.stop_requested=True; 
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

    # Save/export
    def save_all(self,silent=False):
        self.curriculum["personal_info"]={"name":self.var_name.get().strip(),"email":self.var_email.get().strip(),"phone":self.var_phone.get().strip(),"location":self.var_location.get().strip(),"linkedin":self.var_linkedin.get().strip(),"github":self.var_github.get().strip()}
        self.curriculum["summary"]=self.txt_summary.get("1.0","end").strip(); save_curriculum(self.curriculum)
        self.env.update(GEMINI_API_KEY=self.var_gemini_key.get().strip(),LLM_PROVIDER=self.var_llm_provider.get().strip().lower(),OLLAMA_HOST=self.var_ollama_host.get().strip(),OLLAMA_MODEL=self.var_ollama_model.get().strip(),SMTP_HOST=self.var_smtp_host.get().strip(),SMTP_PORT=self.var_smtp_port.get().strip(),SMTP_USER=self.var_smtp_user.get().strip(),SMTP_PASS=self.var_smtp_pass.get().strip(),LINKEDIN_EMAIL=self.var_linkedin_email.get().strip(),LINKEDIN_PASSWORD=self.var_linkedin_pass.get().strip(),GUPY_EMAIL=self.var_gupy_email.get().strip(),GUPY_PASSWORD=self.var_gupy_pass.get().strip(),WORK_MODE=self.var_work_mode.get().strip(),PRESENCIAL_LOCATION=self.var_presencial_loc.get().strip(),CONTRACT_TYPE=self.var_contract.get().strip(),TELEGRAM_BOT_TOKEN=self.var_telegram_token.get().strip(),TELEGRAM_CHAT_ID=self.var_telegram_chat.get().strip(),DAILY_LIMIT=str(int(self.var_daily_limit.get())))
        save_env_dict(self.env)
        cfg={"keywords":[k.strip() for k in self.var_keywords.get().split(",") if k.strip()],"work_mode":self.var_work_mode.get(),"presencial_location":self.var_presencial_loc.get().strip(),"contract_type":self.var_contract.get(),"min_score":int(self.var_min_score.get()),"limit_per_source":int(self.var_limit.get()),"min_salary":int(self.var_min_salary.get()),"level":self.var_level.get(),"exclude_keywords":[k.strip() for k in self.var_exclude.get().split(",") if k.strip()],"mandatory_words":[k.strip() for k in self.var_mandatory.get().split(",") if k.strip()],"blocked_companies":[k.strip() for k in self.var_blocked.get().split(",") if k.strip()],"favorite_companies":[k.strip() for k in self.var_fav.get().split(",") if k.strip()],"max_age_days":int(self.var_max_age.get()),"only_pcd":bool(self.var_only_pcd.get()),"english_filter":self.var_english.get(),"daily_limit":int(self.var_daily_limit.get()),"telegram_bot_token":self.var_telegram_token.get().strip(),"telegram_chat_id":self.var_telegram_chat.get().strip(),"schedule_enabled":bool(self.var_schedule_enabled.get()),"schedule_hour":self.var_schedule_hour.get().strip()}
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
