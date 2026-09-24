import json, os, sys, threading, subprocess, webbrowser, re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from config import Config
from theme import get_active_theme
from gui_common import (
    OUTCOME_OPTIONS, Tooltip, info_icon, card, style_ttk,
    BASE_DIR, CURRICULUM_PATH, ENV_PATH, ENV_EXAMPLE, SEARCH_CONFIG_PATH, DB_PATH,
    load_curriculum, save_curriculum, load_env_dict, save_env_dict, load_search_config, save_search_config,
)

class PerfilGithubTabMixin:
    """Aba 7 - Perfil GitHub: gera e publica READMEs de perfil/repositorios."""
    def _build_profile(self):
        f=self.tab_profile
        t=style_ttk()
        # antes só a seção de repositórios tinha o card arredondado (via card()) - a de cima
        # (username/token/botões/log) ficava direto no fundo da aba, sem moldura, com visual
        # destoante da de baixo. As duas agora usam o mesmo card().
        card_top, top_content = card(f, "README do Perfil")
        card_top.pack(fill="x", pady=(0,10))

        top=ctk.CTkFrame(top_content, fg_color="transparent"); top.pack(fill="x",pady=(0,8))
        ctk.CTkLabel(top,text="Username GitHub",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        ctk.CTkEntry(top,textvariable=self.var_profile_user,width=180).pack(side="left",padx=(0,10))
        ctk.CTkCheckBox(top,text="Usar IA para reescrever bio",variable=self.var_profile_use_llm).pack(side="left")
        info_icon(top,"Se ativado e IA configurada (aba 3), reescreve bio/linhas typing com seu currículo + perfil antigo. Sem IA usa heurístico.").pack(side="left")

        token_row=ctk.CTkFrame(top_content, fg_color="transparent"); token_row.pack(fill="x",pady=(0,8))
        ctk.CTkLabel(token_row,text="GitHub Token (repo scope)",text_color=t["text_dim"]).pack(side="left",padx=(0,6))
        self.ent_github_token=ctk.CTkEntry(token_row,textvariable=self.var_github_token,show="*")
        self.ent_github_token.pack(side="left",padx=(0,6),fill="x",expand=True)
        info_icon(token_row,"Crie em github.com/settings/tokens (classic) com scope 'repo' — necessário para push direto. Deixe vazio para só gerar local.").pack(side="left")
        ctk.CTkButton(token_row,text="Salvar",width=80,fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["window_bg"],command=lambda:self.save_all(silent=True)).pack(side="left",padx=(6,0))

        btns=ctk.CTkFrame(top_content, fg_color="transparent"); btns.pack(fill="x",pady=(0,8))
        ctk.CTkButton(btns,text="🔍 Analisar perfil antigo",fg_color="transparent",border_width=1,border_color=t["primary"],
                      text_color=t["primary"],hover_color=t["window_bg"],command=self.analyze_profile).pack(side="left",padx=(0,6))
        ctk.CTkButton(btns,text="✨ Gerar README Perfil",fg_color=t["success"],hover_color=t["border"],
                      command=self.generate_profile).pack(side="left",padx=6)
        ctk.CTkButton(btns,text="🚀 Gerar e Push Perfil",fg_color=t["success"],hover_color=t["border"],
                      command=self.generate_and_push_profile).pack(side="left",padx=6)
        ctk.CTkButton(btns,text="📂 Abrir output_github",fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["window_bg"],command=lambda:self._open_folder(BASE_DIR/"output_github")).pack(side="left",padx=6)
        ctk.CTkButton(btns,text="📋 Copiar workflow snake",fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["window_bg"],command=self.copy_snake_workflow).pack(side="left",padx=6)

        self.txt_profile_log=tk.Text(top_content,height=8,bg=t["card_bg"],fg=t["text"],font=("Consolas",10),
                                      wrap="word",borderwidth=0,highlightthickness=0)
        self.txt_profile_log.pack(fill="both",expand=True,pady=(0,8))
        self.txt_profile_log.insert("1.0","Pronto. Informe username e clique Analisar. O gerador usa a estética perfeita (dark tokyonight + summary-cards + snake picture) e analisa seu README antigo se existir.\n")

        ctk.CTkLabel(top_content,text="Após gerar: copie output_github/README_<user>.md → repo <user>/<user> → commit → push. Snake: copie output_github/snake.yml → <user>/<user>/.github/workflows/",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"],wraplength=1100,justify="left",anchor="w").pack(fill="x")

        # Repositórios
        card_repos, content_repos = card(f, "Repositórios — selecione com ⭐ para reformular README")
        card_repos.pack(fill="both",expand=True)
        top_repos=ctk.CTkFrame(content_repos, fg_color="transparent"); top_repos.pack(fill="x",pady=(0,8))
        ctk.CTkButton(top_repos,text="🔍 Buscar Repos do Perfil",fg_color="transparent",border_width=1,border_color=t["primary"],
                      text_color=t["primary"],hover_color=t["window_bg"],command=self.fetch_profile_repos).pack(side="left",padx=(0,6))
        ctk.CTkButton(top_repos,text="✨ Reformular Selecionados (⭐)",fg_color=t["primary"],hover_color=t["border"],
                      command=self.generate_selected_repos).pack(side="left",padx=6)
        ctk.CTkButton(top_repos,text="🚀 Push Selecionados",fg_color=t["success"],hover_color=t["border"],
                      command=self.push_selected_repos).pack(side="left",padx=6)
        ctk.CTkButton(top_repos,text="📂 Abrir saída",fg_color="transparent",border_width=1,border_color=t["border"],
                      text_color=t["text"],hover_color=t["window_bg"],command=lambda:self._open_folder(BASE_DIR/"output_github")).pack(side="left",padx=6)
        # linha própria (não inline com os botões) - com 4 botões nessa fileira, o texto
        # inline estourava a largura do card e sobrepunha a borda arredondada
        ctk.CTkLabel(content_repos,text="Clique na linha para ⭐/desmarcar • Gera README otimizado dark por projeto",
                     font=ctk.CTkFont(size=10),text_color=t["text_dim"],anchor="w").pack(fill="x",pady=(0,8))

        cols_repos=("star","repo","lang","stars","readme")
        self.tree_repos=ttk.Treeview(content_repos,columns=cols_repos,show="headings",height=7,style="Vamp.Treeview")
        for c,txt,w in [("star","⭐",30),("repo","Repositório",200),("lang","Lang",80),("stars","★",50),("readme","README?",80)]:
            self.tree_repos.heading(c,text=txt); self.tree_repos.column(c,width=w,anchor="center" if c in ("star","stars","readme") else "w")
        self.tree_repos.pack(fill="both",expand=True)
        self.tree_repos.bind("<ButtonRelease-1>", lambda e: self.after(100, self.toggle_repo_star))
        self.repos_cache=[]
        self.repos_starred=set()
        # carrega seleção persistida
        try:
            sel_path=BASE_DIR/"github_selection.json"
            if sel_path.exists(): self.repos_starred=set(json.loads(sel_path.read_text(encoding="utf-8")))
        except: pass

    def _author_name(self) -> str:
        name = self.curriculum.get("personal_info",{}).get("name","").strip()
        placeholder = name.lower() in ("", "nome completo")
        return self.var_profile_user.get().strip() if placeholder else name

    def _author_email(self) -> str:
        email = self.curriculum.get("personal_info",{}).get("email","").strip()
        if email and email.lower() != "seu@email.com" and "@" in email:
            return email
        user = self.var_profile_user.get().strip()
        return f"{user}@users.noreply.github.com" if user else "jobautofit@users.noreply.github.com"

    def analyze_profile(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        self.txt_profile_log.insert(tk.END,f"\n[Análise] Buscando {user}...\n"); self.txt_profile_log.see(tk.END); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, fetch_github_user, fetch_repos, analyze_old_readme
            old=fetch_old_readme(user)
            info=analyze_old_readme(old)
            udata=fetch_github_user(user)
            repos=fetch_repos(user)
            total_stars=sum(r.get("stargazers_count",0) for r in repos)
            self.txt_profile_log.insert(tk.END,f"  Usuário: {udata.get('name','')} | Repos: {udata.get('public_repos', len(repos))} | Seguidores: {udata.get('followers',0)} | Estrelas totais: {total_stars}\n")
            self.txt_profile_log.insert(tk.END,f"  README antigo: {info.get('status')} | len={info.get('len','0')} | issues: {info.get('issues')}\n")
            if old:
                self.txt_profile_log.insert(tk.END,f"  Preview antigo (500 chars):\n{info.get('preview','')[:500]}\n")
            else:
                self.txt_profile_log.insert(tk.END,"  Nenhum README encontrado em github.com/{user}/{user} — será criado do zero.\n")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Análise",str(e))

    def generate_profile(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Geração] Gerando README para {user} (IA={'sim' if use_llm else 'não'})...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, generate_profile_readme, write_profile_output
            old=fetch_old_readme(user)
            md, info = generate_profile_readme(user, self.curriculum, old, use_llm=use_llm)
            path=write_profile_output(user, md)
            ia_txt = "IA ✓" if info.get("llm_used") else f"heurístico — {info.get('llm_error') or 'IA desativada'}"
            self.txt_profile_log.insert(tk.END,f"  ✓ Gerado em {path} ({ia_txt})\n  Repos: {info['public_repos']} | Estrelas: {info['total_stars']} | Skillicons: {info['skillicons']}\n")
            self.txt_profile_log.insert(tk.END,"  Próximo: abra output_github, copie README_<user>.md para seu repo de perfil e snake.yml para .github/workflows/\n")
            # preview no log
            self.txt_profile_log.insert(tk.END,f"\n--- Preview (primeiras 800 chars) ---\n{md[:800]}\n")
            self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Perfil",f"README gerado em {path}\nSnake workflow em output_github/snake.yml")
            webbrowser.open((Path(path)).as_uri())
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Geração",str(e))

    def copy_snake_workflow(self):
        try:
            from pathlib import Path as _P
            src=_P(BASE_DIR/"output_github"/"snake.yml")
            if not src.exists():
                messagebox.showwarning("Snake","Gere o README primeiro (cria snake.yml)")
                return
            self.txt_profile_log.insert(tk.END,f"[Snake] Workflow em {src} — copie para https://github.com/{self.var_profile_user.get()}/{self.var_profile_user.get()}/.github/workflows/\n")
            webbrowser.open(src.as_uri())
        except Exception as e: messagebox.showerror("Snake",str(e))

    def fetch_profile_repos(self):
        user=self.var_profile_user.get().strip()
        if not user: messagebox.showwarning("Repos","Informe username"); return
        self.txt_profile_log.insert(tk.END,f"\n[Repos] Buscando repos de {user}...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_repos, fetch_repo_readme
            repos=fetch_repos(user)
            # limpa tree
            for i in self.tree_repos.get_children(): self.tree_repos.delete(i)
            self.repos_cache=repos
            for r in sorted(repos, key=lambda x: x.get("stargazers_count",0), reverse=True)[:30]:
                name=r.get("name","")
                lang=r.get("language") or "-"
                stars=r.get("stargazers_count",0)
                has_readme="sim" if fetch_repo_readme(user, name) else "não"
                star="⭐" if name in self.repos_starred else ""
                self.tree_repos.insert("", "end", values=(star, name, lang, stars, has_readme))
            self.txt_profile_log.insert(tk.END,f"  {len(repos)} repos encontrados (mostrando até 30 ordenados por ★). Clique na linha para ⭐.\n")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro repos: {e}\n"); messagebox.showerror("Repos",str(e))

    def toggle_repo_star(self):
        sel=self.tree_repos.selection()
        if not sel: return
        vals=self.tree_repos.item(sel[0],"values")
        if not vals: return
        repo=vals[1]
        if repo in self.repos_starred:
            self.repos_starred.remove(repo)
            self.tree_repos.item(sel[0], values=("", vals[1], vals[2], vals[3], vals[4]))
        else:
            self.repos_starred.add(repo)
            self.tree_repos.item(sel[0], values=("⭐", vals[1], vals[2], vals[3], vals[4]))
        # persiste
        try: (BASE_DIR/"github_selection.json").write_text(json.dumps(sorted(self.repos_starred), ensure_ascii=False, indent=2), encoding="utf-8")
        except: pass
        self.txt_profile_log.insert(tk.END,f"[⭐] {'+'+repo if repo in self.repos_starred else '-'+repo} | total ⭐: {len(self.repos_starred)}\n"); self.txt_profile_log.see(tk.END)

    def generate_selected_repos(self):
        # log imediato para feedback visual
        self.txt_profile_log.insert(tk.END, "\n[Repos] Clique detectado — iniciando...\n"); self.txt_profile_log.see(tk.END); self.update_idletasks()
        user=self.var_profile_user.get().strip()
        if not self.repos_starred:
            messagebox.showwarning("Repos","Selecione ao menos 1 repo com ⭐ (clique na linha)")
            self.txt_profile_log.insert(tk.END, "  Nenhum repo com ⭐ selecionado — clique na estrela da linha.\n"); self.txt_profile_log.see(tk.END)
            return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"[Repos] Reformulando {len(self.repos_starred)} repos ({', '.join(sorted(self.repos_starred))}) com IA={'sim' if use_llm else 'não'}...\n"); self.txt_profile_log.see(tk.END); self.update_idletasks()
        try:
            from profile_generator import fetch_repo_readme, generate_repo_readme, write_repo_output
            out_dir = BASE_DIR / "output_github"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.txt_profile_log.insert(tk.END, f"  Pasta saída: {out_dir}\n"); self.txt_profile_log.see(tk.END)
            for repo in sorted(self.repos_starred):
                self.txt_profile_log.insert(tk.END,f"  → {repo} buscando README antigo..."); self.txt_profile_log.see(tk.END); self.update_idletasks()
                old=fetch_repo_readme(user, repo)
                self.txt_profile_log.insert(tk.END, f" {'tinha' if old else 'sem'} README, gerando..."); self.txt_profile_log.see(tk.END); self.update_idletasks()
                md, info = generate_repo_readme(user, repo, self.curriculum, old, use_llm=use_llm)
                path=write_repo_output(user, repo, md)
                has = "tinha README" if info["has_old"] else "sem README"
                ia_txt = "IA ✓" if info.get("llm_used") else f"heurístico — {info.get('llm_error') or 'IA desativada'}"
                self.txt_profile_log.insert(tk.END,f" ✓ {Path(path).name} ({has}, {info['language']}, {ia_txt})\n"); self.txt_profile_log.see(tk.END)
            self.txt_profile_log.insert(tk.END, f"[Repos] Concluído — {len(self.repos_starred)} arquivos em {out_dir}\n"); self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Repos",f"{len(self.repos_starred)} READMEs gerados em output_github/README_<repo>.md\nRevise em {out_dir}")
            self._open_folder(out_dir)
        except Exception as e:
            import traceback
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n{traceback.format_exc()[:800]}\n"); self.txt_profile_log.see(tk.END); messagebox.showerror("Repos",str(e))

    def generate_and_push_profile(self):
        user=self.var_profile_user.get().strip()
        token=self.var_github_token.get().strip() or self.env.get("GITHUB_TOKEN","")
        if not user: messagebox.showwarning("Perfil","Informe username"); return
        if not token: messagebox.showwarning("Token","Informe GitHub Token (repo) para push"); return
        if not messagebox.askyesno("Push Perfil",f"Gerar README para {user}/{user} e fazer push direto?\nIsso sobrescreve o README remoto."):
            return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Perfil Push] Gerando e enviando para {user}/{user}...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_old_readme, generate_profile_readme, push_profile_readme
            old=fetch_old_readme(user)
            md, info = generate_profile_readme(user, self.curriculum, old, use_llm=use_llm)
            # salva local primeiro
            from profile_generator import write_profile_output
            write_profile_output(user, md)
            self.txt_profile_log.insert(tk.END,"  Gerado local, fazendo push...\n"); self.update_idletasks()
            msg=push_profile_readme(user, token, md, author_name=self._author_name(), author_email=self._author_email())
            self.txt_profile_log.insert(tk.END,f"  ✓ {msg} — https://github.com/{user}/{user}\n")
            messagebox.showinfo("Perfil",f"Push ok em https://github.com/{user}/{user}")
            self.txt_profile_log.see(tk.END)
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro push: {e}\n"); messagebox.showerror("Push Perfil",str(e))

    def push_selected_repos(self):
        user=self.var_profile_user.get().strip()
        token=self.var_github_token.get().strip() or self.env.get("GITHUB_TOKEN","")
        if not self.repos_starred: messagebox.showwarning("Repos","Selecione ao menos 1 repo com ⭐"); return
        if not token: messagebox.showwarning("Token","Informe GitHub Token (repo)"); return
        if not messagebox.askyesno("Push Repos",f"Fazer push de {len(self.repos_starred)} READMEs para GitHub?\nRepos: {', '.join(sorted(self.repos_starred))}"):
            return
        self.save_all(silent=True)
        use_llm=bool(self.var_profile_use_llm.get())
        self.txt_profile_log.insert(tk.END,f"\n[Repos Push] {len(self.repos_starred)} repos...\n"); self.update_idletasks()
        try:
            from profile_generator import fetch_repo_readme, generate_repo_readme, push_repo_readme
            for repo in sorted(self.repos_starred):
                self.txt_profile_log.insert(tk.END,f"  → {repo} gerando..."); self.update_idletasks()
                old=fetch_repo_readme(user, repo)
                md, info = generate_repo_readme(user, repo, self.curriculum, old, use_llm=use_llm)
                # write local
                from profile_generator import write_repo_output
                write_repo_output(user, repo, md)
                ia_txt = "IA ✓" if info.get("llm_used") else f"heurístico — {info.get('llm_error') or 'IA desativada'}"
                self.txt_profile_log.insert(tk.END,f" ({ia_txt}) push..."); self.update_idletasks()
                msg=push_repo_readme(user, repo, token, md, author_name=self._author_name(), author_email=self._author_email())
                self.txt_profile_log.insert(tk.END,f" {msg}\n"); self.txt_profile_log.see(tk.END)
            messagebox.showinfo("Repos","Push concluído! Verifique no GitHub.")
        except Exception as e:
            self.txt_profile_log.insert(tk.END,f"Erro: {e}\n"); messagebox.showerror("Push Repos",str(e))

    # Save/export
