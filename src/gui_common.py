"""Estado e utilitarios compartilhados entre a janela principal (App) e as abas
(src/gui_tabs/*) — extraido de gui.py para as abas poderem importar sem depender de volta
do modulo gui (evita import circular entre gui.py e gui_tabs/*.py)."""
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from config import Config

OUTCOME_OPTIONS = ["sem_resposta", "visualizado", "entrevista", "teste_tecnico", "proposta", "rejeitado", "contratado"]

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

# BASE_DIR vem de Config (mesma detecção de .exe/_MEIPASS usada no resto do projeto) — antes a
# GUI calculava seu próprio BASE_DIR sem essa lógica e ficava com caminhos errados (apontando
# para a pasta temporária de extração) quando rodando como .exe congelado.
BASE_DIR = Config.BASE_DIR
CURRICULUM_PATH = Config.CURRICULUM_PATH
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
SEARCH_CONFIG_PATH = Config.SEARCH_CONFIG_PATH
DB_PATH = Config.DB_PATH

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
    return {"keywords":["Desenvolvedor Python","Python Developer"],"work_mode":"remoto","presencial_location":"","contract_type":"indiferente","min_score":60,"limit_per_source":8,"min_salary":0,"level":"indiferente","exclude_keywords":[],"mandatory_words":[],"blocked_companies":[],"max_age_days":0,"only_pcd":False,"english_filter":"indiferente","daily_limit":20,"enable_linkedin_posts":True,"linkedin_posts_limit":8,"auto_send":True}
def save_search_config(c): SEARCH_CONFIG_PATH.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding="utf-8")
