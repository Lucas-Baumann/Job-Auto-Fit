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

class ExecucaoTabMixin:
    """Aba 4 - Execucao: roda o pipeline completo, log em tempo real, preview de PDF."""
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
        self.btn_preview_ai=tb.Button(row,text="Preview ATS c/ IA (reestrutura)",bootstyle="warning-outline",command=self.preview_pdf); self.btn_preview_ai.pack(side=LEFT,padx=5)
        tb.Button(row,text="Limpar log",bootstyle="secondary-outline",command=lambda:self.log.text.delete("1.0",tk.END)).pack(side=RIGHT)
        self.lbl_exec_ai=tb.Label(f,text="",font=("Segoe UI",8)); self.lbl_exec_ai.pack(anchor=W, pady=(2,0))
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
        self.save_all(silent=True); self.btn_run.config(state=DISABLED); self.progress.start(12); self._log("\n=== Iniciando ===")
        kws=[k.strip() for k in self.var_keywords.get().split(",") if k.strip()] or ["Desenvolvedor Python"]
        loc="Brasil" if self.var_work_mode.get()=="remoto" else (self.var_presencial_loc.get().strip() or "Brasil")
        min_score=int(self.var_min_score.get()); dry_run=bool(self.var_dry_run.get())
        self.proc=None; self.stop_requested=False
        # No .exe congelado não existe python/main.py separado para chamar via subprocess (o .exe
        # empacota só a GUI) — nesse caso roda o pipeline no mesmo processo em vez de subprocess.
        # Parar nesse modo não termina um processo externo (não existe um): run_pipeline recebe
        # should_stop e checa a flag entre keywords/vagas, então "Parar" ainda funciona, só não é
        # instantâneo — a vaga/keyword em andamento termina antes de interromper.
        frozen=bool(getattr(sys,'frozen',False))
        self.btn_stop.config(state=NORMAL)
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
            finally: self.progress.stop(); self.btn_run.config(state=NORMAL); self.btn_stop.config(state=DISABLED); self._refresh_hist(); self._refresh_dashboard()
        threading.Thread(target=target,daemon=True).start()
    def stop_automation(self):
        self.stop_requested=True
        self.btn_stop.config(state=DISABLED)
        try: self.proc.terminate()
        except: pass
        self._log("[Stop] Parada solicitada — aguardando terminar a keyword/vaga em andamento (não é instantâneo).")

    # Dashboard
