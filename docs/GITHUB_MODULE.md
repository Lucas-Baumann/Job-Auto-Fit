# Módulo GitHub/Portfólio — JobAutoFit (Recursivo)

> Este módulo integra **reestruturação de perfil GitHub** ao fluxo de vagas, igual à reestruturação de currículo ATS. Todo progresso fica salvo aqui para ser recursivo.

## Objetivo
Tornar o **GitHub tão atrativo quanto o currículo** para a vaga. Recrutador avalia perfil em 30s — README bonito + pins relevantes aumentam conversão.

## Fluxo
```
[JobAutoFit coleta vaga] → [Pin Optimizer: score repo vs keywords da vaga] → [Gerar README perfil/projeto com IA] → [Preview] → [Push]
```

## Componentes
- `github_optimizer.py:12` `fetch_repos(username, token)` — lista repos ordenados por ★
- `github_optimizer.py:45` `generate_project_readme(repo, curriculum)` — tenta IA configurada (`call_llm`), fallback template sem imagem quebrada
- `github_optimizer.py:78` `score_repo_for_job(repo, keywords)` — 0-100 para sugerir pins
- **GUI nova aba 7. GitHub/Portfólio** — campo username (auto do currículo), token opcional, botão `Buscar Repos` → lista com ⭐ clicável, botão `Gerar READMEs para estrelados` → salva em `output_github/README_<repo>.md`

## Como usar (GUI)
1. Aba GitHub/Portfólio → `Usuário: Lucas-Baumann` → `Buscar Repos` (lista com ★, linguagem, estrelas)
2. Clique na linha para alternar ⭐ (amarelo = selecionado)
3. `Gerar READMEs para estrelados` → drafts em `output_github/` (sem imagem, comentado `<!-- ![Demo](docs/demo.gif) -->` — me envie fotos e eu adiciono)
4. Para perfil: `Gerar README Perfil` → `PROFILE_README_EXPERIMENTAL.md` → copiar para `Lucas-Baumann/Lucas-Baumann`

## Estrela ⭐
- Usuário estrala os repos que **quer** reestruturar (persistido em `github_selection.json`)
- Não sobrescreve o `README.md` original do repo remoto — gera draft local para revisão antes de push
- Para aplicar: copie `output_github/README_<repo>.md` → repo clonado → commit → push

## Imagens
- Deixadas **vazias/comentadas** se não houver foto, para nunca quebrar layout. Quando tiver screenshot/GIF, envie e o módulo insere `![Demo](docs/demo.gif)`

## Próximos passos
- [ ] Pin auto por vaga (ex: vaga Mobile → `done-flow` 1º)
- [ ] Validação de links/badges após geração
- [ ] Push direto via `gh` com branch

> Atualizado em 2026-08-27 — branch `main` (commit pendente). Para reverter: `git checkout main -- docs/GITHUB_MODULE.md`
