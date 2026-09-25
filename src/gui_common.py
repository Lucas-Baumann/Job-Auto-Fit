"""Estado e utilitarios compartilhados entre a janela principal (App) e as abas
(src/gui_tabs/*) — extraido de gui.py para as abas poderem importar sem depender de volta
do modulo gui (evita import circular entre gui.py e gui_tabs/*.py)."""
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import customtkinter as ctk

from config import Config
from theme import get_active_theme

OUTCOME_OPTIONS = ["sem_resposta", "visualizado", "entrevista", "teste_tecnico", "proposta", "rejeitado", "contratado"]

class Tooltip:
    """Tooltip simples ao passar mouse em ícone ⓘ — cores seguem o tema ativo (ver theme.py)
    em vez de fixas, pra não destoar dos cards novos (CustomTkinter) de cada aba."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
    def show(self, _):
        if self.tip: return
        t = get_active_theme()
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + 18
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tip, text=self.text, bg=t["card_bg"], fg=t["text"], relief=SOLID, borderwidth=1,
                       highlightbackground=t["border"], font=("Segoe UI", 8), wraplength=300, justify=LEFT, padx=8, pady=6)
        lbl.pack()
    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None

def info_icon(parent, tooltip_text):
    """Ícone ⓘ com tooltip - usa CTkLabel pra herdar o fundo transparente do card novo
    (CustomTkinter) em vez do fundo do tema ttkbootstrap antigo, que já não bate mais com
    as cores de theme.py."""
    t = get_active_theme()
    lbl = ctk.CTkLabel(parent, text=" ⓘ", font=ctk.CTkFont(size=12, weight="bold"), text_color=t["primary"], cursor="hand2")
    Tooltip(lbl, tooltip_text)
    return lbl

def card(parent, title, theme=None):
    """Container com canto arredondado + título em negrito no topo, substitui o antigo
    tb.Labelframe (borda fina colorida) - ver blueprint_vamp_hunter.md secao 3.B.
    Retorna (frame_externo, frame_conteudo); os widgets do chamador vao dentro do conteudo,
    o titulo ja fica fora reservado.

    bg_color explícito (window_bg, não deixado no default do CustomTkinter): com canto
    arredondado (corner_radius>0) + borda (border_width>0) juntos, o CTkFrame usa bg_color -
    não fg_color - como referência de cor pra suavizar/mascarar os cantos e a borda contra o
    que tem por trás. Sem passar isso, ricocheteava até um cinza-escuro fixo do ttkbootstrap
    antigo (não lia theme.py) e sobrava uma linha escura fina em volta do card - só não
    aparecia nos temas escuros por coincidência de tom com esse cinza."""
    t = theme or get_active_theme()
    outer = ctk.CTkFrame(parent, fg_color=t["card_bg"], corner_radius=10, border_width=1,
                          border_color=t["border"], bg_color=t["window_bg"])
    if title:
        ctk.CTkLabel(outer, text=title, text_color=t["text"], anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=14, pady=(12,2))
    content = ctk.CTkFrame(outer, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=14, pady=(0,14))
    return outer, content

def field(parent, label_text, build_widget, theme=None, tooltip=None):
    """Bloco rótulo-acima-do-campo (blueprint secao 3.A): label em cima, widget embaixo,
    dentro do mesmo frame transparente - facilita empilhar (pack) ou distribuir em grade
    (grid) esses blocos sem repetir o padrao em cada aba. tooltip opcional -> ícone ⓘ ao
    lado do rótulo (mesmo texto explicativo que os info_icon() soltos usavam antes)."""
    t = theme or get_active_theme()
    wrap = ctk.CTkFrame(parent, fg_color="transparent")
    hdr = ctk.CTkFrame(wrap, fg_color="transparent")
    hdr.pack(anchor="w", pady=(0,3), fill="x")
    ctk.CTkLabel(hdr, text=label_text, text_color=t["text_dim"], anchor="w",
                 font=ctk.CTkFont(size=11)).pack(side="left")
    if tooltip:
        info_icon(hdr, tooltip).pack(side="left")
    widget = build_widget(wrap)
    widget.pack(fill="x")
    return wrap, widget

class CTkSpinbox(ctk.CTkFrame):
    """CustomTkinter nao tem Spinbox nativo - reproduz o essencial (entry numerica + -/+)
    o suficiente pros campos desta aplicacao (limites, idade max, score minimo etc). Aceita
    a mesma tk.IntVar/DoubleVar que o codigo ja usava com tb.Spinbox, sem precisar trocar
    o resto da logica que le/escreve essas variaveis."""
    def __init__(self, parent, from_=0, to=100, textvariable=None, increment=1, width=90, theme=None, **kw):
        t = theme or get_active_theme()
        super().__init__(parent, fg_color="transparent", **kw)
        self.from_, self.to, self.increment = from_, to, increment
        self.var = textvariable if textvariable is not None else tk.IntVar(value=from_)
        btn_kw = dict(width=26, height=28, fg_color=t["card_bg"], text_color=t["text"],
                      hover_color=t["border"], border_width=1, border_color=t["border"], corner_radius=6)
        ctk.CTkButton(self, text="−", command=self._dec, **btn_kw).pack(side="left")
        self.entry = ctk.CTkEntry(self, textvariable=self.var, width=width-56, justify="center")
        self.entry.pack(side="left", padx=4)
        ctk.CTkButton(self, text="+", command=self._inc, **btn_kw).pack(side="left")
    def _step(self, delta):
        try: v = float(self.var.get())
        except (ValueError, tk.TclError): v = self.from_
        v = max(self.from_, min(self.to, v + delta))
        self.var.set(int(v) if float(v).is_integer() else v)
    def _dec(self): self._step(-self.increment)
    def _inc(self): self._step(self.increment)

_ttk_styled = False
def style_ttk(theme=None):
    """Configura os estilos ttk (Treeview/Progressbar) pra combinar com o tema ativo
    (theme.py) - usado pelas abas que ainda dependem de widgets ttk puros porque o
    CustomTkinter não tem equivalente nativo (Treeview: Histórico/Perfil GitHub;
    Progressbar indeterminate: Execução). Idempotente - só recalcula se chamado nas
    trocas de tema (hoje só CLEAN_TECH está ativo, ver blueprint_vamp_hunter.md fase 5)."""
    from tkinter import ttk
    t = theme or get_active_theme()
    style = ttk.Style()
    style.theme_use(style.theme_use())  # garante engine 'clam'/tema base já carregado
    style.configure("Vamp.Treeview", background=t["card_bg"], fieldbackground=t["card_bg"],
                     foreground=t["text"], bordercolor=t["border"], borderwidth=0, rowheight=26)
    style.configure("Vamp.Treeview.Heading", background=t["window_bg"], foreground=t["text_dim"],
                     relief="flat", borderwidth=1)
    style.map("Vamp.Treeview", background=[("selected", t["primary"])], foreground=[("selected", "#ffffff")])
    style.map("Vamp.Treeview.Heading", background=[("active", t["border"])])
    style.configure("Vamp.Horizontal.TProgressbar", background=t["primary"], troughcolor=t["card_bg"],
                     bordercolor=t["border"], lightcolor=t["primary"], darkcolor=t["primary"])
    style.configure("Vamp.TFrame", background=t["window_bg"])
    # bordercolor/darkcolor/lightcolor: sem isso, a linha que separa as abas e a moldura ao
    # redor do conteúdo do Notebook ficam presas no cinza fixo do ttkbootstrap antigo
    # (#454545), a mesma classe de bug já corrigida em outros lugares - aqui é estilo ttk
    # puro (engine 'clam'), não CustomTkinter, mas a causa é a mesma ideia: cor que nunca foi
    # conectada ao tema ativo.
    style.configure("Vamp.TNotebook", background=t["window_bg"], borderwidth=1,
                     bordercolor=t["border"], darkcolor=t["border"], lightcolor=t["border"])
    style.configure("Vamp.TNotebook.Tab", background=t["card_bg"], foreground=t["text_dim"],
                     padding=(14,8), borderwidth=1, bordercolor=t["border"],
                     darkcolor=t["border"], lightcolor=t["border"], focuscolor=t["window_bg"])
    style.map("Vamp.TNotebook.Tab", background=[("selected", t["primary"])],
              foreground=[("selected", "#ffffff")],
              bordercolor=[("selected", t["primary"])])
    return t

def make_scrollable(parent, fg_color=None, theme=None):
    """CTkScrollableFrame com scroll do mouse mais robusto. O binding embutido do
    CustomTkinter divide o delta do evento por 6 (`-int(event.delta/6)`) - num mouse comum
    (delta=±120) isso dá 1 unidade tranquilo, mas touchpads precision do Windows mandam
    deltas bem menores por evento (scroll suave), que às vezes zeram nessa divisão e dão a
    impressão de 'o scroll não funciona'. Aqui a rolagem usa um passo fixo (só olha o sinal
    do delta, não a magnitude), então qualquer evento sempre move visivelmente. Reaproveita
    o _check_if_valid_scroll() nativo do CTkScrollableFrame pra só rolar quando o widget sob
    o mouse pertence de fato a este frame (necessário já que várias abas têm cada uma o seu).

    fg_color/bg_color explícitos (não "transparent"): um widget filho com fg_color=
    "transparent" empacotado direto neste frame (sem passar por um card()) tenta detectar
    sozinho a cor de fundo herdada subindo a árvore de widgets - e como o canvas interno do
    CTkScrollableFrame também não tem uma cor "própria" quando fica transparent, a detecção
    ricocheteia até o tema antigo do ttkbootstrap (raiz da janela) e pega um cinza-escuro fixo
    (#222222, sempre o mesmo não importa o tema.py ativo). Passava despercebido nos temas
    escuros (coincidência de tom com o cinza do ttkbootstrap), mas sobrava como uma faixa
    escura atrás de qualquer label solto (fora de card) no tema Daylight (claro). Dar uma cor
    sólida de verdade aqui (em vez de "transparent") corta esse ricochete pela raiz."""
    t = theme or get_active_theme()
    sf = ctk.CTkScrollableFrame(parent, fg_color=fg_color or t["window_bg"], bg_color=t["window_bg"])
    canvas = sf._parent_canvas
    def _on_wheel(event):
        if not sf._check_if_valid_scroll(event.widget): return
        num = getattr(event, "num", None)
        if num in (4,5):
            step = -3 if num == 4 else 3
        else:
            step = -3 if getattr(event, "delta", 0) > 0 else 3
        canvas.yview_scroll(step, "units")
    canvas.bind_all("<MouseWheel>", _on_wheel, add="+")
    canvas.bind_all("<Button-4>", _on_wheel, add="+")
    canvas.bind_all("<Button-5>", _on_wheel, add="+")
    return sf

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
