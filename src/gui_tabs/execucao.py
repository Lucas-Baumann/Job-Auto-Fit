import json, os, sys, threading, subprocess, webbrowser, re, queue
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from config import Config
from theme import get_active_theme, label_for
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, style_ttk,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

class ExecucaoTabMixin:
    """Aba 4 - Execucao: roda o pipeline completo, log em tempo real, preview de PDF."""
    def _build_exec(self):
        f=self.tab_exec
        t=style_ttk()

        # tk.Frame puro (não CTkFrame) - esta aba não passa por make_scrollable()/card() como
        # as outras, então fica parentada direto na aba crua (ttk.Frame, sem cor resolvível
        # pelo CustomTkinter). CTkFrame(fg_color=..., corner_radius=0) ainda deixava uma linha
        # escura fina sob a fileira (renderização em canvas do CTkFrame usa uma cor própria
        # pra máscara de canto que não é a mesma coisa que fg_color, e ela não seguia o tema
        # mesmo com corner_radius=0) - só um container de layout (checkbox + botões), não
        # precisa de nada que o CTkFrame ofereça além da cor sólida, então tk.Frame resolve
        # sem esse problema.
        top=tk.Frame(f, bg=t["window_bg"])
        top.pack(fill="x", pady=(0,10))
        ctk.CTkCheckBox(top,text="dry-run (só PDFs + relatório)",variable=self.var_dry_run).pack(side="left")
        self.btn_run=ctk.CTkButton(top,text=label_for("iniciar_automacao"),width=180,fg_color=t["success"],
                                    hover_color=t["border"],command=self.run_automation)
        self.btn_run.pack(side="right")
        self.btn_stop=ctk.CTkButton(top,text="■ Parar",width=100,fg_color="transparent",border_width=1,
                                     border_color=t["danger"],text_color=t["danger"],hover_color=t["card_bg"],
                                     state="disabled",command=self.stop_automation)
        self.btn_stop.pack(side="right",padx=(0,8))

        self.progress=ttk.Progressbar(f,mode="indeterminate",style="Vamp.Horizontal.TProgressbar")
        self.progress.pack(fill="x",pady=(0,10))

        log_outer=ctk.CTkFrame(f, fg_color=t["card_bg"], corner_radius=10, border_width=1, border_color=t["border"], bg_color=t["window_bg"])
        log_outer.pack(fill="both",expand=True,pady=(0,10))
        log_frame=ctk.CTkFrame(log_outer, fg_color="transparent")
        log_frame.pack(fill="both",expand=True,padx=10,pady=10)
        self.log_text=tk.Text(log_frame,height=18,wrap="word",bg=t["card_bg"],fg=t["text"],
                               insertbackground=t["text"],borderwidth=0,highlightthickness=0,font=("Consolas",11))
        self.log_text.pack(side="left",fill="both",expand=True)
        # cores no log: verde quando algo termina bem, vermelho em erro/parada, azul nos
        # separadores "=== ... ===" - só pra dar sinal visual rápido sem precisar ler o texto
        # todo (pedido explícito: log muito "monocromático" antes).
        self.log_text.tag_configure("ok", foreground=t["success"])
        self.log_text.tag_configure("err", foreground=t["danger"])
        self.log_text.tag_configure("info", foreground=t["primary"])
        sb=ttk.Scrollbar(log_frame,orient="vertical",command=self.log_text.yview)
        sb.pack(side="right",fill="y"); self.log_text.configure(yscrollcommand=sb.set)
        self.log=type("o",(),{"text":self.log_text})()
        # Tkinter não é thread-safe: mexer no Text direto de uma thread em background (o
        # pipeline roda numa) já causou o app travar (ex: ao clicar 'Abrir último HTML' logo
        # depois de uma execução, enquanto a thread do pipeline ainda tocava no widget). _log
        # agora só enfileira; quem realmente escreve no widget é _drain_log_queue, sempre
        # disparado via self.after() no thread principal.
        self._log_queue=queue.Queue()
        self._log("Pronto. Clique em Iniciar.\n")
        self.after(80, self._drain_log_queue)

        row=tk.Frame(f, bg=t["window_bg"])
        row.pack(fill="x")
        ctk.CTkButton(row,text="Abrir último HTML",width=140,command=self.open_last_report).pack(side="left",padx=(0,8))
        ctk.CTkButton(row,text="Pasta OUTPUT",width=120,fg_color="transparent",border_width=1,
                      border_color=t["border"],text_color=t["text"],hover_color=t["card_bg"],
                      command=lambda:self._open_folder(BASE_DIR/"output")).pack(side="left",padx=(0,8))
        self.btn_preview_ai=ctk.CTkButton(row,text="Preview ATS c/ IA (reestrutura)",width=200,fg_color="transparent",
                                           border_width=1,border_color=t["primary"],text_color=t["primary"],
                                           hover_color=t["card_bg"],command=self.preview_pdf)
        self.btn_preview_ai.pack(side="left",padx=(0,8))
        ctk.CTkButton(row,text="Limpar log",width=100,fg_color="transparent",border_width=1,
                      border_color=t["border"],text_color=t["text_dim"],hover_color=t["card_bg"],
                      command=lambda:self.log.text.delete("1.0",tk.END)).pack(side="right")
        self.lbl_exec_ai=ctk.CTkLabel(f,text="",font=ctk.CTkFont(size=11),text_color=t["text_dim"],anchor="w",fg_color=t["window_bg"],bg_color=t["window_bg"])
        self.lbl_exec_ai.pack(fill="x", pady=(6,0))
    def _log(self,msg):
        """Thread-safe: pode ser chamado tanto do thread principal quanto da thread do
        pipeline em background — só enfileira, nunca toca o widget diretamente."""
        self._log_queue.put(msg)
    def _drain_log_queue(self):
        updated=False
        while True:
            try: msg=self._log_queue.get_nowait()
            except queue.Empty: break
            text=msg+("\n" if not msg.endswith("\n") else "")
            for line in text.splitlines(keepends=True):
                tag=self._log_tag_for(line)
                if tag: self.log.text.insert(tk.END, line, tag)
                else: self.log.text.insert(tk.END, line)
            updated=True
        if updated: self.log.text.see(tk.END)
        self.after(80, self._drain_log_queue)
    def _log_tag_for(self, line):
        low=line.lower()
        if "===" in line: return "info"
        if any(k in low for k in ("[erro]","erro:","falhou","parado","authwall","exception")): return "err"
        if any(k in low for k in ("finalizado","concluíd","✓","sucesso")): return "ok"
        return None
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
        kws=[k.strip() for k in self.var_keywords.get().split(",") if k.strip()]
        if not kws:
            # Antes caía num fallback silencioso pra "Desenvolvedor Python" sem avisar nada —
            # o usuário achava que tinha rodado sem filtro nenhum e via uma busca bem
            # específica no log, sem entender de onde veio. Agora bloqueia igual à validação
            # de nome acima, em vez de inventar uma palavra-chave que ninguém pediu.
            messagebox.showwarning("Validação","Informe ao menos uma palavra-chave de busca"); self.nb.select(self.tab_busca); return
        self.save_all(silent=True); self.btn_run.configure(state="disabled"); self.progress.start(12); self._log("\n=== Iniciando ===")
        loc="Brasil" if self.var_work_mode.get()=="remoto" else (self.var_presencial_loc.get().strip() or "Brasil")
        min_score=int(self.var_min_score.get()); dry_run=bool(self.var_dry_run.get())
        self.proc=None; self.stop_requested=False
        # No .exe congelado não existe python/main.py separado pra chamar via subprocess —
        # roda o pipeline no mesmo processo. "Parar" então não mata um processo externo: usa
        # o should_stop de run_pipeline, então não é instantâneo (termina a vaga em andamento).
        frozen=bool(getattr(sys,'frozen',False))
        self.btn_stop.configure(state="normal")
        def target():
            try:
                if frozen:
                    from main import run_pipeline
                    import contextlib
                    class _LogStream:
                        def __init__(self, log_fn): self.log_fn=log_fn; self._buf=""
                        def write(self, s):
                            self._buf+=s
                            while "\n" in self._buf:
                                line, self._buf = self._buf.split("\n",1)
                                self.log_fn(line)
                        def flush(self): pass
                    with contextlib.redirect_stdout(_LogStream(self._log)):
                        run_pipeline(kws, loc, min_score, dry_run=dry_run, should_stop=lambda: self.stop_requested)
                    self._log("\n=== Finalizado ===" if not self.stop_requested else "\n=== Parado ===")
                else:
                    cmd=[sys.executable,str(BASE_DIR/"main.py"),"--keywords",*kws,"--location",loc,"--min-score",str(min_score)]
                    if dry_run: cmd.append("--dry-run")
                    self._log(f"Comando: {' '.join(cmd)}")
                    self.proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",cwd=str(BASE_DIR))
                    for line in self.proc.stdout:
                        if self.stop_requested:
                            try: self.proc.terminate()
                            except: pass
                            break
                        self._log(line.rstrip())
                    self.proc.wait()
                    self._log("\n=== Finalizado ===" if not self.stop_requested else "\n=== Parado ===")
            except Exception as e: self._log(f"[Erro] {e}")
            finally:
                # mesma razão do _log: essas chamadas mexem em widgets Tk e o botão/progress
                # são widgets também — precisam rodar no thread principal, não aqui.
                def _finish():
                    self.progress.stop(); self.btn_run.configure(state="normal"); self.btn_stop.configure(state="disabled")
                    self._refresh_hist(); self._refresh_dashboard()
                self.after(0, _finish)
        threading.Thread(target=target,daemon=True).start()
    def stop_automation(self):
        self.stop_requested=True
        self.btn_stop.configure(state="disabled")
        try: self.proc.terminate()
        except: pass
        self._log("[Stop] Parada solicitada — aguardando terminar a keyword/vaga em andamento (não é instantâneo).")

    # Dashboard
