# import re
# import sqlite3
# import fitz  # PyMuPDF
# from collections import defaultdict

# PDF_PATH = "albaran_pollo_260109_123335.pdf"
# DB_NAME = "packinglist_auto.db"

# TOL_Y = 2.0  # tolerancia para agrupar palabras por línea

# def get_etiqueta(page) -> str:
#     txt = page.get_text("text") or ""
#     m = re.search(r"ETIQUETA.*?(\d{5,})", txt)
#     return m.group(1) if m else "00000000000"

# def clean_tokens(tokens):
#     out = []
#     prev = None
#     for t in tokens:
#         # quitar líderes de puntos / basura
#         if "..." in t or re.fullmatch(r"\.+", t):
#             continue
#         # quitar duplicados consecutivos
#         if t == prev:
#             continue
#         out.append(t)
#         prev = t
#     return out

# def parse_side(tokens):
#     """
#     Parse de 1 lado (izq o der).
#     Espera: CODIGO ... CANTIDAD FORMATO(B/U) UNIDADES
#     Devuelve (codigo, descripcion, cantidad) o None.
#     """
#     tokens = clean_tokens(tokens)

#     # primer código numérico
#     code_idx = None
#     for i, t in enumerate(tokens):
#         if t.isdigit() and 3 <= len(t) <= 12:
#             code_idx = i
#             break
#     if code_idx is None:
#         return None

#     codigo = tokens[code_idx]

#     # si repite el código al inicio, quita el duplicado inmediato
#     if code_idx + 1 < len(tokens) and tokens[code_idx + 1] == codigo:
#         tokens.pop(code_idx + 1)

#     # buscar patrón: (cantidad) (B/U) (unidades)
#     q_idx = None
#     for i in range(code_idx + 1, len(tokens) - 1):
#         if tokens[i] in ("B", "U") and tokens[i - 1].isdigit() and tokens[i + 1].isdigit():
#             q_idx = i - 1
#             break
#     if q_idx is None:
#         return None

#     cantidad = int(tokens[q_idx])
#     descripcion = " ".join(tokens[code_idx + 1 : q_idx]).strip()
#     if not descripcion:
#         return None

#     return codigo, descripcion, cantidad

# def extract_items_from_page(page):
#     words = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,word_no)
#     width = float(page.rect.width)
#     split_x = width / 2.0

#     # agrupar por línea según y0
#     line_groups = defaultdict(list)
#     for x0, y0, x1, y1, w, b, l, wn in words:
#         key = round(y0 / TOL_Y) * TOL_Y
#         line_groups[key].append((x0, w))

#     items = []
#     for ykey in sorted(line_groups.keys()):
#         pairs = sorted(line_groups[ykey], key=lambda p: p[0])
#         left = [w for x, w in pairs if x < split_x]
#         right = [w for x, w in pairs if x >= split_x]

#         for side in (left, right):
#             parsed = parse_side(side)
#             if parsed:
#                 items.append(parsed)

#     return items

# def ensure_schema(cur):
#     cur.execute("CREATE TABLE IF NOT EXISTS Etiqueta (Etiqueta TEXT PRIMARY KEY)")
#     cur.execute("CREATE TABLE IF NOT EXISTS Codigo (Codigo TEXT PRIMARY KEY)")
#     cur.execute("CREATE TABLE IF NOT EXISTS Descripcion (Descripcion TEXT PRIMARY KEY)")
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS Linea (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             Etiqueta TEXT NOT NULL,
#             Codigo TEXT NOT NULL,
#             Descripcion TEXT NOT NULL,
#             Cantidad INTEGER NOT NULL,
#             Falta INTEGER DEFAULT 0
#         )
#     """)

# def main():
#     doc = fitz.open(PDF_PATH)

#     etiqueta_global = "00000000000"
#     acc = {}  # (codigo, descripcion) -> cantidad (sum)

#     for page in doc:
#         etiqueta_global = get_etiqueta(page) or etiqueta_global
#         items = extract_items_from_page(page)
#         for codigo, descripcion, cantidad in items:
#             key = (codigo, descripcion)
#             acc[key] = acc.get(key, 0) + cantidad

#     # guardar DB con el MISMO esquema que tu .db manual
#     conn = sqlite3.connect(DB_NAME)
#     cur = conn.cursor()
#     ensure_schema(cur)

#     cur.execute("DELETE FROM Linea")
#     cur.execute("DELETE FROM Etiqueta")
#     cur.execute("DELETE FROM Codigo")
#     cur.execute("DELETE FROM Descripcion")

#     cur.execute("INSERT INTO Etiqueta (Etiqueta) VALUES (?)", (etiqueta_global,))

#     total_items = 0
#     total_bultos = 0

#     for (codigo, descripcion), cantidad in acc.items():
#         cur.execute("INSERT OR IGNORE INTO Codigo (Codigo) VALUES (?)", (codigo,))
#         cur.execute("INSERT OR IGNORE INTO Descripcion (Descripcion) VALUES (?)", (descripcion,))
#         cur.execute(
#             "INSERT INTO Linea (Etiqueta, Codigo, Descripcion, Cantidad, Falta) VALUES (?, ?, ?, ?, 0)",
#             (etiqueta_global, codigo, descripcion, cantidad),
#         )
#         total_items += 1
#         total_bultos += cantidad

#     conn.commit()
#     conn.close()

#     print(f"\n✅ {DB_NAME} generado con {total_items} productos (etiqueta {etiqueta_global}).")
#     print(f"📦 Total bultos (suma Cantidad): {total_bultos}\n")

# if __name__ == "__main__":
#     main()

import re
import sqlite3
import fitz  # PyMuPDF
from collections import defaultdict

PDF_PATH = "central.pdf"
OUT_DIR = "."          # carpeta de salida
TOL_Y = 2.0            # tolerancia para agrupar palabras por línea

def get_etiqueta(page) -> str:
    txt = page.get_text("text") or ""
    m = re.search(r"ETIQUETA.*?(\d{5,})", txt)
    return m.group(1) if m else "00000000000"

def clean_tokens(tokens):
    out = []
    prev = None
    for t in tokens:
        if "..." in t or re.fullmatch(r"\.+", t):
            continue
        if t == prev:
            continue
        out.append(t)
        prev = t
    return out

def parse_side(tokens):
    tokens = clean_tokens(tokens)

    code_idx = None
    for i, t in enumerate(tokens):
        if t.isdigit() and 3 <= len(t) <= 12:
            code_idx = i
            break
    if code_idx is None:
        return None

    codigo = tokens[code_idx]

    if code_idx + 1 < len(tokens) and tokens[code_idx + 1] == codigo:
        tokens.pop(code_idx + 1)

    q_idx = None
    for i in range(code_idx + 1, len(tokens) - 1):
        if tokens[i] in ("B", "U") and tokens[i - 1].isdigit() and tokens[i + 1].isdigit():
            q_idx = i - 1
            break
    if q_idx is None:
        return None

    cantidad = int(tokens[q_idx])
    descripcion = " ".join(tokens[code_idx + 1 : q_idx]).strip()
    if not descripcion:
        return None

    return codigo, descripcion, cantidad

def extract_items_from_page(page):
    words = page.get_text("words")
    width = float(page.rect.width)
    split_x = width / 2.0

    line_groups = defaultdict(list)
    for x0, y0, x1, y1, w, b, l, wn in words:
        key = round(y0 / TOL_Y) * TOL_Y
        line_groups[key].append((x0, w))

    items = []
    for ykey in sorted(line_groups.keys()):
        pairs = sorted(line_groups[ykey], key=lambda p: p[0])
        left = [w for x, w in pairs if x < split_x]
        right = [w for x, w in pairs if x >= split_x]

        for side in (left, right):
            parsed = parse_side(side)
            if parsed:
                items.append(parsed)

    return items

def ensure_schema(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS Etiqueta (Etiqueta TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS Codigo (Codigo TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS Descripcion (Descripcion TEXT PRIMARY KEY)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Linea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Etiqueta TEXT NOT NULL,
            Codigo TEXT NOT NULL,
            Descripcion TEXT NOT NULL,
            Cantidad INTEGER NOT NULL,
            Falta INTEGER DEFAULT 0
        )
    """)

def write_db(etiqueta, acc, out_path):
    conn = sqlite3.connect(out_path)
    cur = conn.cursor()
    ensure_schema(cur)

    cur.execute("DELETE FROM Linea")
    cur.execute("DELETE FROM Etiqueta")
    cur.execute("DELETE FROM Codigo")
    cur.execute("DELETE FROM Descripcion")

    cur.execute("INSERT INTO Etiqueta (Etiqueta) VALUES (?)", (etiqueta,))

    for (codigo, descripcion), cantidad in acc.items():
        cur.execute("INSERT OR IGNORE INTO Codigo (Codigo) VALUES (?)", (codigo,))
        cur.execute("INSERT OR IGNORE INTO Descripcion (Descripcion) VALUES (?)", (descripcion,))
        cur.execute(
            "INSERT INTO Linea (Etiqueta, Codigo, Descripcion, Cantidad, Falta) VALUES (?, ?, ?, ?, 0)",
            (etiqueta, codigo, descripcion, cantidad),
        )

    conn.commit()
    conn.close()

def main():
    doc = fitz.open(PDF_PATH)

    # por etiqueta -> acumulado (codigo,descripcion)->cantidad
    por_etiqueta = defaultdict(lambda: defaultdict(int))

    for page in doc:
        etq = get_etiqueta(page)
        for codigo, descripcion, cantidad in extract_items_from_page(page):
            por_etiqueta[etq][(codigo, descripcion)] += cantidad

    for etq, acc in por_etiqueta.items():
        out_db = f"{OUT_DIR}/packinglist_etq_{etq}.db"
        write_db(etq, acc, out_db)
        print(f"✅ Generado: {out_db} ({len(acc)} productos)")

if __name__ == "__main__":
    main()
