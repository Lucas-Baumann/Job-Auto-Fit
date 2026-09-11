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

class HistoricoTabMixin:
    """Aba 6 - Historico: vagas processadas, aprovar/enviar manual, marcar resultado."""
    def _build_hist(self):
        f=self.tab_hist
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Label(top,text="Histórico (jobs.db) — duplo clique abre vaga").pack(side=LEFT,padx=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_hist).pack(side=RIGHT,padx=5)
        tb.Button(top,text="🗑 Limpar Histórico",bootstyle="danger-outline",command=self.clear_history).pack(side=RIGHT,padx=5)
        actions=tb.Frame(f); actions.pack(fill=X,pady=(0,5))
        tb.Button(actions,text="✔ Aprovar e Enviar (selecionada)",bootstyle="success",command=self.approve_and_send_selected).pack(side=LEFT,padx=5)
        info_icon(actions,"Só funciona em vagas com status 'ready_to_send' (fila de revisão — ative em\nBusca & Filtros → desmarcar 'Enviar automaticamente'). Envia com o PDF/carta já gerados.").pack(side=LEFT)
        tb.Button(actions,text="📝 Marcar Outcome",bootstyle="info-outline",command=self.mark_job_outcome).pack(side=LEFT,padx=10)
        info_icon(actions,"Registra o resultado real da candidatura (entrevista, rejeitado, proposta...).\nÚtil para no futuro avaliar se o score da IA realmente prediz sucesso.").pack(side=LEFT)
        cols=("vaga","empresa","local","match","status","outcome","plataforma")
        self.tree=tb.Treeview(f,columns=cols,show="headings",bootstyle="dark",height=14)
        for c in cols: self.tree.heading(c,text=c.capitalize())
        self.tree.column("vaga",width=240); self.tree.column("empresa",width=150); self.tree.column("local",width=120); self.tree.column("match",width=55,anchor=CENTER); self.tree.column("status",width=95,anchor=CENTER); self.tree.column("outcome",width=100,anchor=CENTER); self.tree.column("plataforma",width=85,anchor=CENTER)
        self.tree.pack(fill=BOTH,expand=True,pady=5); self.tree.bind("<Double-Button-1>",self._on_hist_dbl); self._refresh_hist()
    def _refresh_hist(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            if not DB_PATH.exists(): return
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT id,title,company,location,match_score,status,outcome,platform FROM jobs ORDER BY id DESC LIMIT 300")
            for r in cur.fetchall():
                self.tree.insert("",tk.END,iid=str(r["id"]),values=(r["title"],r["company"],r["location"],f"{r['match_score'] or 0}%",r["status"],r["outcome"] or "-",r["platform"]))
            con.close()
        except: pass
    def _on_hist_dbl(self,ev):
        sel=self.tree.selection()
        if not sel: return
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT url FROM jobs WHERE id=?",(int(sel[0]),)); row=cur.fetchone()
            if row and row["url"]: webbrowser.open(row["url"])
            con.close()
        except: pass
    def approve_and_send_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Aprovar e Enviar","Selecione uma vaga na lista."); return
        job_id=int(sel[0])
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT * FROM jobs WHERE id=?",(job_id,)); row=cur.fetchone(); con.close()
        except Exception as e: messagebox.showerror("Aprovar e Enviar",str(e)); return
        if not row: messagebox.showwarning("Aprovar e Enviar","Vaga não encontrada."); return
        if row["status"]!="ready_to_send":
            messagebox.showinfo("Aprovar e Enviar",f"Status atual: '{row['status']}'.\nSó é possível aprovar vagas com status 'ready_to_send' (aguardando revisão)."); return
        cover_text=""
        try:
            if row["cover_letter_path"] and Path(row["cover_letter_path"]).exists():
                cover_text=Path(row["cover_letter_path"]).read_text(encoding="utf-8")
        except Exception: pass
        try:
            from sender import apply_to_job
            from db import update_job_status
            status=apply_to_job(dict(row), row["resume_pdf_path"] or "", cover_text)
            update_job_status(job_id, status)
            messagebox.showinfo("Aprovar e Enviar",f"{row['title']} @ {row['company']} → status: {status}")
            self._refresh_hist(); self._refresh_dashboard()
        except Exception as e: messagebox.showerror("Aprovar e Enviar",str(e))
    def mark_job_outcome(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Outcome","Selecione uma vaga na lista."); return
        job_id=int(sel[0])
        top=tb.Toplevel(self); top.title("Atualizar Outcome"); top.geometry("360x150"); top.transient(self); top.grab_set()
        tb.Label(top,text="Resultado real da candidatura:").pack(anchor=W,padx=10,pady=(12,4))
        var_outcome=tk.StringVar(value="sem_resposta")
        tb.Combobox(top,textvariable=var_outcome,values=OUTCOME_OPTIONS,state="readonly").pack(fill=X,padx=10)
        def save():
            try:
                from db import update_job_outcome
                update_job_outcome(job_id, var_outcome.get())
                self._refresh_hist(); self._refresh_dashboard()
            except Exception as e: messagebox.showerror("Outcome",str(e))
            top.destroy()
        tb.Button(top,text="Salvar",bootstyle="success",command=save).pack(pady=12)
    def clear_history(self):
        if not messagebox.askyesno(
            "Limpar Histórico",
            "Isso apaga TODAS as vagas do Histórico e do Dashboard (banco de dados).\n"
            "Essa ação não pode ser desfeita. Continuar?",
            icon="warning",
        ):
            return
        also_delete_files = messagebox.askyesno(
            "Limpar Histórico",
            "Também apagar os PDFs de currículo e cartas de apresentação gerados pra essas vagas (pasta output/)?\n"
            "Se disser não, os arquivos ficam no disco (órfãos, sem vaga associada no histórico)."
        )
        try:
            import sqlite3
            con = sqlite3.connect(str(DB_PATH)); cur = con.cursor()
            if also_delete_files:
                cur.execute("SELECT resume_pdf_path, cover_letter_path FROM jobs")
                removed = 0
                for resume_path, cover_path in cur.fetchall():
                    for p in (resume_path, cover_path):
                        if p:
                            try:
                                Path(p).unlink(missing_ok=True)
                                removed += 1
                            except Exception:
                                pass
            cur.execute("DELETE FROM jobs")
            cur.execute("DELETE FROM sqlite_sequence WHERE name='jobs'")
            con.commit(); con.close()
            self._refresh_hist(); self._refresh_dashboard()
            msg = "Histórico e Dashboard limpos."
            if also_delete_files:
                msg += f"\n{removed} arquivo(s) apagado(s) de output/."
            messagebox.showinfo("Limpar Histórico", msg)
        except Exception as e:
            messagebox.showerror("Limpar Histórico", str(e))

    # Perfil GitHub
