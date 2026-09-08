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

class BuscaTabMixin:
    """Aba 2 - Busca & Filtros: palavras-chave, filtros avancados, agendamento, Telegram."""
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
        row_send=tb.Frame(card3); row_send.pack(fill=X,pady=(6,0))
        tb.Checkbutton(row_send,text="Enviar automaticamente quando o match atingir o score mínimo",variable=self.var_auto_send,bootstyle="round-toggle").pack(side=LEFT,padx=5)
        info_icon(row_send, "Desative para revisar antes de enviar: vagas com match suficiente ficam com status 'ready_to_send'\n(PDF + carta já prontos) na aba Histórico, e você aprova o envio manualmente no botão\n'Aprovar e Enviar'. Recomendado se não quiser confiar 100% na IA em candidaturas reais.").pack(side=LEFT)
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
