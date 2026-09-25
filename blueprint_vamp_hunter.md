# Blueprint de Remodelagem Total: Projeto VampHunter / Bloodhound

Este documento contém a especificação de design, identidade visual, conceitos de gamificação e regras de negócio para a reformulação completa do aplicativo de automação de jobhunting.

---

## 1. Identidade de Marca & Nomes Propostos

O objetivo é transformar um utilitário corporativo em uma aplicação com forte apelo visual, inspirada no universo gótico/vampiresco, sem perder a eficiência técnica.

### Opções de Nomes:
1. **VampHunter** (ou **HunterVamp**): Trocadilho com *Job Hunter*. O robô que caça vagas nas sombras da noite.
2. **Bloodhound ATS**: Focado na ideia do cão de caça que fareja o "sangue" (vagas) a quilômetros de distância.
3. **VampATS**: Fusão direta de *Vampiro* com *Applicant Tracking System* (Gupy, LinkedIn, etc.).
4. **Nightcrawler Jobs**: Remete a algo furtivo que varre a web enquanto o usuário dorme.

> **Decisão (2026-09-23):** nome escolhido foi **VampHunter**.

---

## 2. Paletas de Cores por Tema (UI Themes)

Substituir o fundo preto puro (`#000000`) e as bordas coloridas finas por designs modernos baseados em preenchimento de painéis (cards) com bordas arredondadas e suavizadas.

### 🎨 Tema 1: Corporativo Padrão (Clean Tech - Modo Padrão)
*Para o uso profissional do dia a dia, focado em sobriedade e cansaço visual reduzido.*
* **Fundo da Janela (Window Background):** `#1E222B` (Cinza-escuro azulado moderno)
* **Fundo dos Cards/Painéis (Frame Background):** `#282C34` (Cinza médio, estilo VS Code One Dark)
* **Bordas Sutis (Borders):** `#3E4452` (Cinza claro sutil)
* **Textos Principais (Labels):** `#ABB2BF` (Branco acinzentado confortável)
* **Botões de Destaque (Primary Actions):** `#4B9CD3` ou `#00A86B` (Azul corporativo ou Verde sucesso estável)

### 🎨 Tema 2: Crimson Velvet (Modo Vampiro Vamp)
* **Fundo da Janela:** `#0D080A` (Preto arroxeado profundo)
* **Fundo dos Cards/Painéis:** `#1C0F13` (Vinho escuro)
* **Bordas Sutis:** `#4A1521` (Cereja escuro)
* **Textos Principais:** `#F5EFF1` (Branco giz macio)
* **Botões de Destaque:** `#E62E52` (Vermelho carmim vivo)

### 🎨 Tema 3: Gothic Castle (Modo Vampiro Sóbrio - Estilo VS Code Dark Red)
* **Fundo da Janela:** `#121111` (Cinza carvão quase preto)
* **Fundo dos Cards/Painéis:** `#1A1818` (Cinza ligeiramente mais claro)
* **Bordas Sutis:** `#381616` (Marrom avermelhado queimado)
* **Textos Principais:** `#E0D7D7` (Branco acinzentado)
* **Botões de Destaque:** `#A31C1C` (Vermelho sangue seco)

> **Ajuste (Fase 3, 2026-09-23):** o botão de destaque do Gothic Castle foi clareado pra
> `#C23B3B` em `src/theme.py` — o `#A31C1C` original tinha contraste baixo demais contra o
> fundo quase preto (`#121111`), o botão principal não se destacava como ação primária.

---

## 3. Diretrizes Técnicas de UI & Regras de Layout (Como Codificar)

Para garantir uma visualização limpa e profissional no PC em qualquer um dos temas, a IA deve aplicar as seguintes regras de posicionamento e estrutura de widgets no código Python:

### A. Hierarquia Vertical de Inputs (Rótulos Acima dos Campos)
* **Regra:** Nunca colocar os labels na lateral esquerda dos campos de texto (isso espreme a interface). O rótulo deve ficar estruturado **logo acima** do respectivo campo de entrada.
* **Implementação Python:** Utilizar `grid(row=N, column=M)` ou empilhamento com `pack(side="top", anchor="w")`. Dentre o label e o input, aplicar um `pady=(2, 8)` para criar um espaçamento respirável.

### B. Componentização por Cards (Bordas Arredondadas)
* **Regra:** Eliminar o uso de `LabelFrame` com bordas de linhas finas e coloridas. O agrupamento de seções (Dados Pessoais, Skills, Experiências) deve ser feito criando containers/frames sólidos.
* **Implementação Python:** Usar frames com a cor de fundo do painel (`Frame Background`) e aplicar um raio de canto (`corner_radius` entre `6px` e `10px`). O contraste entre a janela e o card deve ser gerado pela diferença de cor de preenchimento, e não por linhas de contorno.

> **Nota técnica (Fase 2 - POC, 2026-09-23):** tkinter/ttkbootstrap não suporta canto
> arredondado nativo em `Frame`/`Labelframe`. Migrado pra **CustomTkinter** (`CTkFrame`,
> `corner_radius` nativo) pra viabilizar essa regra de verdade. `ttk.Treeview` (tabela) não
> tem equivalente no CustomTkinter — continua embutido dentro dos cards novos, estilizado
> via `ttk.Style()` pra combinar com a paleta. Migração é aba por aba (`src/gui_tabs/*.py`),
> não tudo de uma vez; `src/theme.py` centraliza as paletas desta seção.

### C. Gestão Visual de Botões e Alinhamento
* **Regra de Cores:** Apenas as ações principais (ex: "Iniciar Automação", "Salvar Tudo") herdam a cor de destaque brilhante (`Primary Actions`). Botões secundários (ex: "Editar", "Remover") devem usar tons neutros (cinza do tema) ou estilo *Outline* (apenas borda transparente com texto colorido).
* **Regra de Posicionamento:** Mover botões de finalização de fluxo (como "Salvar Tudo" e "Preview PDF") para o canto inferior direito da janela, respeitando o fluxo natural de leitura e conclusão de tarefas no PC.

---

## 4. Arquitetura do "Modo Vampiro Global" (Easter Eggs)

O aplicativo operará alternando dinamicamente entre os estados através de um mapeamento centralizado de propriedades.

### Gatilhos de Ativação (Triggers):
1. **O Clique no Morcego:** Um micro-ícone de morcego oculto no rodapé. Ao receber 3 cliques consecutivos, o app dispara a transição de temas e textos.
2. **Despertar Noturno (Time-based):** Se o aplicativo for iniciado entre **00:00 e 03:00 da manhã**, o modo ativa automaticamente com um banner temporário no topo.

### Mapeamento de Termos Dinâmicos (Dicionário de Interface):

| Componente na UI | Texto Padrão (Tema Corporativo) | Texto Modificado (Temas Vampiro) |
| :--- | :--- | :--- |
| **Aba 2** | Busca & Filtros | Rastrear Presas |
| **Aba 3** | IA & Conexões | Hipnose (Conexões) / Feitiço de IA |
| **Aba 6** | Histórico de Envio | Vagas Mordidas |
| **Seção** | Resumo Profissional | Grimório / Linhagem |
| **Botão Principal** | Salvar Tudo | Selar Pacto |
| **Botão Execução** | Enviar Currículo / Iniciar | Atacar Vaga / Injetar Sangue |

---

## 5. Recursos Extras de Gamificação e Feedback

* **O Botão de Sangue (Filtro Anti-Alho):** Na aba de *Skills/Competências*, se o usuário tentar digitar palavras como "Alho", "Cruz" ou "Vampiro", o app limpa o campo automaticamente e exibe um aviso customizado: `[Erro]: Ingrediente tóxico detectado para o sistema VampHunter. Acesso negado.`
* **Efeito Queimado pelo Sol (Validação de Arquivo):** Se o usuário arrastar um arquivo inválido ou corrompido para o upload de currículo, exibir a mensagem: `Este arquivo virou cinzas ao entrar em contato com a luz do dia. Use apenas PDFs protegidos pelas sombras.`
* **Farejador de Erros (Se o nome escolhido for Bloodhound):** Em caso de falha de conexão (HTTP Error) com plataformas como Gupy ou LinkedIn, exibir uma linha de log temática: `O Bloodhound perdeu o rastro de sangue desta vaga. Recalculando faro em X segundos...`

---

## 6. Status de Implementação

- ✅ **Fase 1 (Identidade)** — nome, ícone (`icon.ico` = documento com presas, `icon_taskbar.ico`
  = morcego só pra janela/barra de tarefas), splash screen, migração de dados
  (`%LOCALAPPDATA%\JobAutoFit` → `%LOCALAPPDATA%\VampHunter`).
- ✅ **Fase 2 (POC CustomTkinter)** — validado visual (cards, canto arredondado, label acima
  do campo, botão primário/outline) e empacotamento PyInstaller.
- ✅ **Fase 3 (Paleta de cores)** — `src/theme.py` criado com os 3 temas desta seção; só
  `CLEAN_TECH` ativo por enquanto (troca dinâmica fica pra Fase 5).
- ✅ **Fase 4 (Reescrita das abas)** — as 7 abas convertidas pro CustomTkinter (Dashboard como
  piloto, depois Currículo, Busca & Filtros, IA & Conexões, Execução, Histórico e Perfil
  GitHub). Treeview (Histórico/Perfil GitHub) e Progressbar indeterminate (Execução)
  continuam ttk puro, estilizados via `style_ttk()` em `gui_common.py` — CustomTkinter não
  tem equivalente nativo pra nenhum dos dois. Dashboard revisitado depois (2026-09-24): o
  antigo bloco único de texto/ASCII virou 3 gráficos de barra de verdade (tk.Canvas, paleta
  categórica fixa de `theme.CHART_COLORS`) + seção "Vagas Recentes" - resolvia o espaço vazio
  apontado pelo usuário.
- ✅ **Seletor manual de tema** (não estava no blueprint original, adicionado por pedido) —
  combobox na barra de cima (`gui.py`), chama o mesmo `_rebuild_ui()` que os gatilhos
  automáticos da Fase 5 usam. Expandido (2026-09-25) de 3 pra 9 temas cadastrados: Clean Tech
  e Daylight (normais), Gothic Castle, Nightfall, Silver Fang, Wolfsbane, Ashen Crypt, Amber
  Candlelight e Raven's Shadow (escuros, todos escolhíveis no dropdown) - Crimson Velvet
  continua de fora do dropdown, exclusivo do Modo Vampiro (easter egg). Cada um numa família
  de cor diferente (índigo/roxo, azul-prata, verde-veneno, cinza monocromático, dourado-âmbar,
  ciano-petróleo) de propósito, pra não repetir matiz. De quebra, corrigida a cor da linha que
  separa as abas (Notebook), que também estava presa num cinza fixo do ttkbootstrap antigo.
- ✅ **Fase 5 (Modo Vampiro dinâmico + easter eggs)** — os dois gatilhos da seção 4
  (tríplo-clique no morcego escondido no rodapé + "Despertar Noturno" 00h-03h), troca pro
  tema Crimson Velvet com banner temporário, dicionário de termos dinâmicos (abas 2/3/6,
  "Resumo Profissional"→"Grimório", "Salvar Tudo"→"Selar Pacto", botão de execução→"Atacar
  Vaga") via `theme.label_for()`, e os dois easter eggs fixos da seção 5 (filtro anti-alho
  nas skills, mensagem "queimado pelo sol" em arquivo de currículo corrompido). O farejador
  de erros do Bloodhound (seção 5) não se aplica - o nome escolhido foi VampHunter, não
  Bloodhound.
