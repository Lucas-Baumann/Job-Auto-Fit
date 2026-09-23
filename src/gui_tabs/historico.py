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
        tb.Label(top,text="Histórico (jobs.db) — duplo clique abre vaga. Clique no cabeçalho da coluna ordena (crescente → decrescente → sem ordenação)").pack(side=LEFT,padx=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_hist).pack(side=RIGHT,padx=5)
        tb.Button(top,text="🗑 Limpar Histórico",bootstyle="danger-outline",command=self.clear_history).pack(side=RIGHT,padx=5)

        actions=tb.Frame(f); actions.pack(fill=X,pady=(0,5))
        self.btn_approve_send=tb.Button(actions,text="✔ Aprovar e Enviar (selecionada)",bootstyle="success",command=self.approve_and_send_selected); self.btn_approve_send.pack(side=LEFT,padx=5)
        info_icon(actions,"Só funciona em vagas com status 'ready_to_send' (fila de revisão — ative em\nBusca & Filtros → desmarcar 'Enviar automaticamente'). Envia com o PDF/carta já gerados.").pack(side=LEFT)
        tb.Button(actions,text="📝 Marcar Outcome",bootstyle="info-outline",command=self.mark_job_outcome).pack(side=LEFT,padx=10)
        info_icon(actions,"Registra o resultado real da candidatura (entrevista, rejeitado, proposta...).\nÚtil para no futuro avaliar se o score da IA realmente prediz sucesso.").pack(side=LEFT)
        self.btn_gen_docs=tb.Button(actions,text="📄 Gerar PDF/Carta",bootstyle="warning-outline",command=self.generate_docs_selected); self.btn_gen_docs.pack(side=LEFT,padx=10)
        info_icon(actions,"Gera currículo otimizado + carta de apresentação pra vaga selecionada, mesmo que o\nmatch esteja abaixo do piso automático (50%) — dispara uma chamada de IA na hora.").pack(side=LEFT)
        tb.Button(actions,text="📂 Abrir PDF/Carta",bootstyle="secondary-outline",command=self.open_docs_selected).pack(side=LEFT,padx=10)

        cols=("vaga","empresa","local","match","status","outcome","plataforma")
        self._hist_col_labels={"vaga":"Vaga","empresa":"Empresa","local":"Local","match":"Match","status":"Status","outcome":"Outcome","plataforma":"Plataforma"}
        # coluna exibida -> coluna real do SQL, pra ordenação por clique no cabeçalho
        self._hist_col_to_sql={"vaga":"title","empresa":"company","local":"location","match":"match_score","status":"status","outcome":"outcome","plataforma":"platform"}
        # nenhuma coluna ordenada por padrão -> ordem natural (mais recente primeiro, por id)
        self._hist_sort_col=None; self._hist_sort_dir=None
        self.tree=tb.Treeview(f,columns=cols,show="headings",bootstyle="dark",height=14)
        for c in cols: self.tree.heading(c,command=lambda c=c:self._sort_hist_by(c))
        self.tree.column("vaga",width=240); self.tree.column("empresa",width=150); self.tree.column("local",width=120); self.tree.column("match",width=55,anchor=CENTER); self.tree.column("status",width=95,anchor=CENTER); self.tree.column("outcome",width=100,anchor=CENTER); self.tree.column("plataforma",width=85,anchor=CENTER)
        self._update_hist_headers()
        self.tree.pack(fill=BOTH,expand=True,pady=5); self.tree.bind("<Double-Button-1>",self._on_hist_dbl); self._refresh_hist()
    def _update_hist_headers(self):
        for c in self.tree["columns"]:
            label=self._hist_col_labels.get(c,c.capitalize())
            if c==self._hist_sort_col:
                label += " ▲" if self._hist_sort_dir=="asc" else " ▼"
            self.tree.heading(c,text=label)
    def _sort_hist_by(self,col):
        # ciclo de 3 estados por coluna, tipo planilha: crescente -> decrescente -> sem
        # ordenação (volta pra ordem natural por id). Clicar em outra coluna reinicia o
        # ciclo nela (crescente) e some com a setinha da coluna anterior.
        if self._hist_sort_col != col:
            self._hist_sort_col=col; self._hist_sort_dir="asc"
        elif self._hist_sort_dir=="asc":
            self._hist_sort_dir="desc"
        else:
            self._hist_sort_col=None; self._hist_sort_dir=None
        self._update_hist_headers()
        self._refresh_hist()
    def _refresh_hist(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            if not DB_PATH.exists(): return
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()

            if self._hist_sort_col:
                sql_col=self._hist_col_to_sql.get(self._hist_sort_col,"id")
                direction="ASC" if self._hist_sort_dir=="asc" else "DESC"
                order_sql=f"{sql_col} {direction}, id DESC"  # desempate estável (ex: mesmo match_score)
            else:
                order_sql="id DESC"

            cur.execute(f"SELECT id,title,company,location,match_score,status,outcome,platform FROM jobs ORDER BY {order_sql} LIMIT 300")
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
        # mesmo limite diário de ENVIOS reais que o pipeline automático respeita (main.py) -
        # o risco de softban vem da ação de automação em si (Playwright/SMTP), não de quem
        # clicou o botão, então avisa e deixa a pessoa decidir se quer estourar o limite.
        try:
            from db import count_sends_today
            from config import Config
            _daily_limit = int(self.search_cfg.get("daily_limit", Config.DAILY_LIMIT) or Config.DAILY_LIMIT)
            _sent_today = count_sends_today()
            if _daily_limit > 0 and _sent_today >= _daily_limit:
                if not messagebox.askyesno("Limite diário de envios", f"Você já enviou {_sent_today} candidatura(s) hoje (limite configurado: {_daily_limit}).\nEnviar esta mesmo assim?"):
                    return
        except Exception:
            pass
        cover_text=""
        try:
            if row["cover_letter_path"] and Path(row["cover_letter_path"]).exists():
                cover_text=Path(row["cover_letter_path"]).read_text(encoding="utf-8")
        except Exception: pass
        # apply_to_job dispara SMTP/Playwright (pode levar dezenas de segundos, com delays
        # propositais anti-softban) — rodar isso direto no callback do botão travava a janela
        # inteira até terminar. Segue o mesmo padrão de thread+after() já usado em
        # execucao.py:run_automation pra não travar o mainloop do Tkinter.
        row_dict=dict(row)
        self.btn_approve_send.config(state=DISABLED, text="Enviando…")
        def worker():
            try:
                from sender import apply_to_job
                from db import update_job_status, log_send_attempt
                status=apply_to_job(row_dict, row_dict.get("resume_pdf_path") or "", cover_text)
                log_send_attempt(job_id)
                update_job_status(job_id, status)
                def done_ok():
                    self.btn_approve_send.config(state=NORMAL, text="✔ Aprovar e Enviar (selecionada)")
                    messagebox.showinfo("Aprovar e Enviar",f"{row_dict['title']} @ {row_dict['company']} → status: {status}")
                    self._refresh_hist(); self._refresh_dashboard()
                self.after(0, done_ok)
            except Exception as e:
                def done_err():
                    self.btn_approve_send.config(state=NORMAL, text="✔ Aprovar e Enviar (selecionada)")
                    messagebox.showerror("Aprovar e Enviar",str(e))
                self.after(0, done_err)
        threading.Thread(target=worker, daemon=True).start()
    def generate_docs_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Gerar PDF/Carta","Selecione uma vaga na lista."); return
        job_id=int(sel[0])
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT * FROM jobs WHERE id=?",(job_id,)); row=cur.fetchone(); con.close()
        except Exception as e: messagebox.showerror("Gerar PDF/Carta",str(e)); return
        if not row: messagebox.showwarning("Gerar PDF/Carta","Vaga não encontrada."); return
        if not messagebox.askyesno("Gerar PDF/Carta", f"Gerar currículo otimizado + carta de apresentação pra:\n{row['title']} @ {row['company']}\n\nIsso dispara uma chamada de IA agora (mesmo com match de {row['match_score'] or 0}%). Continuar?"):
            return
        row_dict=dict(row)
        # mesma chamada de IA cara que process_job_ats() usa acima do piso automático - aqui
        # roda sem checar o piso, já que é decisão explícita do usuário, não do pipeline. Roda
        # em thread (mesmo padrão de approve_and_send_selected) pra não travar a GUI.
        self.btn_gen_docs.config(state=DISABLED, text="Gerando…")
        def worker():
            try:
                from ats_optimizer import generate_docs_for_job
                from db import update_job_status
                res=generate_docs_for_job(job_id, row_dict["title"], row_dict["company"], row_dict["description"])
                update_job_status(job_id, row_dict["status"], resume_path=res["resume_path"], cover_path=res["cover_path"])
                def done_ok():
                    self.btn_gen_docs.config(state=NORMAL, text="📄 Gerar PDF/Carta")
                    messagebox.showinfo("Gerar PDF/Carta",f"Gerado com sucesso pra {row_dict['title']} @ {row_dict['company']}.\nUse '📂 Abrir PDF/Carta' pra visualizar.")
                    self._refresh_hist()
                self.after(0, done_ok)
            except Exception as e:
                def done_err():
                    self.btn_gen_docs.config(state=NORMAL, text="📄 Gerar PDF/Carta")
                    messagebox.showerror("Gerar PDF/Carta",str(e))
                self.after(0, done_err)
        threading.Thread(target=worker, daemon=True).start()
    def open_docs_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Abrir PDF/Carta","Selecione uma vaga na lista."); return
        job_id=int(sel[0])
        try:
            import sqlite3; con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT resume_pdf_path, cover_letter_path FROM jobs WHERE id=?",(job_id,)); row=cur.fetchone(); con.close()
        except Exception as e: messagebox.showerror("Abrir PDF/Carta",str(e)); return
        if not row or not (row["resume_pdf_path"] or row["cover_letter_path"]):
            messagebox.showinfo("Abrir PDF/Carta","Essa vaga ainda não tem PDF/carta gerados. Use '📄 Gerar PDF/Carta' primeiro."); return
        opened=False
        if row["resume_pdf_path"] and Path(row["resume_pdf_path"]).exists():
            self._open_folder(row["resume_pdf_path"]); opened=True
        if row["cover_letter_path"] and Path(row["cover_letter_path"]).exists():
            self._open_folder(row["cover_letter_path"]); opened=True
        if not opened:
            messagebox.showwarning("Abrir PDF/Carta","Os caminhos salvos no banco não existem mais no disco (arquivo movido/apagado).")
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
