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

class DashboardTabMixin:
    """Aba 5 - Dashboard: metricas agregadas das candidaturas."""
    def _build_dash(self):
        f=self.tab_dash
        top=tb.Frame(f); top.pack(fill=X,pady=5)
        tb.Button(top,text="Atualizar",bootstyle="info-outline",command=self._refresh_dashboard).pack(side=RIGHT)
        self.dash_cards=tb.Frame(f); self.dash_cards.pack(fill=X,pady=5)
        # cards serão labels
        self.lbl_total=tb.Label(self.dash_cards,text="0 vagas",font=("Segoe UI",14,"bold"),bootstyle="primary"); self.lbl_total.pack(side=LEFT,padx=10)
        self.lbl_high=tb.Label(self.dash_cards,text="0 high match",font=("Segoe UI",12),bootstyle="success"); self.lbl_high.pack(side=LEFT,padx=10)
        self.lbl_today=tb.Label(self.dash_cards,text="0 hoje",font=("Segoe UI",12),bootstyle="info"); self.lbl_today.pack(side=LEFT,padx=10)
        # bars por status
        self.frame_bars=tb.Labelframe(f,text="Distribuição por status / plataforma",padding=10); self.frame_bars.pack(fill=BOTH,expand=True,pady=5)
        self.bars_text=tk.Text(self.frame_bars,height=12,bg="#1e1e1e",fg="#d0d0d0",font=("Consolas",9)); self.bars_text.pack(fill=BOTH,expand=True)
    def _refresh_dashboard(self):
        try:
            if not DB_PATH.exists(): return
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT COUNT(*) c FROM jobs"); total=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE match_score>=60"); high=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE date(created_at)=date('now')"); today=cur.fetchone()["c"]
            self.lbl_total.config(text=f"{total} vagas totais"); self.lbl_high.config(text=f"{high} match≥60%"); self.lbl_today.config(text=f"{today} hoje")
            cur.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status"); rows=cur.fetchall()
            cur.execute("SELECT platform, COUNT(*) c FROM jobs GROUP BY platform"); rows2=cur.fetchall()
            cur.execute("SELECT outcome, COUNT(*) c FROM jobs WHERE outcome IS NOT NULL AND outcome!='' GROUP BY outcome"); rows3=cur.fetchall()
            cur.execute("SELECT outcome, AVG(match_score) avg_score, COUNT(*) c FROM jobs WHERE outcome IS NOT NULL AND outcome!='' GROUP BY outcome"); rows4=cur.fetchall()
            con.close()
            txt=f"Por status:\n"
            for r in rows: txt+=f"  {r['status']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            txt+="\nPor plataforma:\n"
            for r in rows2: txt+=f"  {r['platform']:<12} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            if rows3:
                txt+="\nPor outcome (marcados manualmente):\n"
                for r in rows3: txt+=f"  {r['outcome']:<14} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            if rows4:
                # a IA realmente acerta? cruza a nota que ela deu com o resultado real da
                # candidatura (marcado manualmente na aba Histórico) — nota média alta em
                # "rejeitado"/"sem_resposta" e baixa em "entrevista"/"proposta" seria sinal de
                # que o score não está prevendo bem quem realmente avança.
                por_outcome={r["outcome"]:(r["avg_score"] or 0, r["c"]) for r in rows4}
                total_marcados=sum(c for _,c in por_outcome.values())
                txt+="\nMatch médio por outcome (a IA acerta?):\n"
                for o in OUTCOME_OPTIONS:
                    if o in por_outcome:
                        avg,c=por_outcome[o]
                        txt+=f"  {o:<14} {avg:>5.0f}%  (n={c})\n"
                if total_marcados < 5:
                    txt+=f"  (só {total_marcados} vaga(s) com outcome marcado ainda — poucos dados pra essa comparação ser confiável)\n"
            self.bars_text.delete("1.0",tk.END); self.bars_text.insert("1.0",txt)
        except Exception as e: pass

    # Histórico
