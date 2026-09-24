import json, os, sys, threading, subprocess, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import Config
from theme import get_active_theme
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, card, field, CTkSpinbox, make_scrollable,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

class BuscaTabMixin:
    """Aba 2 - Busca & Filtros: palavras-chave, filtros avancados, posts de recrutador."""
    def _build_busca(self):
        f=self.tab_busca
        t=get_active_theme()
        inner=make_scrollable(f)
        inner.pack(fill="both", expand=True)

        outer, content = card(inner, "Palavras-chave (vírgula)")
        outer.pack(fill="x", pady=(0,10))
        ctk.CTkEntry(content, textvariable=self.var_keywords).pack(fill="x")
        ctk.CTkLabel(content, text="Ex: Desenvolvedor Python, Backend, Django, FastAPI, AWS",
                     font=ctk.CTkFont(size=10), text_color=t["text_dim"], anchor="w").pack(anchor="w", pady=(4,0))

        outer, grid = card(inner, "Filtros de Busca")
        outer.pack(fill="x", pady=(0,10))
        # 4 colunas (era 2x4) - mesma informação em metade das linhas, ocupando bem menos
        # altura vertical (o card ficava grande demais pro pouco que mostra).
        for c in range(4): grid.columnconfigure(c, weight=1)
        _cb = lambda values, var, cmd=None: (lambda p: ctk.CTkComboBox(
            p, variable=var, values=values, state="readonly", command=(lambda _v: cmd()) if cmd else None))
        w,_=field(grid,"Regime",_cb(["remoto","presencial","hibrido","indiferente"],self.var_work_mode,self._bind_work_mode)); w.grid(row=0,column=0,sticky="ew",padx=(0,8),pady=6)
        w,_=field(grid,"Contrato",_cb(["clt","pj","indiferente"],self.var_contract)); w.grid(row=0,column=1,sticky="ew",padx=(0,8),pady=6)
        w,_=field(grid,"Nível",_cb(["indiferente","estagio","junior","pleno","senior"],self.var_level),
                   tooltip="Filtra por senioridade no título/descrição.\nIndiferente = não filtra"); w.grid(row=0,column=2,sticky="ew",padx=(0,8),pady=6)
        w,_=field(grid,"Inglês",_cb(["indiferente","sim","nao"],self.var_english)); w.grid(row=0,column=3,sticky="ew",pady=6)
        w,_=field(grid,"Salário mínimo (R$)",lambda p: CTkSpinbox(p,from_=0,to=50000,textvariable=self.var_min_salary,increment=500,width=110),
                   tooltip="Extrai R$ do texto da vaga. Se não achar salário, não filtra."); w.grid(row=1,column=0,sticky="ew",padx=(0,8),pady=6)
        w,_=field(grid,"Idade max (dias, 0=ignora)",lambda p: CTkSpinbox(p,from_=0,to=60,textvariable=self.var_max_age,width=110)); w.grid(row=1,column=1,sticky="ew",padx=(0,8),pady=6)
        w,_=field(grid,"Limite diário envios",lambda p: CTkSpinbox(p,from_=1,to=100,textvariable=self.var_daily_limit,width=110),
                   tooltip="Máximo de CANDIDATURAS ENVIADAS de verdade por dia (automático ou aprovado manualmente no Histórico) — não limita quantas vagas são buscadas/pontuadas, só o disparo real de Playwright/SMTP.\n>30 = alto risco de softban no LinkedIn (erro 999/429, IP bloqueado 15min-24h).\nRecomendado: 15-20."); w.grid(row=1,column=2,sticky="ew",padx=(0,8),pady=6)
        pcd_wrap=ctk.CTkFrame(grid, fg_color="transparent"); pcd_wrap.grid(row=1,column=3,sticky="ew",pady=6)
        ctk.CTkCheckBox(pcd_wrap,text="Apenas vagas PCD",variable=self.var_only_pcd).pack(side="left")
        info_icon(pcd_wrap, "Só passa vaga com 'PCD'/'pessoa com deficiência' no texto").pack(side="left")

        # aviso dinâmico de ban — sempre visível quando em risco
        self.lbl_ban_warning=ctk.CTkLabel(inner, text="", font=ctk.CTkFont(size=11, weight="bold"),
                                           wraplength=900, justify="left")
        self.lbl_ban_warning.pack(fill="x", pady=(0,10))

        # LinkedIn posts de recrutadores — perto do aviso de risco de ban, já que é a fonte
        # que mais precisa de atenção ao limite (login + Playwright, mais request por vaga)
        outer, content = card(inner, "LinkedIn — Posts de Recrutadores (nova fonte)")
        outer.pack(fill="x", pady=(0,10))
        row_posts=ctk.CTkFrame(content, fg_color="transparent"); row_posts.pack(fill="x")
        ctk.CTkCheckBox(row_posts,text="Buscar também posts de recrutadores no LinkedIn",variable=self.var_enable_linkedin_posts).pack(side="left")
        info_icon(row_posts, "Ativa coleta em posts/feed de recrutadores no LinkedIn (ex: 'Estamos contratando').\nBusca a keyword da vaga como frase exata (últimos 7 dias) e filtra por sinais de\nrecrutador (Recruiter/RH/Talent) + keywords de contratação no texto de cada post.\nSem login usa scraping guest (frágil, pode pegar poucos). Com login + Playwright é mais confiável.").pack(side="left")
        row_posts2=ctk.CTkFrame(content, fg_color="transparent"); row_posts2.pack(fill="x",pady=(8,0))
        w,_=field(row_posts2,"Limite posts/keyword",lambda p: CTkSpinbox(p,from_=1,to=20,textvariable=self.var_linkedin_posts_limit,width=110),
                   tooltip="Limite de posts por keyword.\n>10 sem login (guest) = falha/authwall garantida. Com login + Playwright suporta 10-15.\nCada post = 1 request + 1 detalhe, respeita daily_limit.")
        w.pack(side="left")
        ctk.CTkLabel(row_posts2,text="Requer PLAYWRIGHT + login para melhor taxa. Delay + daily_limit evitam softban.",
                     font=ctk.CTkFont(size=10), text_color=t["text_dim"]).pack(side="left",padx=10)

        outer, content = card(inner, "Localização Presencial / Híbrido")
        self.frame_presencial=outer
        # empacotado incondicionalmente aqui (igual ao comportamento original em ttkbootstrap):
        # só esconde/mostra reativamente quando o combobox Regime dispara _bind_work_mode,
        # que não roda no build inicial - então some/aparece só depois da 1a troca do usuário.
        outer.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(content,text="Cidade/Estado ex: São Paulo, SP", text_color=t["text_dim"], anchor="w").pack(anchor="w")
        ctk.CTkEntry(content,textvariable=self.var_presencial_loc).pack(fill="x",pady=(4,0))

        outer, content = card(inner, "Palavras-chave avançadas")
        outer.pack(fill="x", pady=(0,10))
        w,_=field(content,"Excluir vagas que contenham (vírgula)",lambda p: ctk.CTkEntry(p,textvariable=self.var_exclude),
                   tooltip="Se título/descrição contiver qualquer termo aqui, vaga é descartada.\nEx: estágio, temporário, banco de talentos")
        w.pack(fill="x")
        w,_=field(content,"Palavras obrigatórias (pelo menos uma, vírgula)",lambda p: ctk.CTkEntry(p,textvariable=self.var_mandatory),
                   tooltip="Vaga só passa se contiver PELO MENOS UMA dessas palavras.\nNÃO é preenchido automaticamente — você define.\nDica: use 'Sugerir do currículo' para preencher com suas skills.")
        w.pack(fill="x",pady=(6,0))
        ctk.CTkButton(content,text="Sugerir do currículo (preenche com suas skills)",fg_color="transparent",
                      border_width=1,border_color=t["primary"],text_color=t["primary"],hover_color=t["card_bg"],
                      command=self.suggest_mandatory).pack(anchor="w",pady=(4,0))
        w,_=field(content,"Empresas bloqueadas (vírgula)",lambda p: ctk.CTkEntry(p,textvariable=self.var_blocked),
                   tooltip="Empresas que você NÃO quer — vagas delas são ignoradas.\nEx: Empresa X, Consultoria Y")
        w.pack(fill="x",pady=(6,0))

        outer, content = card(inner, "Parâmetros ATS")
        outer.pack(fill="x", pady=(0,10))
        row=ctk.CTkFrame(content, fg_color="transparent"); row.pack(fill="x")
        ctk.CTkLabel(row,text="Score mínimo %", text_color=t["text_dim"]).pack(side="left")
        ctk.CTkSlider(row,from_=0,to=100,variable=self.var_min_score,width=200,
                      progress_color=t["success"]).pack(side="left",padx=8)
        ctk.CTkLabel(row,textvariable=self.var_min_score,width=32).pack(side="left")
        w,_=field(row,"Vagas/fonte",lambda p: CTkSpinbox(p,from_=1,to=30,textvariable=self.var_limit,width=110),
                   tooltip="Vagas por fonte (Gupy/LinkedIn/Remotive).\n>12 por fonte = risco de 429/softban. Recomendado: 8-10.\nO LinkedIn Jobs Guest bloqueia com muitas req/seg.")
        w.pack(side="left",padx=(24,0))
        row_send=ctk.CTkFrame(content, fg_color="transparent"); row_send.pack(fill="x",pady=(10,0))
        ctk.CTkCheckBox(row_send,text="Enviar automaticamente quando o match atingir o score mínimo",variable=self.var_auto_send).pack(side="left")
        info_icon(row_send, "Desative para revisar antes de enviar: vagas com match suficiente ficam com status 'ready_to_send'\n(PDF + carta já prontos) na aba Histórico, e você aprova o envio manualmente no botão\n'Aprovar e Enviar'. Recomendado se não quiser confiar 100% na IA em candidaturas reais.").pack(side="left")

        # hooks para aviso de ban dinâmico
        for v in (self.var_limit, self.var_daily_limit, self.var_linkedin_posts_limit):
            try: v.trace_add("write", lambda *_: self._check_ban_risk())
            except: pass
        try: self.var_enable_linkedin_posts.trace_add("write", lambda *_: self._check_ban_risk())
        except: pass
        self.after(500, self._check_ban_risk)
    def _check_ban_risk(self, *_):
        if not hasattr(self, 'lbl_ban_warning'): return
        t=get_active_theme()
        msgs=[]
        try: lim = int(self.var_limit.get())
        except: lim=8
        try: daily = int(self.var_daily_limit.get())
        except: daily=20
        try: posts_lim = int(self.var_linkedin_posts_limit.get())
        except: posts_lim=8
        enable_posts = bool(self.var_enable_linkedin_posts.get()) if hasattr(self, 'var_enable_linkedin_posts') else False
        # var_linkedin_email/var_linkedin_pass não existem mais desde que o login virou sessão
        # de navegador (browser_auth.py) — o hasattr sempre caía em False, então o aviso
        # assumia "sem login" mesmo com sessão ativa salva na aba IA & Conexões.
        try:
            import browser_auth
            has_login = browser_auth.has_session("linkedin")
        except Exception:
            has_login = False
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
            self.lbl_ban_warning.configure(text="⚠ " + " | ".join(msgs), text_color=t["danger"])
        else:
            self.lbl_ban_warning.configure(text="✓ Limites seguros — ritmo humano, baixo risco de ban", text_color=t["success"])
    def _bind_work_mode(self):
        mode=self.var_work_mode.get()
        if mode in ("presencial","hibrido"): self.frame_presencial.pack(fill="x",pady=(0,10))
        else: self.frame_presencial.pack_forget()

    # IA
