"""Gera as artes ASCII fixas usadas pelos cards: o X da CodenX.

Roda so quando a marca ou o nome mudarem; a saida (xmark.txt, wordmark.txt)
fica versionada, entao o build no CI nao depende de navegador nem de fonte.

O X sai de logo-x.png, o rasterizado do Logo - X.svg oficial, tambem
versionado. Aproximar a marca por poligonos deixa as barras finas demais.

Requer: pillow.
Uso: python scripts/gen_ascii_art.py
"""
import os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = " .`:!+*csS#%@"


def to_ascii(img, cols, rows, floor=0.16):
    img = img.crop(img.getbbox()).resize((cols, rows), Image.LANCZOS)
    px = list(img.getdata())
    out = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            v = px[y * cols + x] / 255.0
            line += " " if v < floor else CHARS[min(len(CHARS) - 1, int(v * (len(CHARS) - 1) + 0.5))]
        out.append(line.rstrip())
    return out


def build_xmark(cols=80, rows=38):
    return to_ascii(Image.open(os.path.join(HERE, "logo-x.png")).convert("L"), cols, rows)


if __name__ == "__main__":
    for name, rows in [("xmark.txt", build_xmark())]:
        open(os.path.join(HERE, name), "w", encoding="utf-8").write("\n".join(rows) + "\n")
        print("  %-14s %d linhas" % (name, len(rows)))
