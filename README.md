# 🚀 JobAutoFit - Automação Inteligente de Candidaturas e Otimização ATS (100% Gratuito)

O **JobAutoFit** é uma solução completa em Python criada para automatizar a busca de vagas (LinkedIn, Gupy e APIs abertas), otimizar seu currículo para passar pelos filtros automáticos (ATS) utilizando IA gratuita, realizar o envio de candidaturas e gerar um relatório final detalhado.

---

## 📌 Funcionalidades Principais

1. **Coleta de Vagas (Gratuito):**
   * Busca vagas automaticamente na **Gupy**, **LinkedIn** e **Remotive** sem dependência de APIs pagas.
2. **Otimização ATS por IA (Custo Zero):**
   * Avalia a aderência da vaga com o seu perfil (% de Match).
   * Reorganiza e reescreve seu currículo base para destacar as palavras-chave da vaga (sem alterar a veracidade).
   * Suporta **Google Gemini (Free Tier)** ou **Ollama (IA 100% local no seu PC)**.
3. **Geração Automática de Documentos:**
   * Gera um currículo **PDF ATS-Friendly** pronto para cada vaga em `output/`.
   * Gera uma **Carta de Apresentação (Cover Letter)** personalizada por vaga.
4. **Envio / Candidatura:**
   * Envio direto por **E-mail (SMTP)** quando há e-mail de recrutador.
   * Automação via **Playwright** para navegação no LinkedIn e preenchimento na Gupy.
5. **Relatório Final Completo:**
   * Gera um arquivo **HTML** e **Markdown** ao final de cada execução contendo lista de empresas, vagas, porcentagem de match, breve descrição e links para os PDFs gerados.

---

## 🛠️ Instalação e Configuração

### 1. Requisitos
* Python 3.10+
* Playwright (opcional, para navegação visual)

### 2. Instalar Dependências
```bash
cd job_auto_fit
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar Variáveis de Ambiente (`.env`)
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Abra o `.env` e adicione sua chave de IA gratuita do Gemini (ou configure para Ollama se usar IA local).

### 4. Configurar seu Currículo Base (`curriculum_base.json`)
Copie `curriculum_base.example.json` para `curriculum_base.json` e edite com suas informações reais (experiências, formação, habilidades). A IA utilizará este arquivo como fonte da verdade.
```bash
cp curriculum_base.example.json curriculum_base.json
```
`curriculum_base.json` fica fora do git (está no `.gitignore`) — assim seus dados pessoais nunca vão parar no repositório. Prefira preencher pela GUI (aba 1 → Importar PDF/DOCX ou edição manual) e clicar em "Salvar Tudo".

---

## 🚀 Como Executar

### Execução Padrão:
```bash
python main.py
```

### Execução Personalizada por Palavras-Chave e Localização:
```bash
python main.py --keywords "Desenvolvedor Python" "Desenvolvedor Backend" --location "Brasil" --min-score 70
```

### Modo Simulação (Dry-Run):
Analisa as vagas, gera os currículos PDF e o relatório HTML sem realizar o envio real:
```bash
python main.py --dry-run
```

---

## 📊 Relatórios Gerados

Ao terminar o ciclo, o relatório completo será salvo em `reports/relatorio_YYYYMMDD_HHMMSS.html`.  
Basta dar um duplo clique no arquivo HTML para visualizar as vagas, estatísticas e acessar os PDFs gerados!
