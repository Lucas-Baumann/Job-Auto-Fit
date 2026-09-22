import json, os, sys, threading, subprocess, webbrowser
from pathlib import Path
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

class BuscaTabMixin:
    """Aba 2 - Busca & Filtros: palavras-chave, filtros avancados, posts de recrutador."""
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
        tb.Label(card,text="Ex: Desenvolvedor Python, Backend, Django, FastAPI, AWS",font=("Segoe UI",8),bootstyle="light").pack(anchor=W,pady=(4,0))
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
        info_icon(grid, "Máximo de CANDIDATURAS ENVIADAS de verdade por dia (automático ou aprovado manualmente no Histórico) — não limita quantas vagas são buscadas/pontuadas, só o disparo real de Playwright/SMTP.\n>30 = alto risco de softban no LinkedIn (erro 999/429, IP bloqueado 15min-24h).\nRecomendado: 15-20.").grid(row=3,column=0,sticky=E,padx=(120,0))
        tb.Checkbutton(grid,text="Apenas vagas PCD",variable=self.var_only_pcd,bootstyle="round-toggle").grid(row=3,column=2,sticky=W,padx=5,pady=4)
        info_icon(grid, "Só passa vaga com 'PCD'/'pessoa com deficiência' no texto").grid(row=3,column=2,sticky=E,padx=(130,0))
        # aviso dinâmico de ban — sempre visível quando em risco
        self.lbl_ban_warning=tb.Label(inner, text="", font=("Segoe UI", 8, "bold"), bootstyle="danger", wraplength=900, justify=LEFT)
        self.lbl_ban_warning.pack(fill=X, pady=(2,4))
        # LinkedIn posts de recrutadores — perto do aviso de risco de ban, já que é a fonte
        # que mais precisa de atenção ao limite (login + Playwright, mais request por vaga)
        card_posts=tb.Labelframe(inner,text="LinkedIn — Posts de Recrutadores (nova fonte)",padding=10,bootstyle="warning"); card_posts.pack(fill=X,pady=5)
        row_posts=tb.Frame(card_posts); row_posts.pack(fill=X)
        tb.Checkbutton(row_posts,text="Buscar também posts de recrutadores no LinkedIn",variable=self.var_enable_linkedin_posts,bootstyle="round-toggle").pack(side=LEFT,padx=5)
        info_icon(row_posts, "Ativa coleta em posts/feed de recrutadores no LinkedIn (ex: 'Estamos contratando').\nFiltra por sinais de recrutador (Recruiter/RH/Talent) + keywords de vaga.\nSem login usa scraping guest (frágil, pode pegar poucos). Com login + Playwright é mais confiável.\nMonta busca booleana: Python Developer → (\"vaga\" OR \"contratando\" OR \"hiring\" OR ...) AND \"Python Developer\"").pack(side=LEFT)
        row_posts2=tb.Frame(card_posts); row_posts2.pack(fill=X,pady=4)
        tb.Label(row_posts2,text="Limite posts/keyword").pack(side=LEFT,padx=5); tb.Spinbox(row_posts2,from_=1,to=20,textvariable=self.var_linkedin_posts_limit,width=6).pack(side=LEFT,padx=5)
        info_icon(row_posts2, "Limite de posts por keyword.\n>10 sem login (guest) = falha/authwall garantida. Com login + Playwright suporta 10-15.\nCada post = 1 request + 1 detalhe, respeita daily_limit.").pack(side=LEFT)
        tb.Label(row_posts2,text="Requer PLAYWRIGHT + login para melhor taxa. Delay + daily_limit evitam softban.",font=("Segoe UI",8),bootstyle="light").pack(side=LEFT,padx=10)
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
        card3=tb.Labelframe(inner,text="Parâmetros ATS",padding=10,bootstyle="success"); card3.pack(fill=X,pady=5)
        row=tb.Frame(card3); row.pack(fill=X)
        tb.Label(row,text="Score mínimo %").pack(side=LEFT,padx=5); tb.Scale(row,from_=0,to=100,variable=self.var_min_score,length=200,bootstyle="success").pack(side=LEFT,padx=5); tb.Label(row,textvariable=self.var_min_score,width=4).pack(side=LEFT)
        tb.Label(row,text="Vagas/fonte").pack(side=LEFT,padx=(20,5)); tb.Spinbox(row,from_=1,to=30,textvariable=self.var_limit,width=6).pack(side=LEFT)
        info_icon(row, "Vagas por fonte (Gupy/LinkedIn/Remotive).\n>12 por fonte = risco de 429/softban. Recomendado: 8-10.\nO LinkedIn Jobs Guest bloqueia com muitas req/seg.").pack(side=LEFT)
        row_send=tb.Frame(card3); row_send.pack(fill=X,pady=(6,0))
        tb.Checkbutton(row_send,text="Enviar automaticamente quando o match atingir o score mínimo",variable=self.var_auto_send,bootstyle="round-toggle").pack(side=LEFT,padx=5)
        info_icon(row_send, "Desative para revisar antes de enviar: vagas com match suficiente ficam com status 'ready_to_send'\n(PDF + carta já prontos) na aba Histórico, e você aprova o envio manualmente no botão\n'Aprovar e Enviar'. Recomendado se não quiser confiar 100% na IA em candidaturas reais.").pack(side=LEFT)
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
            self.lbl_ban_warning.config(text="⚠ " + " | ".join(msgs), bootstyle="danger")
        else:
            self.lbl_ban_warning.config(text="✓ Limites seguros — ritmo humano, baixo risco de ban", bootstyle="success")
    def _bind_work_mode(self):
        mode=self.var_work_mode.get()
        if mode in ("presencial","hibrido"): self.frame_presencial.pack(fill=X,pady=5)
        else: self.frame_presencial.pack_forget()

    # IA
