import json, os, sys, threading, subprocess, webbrowser, re, time
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import customtkinter as ctk

from config import Config, resource_path
from theme import get_active_theme, is_vampire_mode, toggle_vampire_mode, label_for
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, style_ttk,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

# Bump global de 12% no tamanho de widgets/fonte do CustomTkinter (afeta entry/combobox/
# botão/label igual, dimensão e fonte juntas) - texto dos campos ficava pequeno/pouco
# legível no tamanho padrão. Precisa rodar antes de qualquer widget CTk ser criado.
ctk.set_widget_scaling(1.12)
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
        self.title("VampHunter — Automação Completa (Gupy / LinkedIn / ATS)")
        # icone do .exe (Explorer/Propriedades) é o documento com presas (icon.ico, ver
        # VampHunter.spec) - mas o icone da JANELA em execução (barra de tarefas + canto da
        # barra de título) é o morcego, um ícone separado só pra isso, mais simples e legível
        # em tamanho pequeno.
        try:
            # default= (não só o bitmap posicional) propaga o ícone pras janelas
            # "implícitas" tipo messagebox.showinfo/askyesno - sem isso, elas ficam com a
            # penazinha padrão do Tk mesmo com a janela principal certa.
            self.iconbitmap(default=str(resource_path("icon_taskbar.ico")))
        except Exception:
            pass
        self.minsize(1200,750)
        # centraliza na tela - antes sempre abria no canto superior esquerdo (posição
        # default do SO), independente do tamanho/resolução do monitor.
        _w,_h=1280,820
        self.update_idletasks()
        _x=(self.winfo_screenwidth()-_w)//2; _y=(self.winfo_screenheight()-_h)//2
        self.geometry(f"{_w}x{_h}+{max(0,_x)}+{max(0,_y)}")
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
        self.var_max_age=tk.IntVar(value=self.search_cfg.get("max_age_days",0))
        self.var_only_pcd=tk.BooleanVar(value=self.search_cfg.get("only_pcd",False))
        self.var_english=tk.StringVar(value=self.search_cfg.get("english_filter","indiferente"))
        self.var_daily_limit=tk.IntVar(value=self.search_cfg.get("daily_limit",20))
        self.var_auto_send=tk.BooleanVar(value=self.search_cfg.get("auto_send",True))
        self.var_enable_linkedin_posts=tk.BooleanVar(value=self.search_cfg.get("enable_linkedin_posts",True))
        self.var_linkedin_posts_limit=tk.IntVar(value=self.search_cfg.get("linkedin_posts_limit", self.search_cfg.get("limit_per_source",8)))
        _gh_url=self.curriculum.get("personal_info",{}).get("github","")
        self.var_profile_user=tk.StringVar(value=_gh_url.rstrip("/").split("/")[-1].strip() if _gh_url else "")
        self.var_profile_use_llm=tk.BooleanVar(value=True)
        self.var_github_token=tk.StringVar(value=self.env.get("GITHUB_TOKEN",""))
        self.var_dry_run=tk.BooleanVar(value=True)
        self._build_ui(); self._bind_work_mode(); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list(); self._refresh_dashboard()
        self.after(300, self._maybe_show_onboarding)
        # Fase 5 do blueprint (Modo Vampiro) - "Despertar Noturno": abrir o app entre 00h e
        # 03h ativa o tema vampiro sozinho, com um banner avisando (o outro gatilho é o
        # tríplo-clique no morcego escondido no rodapé, ver _on_bat_click).
        if datetime.now().hour < 3:
            self.after(400, lambda: self._activate_vampire_mode("🦇 Despertar Noturno — Modo Vampiro ativado automaticamente (00h–03h)"))
        # sem isso, fechar no X perdia edição não salva sem avisar, e se a automação
        # estivesse rodando em background (thread + Playwright/subprocess), fechar a janela
        # matava o processo Python no meio de uma vaga sem chance de interromper com cuidado.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            running = str(self.btn_stop.cget("state")) == "normal"
        except Exception:
            running = False
        if running:
            if not messagebox.askyesno("Automação em execução", "A automação ainda está rodando. Fechar agora interrompe o processo no meio da vaga atual.\nContinuar mesmo assim?"):
                return
            try: self.stop_automation()
            except Exception: pass
        resp = messagebox.askyesnocancel("Fechar VampHunter", "Salvar alterações antes de sair?")
        if resp is None:
            return
        if resp:
            try: self.save_all(silent=True)
            except Exception: pass
        self.destroy()

    def _maybe_show_onboarding(self):
        # primeira execução (currículo em branco, sem nome nem experiência) — evita a pessoa
        # achar que o app "travou" ou "não importou nada" olhando os campos vazios sem contexto
        pi = self.curriculum.get("personal_info",{})
        if pi.get("name") or self.curriculum.get("experiences"):
            return
        messagebox.showinfo(
            "Bem-vindo ao VampHunter",
            "Primeira execução — nenhum currículo carregado ainda.\n\n"
            "Passo a passo sugerido:\n"
            "1) Aba 3 (IA & Conexões) — configure uma chave de IA (Gemini/OpenRouter grátis ou Ollama local). "
            "Sem isso, o import de PDF usa um modo heurístico mais limitado.\n"
            "2) Aba 1 (Currículo) — clique em \"Importar PDF/DOCX/TXT\" para preencher automaticamente.\n"
            "3) Revise os campos preenchidos e clique em \"Salvar Tudo\"."
        )

    def _on_bat_click(self, _event=None):
        """Gatilho manual do Modo Vampiro (blueprint seção 4): 3 cliques no morceguinho
        escondido no rodapé em até 1.2s. Fica de propósito quase invisível (cor = borda do
        tema, bem próxima do fundo) - é um easter egg, não um botão de verdade."""
        now = time.time()
        self._bat_clicks = [c for c in getattr(self, "_bat_clicks", []) if now - c < 1.2] + [now]
        if len(self._bat_clicks) >= 3:
            self._bat_clicks = []
            self._activate_vampire_mode()

    def _activate_vampire_mode(self, banner_text=None):
        toggle_vampire_mode()
        self._rebuild_ui()
        entering = is_vampire_mode()
        self._show_banner(banner_text or ("🦇 Modo Vampiro ativado" if entering else "☀ Modo Vampiro desativado — de volta ao Clean Tech"))

    def _show_banner(self, msg):
        """Faixa temporária no topo da janela (blueprint: 'banner temporário') - usa place()
        por cima de tudo em vez de disputar espaço no grid do resto da UI, e se auto-destrói
        sozinha depois de alguns segundos (ou no clique do X)."""
        t=get_active_theme()
        banner=ctk.CTkFrame(self, fg_color=t["primary"], corner_radius=0, height=34)
        banner.place(relx=0, rely=0, relwidth=1, anchor="nw")
        ctk.CTkLabel(banner, text=msg, text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=14, pady=6)
        ctk.CTkButton(banner, text="✕", width=26, height=22, fg_color="transparent", hover_color=t["border"],
                      text_color="#ffffff", command=banner.destroy).pack(side="right", padx=8)
        self.after(6000, lambda: banner.destroy() if banner.winfo_exists() else None)

    def _rebuild_ui(self):
        """Reconstrói topo/abas/rodapé do zero com o tema (theme.py) atual - a forma mais
        simples e confiável de trocar tema em tempo real, já que cada aba lê a paleta via
        get_active_theme() só na hora de montar os widgets (não observa mudança depois).
        As tk.Variable (self.var_*) não são recriadas, só reaproveitadas - os dados
        digitados na tela sobrevivem à troca de tema."""
        try: current_tab = self.nb.index(self.nb.select())
        except Exception: current_tab = 0
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self._bind_work_mode(); self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list()
        self._refresh_dashboard(); self._refresh_hist()
        try: self.nb.select(current_tab)
        except Exception: pass

    def _build_ui(self):
        t=style_ttk()
        # janela toda (tb.Window/"darkly") fica em cima do fundo escuro do ttkbootstrap, que
        # não é exatamente a cor de theme.py - força o mesmo window_bg pra não ter costura de
        # cor entre o fundo da janela e os cards CustomTkinter por cima. Só na primeira vez:
        # chamar de novo num _rebuild_ui() (troca de tema) esbarra num bug do CustomTkinter -
        # o configure(bg=...) da raiz tenta re-sincronizar todos os widgets CTk já destruídos
        # e quebra com TclError "invalid command name" num deles. Sem necessidade de repetir
        # mesmo: uma vez com a cor certa já é suficiente, o fundo da raiz nunca aparece de
        # verdade (fica 100% coberto pelos frames de cima/notebook/baixo).
        if not getattr(self, "_root_bg_set", False):
            self.configure(bg=t["window_bg"])
            self._root_bg_set = True
        # grid em vez de pack pra topo/notebook/rodapé: com pack, quando a janela era
        # encolhida abaixo da soma das alturas naturais dos 3, o notebook (expand=True)
        # consumia todo o espaço restante e a barra de baixo ("Salvar Tudo" etc, empacotada
        # por último) sumia da tela por falta de espaço. Com grid e peso só na linha do
        # notebook (linha 1), topo e rodapé sempre ficam com a altura mínima garantida -
        # quem encolhe/corta primeiro é o notebook (cujas abas já têm scroll próprio).
        self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)

        top=ctk.CTkFrame(self, fg_color=t["window_bg"]); top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(top,text="VampHunter",font=ctk.CTkFont(size=20,weight="bold"),text_color=t["primary"]).pack(side="left")
        ctk.CTkLabel(top,text="  Coleta • Filtragem Avançada • ATS • Envio • Relatório • Dashboard",
                     font=ctk.CTkFont(size=12),text_color=t["text_dim"]).pack(side="left",padx=10)
        ctk.CTkButton(top,text="Exportar",width=90,fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["card_bg"],command=self.export_config).pack(side="right",padx=(6,0))
        ctk.CTkButton(top,text="Importar",width=90,fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["card_bg"],command=self.import_config).pack(side="right")
        # seletor manual de tema (controle "oficial", complementar ao easter egg do morcego -
        # esse aqui é descoberto, o do rodapé continua escondido de propósito). Trocar aqui
        # também aciona o Modo Vampiro (Crimson Velvet/Gothic Castle contam como vampiro,
        # ver theme.is_vampire_mode) - textos das abas/botões remapeiam igual ao gatilho oculto.
        from theme import THEME_DISPLAY_NAMES, get_active_theme_name, set_active_theme
        def _on_theme_pick(display_name):
            rev={v:k for k,v in THEME_DISPLAY_NAMES.items()}
            set_active_theme(rev.get(display_name,"clean_tech"))
            self._rebuild_ui()
        combo_theme=ctk.CTkComboBox(top,values=list(THEME_DISPLAY_NAMES.values()),state="readonly",
                                     width=140,command=_on_theme_pick)
        combo_theme.set(THEME_DISPLAY_NAMES[get_active_theme_name()])
        combo_theme.pack(side="right",padx=(0,10))

        self.nb=ttk.Notebook(self, style="Vamp.TNotebook"); self.nb.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        self.tab_perfil=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_busca=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_ia=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_exec=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_dash=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_hist=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.tab_profile=ttk.Frame(self.nb, style="Vamp.TFrame", padding=10)
        self.nb.add(self.tab_perfil,text=" 1. Currículo "); self.nb.add(self.tab_busca,text=f" {label_for('tab_busca')} "); self.nb.add(self.tab_ia,text=f" {label_for('tab_ia')} "); self.nb.add(self.tab_exec,text=" 4. Execução "); self.nb.add(self.tab_dash,text=" 5. Dashboard "); self.nb.add(self.tab_hist,text=f" {label_for('tab_hist')} "); self.nb.add(self.tab_profile,text=" 7. Perfil GitHub ")
        self._build_perfil(); self._build_busca(); self._build_ia(); self._build_exec(); self._build_dash(); self._build_hist(); self._build_profile()

        bottom=ctk.CTkFrame(self, fg_color=t["window_bg"]); bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,10))
        ctk.CTkButton(bottom,text=label_for("salvar_tudo"),width=120,fg_color=t["success"],hover_color=t["border"],
                      command=self.save_all).pack(side="left")
        ctk.CTkLabel(bottom,text="Dica: importe PDF/DOCX do currículo na aba Currículo → Importar. Limite diário evita bloqueio no LinkedIn/Gupy.",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"]).pack(side="left",padx=12)
        ctk.CTkButton(bottom,text="Preview PDF",width=110,fg_color=t["primary"],hover_color=t["border"],
                      command=self.preview_pdf).pack(side="right")
        ctk.CTkButton(bottom,text="Abrir Relatórios",width=130,fg_color="transparent",border_width=1,border_color=t["primary"],
                      text_color=t["primary"],hover_color=t["card_bg"],
                      command=lambda:self._open_folder(BASE_DIR/"reports")).pack(side="right",padx=(0,8))
        # morceguinho escondido (blueprint seção 4 - gatilho manual do Modo Vampiro): cor
        # quase igual ao fundo de propósito, só um pouco mais clara pra dar pra encontrar
        # sabendo que existe. 3 cliques em 1.2s ativa/desativa.
        bat=ctk.CTkLabel(bottom, text="🦇", font=ctk.CTkFont(size=11), text_color=t["border"], cursor="hand2")
        bat.pack(side="right", padx=(0,4))
        bat.bind("<Button-1>", self._on_bat_click)

    # Perfil (com import)
    def save_all(self,silent=False):
        self.curriculum["personal_info"]={"name":self.var_name.get().strip(),"email":self.var_email.get().strip(),"phone":self.var_phone.get().strip(),"location":self.var_location.get().strip(),"linkedin":self.var_linkedin.get().strip(),"github":self.var_github.get().strip()}
        self.curriculum["summary"]=self.txt_summary.get("1.0","end").strip(); save_curriculum(self.curriculum)
        self.env.update(GEMINI_API_KEY=self.var_gemini_key.get().strip(),GEMINI_MODEL=self.var_gemini_model.get().strip() or "gemini-flash-latest",LLM_PROVIDER=self.var_llm_provider.get().strip().lower(),OLLAMA_HOST=self.var_ollama_host.get().strip(),OLLAMA_MODEL=self.var_ollama_model.get().strip(),OPENAI_API_KEY=self.var_openai_key.get().strip(),CLAUDE_API_KEY=self.var_claude_key.get().strip(),GROQ_API_KEY=self.var_groq_key.get().strip(),OPENROUTER_API_KEY=self.var_openrouter_key.get().strip(),OPENROUTER_MODEL=self.var_openrouter_model.get().strip(),CUSTOM_LLM_URL=self.var_custom_url.get().strip(),CUSTOM_LLM_KEY=self.var_custom_key.get().strip(),GITHUB_TOKEN=self.var_github_token.get().strip(),SMTP_HOST=self.var_smtp_host.get().strip(),SMTP_PORT=self.var_smtp_port.get().strip(),SMTP_USER=self.var_smtp_user.get().strip(),SMTP_PASS=self.var_smtp_pass.get().strip(),WORK_MODE=self.var_work_mode.get().strip(),PRESENCIAL_LOCATION=self.var_presencial_loc.get().strip(),CONTRACT_TYPE=self.var_contract.get().strip(),DAILY_LIMIT=str(int(self.var_daily_limit.get())))
        save_env_dict(self.env)
        # No .exe, "Executar Automação" roda run_pipeline() no MESMO processo (sem subprocess
        # python.exe separado, que não existe empacotado) — sem isto, Config.LLM_PROVIDER e as
        # chaves ficavam travadas no valor de quando o app abriu até reiniciar, então trocar de
        # provedor/chave na aba IA e rodar sem reiniciar continuava usando o provedor antigo
        # (ex: log mostrando "GEMINI" mesmo com OpenRouter selecionado e salvo).
        os.environ.update(self.env)
        Config.LLM_PROVIDER = self.env.get("LLM_PROVIDER","gemini").lower()
        Config.GEMINI_API_KEY = self.env.get("GEMINI_API_KEY","")
        Config.GEMINI_MODEL = self.env.get("GEMINI_MODEL") or "gemini-flash-latest"
        Config.OLLAMA_HOST = self.env.get("OLLAMA_HOST","http://localhost:11434")
        Config.OLLAMA_MODEL = self.env.get("OLLAMA_MODEL","llama3:latest")
        Config.OPENAI_API_KEY = self.env.get("OPENAI_API_KEY","")
        Config.CLAUDE_API_KEY = self.env.get("CLAUDE_API_KEY","")
        Config.GROQ_API_KEY = self.env.get("GROQ_API_KEY","")
        Config.OPENROUTER_API_KEY = self.env.get("OPENROUTER_API_KEY","")
        Config.OPENROUTER_MODEL = self.env.get("OPENROUTER_MODEL") or "minimax/minimax-m3:free"
        Config.CUSTOM_LLM_URL = self.env.get("CUSTOM_LLM_URL","")
        Config.CUSTOM_LLM_KEY = self.env.get("CUSTOM_LLM_KEY","")
        Config.GITHUB_TOKEN = self.env.get("GITHUB_TOKEN","")
        cfg={"keywords":[k.strip() for k in self.var_keywords.get().split(",") if k.strip()],"work_mode":self.var_work_mode.get(),"presencial_location":self.var_presencial_loc.get().strip(),"contract_type":self.var_contract.get(),"min_score":int(self.var_min_score.get()),"limit_per_source":int(self.var_limit.get()),"min_salary":int(self.var_min_salary.get()),"level":self.var_level.get(),"exclude_keywords":[k.strip() for k in self.var_exclude.get().split(",") if k.strip()],"mandatory_words":[k.strip() for k in self.var_mandatory.get().split(",") if k.strip()],"blocked_companies":[k.strip() for k in self.var_blocked.get().split(",") if k.strip()],"max_age_days":int(self.var_max_age.get()),"only_pcd":bool(self.var_only_pcd.get()),"english_filter":self.var_english.get(),"daily_limit":int(self.var_daily_limit.get()),"enable_linkedin_posts":bool(self.var_enable_linkedin_posts.get()),"linkedin_posts_limit":int(self.var_linkedin_posts_limit.get()),"auto_send":bool(self.var_auto_send.get())}
        save_search_config(cfg); self.search_cfg=cfg
        if not silent: messagebox.showinfo("Salvo","Salvo em curriculum_base.json, .env, search_config.json")
        try: self.log_text.insert(tk.END,"[Save] ok\n"); self.log_text.see(tk.END)
        except: pass
    def export_config(self):
        # antes exportava só 4 chaves fixas do .env (GEMINI_API_KEY/LLM_PROVIDER/TELEGRAM_*) -
        # trocar de PC perdia SMTP, GitHub token e as outras chaves de IA (OpenAI/Claude/Groq/
        # OpenRouter/Custom) sem aviso nenhum. self.save_all() garante que self.env reflita os
        # campos atuais da tela antes de exportar, e exporta o dict inteiro (sem lista fixa
        # que fica desatualizada toda vez que um campo novo é adicionado).
        self.save_all(silent=True)
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile=f"jobautofit_backup_{datetime.now().strftime('%Y%m%d')}.json")
        if not p: return
        data={"curriculum":self.curriculum,"search_config":self.search_cfg,"env":dict(self.env)}
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
                sc=data["search_config"]; self.var_keywords.set(", ".join(sc.get("keywords",[]))); self.var_work_mode.set(sc.get("work_mode","remoto")); self.var_presencial_loc.set(sc.get("presencial_location","")); self.var_contract.set(sc.get("contract_type","indiferente")); self.var_min_score.set(sc.get("min_score",60)); self.var_limit.set(sc.get("limit_per_source",8)); self.var_min_salary.set(sc.get("min_salary",0)); self.var_level.set(sc.get("level","indiferente")); self.var_exclude.set(", ".join(sc.get("exclude_keywords",[]))); self.var_mandatory.set(", ".join(sc.get("mandatory_words",[]))); self.var_blocked.set(", ".join(sc.get("blocked_companies",[]))); self.var_max_age.set(sc.get("max_age_days",0)); self.var_only_pcd.set(sc.get("only_pcd",False)); self.var_english.set(sc.get("english_filter","indiferente")); self.var_daily_limit.set(sc.get("daily_limit",20)); save_search_config(sc)
            if "env" in data:
                # antes o import não lia essa seção de volta em lugar nenhum - nem as 4 chaves
                # que o export antigo salvava. Agora repopula todos os campos de IA/SMTP/GitHub.
                self.env.update(data["env"]); save_env_dict(self.env)
                self.var_gemini_key.set(self.env.get("GEMINI_API_KEY","")); self.var_gemini_model.set(self.env.get("GEMINI_MODEL","gemini-flash-latest"))
                self.var_llm_provider.set(self.env.get("LLM_PROVIDER","gemini"))
                self.var_ollama_host.set(self.env.get("OLLAMA_HOST","http://localhost:11434")); self.var_ollama_model.set(self.env.get("OLLAMA_MODEL","llama3:latest"))
                self.var_openai_key.set(self.env.get("OPENAI_API_KEY","")); self.var_claude_key.set(self.env.get("CLAUDE_API_KEY","")); self.var_groq_key.set(self.env.get("GROQ_API_KEY",""))
                self.var_openrouter_key.set(self.env.get("OPENROUTER_API_KEY","")); self.var_openrouter_model.set(self.env.get("OPENROUTER_MODEL","minimax/minimax-m3:free"))
                self.var_custom_url.set(self.env.get("CUSTOM_LLM_URL","")); self.var_custom_key.set(self.env.get("CUSTOM_LLM_KEY",""))
                self.var_smtp_host.set(self.env.get("SMTP_HOST","smtp.gmail.com")); self.var_smtp_port.set(self.env.get("SMTP_PORT","587")); self.var_smtp_user.set(self.env.get("SMTP_USER","")); self.var_smtp_pass.set(self.env.get("SMTP_PASS",""))
                self.var_github_token.set(self.env.get("GITHUB_TOKEN",""))
            messagebox.showinfo("Importar","Importado com sucesso!")
        except Exception as e: messagebox.showerror("Importar",str(e))


if __name__=="__main__":
    # Rodando 'python src/gui.py' direto (dev): este bloco executa normalmente. No .exe
    # empacotado, quem realmente roda como __main__ é o gui.py da RAIZ do projeto (um
    # lançador de 6 linhas que importa App daqui) — o fechamento da splash screen fica lá,
    # não aqui (descoberto depurando por que a splash não fechava: __name__ deste módulo no
    # build congelado é 'src.gui', nunca '__main__', então qualquer código aqui dentro deste
    # if nunca roda no .exe).
    App().mainloop()
