import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import Config
from theme import get_active_theme, CHART_COLORS
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, card, make_scrollable,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

class DashboardTabMixin:
    """Aba 5 - Dashboard: metricas agregadas das candidaturas.

    Reescrita (2026-09-24) trocando o antigo bloco único de texto monoespaçado com barras
    ASCII por gráficos de barra de verdade desenhados em tk.Canvas (skill de dataviz: forma
    certa pro trabalho - contagem por categoria é magnitude/identidade, pede barra colorida
    com rótulo direto, não texto). Também ganhou a seção "Vagas Recentes" pra ocupar o espaço
    vertical que sobrava vazio abaixo dos cards de distribuição (apontado pelo usuário)."""
    def _build_dash(self):
        f=self.tab_dash
        t=get_active_theme()
        # mais conteúdo agora (3 gráficos + vagas recentes) do que a versão antiga - sem
        # scroll próprio, a parte de baixo ficava cortada fora da tela no tamanho padrão da
        # janela (mesmo problema já corrigido nas outras abas).
        inner=make_scrollable(f)
        inner.pack(fill="both", expand=True)

        top=ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x", pady=(0,10))
        # ação secundária -> estilo outline (neutro), nao herda a cor de destaque - só ação
        # principal da tela (nenhuma aqui) usaria fg_color=t["primary"] cheio
        ctk.CTkButton(top, text="Atualizar", command=self._refresh_dashboard,
                      fg_color="transparent", border_width=1, border_color=t["border"],
                      text_color=t["text"], hover_color=t["card_bg"], corner_radius=8).pack(side="right")

        # cards de estatística (stat tiles) lado a lado
        self.dash_cards=ctk.CTkFrame(inner, fg_color="transparent")
        self.dash_cards.pack(fill="x", pady=(0,10))
        self.lbl_total=self._stat_tile(self.dash_cards, "0", "vagas totais", t["primary"])
        self.lbl_high=self._stat_tile(self.dash_cards, "0", "match ≥60%", t["success"])
        self.lbl_today=self._stat_tile(self.dash_cards, "0", "hoje", t["text"], last=True)

        # status e plataforma lado a lado - cada um em seu próprio gráfico de barras
        row_charts=ctk.CTkFrame(inner, fg_color="transparent")
        row_charts.pack(fill="x", pady=(0,10))
        row_charts.columnconfigure(0, weight=1); row_charts.columnconfigure(1, weight=1)
        card_status, content_status = card(row_charts, "Por Status")
        card_status.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        self.canvas_status=tk.Canvas(content_status, bg=t["card_bg"], highlightthickness=0, height=1)
        self.canvas_status.pack(fill="x")
        card_plat, content_plat = card(row_charts, "Por Plataforma")
        card_plat.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        self.canvas_plat=tk.Canvas(content_plat, bg=t["card_bg"], highlightthickness=0, height=1)
        self.canvas_plat.pack(fill="x")

        # match médio por outcome - cruza o score que a IA deu com o resultado real marcado
        # manualmente no Histórico (a IA realmente acerta quem avança?)
        self._dash_outcome_note=""
        card_outcome, content_outcome = card(inner, "Match médio por outcome (a IA acerta?)")
        card_outcome.pack(fill="x", pady=(0,10))
        self.canvas_outcome=tk.Canvas(content_outcome, bg=t["card_bg"], highlightthickness=0, height=1)
        self.canvas_outcome.pack(fill="x")
        self.lbl_outcome_note=ctk.CTkLabel(content_outcome, text="", text_color=t["text_dim"],
                                            font=ctk.CTkFont(size=10), anchor="w", justify="left")
        self.lbl_outcome_note.pack(fill="x", pady=(6,0))

        # vagas recentes - preenche o espaço vertical que sobrava vazio antes; duplo clique
        # abre a vaga (mesma ideia do duplo clique no Histórico)
        card_recent, content_recent = card(inner, "Vagas Recentes")
        card_recent.pack(fill="both", expand=True)
        self.lst_recent=tk.Listbox(content_recent, height=8, bg=t["card_bg"], fg=t["text"], borderwidth=0,
                                    highlightthickness=0, font=("Segoe UI", 10), activestyle="none",
                                    selectbackground=t["primary"], selectforeground="#ffffff")
        self.lst_recent.pack(fill="both", expand=True)
        self.lst_recent.bind("<Double-Button-1>", self._open_recent_job)
        self._recent_job_ids=[]

        # redesenha os 3 gráficos quando a largura do canvas muda (redimensionar janela) -
        # os dados ficam guardados (self._dash_*_rows), só recalcula a geometria das barras
        for cv, attr in ((self.canvas_status,"_dash_status_rows"), (self.canvas_plat,"_dash_plat_rows"),
                         (self.canvas_outcome,"_dash_outcome_rows")):
            cv.bind("<Configure>", lambda e, c=cv, a=attr: self._draw_hbars(c, getattr(self, a, [])))

    def _stat_tile(self, parent, value, label, accent_color, last=False):
        """Um card pequeno (número grande + legenda) - unidade repetida 3x no dashboard.

        O último tile não leva padx à direita: senão a linha de cards para 10px antes da
        borda direita, enquanto o card de distribuição logo abaixo vai até o fim (fill="both"
        sem padx) - as duas larguras ficavam visualmente desalinhadas."""
        t=get_active_theme()
        tile=ctk.CTkFrame(parent, fg_color=t["card_bg"], corner_radius=10, border_width=1, border_color=t["border"], bg_color=t["window_bg"])
        tile.pack(side="left", fill="x", expand=True, padx=(0,0 if last else 10))
        lbl_value=ctk.CTkLabel(tile, text=value, text_color=accent_color, font=ctk.CTkFont(size=22, weight="bold"))
        lbl_value.pack(anchor="w", padx=16, pady=(12,0))
        ctk.CTkLabel(tile, text=label, text_color=t["text_dim"]).pack(anchor="w", padx=16, pady=(0,12))
        return lbl_value

    def _draw_hbars(self, canvas, rows):
        """Gráfico de barras horizontais simples: rótulo à esquerda, barra colorida (paleta
        categórica fixa de theme.py, nunca ciclada por sorte - mesma cor sempre pra mesma
        posição), valor por extenso no fim da barra (rótulo direto em vez de eixo/legenda,
        recomendado pra poucas categorias). Redesenha do zero a cada chamada - o dataset aqui
        é pequeno (poucas categorias), redesenhar é instantâneo."""
        t=get_active_theme()
        canvas.delete("all")
        w=canvas.winfo_width()
        if w < 30:
            return  # ainda sem geometria real (1a passada do layout) - o <Configure> chama nem oq roda
        if not rows:
            canvas.configure(height=30)
            canvas.create_text(4, 15, anchor="w", text="Sem dados ainda", fill=t["text_dim"], font=("Segoe UI", 10))
            return
        bar_h, gap, pad_top = 20, 8, 6
        label_w = min(140, max(70, w//4))
        value_w = 56
        bar_area = max(20, w - label_w - value_w - 12)
        max_v = max(v for _, v in rows) or 1
        canvas.configure(height=pad_top*2 + len(rows)*(bar_h+gap) - gap)
        y = pad_top
        for i, (label, v) in enumerate(rows):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            bar_len = max(3, int(bar_area * (v / max_v)))
            canvas.create_text(4, y+bar_h/2, anchor="w", text=str(label), fill=t["text"], font=("Segoe UI", 10))
            x0 = label_w
            canvas.create_rectangle(x0, y+2, x0+bar_len, y+bar_h-2, fill=color, outline="")
            canvas.create_text(x0+bar_area+8, y+bar_h/2, anchor="w", text=str(v), fill=t["text"], font=("Segoe UI", 10, "bold"))
            y += bar_h + gap

    def _open_recent_job(self, _ev=None):
        sel=self.lst_recent.curselection()
        if not sel or sel[0] >= len(self._recent_job_ids): return
        job_id=self._recent_job_ids[sel[0]]
        try:
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT url FROM jobs WHERE id=?", (job_id,)); row=cur.fetchone(); con.close()
            if row and row["url"]: webbrowser.open(row["url"])
        except Exception: pass

    def _refresh_dashboard(self):
        try:
            if not DB_PATH.exists(): return
            import sqlite3
            con=sqlite3.connect(str(DB_PATH)); con.row_factory=sqlite3.Row; cur=con.cursor()
            cur.execute("SELECT COUNT(*) c FROM jobs"); total=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE match_score>=60"); high=cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM jobs WHERE date(created_at)=date('now')"); today=cur.fetchone()["c"]
            self.lbl_total.configure(text=str(total)); self.lbl_high.configure(text=str(high)); self.lbl_today.configure(text=str(today))
            cur.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status ORDER BY c DESC"); rows=cur.fetchall()
            cur.execute("SELECT platform, COUNT(*) c FROM jobs GROUP BY platform ORDER BY c DESC"); rows2=cur.fetchall()
            cur.execute("SELECT outcome, AVG(match_score) avg_score, COUNT(*) c FROM jobs WHERE outcome IS NOT NULL AND outcome!='' GROUP BY outcome"); rows4=cur.fetchall()
            cur.execute("SELECT id,title,company,match_score,status FROM jobs ORDER BY id DESC LIMIT 8"); recent=cur.fetchall()
            con.close()

            self._dash_status_rows=[(r["status"], r["c"]) for r in rows]
            self._dash_plat_rows=[(r["platform"], r["c"]) for r in rows2]
            # a IA realmente acerta? cruza a nota que ela deu com o resultado real da
            # candidatura (marcado manualmente na aba Histórico) — nota média alta em
            # "rejeitado"/"sem_resposta" e baixa em "entrevista"/"proposta" seria sinal de
            # que o score não está prevendo bem quem realmente avança.
            por_outcome={r["outcome"]:(round(r["avg_score"] or 0), r["c"]) for r in rows4}
            self._dash_outcome_rows=[(o, por_outcome[o][0]) for o in OUTCOME_OPTIONS if o in por_outcome]
            total_marcados=sum(c for _,c in por_outcome.values())
            if not por_outcome:
                note="Nenhuma vaga com outcome marcado ainda — marque o resultado real das candidaturas no Histórico."
            elif total_marcados < 5:
                note=f"Só {total_marcados} vaga(s) com outcome marcado ainda — poucos dados pra essa comparação ser confiável."
            else:
                note=f"{total_marcados} vaga(s) com outcome marcado."
            self.lbl_outcome_note.configure(text=note)

            self._draw_hbars(self.canvas_status, self._dash_status_rows)
            self._draw_hbars(self.canvas_plat, self._dash_plat_rows)
            self._draw_hbars(self.canvas_outcome, self._dash_outcome_rows)

            self.lst_recent.delete(0, tk.END)
            self._recent_job_ids=[]
            for r in recent:
                self._recent_job_ids.append(r["id"])
                self.lst_recent.insert(tk.END, f"  {r['match_score'] or 0:>3}%  {r['title']} @ {r['company']}  ({r['status']})")
            if not recent:
                self.lst_recent.insert(tk.END, "  Nenhuma vaga coletada ainda.")
        except Exception as e: pass

    # Histórico
