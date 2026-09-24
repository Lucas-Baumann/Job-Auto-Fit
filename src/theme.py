"""Paletas de cor do VampHunter (ver blueprint_vamp_hunter.md, seção 2). Preparado pra troca
dinâmica futura (Modo Vampiro, Fase 5) — por enquanto só CLEAN_TECH é usado, é o tema padrão
"não-vampiro" do blueprint.

Cada tema é um dict simples (não amarrado a nenhuma lib de UI específica) — CustomTkinter lê
essas cores direto como string hex, e o mesmo dict pode alimentar estilo de ttk.Treeview
(que o CustomTkinter não substitui, ver Fase 2 - POC) sem duplicar a paleta em dois lugares."""

CLEAN_TECH = {
    "window_bg": "#1E222B",
    "card_bg": "#282C34",
    "border": "#3E4452",
    "text": "#ABB2BF",
    "text_dim": "#6B7280",
    "primary": "#4B9CD3",
    "success": "#00A86B",
    "danger": "#E5484D",
}

CRIMSON_VELVET = {
    "window_bg": "#0D080A",
    "card_bg": "#1C0F13",
    "border": "#4A1521",
    "text": "#F5EFF1",
    "text_dim": "#9C8790",
    # ajustado (2026-09-24): o #E62E52 original tinha azul (B=82) alto demais pro tom de
    # verde (G=46) - puxava pra rosa/magenta em vez de vermelho-sangue. Reduzido o azul,
    # brilho mantido (mesmo contraste contra o fundo quase preto).
    "primary": "#D42A34",
    "success": "#00A86B",
    "danger": "#E5484D",
}

GOTHIC_CASTLE = {
    "window_bg": "#121111",
    "card_bg": "#1A1818",
    "border": "#381616",
    "text": "#E0D7D7",
    "text_dim": "#8C7A7A",
    # blueprint original pedia #A31C1C aqui - baixo contraste contra o fundo quase preto
    # (#121111), o botão principal não se destacava o suficiente como "ação primária".
    # Clareado mantendo a mesma família "sangue seco".
    "primary": "#C23B3B",
    "success": "#00A86B",
    "danger": "#E5484D",
}

THEMES = {"clean_tech": CLEAN_TECH, "crimson_velvet": CRIMSON_VELVET, "gothic_castle": GOTHIC_CASTLE}
THEME_DISPLAY_NAMES = {"clean_tech": "Clean Tech", "crimson_velvet": "Crimson Velvet", "gothic_castle": "Gothic Castle"}

# Paleta categórica fixa pra gráficos (Dashboard) - ordem fixa, nunca ciclada/gerada (ver
# skill de dataviz: "assign categorical hues in fixed order"). Matizes bem distintos entre
# si de propósito (azul/dourado/verde-água/roxo/rosa/cinza) - não são as cores de status
# (primary/success/danger) porque aqui a cor identifica CATEGORIA (status da vaga, plataforma),
# não estado (sucesso/erro), então reciclar as cores de status confundiria os dois sentidos.
# Um único conjunto pras 3 paletas (não uma por tema) - simplificação deliberada: a cor de
# um gráfico não precisa combinar com a cor de marca do tema, só precisa ser legível contra
# fundos escuros (todos os 3 temas são escuros) e distinguível categoria a categoria.
CHART_COLORS = ["#4B9CD3", "#E0A93E", "#3EC9B0", "#9B7FE0", "#E0719B", "#8B93A1"]

_active_theme_name = "clean_tech"

def get_active_theme() -> dict:
    return THEMES[_active_theme_name]

def get_active_theme_name() -> str:
    return _active_theme_name

def set_active_theme(name: str):
    global _active_theme_name
    if name in THEMES:
        _active_theme_name = name

def is_vampire_mode() -> bool:
    return _active_theme_name != "clean_tech"

def toggle_vampire_mode():
    """Liga/desliga o Modo Vampiro (Fase 5) - alterna pro tema Crimson Velvet (o mais
    "vampiro" dos dois temas escuros do blueprint) e volta pro Clean Tech. Gothic Castle
    fica disponível pra troca manual futura, mas não faz parte do easter egg dinâmico."""
    set_active_theme("clean_tech" if is_vampire_mode() else "crimson_velvet")

# Dicionário de termos dinâmicos (blueprint seção 4) - textos que só aparecem trocados
# quando o Modo Vampiro está ativo. label_for() é a única forma de acessar esses textos
# pra garantir que a checagem de tema não fique espalhada/duplicada pela GUI.
VAMPIRE_LABELS = {
    "tab_busca": ("2. Busca & Filtros", "2. Rastrear Presas"),
    "tab_ia": ("3. IA & Conexões", "3. Hipnose & Feitiço de IA"),
    "tab_hist": ("6. Histórico", "6. Vagas Mordidas"),
    "resumo_profissional": ("Resumo Profissional (IA reescreve mantendo contexto)", "Grimório (IA reescreve mantendo a linhagem)"),
    "salvar_tudo": ("Salvar Tudo", "Selar Pacto"),
    "iniciar_automacao": ("▶ Iniciar Automação", "🩸 Atacar Vaga"),
}

def label_for(key: str) -> str:
    normal, vamp = VAMPIRE_LABELS[key]
    return vamp if is_vampire_mode() else normal
