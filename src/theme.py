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
    "primary": "#E62E52",
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

_active_theme_name = "clean_tech"

def get_active_theme() -> dict:
    return THEMES[_active_theme_name]

def set_active_theme(name: str):
    global _active_theme_name
    if name in THEMES:
        _active_theme_name = name
