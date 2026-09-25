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

DAYLIGHT = {
    "window_bg": "#F3F4F6",
    "card_bg": "#FFFFFF",
    "border": "#D9DCE1",
    "text": "#1F2430",
    "text_dim": "#6B7280",
    "primary": "#2F6FD1",
    # success/danger próprios (não os #00A86B/#E5484D compartilhados pelos temas escuros) -
    # esses dois valores foram calibrados pra contraste contra fundo quase-preto; usados como
    # TEXTO direto sobre fundo branco (não só preenchimento de botão) ficariam com contraste
    # fraco (~3:1, abaixo do mínimo de acessibilidade de 4.5:1 pra texto normal). Versões mais
    # escuras/saturadas aqui.
    "success": "#128A3E",
    "danger": "#C81E3A",
}

THEMES = {"clean_tech": CLEAN_TECH, "crimson_velvet": CRIMSON_VELVET, "gothic_castle": GOTHIC_CASTLE, "daylight": DAYLIGHT}
# Só os temas "normais" aparecem no seletor manual (gui.py) - Crimson Velvet é exclusivo do
# Modo Vampiro (easter egg, ver toggle_vampire_mode), nunca escolhível direto no dropdown.
THEME_DISPLAY_NAMES = {"clean_tech": "Clean Tech", "gothic_castle": "Gothic Castle", "daylight": "Daylight"}

# Paleta categórica fixa pra gráficos (Dashboard) - ordem fixa, nunca ciclada/gerada (ver
# skill de dataviz: "assign categorical hues in fixed order"). Matizes bem distintos entre
# si de propósito (azul/dourado/verde-água/roxo/rosa/cinza) - não são as cores de status
# (primary/success/danger) porque aqui a cor identifica CATEGORIA (status da vaga, plataforma),
# não estado (sucesso/erro), então reciclar as cores de status confundiria os dois sentidos.
# Um único conjunto pras 3 paletas (não uma por tema) - simplificação deliberada: a cor de
# um gráfico não precisa combinar com a cor de marca do tema, só precisa ser legível contra
# fundos escuros (todos os 3 temas são escuros) e distinguível categoria a categoria.
CHART_COLORS = ["#4B9CD3", "#E0A93E", "#3EC9B0", "#9B7FE0", "#E0719B", "#8B93A1"]

# Modo Vampiro é um FLAG separado da escolha de tema, não "qualquer tema != clean_tech" como
# na primeira versão - isso fazia Gothic Castle (que é só um tema escuro sóbrio, escolhível
# manualmente) disparar os mesmos textos/easter eggs do Crimson Velvet (esse sim exclusivo do
# easter egg). Agora: _manual_theme_name é o que a pessoa escolhe no seletor (nunca
# crimson_velvet - ele nem aparece no THEME_DISPLAY_NAMES); _vampire_mode só liga/desliga via
# toggle_vampire_mode() (gatilhos da Fase 5: morcego ou madrugada) e, quando ligado, força o
# tema pra Crimson Velvet por cima da escolha manual - ao desligar, volta pro tema manual de
# antes (não reseta pra Clean Tech à força).
_manual_theme_name = "clean_tech"
_vampire_mode = False

def get_active_theme_name() -> str:
    return "crimson_velvet" if _vampire_mode else _manual_theme_name

def get_active_theme() -> dict:
    return THEMES[get_active_theme_name()]

def get_manual_theme_name() -> str:
    """O tema escolhido manualmente (seletor), sem o Modo Vampiro sobrepor - é o valor que o
    dropdown deve mostrar, mesmo com o Modo Vampiro ligado por cima."""
    return _manual_theme_name

def set_active_theme(name: str):
    """Troca do seletor manual (gui.py) - nunca aceita 'crimson_velvet' aqui, esse só entra
    via toggle_vampire_mode()."""
    global _manual_theme_name
    if name in THEMES and name != "crimson_velvet":
        _manual_theme_name = name

def is_vampire_mode() -> bool:
    return _vampire_mode

def toggle_vampire_mode():
    """Liga/desliga o Modo Vampiro (Fase 5) - só mexe no flag, não na escolha manual de tema."""
    global _vampire_mode
    _vampire_mode = not _vampire_mode

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

def apply_ctk_defaults(theme=None):
    """Faz o CTkEntry/CTkComboBox/CTkCheckBox/CTkScrollbar de todo o app seguirem a paleta
    ativa (theme.py) - descoberto testando o tema Daylight: esses widgets nunca recebem
    fg_color/text_color explícito em nenhuma aba (só CTkFrame/CTkButton/CTkLabel recebem),
    então ficavam sempre com o cinza-escuro padrão do CustomTkinter (ThemeManager), fixo
    independente do tema.py - nos temas escuros passava despercebido (cinza-escuro combinava
    por coincidência), mas no Daylight (claro) virava uma caixa escura solta no meio de um
    fundo branco. Mais simples que adicionar fg_color/text_color em cada CTkEntry de cada
    aba: sobrescreve os valores default do ThemeManager global antes de construir os
    widgets - roda no início de _build_ui()/_rebuild_ui(), então toda troca de tema já
    aplica de novo nos widgets recriados."""
    import customtkinter as ctk
    t = theme or get_active_theme()
    entry_like = {"fg_color": [t["card_bg"], t["card_bg"]], "border_color": [t["border"], t["border"]],
                  "text_color": [t["text"], t["text"]], "placeholder_text_color": [t["text_dim"], t["text_dim"]]}
    ctk.ThemeManager.theme["CTkEntry"].update(entry_like)
    ctk.ThemeManager.theme["CTkComboBox"].update({**entry_like,
        "button_color": [t["border"], t["border"]], "button_hover_color": [t["primary"], t["primary"]]})
    ctk.ThemeManager.theme["CTkCheckBox"].update({
        "fg_color": [t["primary"], t["primary"]], "border_color": [t["border"], t["border"]],
        "hover_color": [t["border"], t["border"]], "checkmark_color": ["#ffffff", "#ffffff"],
        "text_color": [t["text"], t["text"]]})
    ctk.ThemeManager.theme["CTkScrollbar"].update({
        "button_color": [t["border"], t["border"]], "button_hover_color": [t["primary"], t["primary"]]})
    # A raiz de verdade do problema (achada depurando pixel a pixel): todo widget CTk é
    # desenhado sobre um Canvas próprio, e quando não dá pra descobrir a cor real do pai (bg_
    # color) subindo a árvore - nosso caso, já que a janela raiz é um tb.Window/ttkbootstrap,
    # não um ctk.CTk de verdade - ele cai nesse default global ThemeManager.theme["CTk"]
    # ("gray14" no modo escuro, ~#242424) pra pintar o canvas por trás do conteúdo. Isso
    # sobra como cantos/linhas escuras em qualquer widget arredondado ou com borda (card(),
    # CTkLabel solto, etc.) cujo bg_color não foi passado explicitamente - sobrescrever aqui
    # cobre TODOS esses casos de uma vez, em vez de caçar cada widget um por um.
    ctk.ThemeManager.theme["CTk"]["fg_color"] = [t["window_bg"], t["window_bg"]]
