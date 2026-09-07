_MONO = "'IBM Plex Mono',monospace"

COLORS = {
    "bg": "#0c1220",
    "border": "#192438",
    "text": "#dce8f5",
    "muted": "#6898b8",
    "label": "#8ab8cc",
    "accent": "#1860c4",
    "warn": "#c47e0a",
    "danger": "#c42826",
    "ok": "#2aac60",
}

PLOT_LAYOUT = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["bg"],
    font_color=COLORS["text"],
    margin=dict(l=0, r=10, t=0, b=0),
)

_BADGE = {
    "open": ("#22c55e", "rgba(34,197,94,.08)"),
    "hold": ("#fbbf24", "rgba(251,191,36,.08)"),
    "closed": ("#6898b8", "rgba(104,152,184,.10)"),
    "danger": ("#ef4444", "rgba(196,40,38,.10)"),
    "default": ("#5090d8", "rgba(24,96,196,.12)"),
}


def badge(text, kind="default"):
    fg, bg = _BADGE.get(kind, _BADGE["default"])
    return (
        f'<span style="font-family:{_MONO};font-size:9px;padding:2px 8px;'
        f'background:{bg};color:{fg};border:1px solid {fg}55;'
        f'letter-spacing:.08em;border-radius:2px;">{text}</span>'
    )


def panel_header(text):
    return (
        f'<div style="font-family:{_MONO};font-size:9px;letter-spacing:.1em;'
        f'color:{COLORS["muted"]};padding:2px 0 8px;">{text}</div>'
    )


def stat_card(label, value, accent=COLORS["accent"]):
    return (
        f'<div style="background:{COLORS["bg"]};border:1px solid {COLORS["border"]};'
        f'border-top:2px solid {accent};padding:14px 16px;">'
        f'<div style="font-family:{_MONO};font-size:9px;letter-spacing:.12em;'
        f'color:{COLORS["muted"]};margin-bottom:8px;">{label}</div>'
        f'<div style="font-family:{_MONO};font-size:32px;font-weight:600;'
        f'color:{COLORS["text"]};line-height:1;">{value}</div></div>'
    )


def topbar(username, server_time):
    return (
        f'<div style="display:flex;align-items:center;gap:14px;padding:6px 2px;'
        f'border-bottom:1px solid {COLORS["border"]};margin-bottom:14px;flex-wrap:wrap;">'
        f'<span style="font-family:{_MONO};font-size:8px;letter-spacing:.14em;'
        f'color:{COLORS["danger"]};background:rgba(196,40,38,.07);'
        f'border:1px solid rgba(196,40,38,.15);padding:2px 8px;">RESTRICTED</span>'
        f'<span style="font-family:{_MONO};font-weight:600;font-size:13px;'
        f'letter-spacing:.22em;color:{COLORS["text"]};">CIS</span>'
        f'<span style="font-size:10px;color:{COLORS["label"]};">Crime Intelligence System</span>'
        f'<span style="flex:1;"></span>'
        f'<span style="font-family:{_MONO};font-size:9px;color:{COLORS["ok"]};">● SYSTEMS NOMINAL</span>'
        f'<span style="font-family:{_MONO};font-size:11px;color:{COLORS["muted"]};">{server_time}</span>'
        f'<span style="font-size:11px;color:{COLORS["muted"]};">{username}</span></div>'
    )
