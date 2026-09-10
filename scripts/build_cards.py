"""Gera os cards do README nas cores da CodenX.

Layout e conjunto de informacoes espelham as secoes do GitSkins (preset
Showcase); a arte, as cores e o fundo sao proprios. Nenhuma chamada ao
GitSkins em tempo de execucao.

Uso: python scripts/build_cards.py [usuario]
Dados: API publica do GitHub + github-contributions-api.jogruber.de
As artes ASCII fixas (xmark.txt, wordmark.txt) vem de gen_ascii_art.py.
"""
import base64, datetime, io, json, os, re, sys, urllib.request
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codenx_theme import GRID, ACCENT, TEXT, DIM, FAINT, MONO, card

USER = sys.argv[1] if len(sys.argv) > 1 else "MadeByLucas"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets")

W = 860.0                       # largura de todos os cards, como no GitSkins
PANEL = "rgba(8,8,12,0.5)"      # painel interno, mesmo valor do GitSkins
LEVELS = ["#14140f", "#3b350f", "#816f1c", "#bda52d", ACCENT]

# ---------------------------------------------------------------- perfil
# Unico lugar a editar quando algo seu mudar. Numeros (repos, estrelas,
# seguidores, contribuicoes) NAO ficam aqui: vem da API do GitHub.
PERFIL = {
    "nome": "Lucas Barbosa",
    "cargo": "Fundador da CodenX",
    "local": "Monte Azul Paulista · SP, Brasil",
    "tags": ["Open Source", "Projects", "Systems"],
    "stack": ["HTML", "CSS", "JavaScript", "React", "Node.js",
              "Figma", "Photoshop", "Illustrator"],
    "links": [("GitHub", "@madebylucas", "github", "https://github.com/MadeByLucas"),
              ("Site", "codenx.com.br", "site", "https://codenx.com.br"),
              ("LinkedIn", "lucasbarbosa21", "linkedin", "https://www.linkedin.com/in/lucasbarbosa21/"),
              ("Instagram", "luczx.jpg", "instagram", "https://www.instagram.com/luczx.jpg/")],
}

# Retrato ASCII. Retrato de estudio: rosto claro, polo preta, fundo cinza com
# vinheta. O fundo e MODELADO (quadrico ajustado pela borda), nao um valor
# unico -- so assim a vinheta some e o limiar vale igual em toda a imagem.
#
# Desenhamos apenas o que e mais CLARO que o fundo. Incluir o lado escuro
# traria a polo preta, mas junto vem a textura do fundo, e o rosto perde
# definicao; enquadrar o busto inteiro tambem encolhe demais a cabeca.
ASCII_CHARS = " .`:!+*csS#%@"
ASCII_FLOOR, ASCII_GAMMA = 0.28, 0.9
ASCII_SRC = "portrait-src.png"           # foto de estudio versionada no repo
ASCII_REF_W = 1122                       # largura original em que o recorte foi medido
ASCII_CROP = (320, 200, 802, 646)        # cabeca e ombros, bem enquadrados
GRID_COLS, GRID_ROWS = 80, 40            # grade compartilhada pelo retrato e pelo X


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "codenx-cards"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def read_art(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return []
    return io.open(p, encoding="utf-8").read().rstrip("\n").split("\n")


def fetch():
    user = get("https://api.github.com/users/%s" % USER)
    repos = [r for r in get("https://api.github.com/users/%s/repos?per_page=100&sort=pushed" % USER)
             if not r["fork"] and r["name"].lower() != USER.lower()]
    langs = {}
    for r in repos:
        try:
            for name, b in get(r["languages_url"]).items():
                langs[name] = langs.get(name, 0) + b
        except Exception:
            pass
    contrib = get("https://github-contributions-api.jogruber.de/v4/%s?y=last" % USER)
    return user, repos, langs, contrib, contagens()


def contagens():
    """PRs, issues e commits: a API de usuario nao traz esses numeros, so a
    busca. Se a busca falhar (limite de requisicoes), o card simplesmente
    nao mostra as caixas correspondentes."""
    base = "https://api.github.com/search/%s?q=author:%s%s&per_page=1"
    out = {}
    for chave, rota, extra in (("commits", "commits", ""),
                               ("prs", "issues", "+type:pr"),
                               ("issues", "issues", "+type:issue")):
        try:
            out[chave] = get(base % (rota, USER, extra))["total_count"]
        except Exception:
            pass
    return out


def streaks(days):
    today = datetime.date.today().isoformat()
    best = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        best = max(best, run)
    i = len(days) - 1
    while i >= 0 and days[i]["date"] > today:
        i -= 1
    if i >= 0 and days[i]["count"] == 0:   # hoje ainda pode estar vazio
        i -= 1
    cur = 0
    while i >= 0 and days[i]["count"] > 0:
        cur += 1
        i -= 1
    return cur, best


def num(n):
    return ("%.1fk" % (n / 1000)).replace(".0k", "k") if n >= 1000 else str(n)


def panel(x, y, w, h, rx=20):
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s"/>'
            % (x, y, w, h, rx, PANEL, GRID))


def modelo_fundo(px, cols, rows):
    """Ajusta um quadrico a borda da imagem para cancelar a vinheta do estudio.

    Devolve f(x, y) com o nivel de fundo esperado em cada celula. Um valor
    unico nao serve: o fundo do estudio e bem mais claro no centro que nos
    cantos, e a diferenca e da mesma ordem que a do sujeito.
    """
    def base(u, v):
        return (1.0, u, v, u * u, v * v, u * v)

    n = 6
    A = [[0.0] * (n + 1) for _ in range(n)]
    for y in range(rows):
        for x in range(cols):
            if not (x < 3 or x >= cols - 3 or y < 2 or y >= rows - 2):
                continue
            b = base(x / float(cols), y / float(rows))
            z = px[y * cols + x]
            for i in range(n):
                for j in range(n):
                    A[i][j] += b[i] * b[j]
                A[i][n] += b[i] * z
    for i in range(n):                                   # eliminacao de Gauss
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        if abs(A[i][i]) < 1e-9:
            return lambda x, y: sum(px) / float(len(px))
        for r in range(i + 1, n):
            f = A[r][i] / A[i][i]
            for c in range(i, n + 1):
                A[r][c] -= f * A[i][c]
    coef = [0.0] * n
    for i in range(n - 1, -1, -1):
        coef[i] = (A[i][n] - sum(A[i][j] * coef[j] for j in range(i + 1, n))) / A[i][i]
    return lambda x, y: sum(c * b for c, b in zip(coef, base(x / float(cols), y / float(rows))))


def ascii_portrait(avatar_url, cols, rows):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return []
    local = os.path.join(HERE, ASCII_SRC)
    if os.path.exists(local):
        img = Image.open(local).convert("L")
    else:                                    # sem a foto versionada, cai no avatar
        req = urllib.request.Request(avatar_url, headers={"User-Agent": "codenx-cards"})
        with urllib.request.urlopen(req, timeout=30) as r:
            img = Image.open(io.BytesIO(r.read())).convert("L")
    # recorta na resolucao do arquivo e so depois reduz: reduzir antes perde detalhe
    k = img.size[0] / float(ASCII_REF_W)
    img = ImageOps.autocontrast(img.crop(tuple(int(v * k) for v in ASCII_CROP)), cutoff=0.5)
    px = list(img.resize((cols, rows), Image.LANCZOS).getdata())
    fundo = modelo_fundo(px, cols, rows)
    dev = [px[y * cols + x] - fundo(x, y) for y in range(rows) for x in range(cols)]
    claro = max(1.0, max(dev))
    out = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            v = dev[y * cols + x] / claro          # so o que e mais claro que o fundo
            if v < ASCII_FLOOR:
                line += " "
            else:
                t = min(1.0, (v - ASCII_FLOOR) / (1 - ASCII_FLOOR)) ** ASCII_GAMMA
                line += ASCII_CHARS[min(len(ASCII_CHARS) - 1, int(t * (len(ASCII_CHARS) - 1) + 0.5))]
        out.append(line if line.strip() else "")
    # sem aparar linhas: o retrato e o X dividem a mesma grade, entao
    # precisam ocupar exatamente a mesma caixa para a troca ficar alinhada
    return out


def ascii_block(rows, cls, x, y, cw, lh, fs, cols, stagger=0.035):
    out = []
    for i, line in enumerate(rows):
        if not line.strip():
            continue
        out.append('<text class="%s mono" x="%.1f" y="%.1f" textLength="%.1f" lengthAdjust="spacingAndGlyphs" '
                   'style="font-size:%spx;animation-delay:%.2fs" xml:space="preserve">%s</text>'
                   % (cls, x, y + i * lh, cols * cw, fs, i * stagger, escape(line.ljust(cols))))
    return "\n    ".join(out)


# ------------------------------------------------------------------ cards

def card_hero(user, repos, contrib):
    """Cartao de identidade: avatar, nome, bio e etiquetas -- com animacao."""
    H = 260.0
    bio = (user.get("bio") or "").strip()
    try:
        from PIL import Image, ImageDraw
        req = urllib.request.Request(user["avatar_url"], headers={"User-Agent": "codenx-cards"})
        with urllib.request.urlopen(req, timeout=30) as r:
            im = Image.open(io.BytesIO(r.read())).convert("RGB").resize((228, 228), Image.LANCZOS)
        mask = Image.new("L", (228, 228), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 227, 227), fill=255)
        im.putalpha(mask)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        avatar = ('<image x="56" y="69" width="114" height="114" href="data:image/png;base64,%s"/>'
                  % base64.b64encode(buf.getvalue()).decode())
    except Exception:
        avatar = ""

    XT = 196.0                       # coluna do texto, ao lado do avatar
    body = [panel(26, 26, W - 52, H - 52, 18),
            '<circle class="anel" cx="113" cy="126" r="60" fill="none" stroke="%s" stroke-width="1.8"/>' % ACCENT,
            '<circle cx="113" cy="126" r="66" fill="none" stroke="%s" stroke-opacity="0.14"/>' % ACCENT,
            avatar,
            '<g class="orbe">'
            '<circle cx="740" cy="126" r="52" fill="none" stroke="%s" stroke-opacity="0.18"/>'
            '<circle cx="740" cy="126" r="34" fill="none" stroke="%s" stroke-opacity="0.10"/>'
            '<circle cx="740" cy="126" r="4" fill="%s" opacity="0.7"/></g>' % (ACCENT, ACCENT, ACCENT),
            '<text class="ent mono" x="%.0f" y="86" style="font-size:14px;font-weight:700;fill:%s;'
            'animation-delay:.05s">@%s</text>' % (XT + 2, ACCENT, USER.lower()),
            '<text class="ent" x="%.0f" y="136" style="font-size:40px;font-weight:800;fill:%s;'
            'animation-delay:.15s">%s</text>' % (XT, TEXT, escape(PERFIL["nome"])),
            '<text class="ent k" x="%.0f" y="164" style="font-size:13px;animation-delay:.25s">%s</text>'
            % (XT + 2, escape(bio))]
    x = XT + 2
    for i, t in enumerate(PERFIL["tags"]):
        w = 34 + len(t) * 7.4
        body.append('<g class="ent" style="animation-delay:%.2fs">'
                    '<rect x="%.1f" y="176" width="%.1f" height="30" rx="15" fill="%s" opacity="0.08"/>'
                    '<rect x="%.1f" y="176" width="%.1f" height="30" rx="15" fill="none" stroke="%s" stroke-opacity="0.32"/>'
                    '<text class="mono" text-anchor="middle" x="%.1f" y="195.5" style="font-size:11.5px;fill:%s">%s</text>'
                    '</g>' % (0.35 + i * 0.08, x, w, ACCENT, x, w, ACCENT, x + w / 2, ACCENT, escape(t)))
        x += w + 14
    style = """
    .ent { animation: entra .9s cubic-bezier(.22,1,.36,1) both; }
    .anel { animation: pulso 3.4s ease-in-out infinite; transform-origin: 113px 126px; }
    .orbe { animation: respira 5s ease-in-out infinite; transform-origin: 740px 126px; }
    @keyframes entra  { from { opacity: 0; transform: translateX(-14px) } to { opacity: 1; transform: none } }
    @keyframes pulso  { 0%,100% { opacity: .45; transform: scale(1) } 50% { opacity: 1; transform: scale(1.035) } }
    @keyframes respira{ 0%,100% { opacity: .55 } 50% { opacity: 1 } }
    @media (prefers-reduced-motion: reduce) {
      .ent, .anel, .orbe { animation: none }
    }"""
    return card(W, H, "hr", ("%s    " % chr(10)).join(body), extra_style=style,
                label="%s - %s" % (PERFIL["nome"], PERFIL["cargo"]))


def card_highlights(user, repos):
    H = 180.0
    items = [("Open Source", "%d repositórios públicos" % user["public_repos"]),
             ("Impacto", "%d estrelas recebidas" % sum(r["stargazers_count"] for r in repos)),
             ("Comunidade", "%d seguidores" % user["followers"])]
    body = ['<text class="h" x="30" y="44">DESTAQUES</text>']
    for i, (t, s) in enumerate(items):
        x = 28 + i * 273
        body.append('<rect x="%d" y="60" width="257" height="96" rx="16" fill="%s" stroke="%s"/>' % (x, PANEL, GRID))
        body.append('<rect x="%d" y="82" width="4" height="52" rx="2" fill="%s" opacity="%.2f"/>' % (x, ACCENT, 1 - i * 0.22))
        body.append('<text x="%d" y="98" style="font-size:16px;font-weight:700;fill:%s">%s</text>' % (x + 24, TEXT, t))
        body.append('<text class="k" x="%d" y="122" style="font-size:12.5px">%s</text>' % (x + 24, s))
    return card(W, H, "hl", "\n    ".join(body), label="Destaques do perfil")


def card_heatmap(contrib):
    """Calendario do ano com a cobrinha percorrendo e comendo os quadrados."""
    days = contrib["contributions"]
    CELL, GAP = 11.0, 2.6
    STEP = CELL + GAP
    weeks = (len(days) + 6) // 7
    LABEL_W = 30.0                       # faixa dos dias da semana, a esquerda
    grade_w = weeks * STEP - GAP
    X0 = (W - (LABEL_W + grade_w)) / 2 + LABEL_W
    Y0 = 112.0
    H = 236.0

    order = []
    for c in range(weeks):
        for r in (range(7) if c % 2 == 0 else range(6, -1, -1)):
            order.append((c, r))
    pos = dict((cr, k) for k, cr in enumerate(order))
    N, T = len(order), 22.0
    sd = T / N

    cells = []
    for i, d in enumerate(days):
        c, r = divmod(i, 7)
        cells.append('<rect class="cell" x="%.1f" y="%.1f" width="%s" height="%s" rx="2.5" fill="%s" style="animation-delay:%.3fs"/>'
                     % (X0 + c * STEP, Y0 + r * STEP, CELL, CELL, LEVELS[d["level"]], pos[(c, r)] * sd))
    stops = "".join("%.3f%%{transform:translate(%.1fpx,%.1fpx)}"
                    % (k / (N - 1) * 100, X0 + c * STEP, Y0 + r * STEP)
                    for k, (c, r) in enumerate(order))

    # Segmentos do tamanho do PASSO (nao da celula) para cobrir o vao entre
    # elas: e isso que faz o corpo parecer continuo em vez de picotado.
    snake = []
    for i in range(9):
        cabeca = i == 0
        sz = STEP + (1.6 if cabeca else 0.0)
        off = (CELL - sz) / 2.0
        snake.append('<rect class="seg" x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.1f" '
                     'fill="%s" opacity="%.2f" style="animation-delay:%.3fs"/>'
                     % (off, off, sz, sz, 4.5 if cabeca else 3.2, ACCENT,
                        1.0 if cabeca else 0.92 - i * 0.07, i * sd))

    leg = ['<text class="s" x="642" y="72">menos</text>']
    for i, col in enumerate(LEVELS):
        leg.append('<rect x="%d" y="62" width="%s" height="%s" rx="2.5" fill="%s"/>' % (686 + i * 15, CELL, CELL, col))
    leg.append('<text class="s" x="764" y="72">mais</text>')

    MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]
    marcas, ultimo, ultimo_x = [], None, -99.0
    for c in range(weeks - 1):
        if c * 7 >= len(days):
            break
        m = int(days[c * 7]["date"][5:7])
        x = X0 + c * STEP
        if m != ultimo:
            ultimo = m
            if x - ultimo_x >= 26:            # evita rotulos colados
                marcas.append('<text class="s" x="%.1f" y="%.0f" style="font-size:10px">%s</text>'
                              % (x, Y0 - 7, MESES[m - 1]))
                ultimo_x = x

    semana = ['<text class="s" text-anchor="end" x="%.1f" y="%.1f" style="font-size:10px">%s</text>'
              % (X0 - 8, Y0 + r * STEP + CELL - 2, nome)
              for r, nome in ((1, "seg"), (3, "qua"), (5, "sex"))]

    body = [panel(26, 26, W - 52, H - 52),
            '<text x="46" y="60" style="font-size:24px;font-weight:800;fill:%s">Atividade</text>' % TEXT,
            '<text class="k" x="48" y="84" style="font-size:13px">%d contribuições no último ano</text>'
            % contrib["total"]["lastYear"],
            "\n    ".join(leg), "\n    ".join(marcas), "\n    ".join(semana),
            "\n    ".join(cells), "".join(snake)]
    style = """
    .cell { animation: eat %ss linear infinite both; }
    .seg  { animation: move %ss linear infinite both; }
    @keyframes eat { 0%%{opacity:1} 1.5%%{opacity:.18} 100%%{opacity:.18} }
    @keyframes move{%s}
    @media (prefers-reduced-motion: reduce) { .cell { animation: none } .seg { display: none } }""" % (T, T, stops)
    return card(W, H, "ct", "\n    ".join(body), extra_style=style,
                label="Gráfico de contribuições com a cobrinha")


def quebra(texto, largura, fs, max_linhas=2):
    """Quebra por palavra dentro da largura do bloco, sem cortar no meio."""
    cpl = max(8, int(largura / (fs * 0.53)))
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if len(teste) <= cpl:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
            if len(linhas) == max_linhas:
                break
    if atual and len(linhas) < max_linhas:
        linhas.append(atual)
    if len(linhas) == max_linhas and len(" ".join(linhas)) < len(texto):
        linhas[-1] = linhas[-1][:cpl - 1].rstrip() + "…"
    return linhas


def card_projects(repos):
    rows = repos[:4]
    cols = 1 if len(rows) == 1 else 2
    CWD = 808.0 if cols == 1 else 394.0
    lines = (len(rows) + cols - 1) // cols

    # Altura de cada bloco vem do conteudo: descricao de uma ou duas linhas,
    # com ou sem a etiqueta de linguagem.
    desenhos = []
    for r in rows:
        ls = quebra(r["description"] or "Sem descrição", CWD - 36, 11.5)
        y = 82.0 + (len(ls) - 1) * 16
        if r.get("language"):
            y += 32
        desenhos.append((r, ls, y + 48))
    CH = max(d[2] for d in desenhos)
    H = 60 + lines * (CH + 14) + 16

    body = ['<text class="h" x="30" y="40">PROJETOS</text>']
    for i, (r, ls, _) in enumerate(desenhos):
        gx = 26 + (i % cols) * (CWD + 14)
        gy = 60 + (i // cols) * (CH + 14)
        body.append('<g transform="translate(%.0f,%.0f)">' % (gx, gy))
        body.append('  <rect width="%s" height="%s" rx="13" fill="#0b0b0d" stroke="%s"/>' % (CWD, CH, GRID))
        body.append('  <text class="mono s" x="18" y="26" style="font-size:10.5px">&#8226; %s</text>' % escape(r["name"]))
        body.append('  <text class="mono" x="18" y="58" style="font-size:16.5px;font-weight:700;fill:%s">%s</text>'
                    % (ACCENT, escape(r["name"])))
        for j, l in enumerate(ls):
            body.append('  <text class="k" x="18" y="%.0f" style="font-size:11.5px">%s</text>' % (82 + j * 16, escape(l)))
        y = 82.0 + (len(ls) - 1) * 16
        if r.get("language"):
            lw = 22 + len(r["language"]) * 6.4
            body.append('  <rect x="18" y="%.0f" width="%.0f" height="18" rx="9" fill="%s" opacity="0.16"/>' % (y + 14, lw, ACCENT))
            body.append('  <text class="mono" text-anchor="middle" x="%.0f" y="%.0f" style="font-size:9.5px;fill:%s">%s</text>'
                        % (18 + lw / 2, y + 26.5, ACCENT, escape(r["language"])))
            y += 32
        body.append('  <text class="mono s" x="18" y="%.0f" style="font-size:11px">&#9733; %d  &#183;  atualizado %s</text>'
                    % (y + 30, r["stargazers_count"], (r.get("pushed_at") or "")[:10] or "n/d"))
        body.append('</g>')
    return card(W, H, "pj", ("%s    " % chr(10)).join(body), label="Projetos em destaque")


# Icones de marca, desenhados em viewBox 24x24 e reescalados na hora de usar.
ICONES = {
    "github": '<path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.21 3.44 9.63 8.2 11.19.6.11.82-.25.82-.56v-2.2c-3.34.7-4.04-1.57-4.04-1.57-.55-1.36-1.34-1.73-1.34-1.73-1.09-.73.08-.72.08-.72 1.2.08 1.84 1.21 1.84 1.21 1.07 1.79 2.81 1.27 3.5.97.11-.76.42-1.27.76-1.56-2.67-.29-5.47-1.29-5.47-5.75 0-1.27.46-2.31 1.21-3.12-.12-.29-.53-1.47.12-3.06 0 0 .99-.31 3.24 1.19a11.5 11.5 0 0 1 5.9 0c2.25-1.5 3.24-1.19 3.24-1.19.65 1.59.24 2.77.12 3.06.75.81 1.2 1.85 1.2 3.12 0 4.47-2.8 5.45-5.48 5.74.43.36.81 1.09.81 2.2v3.26c0 .31.22.68.83.56A12.02 12.02 0 0 0 24 12.29C24 5.78 18.63.5 12 .5z"/>',
    "linkedin": '<path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05a3.74 3.74 0 0 1 3.37-1.85c3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.07 2.07 0 1 1 0-4.14 2.07 2.07 0 0 1 0 4.14zm1.78 13.02H3.55V9h3.57v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z"/>',
    "instagram": ('<rect x="2" y="2" width="20" height="20" rx="6" fill="none" stroke="currentColor" stroke-width="2"/>'
                  '<circle cx="12" cy="12" r="4.6" fill="none" stroke="currentColor" stroke-width="2"/>'
                  '<circle cx="17.8" cy="6.2" r="1.5"/>'),
    "site": ('<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
             '<ellipse cx="12" cy="12" rx="4.4" ry="10" fill="none" stroke="currentColor" stroke-width="2"/>'
             '<path d="M2.4 8.6h19.2M2.4 15.4h19.2" fill="none" stroke="currentColor" stroke-width="2"/>'),
}


def card_social():
    H = 126.0
    items = PERFIL["links"]
    PW, GAP, SZ = 186.0, 12.0, 19.0
    x0 = 26 + (808 - (len(items) * PW + (len(items) - 1) * GAP)) / 2
    body = [panel(26, 22, 808, 82, 22)]
    for i, (label, val, icone, _url) in enumerate(items):
        x = x0 + i * (PW + GAP)
        body.append('<rect x="%.1f" y="38" width="%.0f" height="50" rx="25" fill="%s"/>' % (x, PW, PANEL))
        body.append('<rect x="%.1f" y="39" width="%.0f" height="48" rx="24" fill="none" stroke="%s" stroke-opacity="0.45"/>'
                    % (x + 1, PW - 2, ACCENT))
        body.append('<g transform="translate(%.1f,%.1f) scale(%.4f)" fill="%s" color="%s">%s</g>'
                    % (x + 20, 63 - SZ / 2, SZ / 24.0, ACCENT, ACCENT, ICONES[icone]))
        body.append('<text class="s" x="%.1f" y="58" style="font-size:9.5px">%s</text>' % (x + 20 + SZ + 12, label))
        body.append('<text class="mono" x="%.1f" y="75" style="font-size:12px;fill:%s">%s</text>'
                    % (x + 20 + SZ + 12, TEXT, escape(val)))
    return card(W, H, "so", "\n    ".join(body), label="Contatos")


def card_portrait(user):
    """O rosto em ASCII cujos caracteres migram, um a um, ate formarem o X.

    Cada caractere e uma particula: nasce na sua celula do retrato e viaja
    ate uma celula do X. O pareamento e por densidade -- o caractere mais
    cheio do rosto vai para a celula mais cheia do X -- entao a marca chega
    com o peso certo mesmo sendo desenhada com os caracteres do rosto.
    """
    COLS, ROWS = GRID_COLS, GRID_ROWS
    CWD, LH, FS = 6.6, 12.2, 11.0
    TOP, T = 74.0, 16.0
    H = TOP + ROWS * LH + 26
    x0 = (W - COLS * CWD) / 2

    def ink(rows):
        out = []
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch != " ":
                    out.append((c, r, ch))
        return out

    def centraliza(rows):
        """O X e gerado na proporcao do logo; sobra e centrada na grade."""
        pad = (ROWS - len(rows)) // 2
        return [""] * pad + list(rows) + [""] * (ROWS - len(rows) - pad)

    peso = lambda t: ASCII_CHARS.index(t[2])
    origem = sorted(ink(ascii_portrait(user["avatar_url"], COLS, ROWS)),
                    key=lambda t: (-peso(t), t[1], t[0]))

    # O X tem densidade quase uniforme, entao ordenar o destino por peso faz o
    # desempate (a linha) mandar, e os caracteres chegam em faixas horizontais.
    # Ordenando do nucleo para as pontas, os traços mais cheios do rosto caem
    # no miolo da marca e os leves nas extremidades.
    alvo = ink(centraliza(read_art("xmark.txt")))
    if alvo:
        cx = sum(t[0] for t in alvo) / len(alvo)
        cy = sum(t[1] for t in alvo) / len(alvo)
        destino = sorted(alvo, key=lambda t: ((t[0] - cx) ** 2 + ((t[1] - cy) * 2.0) ** 2))
    else:
        destino = []

    parts = []
    if origem and destino:
        n = max(len(origem), len(destino))
        for i in range(n):
            sc, sr, ch = origem[i * len(origem) // n]
            dc, dr, _ = destino[i * len(destino) // n]
            parts.append('<text class="f" x="%.1f" y="%.1f" style="--dx:%.1fpx;--dy:%.1fpx;'
                         'animation-delay:%.2fs">%s</text>'
                         % (x0 + sc * CWD, TOP + sr * LH, (dc - sc) * CWD, (dr - sr) * LH,
                            dc / COLS * 1.6, escape(ch)))

    body = ['<text class="h" x="30" y="36">RETRATO &#8594; X</text>',
            '<line x1="0" y1="52" x2="%.0f" y2="52" stroke="%s"/>' % (W, GRID),
            "\n    ".join(parts)]
    style = """
    .f { fill: %s; font-family: %s; font-size: %spx;
         animation: fly %ss ease-in-out infinite both; }
    @keyframes fly {
      0%%, 20%%   { transform: translate(0px, 0px) }
      48%%, 74%%  { transform: translate(var(--dx), var(--dy)) }
      96%%, 100%% { transform: translate(0px, 0px) }
    }
    @media (prefers-reduced-motion: reduce) { .f { animation: none } }""" % (ACCENT, MONO, FS, T)
    return card(W, H, "pr", "\n    ".join(body), extra_style=style,
                label="Retrato ASCII cujos caracteres migram e formam o X da CodenX")


# Paleta dos pontos da cobrinha -- a mesma passada ao Platane/snk no workflow.
SNK_DOTS = ["#0d0d0c", "#3b350f", "#816f1c", "#bda52d", ACCENT]

# Cor de cada item da stack, na marca de cada tecnologia.
STACK_COR = {
    "HTML": "#e34c26", "CSS": "#563d7c", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "React": "#61dafb", "Node.js": "#3c873a",
    "Figma": "#a259ff", "Photoshop": "#31a8ff", "Illustrator": "#ff9a00",
}


def card_snake(contrib):
    """Envolve a saida real do Platane/snk (assets/snake-core.svg) no card.

    O snk gera SVG com CSS proprio; as classes dele (.c .s .u) colidem com as
    do card, entao levam o prefixo k antes de entrar. Sem o arquivo do snk,
    cai no calendario proprio.
    """
    core = os.path.join(OUT, "snake-core.svg")
    if not os.path.exists(core):
        return card_heatmap(contrib)
    src = io.open(core, encoding="utf-8").read()
    vb = re.search(r'<svg[^>]*viewBox="([^"]+)"', src).group(1)
    vw, vh = [float(v) for v in vb.split()[2:]]
    inner = src[src.index(">", src.index("<svg")) + 1:src.rindex("</svg>")]
    st = re.search(r"<style>(.*?)</style>", inner, re.S)
    estilo = re.sub(r"\.([csu][0-9a-z]*)", r".k\1", st.group(1))
    inner = (inner[:st.start()] + inner[st.end():])
    inner = re.sub(r'class="([^"]+)"',
                   lambda m: 'class="%s"' % " ".join("k" + t for t in m.group(1).split()),
                   inner)

    pad, top = 34.0, 52.0
    gw = W - 2 * pad
    gh = vh * gw / vw
    H = top + gh + 16.0
    body = ['<text class="h" x="30" y="46">ATIVIDADE</text>']
    for i, c in enumerate(SNK_DOTS):
        body.append('<rect x="%.0f" y="36" width="11" height="11" rx="2.5" fill="%s" '
                    'stroke="%s" stroke-opacity="0.5"/>' % (W - 101 + i * 15, c, GRID))
    body.append('<svg x="%.1f" y="%.1f" width="%.1f" height="%.1f" viewBox="%s" '
                'preserveAspectRatio="xMidYMid meet">%s</svg>' % (pad, top, gw, gh, vb, inner))
    return card(W, H, "sn", ("%s    " % chr(10)).join(body), extra_style=estilo,
                label="Contribuições do último ano, com a cobrinha do Platane/snk")


def card_stack():
    """Stack declarada. O GitHub nao reporta bytes de linguagem nos repos
    (a API /languages devolve vazio), entao o card mostra o que eu uso de
    fato em vez de um grafico vazio."""
    itens = PERFIL["stack"]
    COLS = 4
    linhas = (len(itens) + COLS - 1) // COLS
    cw, ch = (W - 56 - (COLS - 1) * 14) / COLS, 46.0
    H = 104.0 + linhas * (ch + 14)
    body = ['<text class="h" x="30" y="46">LINGUAGENS &amp; FERRAMENTAS</text>']
    for i, t in enumerate(itens):
        r, c = divmod(i, COLS)
        x, y = 28 + c * (cw + 14), 70 + r * (ch + 14)
        cor = STACK_COR.get(t, ACCENT)
        body.append('<g class="ent" style="animation-delay:%.2fs">'
                    '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="12" fill="#0b0b0d" stroke="%s"/>'
                    '<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>'
                    '<text x="%.1f" y="%.1f" style="font-size:14px;font-weight:600;fill:%s">%s</text>'
                    '</g>' % (i * 0.06, x, y, cw, ch, GRID,
                              x + 24, y + ch / 2, cor,
                              x + 40, y + ch / 2 + 5, TEXT, escape(t)))
    style = """
    .ent { animation: entra .7s cubic-bezier(.22,1,.36,1) both; }
    @keyframes entra { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }
    @media (prefers-reduced-motion: reduce) { .ent { animation: none } }"""
    return card(W, H, "st", ("%s    " % chr(10)).join(body), extra_style=style,
                label="Linguagens e ferramentas que uso")


def caixas(itens, y0, ch, fs_val, fs_lbl, dy_val, dy_lbl):
    """Fileira de caixas opacas com numero em cima e rotulo embaixo.

    Opacas de proposito: a diagonal do fundo passa por tras em vez de cortar
    o texto no meio.
    """
    n = len(itens)
    cw = (W - 56 - (n - 1) * 12) / n
    out = []
    for i, (rot, val) in enumerate(itens):
        x = 28 + i * (cw + 12)
        out.append('<g class="ent" style="animation-delay:%.2fs">'
                   '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="13" fill="#0b0b0d" stroke="%s"/>'
                   '<text x="%.1f" y="%.1f" style="font-size:%spx;font-weight:800;fill:%s">%s</text>'
                   '<text class="k" x="%.1f" y="%.1f" style="font-size:%spx">%s</text>'
                   '</g>' % (i * 0.07, x, y0, cw, ch, GRID,
                             x + 18, y0 + dy_val, fs_val, ACCENT, escape(val),
                             x + 18, y0 + dy_lbl, fs_lbl, escape(rot)))
    return out


ENTRA = """
    .ent { animation: entra .7s cubic-bezier(.22,1,.36,1) both; }
    @keyframes entra { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }
    @media (prefers-reduced-motion: reduce) { .ent { animation: none } }"""


def card_stats(user, repos, cont):
    itens = [("Estrelas", num(sum(r["stargazers_count"] for r in repos)))]
    if "commits" in cont:
        itens.append(("Commits", num(cont["commits"])))
    if "prs" in cont:
        itens.append(("Pull requests", num(cont["prs"])))
    if "issues" in cont:
        itens.append(("Issues", num(cont["issues"])))
    itens.append(("Repositórios", num(user["public_repos"])))
    itens.append(("Seguidores", num(user["followers"])))
    ch = 88.0
    body = ['<text class="h" x="30" y="46">NÚMEROS</text>'] + caixas(itens, 66.0, ch, 30, 11, 52, 74)
    return card(W, 66.0 + ch + 26.0, "sa", ("%s    " % chr(10)).join(body),
                extra_style=ENTRA, label="Números do perfil no GitHub")


def card_streak(contrib):
    days = contrib["contributions"]
    cur, best = streaks(days)
    total = sum(d["count"] for d in days)
    itens = [("Contribuições no último ano", num(total)),
             ("Sequência atual", "%dd" % cur),
             ("Maior sequência", "%dd" % best)]
    ch = 98.0
    body = ['<text class="h" x="30" y="46">CONSISTÊNCIA</text>'] + caixas(itens, 66.0, ch, 36, 12, 58, 82)
    return card(W, 66.0 + ch + 26.0, "sk", ("%s    " % chr(10)).join(body),
                extra_style=ENTRA, label="Consistência de contribuições")


def main():
    os.makedirs(OUT, exist_ok=True)
    user, repos, langs, contrib, cont = fetch()
    files = {
        "hero.svg": card_hero(user, repos, contrib),
        "stats.svg": card_stats(user, repos, cont),
        "streak.svg": card_streak(contrib),
        "snake.svg": card_snake(contrib),
        "stack.svg": card_stack(),
        "highlights.svg": card_highlights(user, repos),
        "projects.svg": card_projects(repos),
        "social.svg": card_social(),
        "portrait.svg": card_portrait(user),
    }
    for name, svg in sorted(files.items()):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("  %-18s %7d bytes" % (name, len(svg)))


if __name__ == "__main__":
    main()
