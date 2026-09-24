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

class PerfilTabMixin:
    """Aba 1 - Curriculo: dados pessoais, resumo, skills, experiencias, formacao, import de PDF/DOCX/TXT."""
    def _build_perfil(self):
        f=self.tab_perfil
        t=get_active_theme()
        inner=make_scrollable(f)
        inner.pack(fill="both", expand=True)
        outer, grid = card(inner, "Dados Pessoais")
        outer.pack(fill="x", pady=(0,10))
        for c in range(2): grid.columnconfigure(c, weight=1)
        w,_=field(grid,"Nome completo",lambda p: ctk.CTkEntry(p,textvariable=self.var_name)); w.grid(row=0,column=0,columnspan=2,sticky="ew",pady=4)
        w,_=field(grid,"E-mail",lambda p: ctk.CTkEntry(p,textvariable=self.var_email)); w.grid(row=1,column=0,sticky="ew",padx=(0,8),pady=4)
        w,_=field(grid,"Telefone",lambda p: ctk.CTkEntry(p,textvariable=self.var_phone)); w.grid(row=1,column=1,sticky="ew",pady=4)
        w,_=field(grid,"Localização",lambda p: ctk.CTkEntry(p,textvariable=self.var_location)); w.grid(row=2,column=0,sticky="ew",padx=(0,8),pady=4)
        w,_=field(grid,"LinkedIn URL",lambda p: ctk.CTkEntry(p,textvariable=self.var_linkedin)); w.grid(row=2,column=1,sticky="ew",pady=4)
        w,_=field(grid,"GitHub / Portfólio",lambda p: ctk.CTkEntry(p,textvariable=self.var_github)); w.grid(row=3,column=0,sticky="ew",padx=(0,8),pady=4)
        btn_wrap=ctk.CTkFrame(grid, fg_color="transparent"); btn_wrap.grid(row=3,column=1,sticky="ews",pady=4)
        ctk.CTkButton(btn_wrap,text="Importar PDF/DOCX/TXT",fg_color="transparent",border_width=1,border_color=t["primary"],
                      text_color=t["primary"],hover_color=t["card_bg"],command=self.import_cv_file).pack(side="bottom",fill="x")

        outer, content = card(inner, "Resumo Profissional (IA reescreve mantendo contexto)")
        outer.pack(fill="x", pady=(0,10))
        self.txt_summary=tk.Text(content,height=4,wrap="word",bg=t["window_bg"],fg=t["text"],
                                  insertbackground=t["text"],borderwidth=0,highlightthickness=0)
        self.txt_summary.pack(fill="x"); self.txt_summary.insert("1.0",self.curriculum.get("summary",""))

        cols=ctk.CTkFrame(inner, fg_color="transparent"); cols.pack(fill="both",expand=True)
        for i in range(3): cols.columnconfigure(i,weight=1)
        self.card_skills, content_skills = card(cols, "Skills (ATS)")
        self.card_skills.grid(row=0,column=0,sticky="nsew",padx=(0,6))
        self.lst_skills=tk.Listbox(content_skills,height=8,bg=t["window_bg"],fg=t["text"],borderwidth=0,highlightthickness=0)
        self.lst_skills.pack(fill="both",expand=True)
        row=ctk.CTkFrame(content_skills, fg_color="transparent"); row.pack(fill="x",pady=(6,0))
        self.ent_skill=ctk.CTkEntry(row); self.ent_skill.pack(side="left",fill="x",expand=True,padx=(0,6)); self.ent_skill.bind("<Return>",lambda e:self.add_skill())
        ctk.CTkButton(row,text="+",width=32,fg_color=t["success"],hover_color=t["border"],command=self.add_skill).pack(side="left")
        ctk.CTkButton(row,text="–",width=32,fg_color="transparent",border_width=1,border_color=t["danger"],
                      text_color=t["danger"],hover_color=t["card_bg"],command=self.del_skill).pack(side="left",padx=(4,0))

        self.card_exp, content_exp = card(cols, "Experiências")
        self.card_exp.grid(row=0,column=1,sticky="nsew",padx=6)
        self.lst_exp=tk.Listbox(content_exp,height=8,bg=t["window_bg"],fg=t["text"],borderwidth=0,highlightthickness=0)
        self.lst_exp.pack(fill="both",expand=True); self.lst_exp.bind("<Double-Button-1>",lambda e:self.edit_exp())
        btns=ctk.CTkFrame(content_exp, fg_color="transparent"); btns.pack(fill="x",pady=(6,0))
        ctk.CTkButton(btns,text="Adicionar",fg_color=t["primary"],hover_color=t["border"],command=self.add_exp).pack(side="left",fill="x",expand=True,padx=(0,3))
        ctk.CTkButton(btns,text="Editar",fg_color="transparent",border_width=1,border_color=t["border"],text_color=t["text"],
                      hover_color=t["window_bg"],command=self.edit_exp).pack(side="left",fill="x",expand=True,padx=3)
        ctk.CTkButton(btns,text="Remover",fg_color="transparent",border_width=1,border_color=t["danger"],text_color=t["danger"],
                      hover_color=t["window_bg"],command=self.del_exp).pack(side="left",fill="x",expand=True,padx=(3,0))

        self.card_edu, content_edu = card(cols, "Formação")
        self.card_edu.grid(row=0,column=2,sticky="nsew",padx=(6,0))
        self.lst_edu=tk.Listbox(content_edu,height=8,bg=t["window_bg"],fg=t["text"],borderwidth=0,highlightthickness=0)
        self.lst_edu.pack(fill="both",expand=True); self.lst_edu.bind("<Double-Button-1>",lambda e:self.edit_edu())
        btns2=ctk.CTkFrame(content_edu, fg_color="transparent"); btns2.pack(fill="x",pady=(6,0))
        ctk.CTkButton(btns2,text="Adicionar",fg_color=t["primary"],hover_color=t["border"],command=self.add_edu).pack(side="left",fill="x",expand=True,padx=(0,3))
        ctk.CTkButton(btns2,text="Editar",fg_color="transparent",border_width=1,border_color=t["border"],text_color=t["text"],
                      hover_color=t["window_bg"],command=self.edit_edu).pack(side="left",fill="x",expand=True,padx=3)
        ctk.CTkButton(btns2,text="Remover",fg_color="transparent",border_width=1,border_color=t["danger"],text_color=t["danger"],
                      hover_color=t["window_bg"],command=self.del_edu).pack(side="left",fill="x",expand=True,padx=(3,0))
    def _refresh_skills_list(self):
        self.lst_skills.delete(0,tk.END)
        for s in self.curriculum.get("skills",[]): self.lst_skills.insert(tk.END,s)
    def add_skill(self):
        v=self.ent_skill.get().strip()
        if v: self.curriculum.setdefault("skills",[]).append(v); self.ent_skill.delete(0,tk.END); self._refresh_skills_list()
    def del_skill(self):
        sel=self.lst_skills.curselection()
        if sel: self.curriculum["skills"].pop(sel[0]); self._refresh_skills_list()
    def _refresh_exp_list(self):
        self.lst_exp.delete(0,tk.END)
        for e in self.curriculum.get("experiences",[]): self.lst_exp.insert(tk.END,f"{e.get('position','')} @ {e.get('company','')} ({e.get('period','')})")
    def _exp_dialog(self,data=None):
        t=get_active_theme()
        top=ctk.CTkToplevel(self); top.title("Experiência"); top.geometry("560x360"); top.transient(self); top.grab_set()
        vals=data or {"company":"","position":"","period":"","highlights":[]}
        v_company=tk.StringVar(value=vals.get("company","")); v_position=tk.StringVar(value=vals.get("position","")); v_period=tk.StringVar(value=vals.get("period",""))
        ctk.CTkLabel(top,text="Empresa").pack(anchor="w",padx=10,pady=(10,0)); ctk.CTkEntry(top,textvariable=v_company).pack(fill="x",padx=10)
        ctk.CTkLabel(top,text="Cargo").pack(anchor="w",padx=10,pady=(8,0)); ctk.CTkEntry(top,textvariable=v_position).pack(fill="x",padx=10)
        ctk.CTkLabel(top,text="Período").pack(anchor="w",padx=10,pady=(8,0)); ctk.CTkEntry(top,textvariable=v_period).pack(fill="x",padx=10)
        ctk.CTkLabel(top,text="Destaques (um por linha)").pack(anchor="w",padx=10,pady=(8,0))
        txt=tk.Text(top,height=6,bg=t["window_bg"],fg=t["text"],borderwidth=0,highlightthickness=0); txt.pack(fill="both",expand=True,padx=10); txt.insert("1.0","\n".join(vals.get("highlights",[])))
        result={}
        def ok(): result.update(company=v_company.get().strip(),position=v_position.get().strip(),period=v_period.get().strip(),highlights=[l.strip() for l in txt.get("1.0","end").splitlines() if l.strip()]); top.destroy()
        ctk.CTkButton(top,text="Salvar",fg_color=t["success"],hover_color=t["border"],command=ok).pack(pady=10); self.wait_window(top); return result if result else None
    def add_exp(self):
        d=self._exp_dialog()
        if d and d.get("company"): self.curriculum.setdefault("experiences",[]).append(d); self._refresh_exp_list()
    def edit_exp(self):
        sel=self.lst_exp.curselection()
        if not sel: return
        idx=sel[0]; d=self._exp_dialog(self.curriculum["experiences"][idx])
        if d: self.curriculum["experiences"][idx]=d; self._refresh_exp_list()
    def del_exp(self):
        sel=self.lst_exp.curselection()
        if sel: self.curriculum["experiences"].pop(sel[0]); self._refresh_exp_list()
    def _refresh_edu_list(self):
        self.lst_edu.delete(0,tk.END)
        for e in self.curriculum.get("education",[]): self.lst_edu.insert(tk.END,f"{e.get('degree','')} - {e.get('institution','')} ({e.get('year','')})")
    def _edu_dialog(self,data=None):
        t=get_active_theme()
        top=ctk.CTkToplevel(self); top.title("Formação"); top.geometry("480x220"); top.transient(self); top.grab_set()
        vals=data or {"degree":"","institution":"","year":""}; v_degree=tk.StringVar(value=vals.get("degree","")); v_inst=tk.StringVar(value=vals.get("institution","")); v_year=tk.StringVar(value=vals.get("year",""))
        ctk.CTkLabel(top,text="Curso / Título").pack(anchor="w",padx=10,pady=(10,0)); ctk.CTkEntry(top,textvariable=v_degree).pack(fill="x",padx=10)
        ctk.CTkLabel(top,text="Instituição").pack(anchor="w",padx=10,pady=(8,0)); ctk.CTkEntry(top,textvariable=v_inst).pack(fill="x",padx=10)
        ctk.CTkLabel(top,text="Ano / Período").pack(anchor="w",padx=10,pady=(8,0)); ctk.CTkEntry(top,textvariable=v_year).pack(fill="x",padx=10)
        result={}
        def ok(): result.update(degree=v_degree.get().strip(),institution=v_inst.get().strip(),year=v_year.get().strip()); top.destroy()
        ctk.CTkButton(top,text="Salvar",fg_color=t["success"],hover_color=t["border"],command=ok).pack(pady=10); self.wait_window(top); return result if result else None
    def add_edu(self):
        d=self._edu_dialog()
        if d and d.get("degree"): self.curriculum.setdefault("education",[]).append(d); self._refresh_edu_list()
    def edit_edu(self):
        sel=self.lst_edu.curselection()
        if not sel: return
        d=self._edu_dialog(self.curriculum["education"][sel[0]])
        if d: self.curriculum["education"][sel[0]]=d; self._refresh_edu_list()
    def del_edu(self):
        sel=self.lst_edu.curselection()
        if sel: self.curriculum["education"].pop(sel[0]); self._refresh_edu_list()
    def import_cv_file(self):
        p=filedialog.askopenfilename(filetypes=[("PDF/DOCX/TXT","*.pdf *.docx *.txt"),("Todos","*.*")])
        if not p: return
        try:
            # salvar IA config atual antes de verificar (usuário pode ter testado OK mas não salvado)
            try: self.save_all(silent=True)
            except: pass
            from importer import import_file_to_curriculum
            from config import Config
            # verificar IA tanto via Config (salvo) quanto via GUI vars (atual)
            has_llm_cfg = any([Config.GEMINI_API_KEY, Config.OPENAI_API_KEY, Config.CLAUDE_API_KEY, Config.GROQ_API_KEY, Config.OPENROUTER_API_KEY, Config.CUSTOM_LLM_KEY]) or Config.LLM_PROVIDER=="ollama"
            has_llm_gui = any([self.var_gemini_key.get().strip(), self.var_openai_key.get().strip(), self.var_claude_key.get().strip(), self.var_groq_key.get().strip(), self.var_openrouter_key.get().strip(), self.var_custom_key.get().strip()])
            has_llm = has_llm_cfg or has_llm_gui
            if not has_llm:
                self._log("[Import] Sem IA configurada → usando heurístico. Para melhor análise de experiências/formação, configure OpenRouter/Gemini na aba 3.")
            parsed=import_file_to_curriculum(Path(p))
            # merge personal_info (inclui location)
            for k in ["name","email","phone","linkedin","github","location"]:
                if parsed.get("personal_info",{}).get(k): self.curriculum.setdefault("personal_info",{})[k]=parsed["personal_info"][k]
            if parsed.get("skills"):
                # limpar exemplo genérico ao importar (substitui, não soma)
                generico = {"python","javascript","sql","git","apis rest"}
                atual = {s.lower() for s in self.curriculum.get("skills",[])}
                if atual == generico or len(self.curriculum.get("skills",[]))<=5:
                    self.curriculum["skills"]=parsed["skills"]
                else:
                    self.curriculum["skills"]=list(dict.fromkeys(self.curriculum.get("skills",[])+parsed["skills"]))
            if parsed.get("summary"):
                # antes só substituía se o campo estivesse vazio — mas o campo sempre tem o
                # texto padrão do curriculum_base.json de exemplo, então o resumo extraído do
                # PDF nunca aparecia (a condição nunca era vazia, e o 'elif' só fazia 'pass')
                self.txt_summary.delete("1.0",tk.END); self.txt_summary.insert("1.0",parsed["summary"])
            # experiências e formação (novo)
            if parsed.get("experiences"):
                self.curriculum["experiences"]=parsed["experiences"]
            if parsed.get("education"):
                self.curriculum["education"]=parsed["education"]
            if parsed.get("languages"):
                self.curriculum["languages"]=parsed["languages"]
            # refresh UI
            pi=self.curriculum.get("personal_info",{})
            self.var_name.set(pi.get("name","")); self.var_email.set(pi.get("email","")); self.var_phone.set(pi.get("phone","")); self.var_location.set(pi.get("location","")); self.var_linkedin.set(pi.get("linkedin","")); self.var_github.set(pi.get("github",""))
            self._refresh_skills_list(); self._refresh_exp_list(); self._refresh_edu_list()
            # mensagem com aviso sobre IA
            exp_count=len(parsed.get("experiences",[]))
            edu_count=len(parsed.get("education",[]))
            skills_count=len(parsed.get("skills",[]))
            msg=f"Importado de {Path(p).name}\nExperiências: {exp_count} | Formação: {edu_count} | Skills: {skills_count}\nRevise os campos antes de salvar."
            # avisa campo a campo quando algo veio vazio — currículos fora do formato usual
            # (outra área, outro modelo/idioma) podem escapar até da IA, e ficar em silêncio
            # nesse caso é o que gerava a sensação de "sumiu"/"bagunçou"
            faltando=[]
            if exp_count==0: faltando.append("nenhuma experiência")
            if edu_count==0: faltando.append("nenhuma formação")
            if skills_count==0: faltando.append("nenhuma habilidade")
            if faltando:
                msg+="\n\n⚠ Não foi identificada "+", ".join(faltando)+" — preencha manualmente nesta aba."
            if not has_llm:
                msg+="\n\n⚠ Sem IA configurada — análise heurística. Com IA (aba 3 → OpenRouter/Gemini) a extração de experiências/formação é 100% precisa e preenche automaticamente."
                messagebox.showwarning("Importar — IA recomendada",msg)
            elif faltando:
                messagebox.showwarning("Importar — revise os campos",msg)
            else:
                messagebox.showinfo("Importar",msg + "\n\n✓ IA usada para melhor análise.")
        except Exception as e: messagebox.showerror("Importar",str(e))
    def suggest_mandatory(self):
        skills = self.curriculum.get("skills", [])
        if not skills:
            messagebox.showwarning("Sugerir", "Adicione skills no currículo primeiro (aba Currículo).")
            return
        sug = ", ".join(skills[:8])
        self.var_mandatory.set(sug)
        self._log(f"[Sugestão] Palavras obrigatórias preenchidas: {sug}")

    # Busca avançada
