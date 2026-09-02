# OpenCode Guide — JobAutoFit

> Cole este arquivo no chat do **OpenCode** no outro computador para o agente retomar exatamente de onde parou.

## 1) O que é
**JobAutoFit** — Automação gratuita de currículos para **Gupy + LinkedIn**:
- Coleta (Gupy API, LinkedIn guest, Remotive)
- Filtragem avançada (salário, nível, excluir/obrigatórias, PCD, inglês, idade, bloqueadas/favoritas, regime remoto/presencial/híbrido, CLT/PJ)
- Reestruturação ATS + Carta via IA **opcional** (Gemini gratuito, Ollama local, OpenAI/Claude/Groq/Custom pagos — todos opcionais, com fallback heurístico)
- Geração PDF ATS + envio SMTP/Playwright + relatório HTML/Markdown + Dashboard + Notificações (desktop/Telegram) + Agendamento + Importador PDF/DOCX
- GUI `ttkbootstrap` dark + CLI `main.py` + `.exe` standalone (PyInstaller)

## 2) Stack
- Python 3.10+ • `ttkbootstrap`, `reportlab`, `beautifulsoup4`, `requests`, `python-dotenv`, `pypdf`, `python-docx`, `plyer`, `playwright` (opcional)
- IA: `google-generativeai` (opcional) ou qualquer OpenAI-compatível
- Build: `pyinstaller` (`JobAutoFit.spec`, `build_exe.ps1`)

## 3) Estrutura
```
job_auto_fit/
├─ gui.py                # GUI principal (ttkbootstrap dark) — 6 abas
├─ main.py               # CLI orquestrador (coleta → filtros → ATS → envio → relatório)
├─ config.py             # Config + .env + search_config.json
├─ collector.py          # Gupy / LinkedIn / Remotive
├─ filters.py            # Filtros avançados (parse salário, nível, PCD, inglês, idade)
├─ ats_optimizer.py      # LLM multi-provider + heuristics + generate_ats_pdf()
├─ sender.py             # SMTP + Playwright Gupy/LinkedIn
├─ report.py             # HTML/Markdown
├─ notify.py             # plyer + Telegram
├─ importer.py           # PDF/DOCX/TXT → curriculum heuristics
├─ db.py                 # SQLite jobs.db (hash evita duplicatas, daily_limit)
├─ curriculum_base.json  # Currículo base (fonte da verdade)
├─ search_config.json    # Busca & filtros (gerado pela GUI)
├─ .env.example / .env   # Chaves (não commitado)
├─ requirements.txt
├─ JobAutoFit.spec / build_exe.ps1
├─ output/ / reports/ / dist/ / build/  # gerados, ignorados no git
└─ OPENCODE.md           # este guia
```

## 4) Como rodar (outro PC)
```powershell
git clone https://github.com/Lucas-Baumann/Job-Auto-Fit.git
cd Job-Auto-Fit
pip install -r requirements.txt
# opcional Playwright: playwright install chromium
python gui.py          # GUI dark
# ou
python main.py --dry-run --keywords "Python Developer" --location "Brasil" --min-score 60
# .exe (se dist/Commit):
.\dist\JobAutoFit.exe
```

## 5) Config
- **GUI** salva em 3 lugares: `curriculum_base.json` (perfil), `.env` (chaves SMTP/IA/LinkedIn/Gupy), `search_config.json` (filtros)
- **IA campo OPCIONAL:** `Aba 3 → Provedor IA`. Sem chave, funções com IA ficam cinza/`DISABLED` (`gui.py:_update_ai_state`) e o `ats_optimizer` usa heurístico
- **Provedores:** `gemini` (GOOGLE `aistudio.google.com`), `ollama` (`ollama.com`), `openai`/`claude`/`groq`/`custom` (URL OpenAI-compatível)
- **Tooltips ⓘ:** hover mostra resumo (SMTP, IA, filtros)
- **Importar currículo:** Aba 1 → `Importar PDF/DOCX/TXT` preenche nome/email/tel/skills (revisar e Salvar)
- **Palavras obrigatórias:** não é auto-preenchido; botão `Sugerir do currículo` preenche com suas 8 skills

## 6) Campos que usam IA (obrigatoriamente)
Apenas dentro de `ats_optimizer.py:call_llm()` → `evaluate_and_optimize_resume()`:
- Reescrita do `summary/skills` para bater ATS
- Cálculo `match_score/match_reason` + `cover_letter`
- Quando `_update_ai_state` detecta IA desabilitada, `gui.py:btn_preview_ai` e labels ficam `secondary`/cinza

## 7) PDF
- **Opcional:** se não enviar PDF, o sistema cria `output/CV_Empresa_ID.pdf` ATS-friendly
- **Se enviar:** `importer.py` extrai e auto-preenche a GUI

## 8) Estado atual (v2)
- [x] GUI dark + regime/contrato/localização condicional
- [x] Filtros avançados + daily_limit + notify + dashboard + agendamento + importer + exe
- [x] Multi-provider IA + tooltips + travar funções sem IA
- [x] `.exe` 45MB em `dist/JobAutoFit.exe` (windowed)
- [x] Git `main` pushado em `Lucas-Baumann/Job-Auto-Fit`

## 9) Próximas ideias (se pedir)
- Filtro por faixa salarial com conversão USD→BRL configurável
- Geocoding real para `max_distance_km` presencial
- Export CSV do histórico + métricas no Dashboard com gráficos
- OAuth LinkedIn/Gupy mais robusto

## 10) Para o agente OpenCode no outro PC
```
Você está no projeto JobAutoFit. Leia gui.py, config.py, filters.py, ats_optimizer.py e OPENCODE.md.
Objetivo do usuário: automatizar envio de currículos Gupy/LinkedIn com reestruturação ATS.
Restrições: gratuito primeiro, velocidade não é prioridade, relatório ao terminar, IA opcional (travar funções sem chave), tooltips ⓘ.
Stack: ttkbootstrap dark, PyInstaller.
Tarefas: manter compatibilidade .env/search_config.json/curriculum_base.json, validar com python gui.py / python main.py --dry-run, e recompilar exe se alterar GUI.
```
