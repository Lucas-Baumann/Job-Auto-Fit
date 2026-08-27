# 🚀 JobAutoFit — Automação Completa (Gupy / LinkedIn / ATS) 100% Gratuito

Solução Python completa para buscar, filtrar, otimizar com IA, enviar e gerar relatório de candidaturas em Gupy, LinkedIn e Remotive.

---

## Funcionalidades
1. Coleta gratuita Gupy / LinkedIn / Remotive (`collector.py`)
2. Filtros avançados: salário, nível, excluir/obrigatórias, PCD, inglês, idade, bloqueadas, favoritos (`filters.py` + `config.py`)
3. Otimização ATS + Carta personalizada via IA opcional (gemini / openrouter / ollama / openai / claude / groq / custom) — `ats_optimizer.py`
4. Envio SMTP (e-mail direto) + Playwright (LinkedIn Easy Apply / Gupy) (`sender.py`)
5. Relatório HTML/Markdown + Dashboard com gráfico funil matplotlib (`report.py` + `gui.py` tab 5)
6. Histórico ordenável com filtro, menu contexto (abrir/copiar/diff/entrevista/excluir/nota) (`gui.py` tab 6)
7. Importar currículo PDF/DOCX/TXT e auto-preencher (`importer.py`)
8. Agendamento diário + notificações desktop (plyer) / Telegram (`notify.py`)
9. Perfil GitHub reestruturado (`github_optimizer.py`) + README bonito (`PROFILE_README_EXPERIMENTAL.md`)
10. GUI `ttkbootstrap` dark/claro (`gui.py`) + CLI `main.py` + `.exe` (`dist/JobAutoFit_v2.exe`)

---

## Instalação
```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuração
```bash
cp .env.example .env
# edite com suas chaves (opcional: GEMINI_API_KEY, OPENROUTER_API_KEY, SMTP etc)
```
Preencha `curriculum_base.json` ou importe PDF/DOCX pela GUI (`Importar PDF/DOCX/TXT`).

## Execução
```bash
python gui.py              # GUI
python main.py --dry-run   # CLI simulação
python main.py --keywords "Python Developer" --location "Brasil" --min-score 70
```

## Relatório
Ao terminar: `reports/relatorio_YYYYMMDD_HHMMSS.html` (vagas, empresa, match %, descrição resumida, links PDF, carta).

---

## Arquivos Principais
- `gui.py`: GUI 7 abas (Perfil, Busca, IA, Execução, Dashboard, Histórico, GitHub)
- `main.py`: CLI com filtros, ATS, envio, relatório
- `filters.py`: parsing salário/nível/PCD/inglês/idade/bloqueio
- `github_optimizer.py`: fetch repos + README gerador
- `docs/GITHUB_MODULE.md`: documentação recursiva do módulo
- `.gitignore`: protege `.env`, `.db`, `output/`, `reports/`, `dist/`, `build/`
- `dist/JobAutoFit_v2.exe`: executável standalone
- `PROFILE_README_EXPERIMENTAL.md`: perfil GitHub reestruturado

---

## Status
- [x] Completo: todos módulos, GUI, `.exe`, perfil, docs recursivas
- [x] `.env` sem placeholders (removido)
- [x] Logo `logo.ico` integrado no `.exe`
- [ ] Futuro: geocoding real (`max_distance_km`), gráficos `matplotlib` no Dashboard, webhook avançado

---

## Reverter / Recuperar
```bash
git log --oneline
git checkout main -- arquivo
# ou para versão anterior:
git revert <commit>
# o branch `profile-experimental` foi mesclado em `main`
```

---

## Compilar `.exe`
```powershell
pip install pyinstaller
pyinstaller JobAutoFit.spec --noconfirm --clean
```
Saída: `dist/JobAutoFit_v2.exe` (~45MB).
