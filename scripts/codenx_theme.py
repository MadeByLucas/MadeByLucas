"""Identidade visual CodenX compartilhada por todos os cards.

Cores medidas no main.css do codenx.com.br; geometria medida no
banner-linkedin-v7.png (grade de 76px, diagonal de (0,379) a (2256,262)).
"""

BG      = "#080808"
GRID    = "#1f1c14"
ACCENT  = "#e5cb43"
TEXT    = "#f0f0f0"
DIM     = "#a0a0a0"
FAINT   = "#555555"
BORDER  = "rgba(255,255,255,0.07)"

MONO = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'
SANS = '"Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif'

GRID_STEP = 38.0
DIAG_Y0_F, DIAG_Y1_F = 0.992, 0.686   # fracoes de altura, iguais as do banner

# paths reais do Logo - X.svg (viewBox 0 0 508 444)
LOGO_PATHS = [
    "M17.248,0l92.362,0c19.99,0 49.341,15.304 65.557,34.183l321.958,374.835c16.216,18.879 13.156,34.183 -6.835,34.183l-92.362,0c-19.99,0 -49.341,-15.304 -65.557,-34.183l-321.959,-374.835c-16.216,-18.879 -13.156,-34.183 6.835,-34.183Z",
    "M490.417,0.162l-92.323,0c-19.982,0 -49.32,15.299 -65.529,34.17l-321.822,374.698c-16.209,18.872 -13.15,34.171 6.832,34.171l92.323,0c19.982,0 49.32,-15.299 65.529,-34.171l321.823,-374.698c16.209,-18.872 13.15,-34.17 -6.832,-34.17Z",
]
LOGO_W, LOGO_H = 508.0, 444.0


def defs(uid):
    """Gradientes e clip usados pelo fundo. uid evita colisao de ids entre cards."""
    return f'''<linearGradient id="d{uid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.10"/>
      <stop offset="65%" stop-color="{ACCENT}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0.10"/>
    </linearGradient>
    <linearGradient id="p{uid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0.05"/>
    </linearGradient>
    <clipPath id="c{uid}"><rect width="{{w}}" height="{{h}}" rx="14"/></clipPath>'''


def background(w, h, uid, radius=14):
    """O banner reconstruido: base, grade, marca d'agua do X e diagonal dourada."""
    lines = []
    x = GRID_STEP
    while x < w:
        lines.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{h:.0f}"/>')
        x += GRID_STEP
    y = GRID_STEP
    while y < h:
        lines.append(f'<line x1="0" y1="{y:.0f}" x2="{w:.0f}" y2="{y:.0f}"/>')
        y += GRID_STEP
    grid = "\n      ".join(lines)

    wm_h = h * 1.15
    s = wm_h / LOGO_H
    wm_x = w * 0.93 - (LOGO_W * s) / 2
    wm_y = (h - wm_h) / 2
    wm = "\n        ".join(f'<path d="{d}"/>' for d in LOGO_PATHS)

    dy0 = h * DIAG_Y0_F
    dy1 = h * DIAG_Y1_F

    return f'''<rect width="{w:.0f}" height="{h:.0f}" fill="{BG}"/>
    <rect width="{w:.0f}" height="{h:.0f}" fill="url(#p{uid})"/>
    <g stroke="{GRID}" stroke-width="1" fill="none">
      {grid}
    </g>
    <g fill="{ACCENT}" opacity="0.055" transform="translate({wm_x:.1f},{wm_y:.1f}) scale({s:.4f})">
        {wm}
    </g>
    <line x1="0" y1="{dy0:.1f}" x2="{w:.0f}" y2="{dy1:.1f}" stroke="url(#d{uid})" stroke-width="1.4"/>'''


def frame(w, h, radius=14):
    return (f'<rect x="0.5" y="0.5" width="{w-1:.0f}" height="{h-1:.0f}" '
            f'rx="{radius}" fill="none" stroke="{BORDER}"/>')


def card(w, h, uid, body, extra_defs="", extra_style="", label=""):
    """Monta um card completo: fundo + conteudo + moldura."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{label}">
  <title>{label}</title>
  <defs>
    {defs(uid).format(w=int(w), h=int(h))}
    {extra_defs}
  </defs>
  <style>
    text {{ font-family: {SANS}; }}
    .mono {{ font-family: {MONO}; }}
    .h {{ fill: {ACCENT}; font-size: 13px; font-weight: 700; letter-spacing: 1.6px; }}
    .k {{ fill: {DIM}; font-size: 13px; }}
    .v {{ fill: {TEXT}; font-size: 15px; font-weight: 700; }}
    .s {{ fill: {FAINT}; font-size: 11px; }}
    {extra_style}
  </style>
  <g clip-path="url(#c{uid})">
    {background(w, h, uid)}
    {body}
  </g>
  {frame(w, h)}
</svg>
'''
