import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import Config
from theme import get_active_theme
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, card, field, make_scrollable,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

def _outline_btn(parent, text, theme, color_key="border", **kw):
    t=theme
    return ctk.CTkButton(parent, text=text, fg_color="transparent", border_width=1,
                          border_color=t[color_key], text_color=t[color_key] if color_key!="border" else t["text"],
                          hover_color=t["card_bg"], **kw)

class IATabMixin:
    """Aba 3 - IA & Conexoes: provedor de IA, SMTP, GitHub token, LinkedIn/Gupy."""
    def _build_ia(self):
        f=self.tab_ia
        t=get_active_theme()
        inner=make_scrollable(f)
        inner.pack(fill="both", expand=True)
        outer, content = card(inner, "Provedor IA (gratuito ou pago) — campo OPCIONAL")
        outer.pack(fill="x", pady=(0,10))
        row_prov=ctk.CTkFrame(content, fg_color="transparent"); row_prov.pack(fill="x")
        ctk.CTkLabel(row_prov,text="Provedor",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.combo_llm=ctk.CTkComboBox(row_prov,variable=self.var_llm_provider,
                                        values=["gemini","ollama","openai","claude","groq","openrouter","custom"],
                                        state="readonly",width=140)
        self.combo_llm.pack(side="left",padx=(0,6))
        info_icon(row_prov, "Escolha a IA que reescreve seu currículo/Carta para o ATS.\n• gemini = gratuito (aistudio.google.com)\n• ollama = local gratuito\n• openai/claude/groq = pago\n• openrouter = free tier (openrouter.ai/keys) :free").pack(side="left")
        self.btn_test_gemini=_outline_btn(row_prov,"Testar Conexão",t,"success",command=self.test_gemini)
        self.btn_test_gemini.pack(side="left",padx=(10,0))
        self.lbl_ai_status=ctk.CTkLabel(content,text="",font=ctk.CTkFont(size=11,weight="bold"),anchor="w")
        self.lbl_ai_status.pack(fill="x",pady=(8,0))
        ctk.CTkLabel(content,text="Gemini gratuito: aistudio.google.com/app/apikey — deixe em branco para heurístico.",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"],anchor="w").pack(anchor="w")
        # container dinâmico — mostra só o provider selecionado
        self.frame_ia_dynamic=ctk.CTkFrame(content, fg_color="transparent"); self.frame_ia_dynamic.pack(fill="x",pady=(8,0))

        self.frame_gemini=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_gemini,text="Gemini Key",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_gemini=ctk.CTkEntry(self.frame_gemini,textvariable=self.var_gemini_key,show="*",width=280)
        self.ent_gemini.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(self.frame_gemini, "Chave gratuita do Google Gemini. Deixe em branco para heurístico.").pack(side="left")
        def toggle():
            showing = self.ent_gemini.cget("show")==""
            self.ent_gemini.configure(show="*" if showing else "")
            btn_show.configure(text="Mostrar" if showing else "Ocultar")
        btn_show=_outline_btn(self.frame_gemini,"Mostrar",t,"border",width=80,command=toggle); btn_show.pack(side="left",padx=(6,0))
        ctk.CTkLabel(self.frame_gemini,text="Modelo",text_color=t["text_dim"]).pack(side="left",padx=(10,6))
        self.combo_gemini_model=ctk.CTkComboBox(self.frame_gemini,variable=self.var_gemini_model,
                                                 values=["gemini-flash-latest","gemini-pro-latest"],width=180)
        self.combo_gemini_model.pack(side="left")
        info_icon(self.frame_gemini, "'-latest' segue automaticamente a versão estável mais recente do Google. Se der 404, veja o nome atual em ai.google.dev/gemini-api/docs/models e digite aqui.").pack(side="left")

        self.frame_ollama=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_ollama,text="Ollama Host",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_ollama_host=ctk.CTkEntry(self.frame_ollama,textvariable=self.var_ollama_host,width=220)
        self.ent_ollama_host.pack(side="left",padx=(0,6))
        info_icon(self.frame_ollama, "IA local gratuita. Instale em ollama.com e rode 'ollama run llama3'").pack(side="left")
        ctk.CTkLabel(self.frame_ollama,text="Modelo",text_color=t["text_dim"]).pack(side="left",padx=(10,6))
        self.ent_ollama_model=ctk.CTkEntry(self.frame_ollama,textvariable=self.var_ollama_model,width=150)
        self.ent_ollama_model.pack(side="left")

        self.frame_openai=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_openai,text="OpenAI Key",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_openai=ctk.CTkEntry(self.frame_openai,textvariable=self.var_openai_key,show="*",width=280)
        self.ent_openai.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(self.frame_openai, "platform.openai.com/api-keys — pago, modelo gpt-4o-mini").pack(side="left")

        self.frame_claude=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_claude,text="Claude Key",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_claude=ctk.CTkEntry(self.frame_claude,textvariable=self.var_claude_key,show="*",width=280)
        self.ent_claude.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(self.frame_claude, "console.anthropic.com — pago, modelo claude-3-haiku").pack(side="left")

        self.frame_groq=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_groq,text="Groq Key",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_groq=ctk.CTkEntry(self.frame_groq,textvariable=self.var_groq_key,show="*",width=280)
        self.ent_groq.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(self.frame_groq, "console.groq.com — gratuito/pago, rápido").pack(side="left")

        self.frame_openrouter=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_openrouter,text="OpenRouter Key",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_openrouter=ctk.CTkEntry(self.frame_openrouter,textvariable=self.var_openrouter_key,show="*",width=200)
        self.ent_openrouter.pack(side="left",padx=(0,6))
        info_icon(self.frame_openrouter, "openrouter.ai/keys → Free tier :free sem cartão").pack(side="left")
        ctk.CTkLabel(self.frame_openrouter,text="Modelo",text_color=t["text_dim"]).pack(side="left",padx=(10,6))
        # valores vêm de Config (config.py) — fonte única com o fallback usado de verdade em
        # ats_optimizer.py; antes essa lista tinha modelos diferentes dos realmente tentados.
        _or_models=[Config.OPENROUTER_MODEL]+[m for m in Config.OPENROUTER_FALLBACK_MODELS if m!=Config.OPENROUTER_MODEL]
        self.combo_openrouter_model=ctk.CTkComboBox(self.frame_openrouter,variable=self.var_openrouter_model,values=_or_models,width=280)
        self.combo_openrouter_model.pack(side="left",padx=(0,6))
        _outline_btn(self.frame_openrouter,"↗ Lista free",t,"primary",width=110,
                     command=lambda: webbrowser.open("https://openrouter.ai/models?max_price=0")).pack(side="left")
        info_icon(self.frame_openrouter, "Digite manualmente o slug :free visto na lista (copie de openrouter.ai/models?max_price=0). Lista muda; se 404, tente outro.").pack(side="left")

        self.frame_custom=ctk.CTkFrame(self.frame_ia_dynamic, fg_color="transparent")
        ctk.CTkLabel(self.frame_custom,text="Custom URL",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_custom_url=ctk.CTkEntry(self.frame_custom,textvariable=self.var_custom_url,width=260)
        self.ent_custom_url.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(self.frame_custom, "Ex: https://api.deepseek.com/v1/chat/completions").pack(side="left")
        ctk.CTkLabel(self.frame_custom,text="Custom Key",text_color=t["text_dim"]).pack(side="left",padx=(10,6))
        self.ent_custom_key=ctk.CTkEntry(self.frame_custom,textvariable=self.var_custom_key,show="*",width=160)
        self.ent_custom_key.pack(side="left")

        # trace para habilitar/desabilitar
        self.var_gemini_key.trace_add("write", lambda *_: self._update_ai_state())
        self.var_openrouter_key.trace_add("write", lambda *_: self._update_ai_state())
        self.var_llm_provider.trace_add("write", lambda *_: self._update_ai_state())
        self.after(300, self._update_ai_state)

        outer, content2 = card(inner, "E-mail SMTP (envio automático, opcional)")
        outer.pack(fill="x", pady=(0,10))
        hdr2=ctk.CTkFrame(content2, fg_color="transparent"); hdr2.pack(fill="x")
        ctk.CTkLabel(hdr2,text="Envia currículos automaticamente por e-mail quando a vaga divulga e-mail de contato",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"]).pack(side="left")
        info_icon(hdr2, "SMTP = protocolo de envio de e-mail.\nGmail: smtp.gmail.com:587 + Senha de App (myaccount.google.com > Segurança > Senhas de app).\nOutlook: smtp.office365.com:587\nSe deixar vazio, o sistema só gera PDFs e relatório (não envia).").pack(side="left",padx=4)
        g=ctk.CTkFrame(content2, fg_color="transparent"); g.pack(fill="x", pady=(8,0))
        g.columnconfigure(0,weight=1); g.columnconfigure(1,weight=1)
        w,_=field(g,"Host",lambda p: ctk.CTkEntry(p,textvariable=self.var_smtp_host)); w.grid(row=0,column=0,sticky="ew",padx=(0,8),pady=4)
        w,_=field(g,"Porta",lambda p: ctk.CTkEntry(p,textvariable=self.var_smtp_port,width=90)); w.grid(row=0,column=1,sticky="w",pady=4)
        w,_=field(g,"Usuário",lambda p: ctk.CTkEntry(p,textvariable=self.var_smtp_user)); w.grid(row=1,column=0,sticky="ew",padx=(0,8),pady=4)
        w,_=field(g,"Senha / App Pass",lambda p: ctk.CTkEntry(p,textvariable=self.var_smtp_pass,show="*")); w.grid(row=1,column=1,sticky="ew",pady=4)
        ctk.CTkLabel(content2,text="Se vazio, não envia e-mail — apenas gera PDFs.",font=ctk.CTkFont(size=10),
                     text_color=t["text_dim"]).pack(anchor="w", pady=(6,0))

        outer, content3 = card(inner, "LinkedIn / Gupy (automação navegador, opcional)")
        outer.pack(fill="x", pady=(0,10))
        hdr3=ctk.CTkFrame(content3, fg_color="transparent"); hdr3.pack(fill="x")
        ctk.CTkLabel(hdr3,text="Login feito num navegador real — o app nunca vê nem guarda sua senha, só a sessão",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"]).pack(side="left")
        info_icon(hdr3, "Clique em 'Fazer login' — abre um Chromium de verdade na página de login do site.\nLogue do jeito que quiser (senha, Google, 2FA); o app não vê nada disso.\nDepois de detectar o login, salva só a sessão (cookies) localmente — nunca a senha.\nSe a sessão expirar depois, o app avisa e é só logar de novo pelo mesmo botão.").pack(side="left",padx=4)
        g2=ctk.CTkFrame(content3, fg_color="transparent"); g2.pack(fill="x",pady=(8,0))
        ctk.CTkLabel(g2,text="LinkedIn:",text_color=t["text_dim"]).grid(row=0,column=0,sticky="w",padx=(0,8),pady=4)
        self.lbl_linkedin_auth=ctk.CTkLabel(g2,text="…",width=110,anchor="w"); self.lbl_linkedin_auth.grid(row=0,column=1,sticky="w",padx=(0,8))
        self.btn_linkedin_login=_outline_btn(g2,"🔗 Fazer login",t,"primary",command=lambda:self._start_browser_login("linkedin"))
        self.btn_linkedin_login.grid(row=0,column=2,padx=(0,8))
        _outline_btn(g2,"🗑 Esquecer",t,"border",command=lambda:self._forget_browser_session("linkedin")).grid(row=0,column=3)
        ctk.CTkLabel(g2,text="Gupy:",text_color=t["text_dim"]).grid(row=1,column=0,sticky="w",padx=(0,8),pady=4)
        self.lbl_gupy_auth=ctk.CTkLabel(g2,text="…",width=110,anchor="w"); self.lbl_gupy_auth.grid(row=1,column=1,sticky="w",padx=(0,8))
        self.btn_gupy_login=_outline_btn(g2,"🔗 Fazer login",t,"primary",command=lambda:self._start_browser_login("gupy"))
        self.btn_gupy_login.grid(row=1,column=2,padx=(0,8))
        _outline_btn(g2,"🗑 Esquecer",t,"border",command=lambda:self._forget_browser_session("gupy")).grid(row=1,column=3)
        self.after(200, self._refresh_browser_auth_status)

    def _refresh_browser_auth_status(self):
        t=get_active_theme()
        try:
            import browser_auth
            for service, lbl in (("linkedin", getattr(self,"lbl_linkedin_auth",None)), ("gupy", getattr(self,"lbl_gupy_auth",None))):
                if lbl is None: continue
                if browser_auth.has_session(service):
                    lbl.configure(text="✓ Logado", text_color=t["success"])
                else:
                    lbl.configure(text="○ Não logado", text_color=t["text_dim"])
        except Exception:
            pass

    def _start_browser_login(self, service: str):
        label = {"linkedin":"LinkedIn","gupy":"Gupy"}.get(service, service)
        btn = getattr(self, f"btn_{service}_login", None)
        if btn: btn.configure(state="disabled", text="Aguardando login…")
        t=get_active_theme()
        lbl = getattr(self, f"lbl_{service}_auth", None)
        if lbl: lbl.configure(text="⏳ aguardando…", text_color=t["primary"])
        def worker():
            import browser_auth
            ok = browser_auth.login_via_browser(service)
            def done():
                if btn: btn.configure(state="normal", text="🔗 Fazer login")
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
        t=get_active_theme()
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
            self.btn_test_gemini.configure(state="normal" if need_key else "disabled",
                                            border_color=t["success"] if need_key else t["border"],
                                            text_color=t["success"] if need_key else t["text_dim"])
        # habilitar apenas campos do provedor ativo
        if hasattr(self, 'ent_gemini'): self.ent_gemini.configure(state="normal" if p=="gemini" else "disabled")
        if hasattr(self, 'ent_openai'): self.ent_openai.configure(state="normal" if p=="openai" else "disabled")
        if hasattr(self, 'ent_claude'): self.ent_claude.configure(state="normal" if p=="claude" else "disabled")
        if hasattr(self, 'ent_groq'): self.ent_groq.configure(state="normal" if p=="groq" else "disabled")
        if hasattr(self, 'ent_openrouter'):
            s_or = "normal" if p=="openrouter" else "disabled"
            self.ent_openrouter.configure(state=s_or)
            if hasattr(self, 'combo_openrouter_model'): self.combo_openrouter_model.configure(state=s_or)
        if hasattr(self, 'ent_ollama_host'):
            s = "normal" if p=="ollama" else "disabled"
            self.ent_ollama_host.configure(state=s); self.ent_ollama_model.configure(state=s)
        if hasattr(self, 'ent_custom_url'):
            s2 = "normal" if p=="custom" else "disabled"
            self.ent_custom_url.configure(state=s2); self.ent_custom_key.configure(state=s2)
        # mostra só frame do provider selecionado (dropdown único dinâmico)
        if hasattr(self, 'frame_gemini'):
            for fr in [self.frame_gemini, self.frame_ollama, self.frame_openai, self.frame_claude, self.frame_groq, self.frame_openrouter, self.frame_custom]:
                try: fr.pack_forget()
                except: pass
            if p=="gemini": self.frame_gemini.pack(fill="x", pady=2)
            elif p=="ollama": self.frame_ollama.pack(fill="x", pady=2)
            elif p=="openai": self.frame_openai.pack(fill="x", pady=2)
            elif p=="claude": self.frame_claude.pack(fill="x", pady=2)
            elif p=="groq": self.frame_groq.pack(fill="x", pady=2)
            elif p=="openrouter": self.frame_openrouter.pack(fill="x", pady=2)
            elif p=="custom": self.frame_custom.pack(fill="x", pady=2)
        if hasattr(self, 'lbl_ai_status'):
            if ai_available:
                self.lbl_ai_status.configure(text=f"✓ IA habilitada ({p}) — reestruturação ATS e carta com IA ativas", text_color=t["success"])
            else:
                self.lbl_ai_status.configure(text=f"○ IA desabilitada — preencha a chave de '{p}' acima para ativar (opcional). Sem chave usa heurístico e funções com IA ficam cinza.", text_color=t["text_dim"])
        for attr in ["btn_preview_ai"]:
            if hasattr(self, attr):
                try: getattr(self, attr).configure(state="normal" if ai_available else "disabled")
                except: pass
        if hasattr(self, 'lbl_exec_ai'):
            if ai_available:
                self.lbl_exec_ai.configure(text=f"IA pronta ({p}) — currículos serão reestruturados com palavras-chave da vaga", text_color=t["success"])
            else:
                self.lbl_exec_ai.configure(text="IA desabilitada — execução usará heurístico (sem reestruturação por IA). Preencha a chave para habilitar.", text_color=t["text_dim"])

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
