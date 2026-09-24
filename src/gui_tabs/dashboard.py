import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import Config
from theme import get_active_theme
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

class DashboardTabMixin:
    """Aba 5 - Dashboard: metricas agregadas das candidaturas.

    Primeira aba convertida pro visual novo (CustomTkinter: cards com canto arredondado,
    ver blueprint_vamp_hunter.md) - as outras 6 abas ainda usam ttkbootstrap (conversão
    aba por aba, não tudo de uma vez). CTkFrame funciona embutido dentro do tb.Frame que
    gui.py cria pra cada aba (self.tab_dash) sem problema - testado na prática aqui."""
    def _build_dash(self):
        f=self.tab_dash
        t=get_active_theme()

        top=ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", pady=(0,10))
        # ação secundária -> estilo outline (neutro), nao herda a cor de destaque - só ação
        # principal da tela (nenhuma aqui) usaria fg_color=t["primary"] cheio
        ctk.CTkButton(top, text="Atualizar", command=self._refresh_dashboard,
                      fg_color="transparent", border_width=1, border_color=t["border"],
                      text_color=t["text"], hover_color=t["card_bg"], corner_radius=8).pack(side="right")

        # cards de estatística (stat tiles) lado a lado
        self.dash_cards=ctk.CTkFrame(f, fg_color="transparent")
        self.dash_cards.pack(fill="x", pady=(0,10))
        self.lbl_total=self._stat_tile(self.dash_cards, "0", "vagas totais", t["primary"])
        self.lbl_high=self._stat_tile(self.dash_cards, "0", "match ≥60%", t["success"])
        self.lbl_today=self._stat_tile(self.dash_cards, "0", "hoje", t["text"], last=True)

        # distribuição por status/plataforma
        self.frame_bars=ctk.CTkFrame(f, fg_color=t["card_bg"], corner_radius=10, border_width=1, border_color=t["border"])
        self.frame_bars.pack(fill="both", expand=True)
        ctk.CTkLabel(self.frame_bars, text="Distribuição por status / plataforma", text_color=t["text"], anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=16, pady=(14,4))
        self.bars_text=tk.Text(self.frame_bars, height=12, bg=t["card_bg"], fg=t["text"], font=("Consolas",9),
                                borderwidth=0, highlightthickness=0)
        self.bars_text.pack(fill="both", expand=True, padx=16, pady=(0,16))

    def _stat_tile(self, parent, value, label, accent_color, last=False):
        """Um card pequeno (número grande + legenda) - unidade repetida 3x no dashboard.

        O último tile não leva padx à direita: senão a linha de cards para 10px antes da
        borda direita, enquanto o card de distribuição logo abaixo vai até o fim (fill="both"
        sem padx) - as duas larguras ficavam visualmente desalinhadas."""
        t=get_active_theme()
        tile=ctk.CTkFrame(parent, fg_color=t["card_bg"], corner_radius=10, border_width=1, border_color=t["border"])
        tile.pack(side="left", fill="x", expand=True, padx=(0,0 if last else 10))
        lbl_value=ctk.CTkLabel(tile, text=value, text_color=accent_color, font=ctk.CTkFont(size=22, weight="bold"))
        lbl_value.pack(anchor="w", padx=16, pady=(12,0))
        ctk.CTkLabel(tile, text=label, text_color=t["text_dim"]).pack(anchor="w", padx=16, pady=(0,12))
        return lbl_value

    def _refresh_dashboard(self):
        try:
            if not DB_PATH.exists(): return
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT COUNT(*) c FROM jobs"); total=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE match_score>=60"); high=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE date(created_at)=date('now')"); today=cur.fetchone()["c"]
            self.lbl_total.configure(text=str(total)); self.lbl_high.configure(text=str(high)); self.lbl_today.configure(text=str(today))
            cur.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status"); rows=cur.fetchall()
            cur.execute("SELECT platform, COUNT(*) c FROM jobs GROUP BY platform"); rows2=cur.fetchall()
            cur.execute("SELECT outcome, COUNT(*) c FROM jobs WHERE outcome IS NOT NULL AND outcome!='' GROUP BY outcome"); rows3=cur.fetchall()
            cur.execute("SELECT outcome, AVG(match_score) avg_score, COUNT(*) c FROM jobs WHERE outcome IS NOT NULL AND outcome!='' GROUP BY outcome"); rows4=cur.fetchall()
            con.close()
            # largura da coluna calculada a partir do maior nome de cada seção - um valor fixo
            # (ex: "<12") quebra o alinhamento assim que aparece um nome mais comprido (foi o
            # caso de "linkedin_post", 13 chars, deslocando número e barra pra direita).
            txt=f"Por status:\n"
            w=max((len(r['status']) for r in rows), default=0)+2
            for r in rows: txt+=f"  {r['status']:<{w}} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            txt+="\nPor plataforma:\n"
            w=max((len(r['platform']) for r in rows2), default=0)+2
            for r in rows2: txt+=f"  {r['platform']:<{w}} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            if rows3:
                txt+="\nPor outcome (marcados manualmente):\n"
                w=max((len(r['outcome']) for r in rows3), default=0)+2
                for r in rows3: txt+=f"  {r['outcome']:<{w}} {r['c']:>4} {'█'*min(30,r['c'])}\n"
            if rows4:
                # a IA realmente acerta? cruza a nota que ela deu com o resultado real da
                # candidatura (marcado manualmente na aba Histórico) — nota média alta em
                # "rejeitado"/"sem_resposta" e baixa em "entrevista"/"proposta" seria sinal de
                # que o score não está prevendo bem quem realmente avança.
                por_outcome={r["outcome"]:(r["avg_score"] or 0, r["c"]) for r in rows4}
                total_marcados=sum(c for _,c in por_outcome.values())
                txt+="\nMatch médio por outcome (a IA acerta?):\n"
                w=max((len(o) for o in OUTCOME_OPTIONS if o in por_outcome), default=0)+2
                for o in OUTCOME_OPTIONS:
                    if o in por_outcome:
                        avg,c=por_outcome[o]
                        txt+=f"  {o:<{w}} {avg:>5.0f}%  (n={c})\n"
                if total_marcados < 5:
                    txt+=f"  (só {total_marcados} vaga(s) com outcome marcado ainda — poucos dados pra essa comparação ser confiável)\n"
            self.bars_text.delete("1.0",tk.END); self.bars_text.insert("1.0",txt)
        except Exception as e: pass

    # Histórico
