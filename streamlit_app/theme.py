"""Inline-HTML snippet builders. Pure str output, no streamlit, no DOM targeting."""

_MONO = "'IBM Plex Mono',monospace"

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


def micro_label(text):
    return (
        f'<span style="font-family:{_MONO};font-size:9px;letter-spacing:.12em;'
        f'color:#8ab8cc;">{text}</span>'
    )


def panel_header(text):
    return (
        f'<div style="font-family:{_MONO};font-size:9px;letter-spacing:.1em;'
        f'color:#6898b8;padding:2px 0 8px;">{text}</div>'
    )


def stat_card(label, value, accent="#1860c4"):
    return (
        f'<div style="background:#0c1220;border:1px solid #192438;'
        f'border-top:2px solid {accent};padding:14px 16px;">'
        f'<div style="font-family:{_MONO};font-size:9px;letter-spacing:.12em;'
        f'color:#6898b8;margin-bottom:8px;">{label}</div>'
        f'<div style="font-family:{_MONO};font-size:32px;font-weight:600;'
        f'color:#dce8f5;line-height:1;">{value}</div></div>'
    )


def topbar(username, server_time):
    return (
        f'<div style="display:flex;align-items:center;gap:14px;padding:6px 2px;'
        f'border-bottom:1px solid #192438;margin-bottom:14px;flex-wrap:wrap;">'
        f'<span style="font-family:{_MONO};font-size:8px;letter-spacing:.14em;'
        f'color:#c42826;background:rgba(196,40,38,.07);'
        f'border:1px solid rgba(196,40,38,.15);padding:2px 8px;">RESTRICTED</span>'
        f'<span style="font-family:{_MONO};font-weight:600;font-size:13px;'
        f'letter-spacing:.22em;color:#dce8f5;">CIS</span>'
        f'<span style="font-size:10px;color:#8ab8cc;">Crime Intelligence System</span>'
        f'<span style="flex:1;"></span>'
        f'<span style="font-family:{_MONO};font-size:9px;color:#2aac60;">● SYSTEMS NOMINAL</span>'
        f'<span style="font-family:{_MONO};font-size:11px;color:#6898b8;">{server_time}</span>'
        f'<span style="font-size:11px;color:#6898b8;">{username}</span></div>'
    )
