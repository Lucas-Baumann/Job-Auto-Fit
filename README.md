# 🚀 JobAutoFit - Automação Inteligente de Candidaturas e Otimização ATS (100% Gratuito)

[![Build & Release](https://github.com/Lucas-Baumann/Job-Auto-Fit/actions/workflows/build.yml/badge.svg)](https://github.com/Lucas-Baumann/Job-Auto-Fit/actions/workflows/build.yml)

O **JobAutoFit** é uma solução completa em Python (GUI + CLI) criada para automatizar a busca de vagas (LinkedIn, Gupy e APIs abertas), otimizar seu currículo para passar pelos filtros automáticos (ATS) utilizando IA gratuita, realizar o envio de candidaturas e acompanhar o resultado de cada uma.

---

## 📥 Download (sem instalar Python)

Baixe o executável pronto para o seu sistema na página de [**Releases**](https://github.com/Lucas-Baumann/Job-Auto-Fit/releases/latest):

* **Windows** → `JobAutoFit_v2-windows.exe`
* **Linux** → `JobAutoFit_v2-linux` (dê `chmod +x` antes de executar)

Depois de baixar, veja a seção **"🛠️ Configuração"** mais abaixo — o executável lê `.env` e `curriculum_base.json` na mesma pasta onde ele estiver, e começa em branco se não encontrar nenhum dos dois.

---

## 📌 Funcionalidades Principais

1. **Coleta de Vagas (Gratuito):** busca automática na **Gupy**, **LinkedIn** e **Remotive**, sem dependência de APIs pagas.
2. **Otimização ATS por IA (Custo Zero):** avalia a aderência da vaga com seu perfil (% de match), reorganiza e reescreve seu currículo para destacar as palavras-chave da vaga (sem alterar a veracidade). Suporta **Gemini**, **OpenRouter** (com modelos `:free`), **Ollama** (100% local), além de OpenAI/Claude/Groq/endpoint próprio.
3. **Geração Automática de Documentos:** PDF de currículo ATS-friendly e carta de apresentação personalizada por vaga, salvos em `output/`.
4. **Envio / Candidatura:** por **e-mail (SMTP)** quando há contato do recrutador, ou automação via **Playwright** no LinkedIn/Gupy.
5. **Dashboard & Histórico:** métricas agregadas de todas as candidaturas e acompanhamento vaga a vaga, incluindo marcação manual do resultado real (entrevista, rejeitada, contratado...).
6. **Perfil GitHub automatizado:** gera e publica um README de perfil e de repositórios usando IA para analisar linguagens/estrelas/tópicos reais do seu GitHub.
7. **Relatório Final:** um arquivo HTML por execução, com lista de vagas, % de match, descrição e links para os PDFs gerados.
8. **Cache de IA:** vagas já avaliadas não são reprocessadas, economizando chamadas de IA em execuções repetidas.

---

## 🖥️ Usando pela Interface Gráfica (recomendado)

Abra `JobAutoFit_v2.exe` / `./JobAutoFit_v2-linux`, ou rode `python gui.py` a partir do código-fonte. A janela tem 7 abas:

| Aba | Para que serve |
|---|---|
| **1. Currículo** | Dados pessoais, resumo, skills, experiências e formação. Botão **"Importar PDF/DOCX/TXT"** preenche tudo automaticamente (via IA, se configurada na aba 3 — sem IA, usa um modo heurístico mais limitado). |
| **2. Busca & Filtros** | Palavras-chave, modo de trabalho, salário mínimo, nível, empresas bloqueadas/favoritas, limite diário, Telegram, agendamento — ver tabela completa na seção **"🔍 Filtros de busca"** mais abaixo. |
| **3. IA & Conexões** | Provedor de IA + chave, SMTP, token do GitHub, credenciais LinkedIn/Gupy. |
| **4. Execução** | Roda o pipeline completo (coleta → filtro → ATS → envio → relatório) com log em tempo real; permite preview do PDF antes de rodar de verdade. |
| **5. Dashboard** | Métricas agregadas: total de vagas processadas, match médio, distribuição de resultado. |
| **6. Histórico** | Lista de vagas já processadas — duplo clique pra detalhes, "Aprovar e Enviar" para candidaturas pendentes, marcação manual do resultado. |
| **7. Perfil GitHub** | Gera e publica README de perfil e de repositórios do seu GitHub. |

Clique em **"Salvar Tudo"** (rodapé) para persistir qualquer alteração.

---

## ⌨️ Usando por linha de comando (CLI)

Alternativa à GUI para quem quer automatizar via `cron`/Agendador de Tarefas, sem abrir janela:

```bash
python main.py                                                          # execução padrão
python main.py --keywords "Desenvolvedor Python" "Backend" --location "Brasil" --min-score 70
python main.py --dry-run                                                # simula sem enviar candidaturas
python main.py --enable-linkedin-posts                                  # também coleta posts de recrutadores
```

A CLI lê as mesmas configurações salvas pela GUI (`.env`, `curriculum_base.json`, `search_config.json`).

---

## 🛠️ Configuração

### 1. Requisitos (rodando do código-fonte)
* Python 3.10+
* Playwright (opcional, só necessário para automação de navegador)

### 2. Instalar dependências
```bash
cd job_auto_fit
pip install -r requirements.txt
playwright install chromium
```

### 3. Variáveis de ambiente (`.env`)
```bash
cp .env.example .env
```
Preencha pela GUI (aba 3) ou editando o arquivo diretamente. Referência completa:

| Variável | Descrição |
|---|---|
| `LLM_PROVIDER` | `gemini` \| `ollama` \| `openai` \| `claude` \| `groq` \| `openrouter` \| `custom` |
| `GEMINI_API_KEY` | Chave gratuita do [Google AI Studio](https://aistudio.google.com/apikey) |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | Chave da [OpenRouter](https://openrouter.ai/keys) — tem modelos gratuitos (sufixo `:free`) |
| `OPENAI_API_KEY` / `CLAUDE_API_KEY` / `GROQ_API_KEY` | Provedores pagos alternativos (opcional) |
| `CUSTOM_LLM_URL` / `CUSTOM_LLM_KEY` | Endpoint próprio compatível com a API da OpenAI (opcional) |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | IA rodando localmente — grátis e sem enviar dados pra fora |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Envio de candidaturas por e-mail — **ver nota abaixo** |
| `GITHUB_TOKEN` | Token *classic* do GitHub, escopo `repo` — necessário só para a aba **Perfil GitHub** publicar direto |
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | Login usado pela automação Playwright (Easy Apply / posts) |
| `GUPY_EMAIL` / `GUPY_PASSWORD` | Login usado no preenchimento automático na Gupy |

> **SMTP com Gmail:** `SMTP_PASS` não é sua senha normal — o Google bloqueia login direto de app assim. Gere uma **Senha de App** em `myaccount.google.com` → Segurança → Verificação em duas etapas → Senhas de app, e use essa senha de 16 caracteres aqui. Sem isso configurado, o app ainda funciona normalmente (só o envio por e-mail fica desativado).
>
> **GITHUB_TOKEN:** crie em `github.com/settings/tokens` (classic), marcando o escopo `repo`. Sem ele, a aba 7 gera o conteúdo dos READMEs mas não publica sozinho — você cola manualmente.

### 4. Currículo base (`curriculum_base.json`)
```bash
cp curriculum_base.example.json curriculum_base.json
```
`curriculum_base.json` fica fora do git (`.gitignore`) e nunca é incluído no executável compilado — cada instalação começa em branco. Prefira preencher pela GUI (aba 1 → Importar PDF/DOCX ou edição manual) e clicar em **"Salvar Tudo"**.

---

## 🔍 Filtros de busca (aba "Busca & Filtros")

| Campo | Padrão | O que faz |
|---|---|---|
| Palavras-chave | *Desenvolvedor Python, Python Developer* | Termos usados na busca das vagas |
| Modo de trabalho | remoto | remoto / presencial / híbrido / indiferente |
| Tipo de contrato | indiferente | CLT / PJ / indiferente |
| Match mínimo | 60% | Só processa/envia vagas com aderência ATS igual ou acima deste valor |
| Limite por fonte | 8 | Máximo de vagas coletadas por plataforma a cada execução |
| Salário mínimo | 0 (sem filtro) | Ignora vagas abaixo do valor informado |
| Nível | indiferente | Júnior / Pleno / Sênior / indiferente |
| Palavras obrigatórias / excluídas | vazio | Exige ou bloqueia vagas conforme termos na descrição |
| Empresas bloqueadas / favoritas | vazio | Nunca ou sempre priorizar certas empresas |
| Idade máxima da vaga | 0 (sem limite) | Ignora vagas publicadas há mais dias que isso |
| Somente PCD | desativado | Filtra só vagas afirmativas para PCD |
| Filtro de inglês | indiferente | Exige ou evita vagas que pedem inglês avançado |
| Limite diário | 20 | Máximo de candidaturas/dia — evita bloqueio nas plataformas |
| Envio automático | ativado | Se desativado, vagas ficam "prontas para enviar" até aprovação manual na aba Histórico |
| Posts do LinkedIn | ativado | Também coleta posts de recrutadores como fonte extra de vagas |
| Agendamento | desativado | Roda a automação sozinha em um horário fixo do dia — **a GUI precisa ficar aberta**; para rodar sem depender disso, use o Agendador de Tarefas/`cron` chamando `python main.py` diretamente (ver seção CLI) |
| Telegram Bot Token / Chat ID | vazio | Notifica cada vaga processada por Telegram — ver abaixo |

> **Telegram:** fale com [@BotFather](https://t.me/BotFather) no Telegram (comando `/newbot`) para gerar o token do bot. Para o Chat ID, envie qualquer mensagem para o bot e acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` no navegador — o campo `chat.id` aparece na resposta.

---

## 📊 Dashboard, Histórico e acompanhamento de resultado

A aba **Dashboard** mostra métricas agregadas (vagas processadas, match médio, distribuição de resultado). A aba **Histórico** lista cada vaga individualmente: duplo clique para detalhes, **"Aprovar e Enviar"** para candidaturas pendentes de revisão manual, e marcação do resultado real conforme o retorno das empresas for chegando. Todo esse histórico fica local, em `jobs.db` — nunca sai do seu computador.

---

## 🧑‍💻 Perfil GitHub (aba 7)

Gera automaticamente um README de perfil (`github.com/SEU_USUARIO/SEU_USUARIO`) e READMEs individuais de repositórios, usando IA para analisar linguagens, estrelas e tópicos reais de cada repo (com fallback heurístico caso a IA falhe ou não esteja configurada). Publicar direto no GitHub requer `GITHUB_TOKEN` com escopo `repo`; sem token, o conteúdo é gerado normalmente, só não é enviado sozinho.

---

## 📊 Relatórios Gerados

Ao terminar o ciclo, o relatório completo é salvo em `reports/relatorio_YYYYMMDD_HHMMSS.html`. Dê duplo clique no arquivo para visualizar vagas, estatísticas e acessar os PDFs gerados.

---

## 🏗️ Compilando o executável / CI

Os binários oficiais (Windows + Linux) são gerados automaticamente pelo GitHub Actions ([`.github/workflows/build.yml`](.github/workflows/build.yml)) a cada tag `vX.Y.Z`, e publicados em [Releases](https://github.com/Lucas-Baumann/Job-Auto-Fit/releases/latest). Para compilar localmente:

```bash
pip install pyinstaller
pyinstaller JobAutoFit.spec --noconfirm
```

O binário sai em `dist/`. **Importante:** `curriculum_base.json` nunca entra no build (nem no `.spec` nem no `build_exe.ps1`) — dados pessoais reais nunca ficam gravados dentro do binário distribuído.

---

## ✅ Rodando os testes

```bash
python tests/validar_projeto.py
```

Valida config, banco de dados, filtros, coleta, ATS, importador de currículo, GUI e geração de relatório de ponta a ponta, usando um banco/pasta de saída isolados (`tests/_scratch/`) — não toca no `jobs.db`/`output/` reais.

---

## 📁 Estrutura do projeto

```
job_auto_fit/
├── gui.py, main.py             # launchers finos na raiz — código real fica em src/
├── src/
│   ├── gui.py                   # interface gráfica (7 abas)
│   ├── main.py                   # pipeline CLI (coleta → filtro → ATS → envio → relatório)
│   ├── collector.py              # coleta de vagas (Gupy, LinkedIn, Remotive)
│   ├── filters.py                # filtros de busca avançados
│   ├── ats_optimizer.py          # match ATS + PDF/carta + cache de IA
│   ├── importer.py               # parser de currículo (PDF/DOCX/TXT — heurístico + IA)
│   ├── profile_generator.py      # geração/publicação de READMEs do GitHub
│   ├── notify.py                 # notificações (desktop + Telegram)
│   ├── sender.py                 # envio de candidaturas (e-mail, Playwright)
│   ├── db.py                     # SQLite (jobs.db) — histórico, cache, resultado
│   └── config.py                 # .env + resolução de paths (dev vs. .exe empacotado)
├── tests/validar_projeto.py     # suíte de validação de ponta a ponta
├── JobAutoFit.spec               # build oficial do executável (PyInstaller)
└── .github/workflows/build.yml  # CI: build Windows + Linux e release automática por tag
```

---

## 🔒 Segurança e privacidade

* `curriculum_base.json`, `.env`, `search_config.json` e `jobs.db` ficam fora do controle de versão (`.gitignore`) — seus dados pessoais nunca são commitados nem entram no executável compilado.
* Chaves de IA e tokens ficam só no seu `.env` local; os binários distribuídos não contêm nenhuma credencial embutida.
* O importador de currículo prioriza IA quando configurada; sem chave, usa um modo heurístico (regex) mais limitado — a tela de import avisa explicitamente quando isso acontece e quando algum campo não foi identificado.

---

## ⚠️ Limitações conhecidas

* O parser heurístico (sem IA) foi calibrado para currículos em PT-BR/EN com seções bem definidas; modelos muito fora do padrão podem exigir revisão manual dos campos importados.
* A coleta no LinkedIn está sujeita a bloqueios (HTTP 429/999); já existe um backoff automático, mas buscas muito frequentes ainda podem ser limitadas pela própria plataforma.
* A automação de Easy Apply/Gupy via Playwright depende da estrutura atual dessas páginas — mudanças no site podem exigir ajuste nos seletores.
