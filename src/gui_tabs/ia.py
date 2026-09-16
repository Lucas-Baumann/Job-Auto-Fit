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

class IATabMixin:
    """Aba 3 - IA & Conexoes: provedor de IA, SMTP, GitHub token, LinkedIn/Gupy."""
    def _build_ia(self):
        f=self.tab_ia
        card=tb.Labelframe(f,text="Provedor IA (gratuito ou pago) — campo OPCIONAL",padding=10,bootstyle="success"); card.pack(fill=X,pady=5)
        row_prov=tb.Frame(card); row_prov.pack(fill=X)
        tb.Label(row_prov,text="Provedor").pack(side=LEFT,padx=5); self.combo_llm=tb.Combobox(row_prov,textvariable=self.var_llm_provider,values=["gemini","ollama","openai","claude","groq","openrouter","custom"],state="readonly",width=16); self.combo_llm.pack(side=LEFT,padx=5)
        info_icon(row_prov, "Escolha a IA que reescreve seu currículo/Carta para o ATS.\n• gemini = gratuito (aistudio.google.com)\n• ollama = local gratuito\n• openai/claude/groq = pago\n• openrouter = free tier (openrouter.ai/keys) :free").pack(side=LEFT)
        self.btn_test_gemini=tb.Button(row_prov,text="Testar Conexão",bootstyle="success-outline",command=self.test_gemini); self.btn_test_gemini.pack(side=LEFT,padx=5)
        self.lbl_ai_status=tb.Label(card,text="",font=("Segoe UI",8,"bold")); self.lbl_ai_status.pack(anchor=W,pady=(6,0))
        tb.Label(card,text="Gemini gratuito: aistudio.google.com/app/apikey — deixe em branco para heurístico.",font=("Segoe UI",8),bootstyle="light").pack(anchor=W)
        # container dinâmico — mostra só o provider selecionado
        self.frame_ia_dynamic=tb.Frame(card); self.frame_ia_dynamic.pack(fill=X,pady=6)
        self.frame_gemini=tb.Frame(self.frame_ia_dynamic)
        tb.Label(self.frame_gemini,text="Gemini Key").pack(side=LEFT,padx=5); self.ent_gemini=tb.Entry(self.frame_gemini,textvariable=self.var_gemini_key,show="*",width=40); self.ent_gemini.pack(side=LEFT,padx=5,fill=X,expand=True)
        info_icon(self.frame_gemini, "Chave gratuita do Google Gemini. Deixe em branco para heurístico.").pack(side=LEFT)
        def toggle(): self.ent_gemini.config(show="" if self.ent_gemini.cget("show")=="*" else "*"); btn_show.config(text="Ocultar" if self.ent_gemini.cget("show")=="" else "Mostrar")
        btn_show=tb.Button(self.frame_gemini,text="Mostrar",bootstyle="secondary-outline",command=toggle,width=8); btn_show.pack(side=LEFT,padx=5)
        tb.Label(self.frame_gemini,text="Modelo").pack(side=LEFT,padx=5); self.combo_gemini_model=tb.Combobox(self.frame_gemini,textvariable=self.var_gemini_model,values=["gemini-flash-latest","gemini-pro-latest"],width=20); self.combo_gemini_model.pack(side=LEFT,padx=5)
        info_icon(self.frame_gemini, "'-latest' segue automaticamente a versão estável mais recente do Google. Se der 404, veja o nome atual em ai.google.dev/gemini-api/docs/models e digite aqui.").pack(side=LEFT)
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
        tb.Label(self.frame_openrouter,text="Modelo").pack(side=LEFT,padx=5); self.combo_openrouter_model=tb.Combobox(self.frame_openrouter,textvariable=self.var_openrouter_model,values=["minimax/minimax-m3:free","nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"],width=42); self.combo_openrouter_model.pack(side=LEFT,padx=5)
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
        hdr2=tb.Frame(card2); hdr2.pack(fill=X); tb.Label(hdr2,text="Envia currículos automaticamente por e-mail quando a vaga divulga e-mail de contato",font=("Segoe UI",8),bootstyle="light").pack(side=LEFT); info_icon(hdr2, "SMTP = protocolo de envio de e-mail.\nGmail: smtp.gmail.com:587 + Senha de App (myaccount.google.com > Segurança > Senhas de app).\nOutlook: smtp.office365.com:587\nSe deixar vazio, o sistema só gera PDFs e relatório (não envia).").pack(side=LEFT,padx=4)
        g=tb.Frame(card2); g.pack(fill=X, pady=(6,0)); g.columnconfigure(1,weight=1); g.columnconfigure(3,weight=1)
        tb.Label(g,text="Host").grid(row=0,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_host).grid(row=0,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Porta").grid(row=0,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_port,width=8).grid(row=0,column=3,sticky=W,padx=5,pady=3)
        tb.Label(g,text="Usuário").grid(row=1,column=0,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_user).grid(row=1,column=1,sticky=EW,padx=5,pady=3)
        tb.Label(g,text="Senha / App Pass").grid(row=1,column=2,sticky=W,padx=5,pady=3); tb.Entry(g,textvariable=self.var_smtp_pass,show="*").grid(row=1,column=3,sticky=EW,padx=5,pady=3)
        tb.Label(card2,text="Se vazio, não envia e-mail — apenas gera PDFs.",font=("Segoe UI",8),bootstyle="light").pack(anchor=W, pady=(4,0))
        card3=tb.Labelframe(f,text="LinkedIn / Gupy (automação navegador, opcional)",padding=10,bootstyle="warning"); card3.pack(fill=X,pady=5)
        hdr3=tb.Frame(card3); hdr3.pack(fill=X); tb.Label(hdr3,text="Login feito num navegador real — o app nunca vê nem guarda sua senha, só a sessão",font=("Segoe UI",8),bootstyle="light").pack(side=LEFT); info_icon(hdr3, "Clique em 'Fazer login' — abre um Chromium de verdade na página de login do site.\nLogue do jeito que quiser (senha, Google, 2FA); o app não vê nada disso.\nDepois de detectar o login, salva só a sessão (cookies) localmente — nunca a senha.\nSe a sessão expirar depois, o app avisa e é só logar de novo pelo mesmo botão.").pack(side=LEFT,padx=4)
        g2=tb.Frame(card3); g2.pack(fill=X,pady=(4,0))
        tb.Label(g2,text="LinkedIn:").grid(row=0,column=0,sticky=W,padx=5,pady=4)
        self.lbl_linkedin_auth=tb.Label(g2,text="…",width=16); self.lbl_linkedin_auth.grid(row=0,column=1,sticky=W,padx=5)
        self.btn_linkedin_login=tb.Button(g2,text="🔗 Fazer login",bootstyle="warning-outline",command=lambda:self._start_browser_login("linkedin")); self.btn_linkedin_login.grid(row=0,column=2,padx=5)
        tb.Button(g2,text="🗑 Esquecer",bootstyle="secondary-outline",command=lambda:self._forget_browser_session("linkedin")).grid(row=0,column=3,padx=5)
        tb.Label(g2,text="Gupy:").grid(row=1,column=0,sticky=W,padx=5,pady=4)
        self.lbl_gupy_auth=tb.Label(g2,text="…",width=16); self.lbl_gupy_auth.grid(row=1,column=1,sticky=W,padx=5)
        self.btn_gupy_login=tb.Button(g2,text="🔗 Fazer login",bootstyle="warning-outline",command=lambda:self._start_browser_login("gupy")); self.btn_gupy_login.grid(row=1,column=2,padx=5)
        tb.Button(g2,text="🗑 Esquecer",bootstyle="secondary-outline",command=lambda:self._forget_browser_session("gupy")).grid(row=1,column=3,padx=5)
        self.after(200, self._refresh_browser_auth_status)

    def _refresh_browser_auth_status(self):
        try:
            import browser_auth
            for service, lbl in (("linkedin", getattr(self,"lbl_linkedin_auth",None)), ("gupy", getattr(self,"lbl_gupy_auth",None))):
                if lbl is None: continue
                if browser_auth.has_session(service):
                    lbl.config(text="✓ Logado", bootstyle="success")
                else:
                    lbl.config(text="○ Não logado", bootstyle="light")
        except Exception:
            pass

    def _start_browser_login(self, service: str):
        label = {"linkedin":"LinkedIn","gupy":"Gupy"}.get(service, service)
        btn = getattr(self, f"btn_{service}_login", None)
        if btn: btn.config(state=DISABLED, text="Aguardando login…")
        lbl = getattr(self, f"lbl_{service}_auth", None)
        if lbl: lbl.config(text="⏳ aguardando…", bootstyle="warning")
        def worker():
            import browser_auth
            ok = browser_auth.login_via_browser(service)
            def done():
                if btn: btn.config(state=NORMAL, text="🔗 Fazer login")
                self._refresh_browser_auth_status()
                if ok:
                    messagebox.showinfo("Login", f"Login no {label} salvo com sucesso.")
                else:
                    messagebox.showwarning("Login", f"Login no {label} não foi concluído (janela fechada ou tempo esgotado). Tente novamente.")
            self.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    def _forget_browser_session(self, service: str):
        label = {"linkedin":"LinkedIn","gupy":"Gupy"}.get(service, service)
        if not messagebox.askyesno("Esquecer login", f"Isso apaga a sessão salva do {label}. Você vai precisar logar de novo pra usar automação com login. Continuar?"):
            return
        import browser_auth
        browser_auth.clear_session(service)
        self._refresh_browser_auth_status()

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
                self.lbl_ai_status.config(text=f"○ IA desabilitada — preencha a chave de '{p}' acima para ativar (opcional). Sem chave usa heurístico e funções com IA ficam cinza.", bootstyle="light")
        for attr in ["btn_preview_ai"]:
            if hasattr(self, attr):
                try: getattr(self, attr).config(state=NORMAL if ai_available else DISABLED)
                except: pass
        if hasattr(self, 'lbl_exec_ai'):
            if ai_available:
                self.lbl_exec_ai.config(text=f"IA pronta ({p}) — currículos serão reestruturados com palavras-chave da vaga", bootstyle="success")
            else:
                self.lbl_exec_ai.config(text="IA desabilitada — execução usará heurístico (sem reestruturação por IA). Preencha a chave para habilitar.", bootstyle="light")

    def test_gemini(self):
        p=self.var_llm_provider.get()
        if p=="openrouter":
            key=self.var_openrouter_key.get().strip()
            model=self.var_openrouter_model.get().strip() or "meta-llama/llama-3.1-8b-instruct:free"
            if not key: messagebox.showwarning("OpenRouter","Informe a key em openrouter.ai/keys"); return
            try:
                from ats_optimizer import call_openrouter_once
                r=call_openrouter_once("Responda apenas OK", key, model, max_tokens=20)
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
        model_name=self.var_gemini_model.get().strip() or "gemini-flash-latest"
        try:
            import google.generativeai as genai
            genai.configure(api_key=key); m=genai.GenerativeModel(model_name); r=m.generate_content("Responda OK")
            messagebox.showinfo("Gemini",r.text[:200])
        except Exception as e: messagebox.showerror("Gemini",f"Modelo '{model_name}': {e}")

    # Execução
