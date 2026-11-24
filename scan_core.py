# -*- coding: utf-8 -*-
"""Baca scan laporan TLD (PDF/gambar) -> baris (No TLD, nama, angka dosis) -> cocokkan ke petugas. OCR memakai tesseract (CLI)."""
import io, os, re, shutil, subprocess, tempfile, difflib
import numpy as np, pandas as pd
from PIL import Image, ImageOps, ImageFilter

NUM = re.compile(r"^<?\d+(?:[.,]\d+)?$")
SPECIAL = re.compile(r"^(n/?a|nd|-|—)$", re.I)
TLD_FULL = re.compile(r"[MN]?\s?1123\s?[-–—._]?\s?\d{2}\s?[-–—._]?\s?(\d{1,3}|[A-Z])\b", re.I)

def tesseract_ok(): return shutil.which("tesseract") is not None

def render_pages(data, filename, dpi=220, max_pages=8):
    """PDF -> daftar gambar; file gambar -> satu gambar."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data); out = []
        for i in range(min(len(pdf), max_pages)): out.append(pdf[i].render(scale=dpi / 72).to_pil().convert("RGB"))
        return out
    return [Image.open(io.BytesIO(data)).convert("RGB")]

def preprocess(img):
    g = ImageOps.grayscale(img)
    if g.width < 2200:   # perbesar agar angka kecil terbaca
        k = 2200 / g.width; g = g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS)
    g = ImageOps.autocontrast(g, cutoff=1).filter(ImageFilter.SHARPEN)
    return g

def ocr_lines(img, psm=6):
    """Hasil OCR per baris: list token (teks, x_kiri, confidence)."""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "p.png"); preprocess(img).save(p)
        r = subprocess.run(["tesseract", p, "stdout", "--psm", str(psm), "-l", "eng", "tsv"], capture_output=True, text=True, timeout=180)
    if r.returncode != 0: raise RuntimeError(r.stderr[:300])
    df = pd.read_csv(io.StringIO(r.stdout), sep="\t", quoting=3, dtype=str, keep_default_na=False)
    df = df[(df["level"] == "5") & (df["text"].str.strip() != "")]
    lines = {}
    for _, w in df.iterrows(): lines.setdefault((w["block_num"], w["par_num"], w["line_num"]), []).append((w["text"].strip(), int(w["left"]), float(w["conf"] or 0)))
    return [sorted(v, key=lambda t: t[1]) for v in lines.values()]

def _tail(t):
    m = re.search(r"(\d{1,3})$", str(t or "")); return m.group(1).zfill(3) if m else None

def parse_lines(lines, page=1):
    rows = []
    for toks in lines:
        words = [w for w in (re.sub(r"^[\[\]|()_]+|[\[\]|_]+$", "", t[0]) for t in toks) if w]; txt = " ".join(words)
        tld = None; start = 0
        m = TLD_FULL.search(txt)
        if m: tld = re.sub(r"\s", "", m.group(0)).upper(); after = txt[m.end():].split()
        elif len(words) >= 3 and words[0].isdigit() and re.fullmatch(r"\d{3}", words[1]): tld = words[1]; after = words[2:]
        else: continue
        name, nums, in_name = [], [], True
        for w in after:
            wn = w.replace(",", ".")
            if NUM.match(wn) or SPECIAL.match(w):
                in_name = False; nums.append(w)
            elif in_name and re.search(r"[A-Za-z]", w): name.append(w)
        vals = []
        for w in nums:
            wn = w.replace(",", ".")
            if SPECIAL.match(w): vals.append(None)
            elif wn.startswith("<"): vals.append(0.0)
            else:
                try: vals.append(float(wn))
                except ValueError: vals.append(None)
        if not vals: continue
        rows.append(dict(page=page, tld=tld, nama=" ".join(name), nums=vals, raw=txt))
    return rows

def pick(nums, mode):
    n = [x for x in nums]
    i = {"Angka pertama": 0, "Angka kedua": 1, "Angka ketiga": 2, "Angka terakhir": -1}.get(mode, 0)
    try: return n[i]
    except IndexError: return None

def _norm(s): return " ".join(re.sub(r"\b(dr|drg|sp\w*|fiha|ph|d|k|ri)\b|[^a-z ]", " ", str(s).lower().replace(".", " ")).split())

def match_roster(rows, roster):
    """Cocokkan baris scan ke petugas: No TLD (3 digit terakhir) + kemiripan nama."""
    out = []
    for r in rows:
        tail = _tail(r["tld"]); cand = roster[[(_tail(x) == tail) for x in roster["No TLD"]]] if tail else roster.iloc[0:0]
        best, sc = None, 0.0
        pool = cand if len(cand) else roster
        for _, p in pool.iterrows():
            s = difflib.SequenceMatcher(None, _norm(p["Nama"]), _norm(r["nama"])).ratio() if r["nama"] else (0.6 if len(cand) == 1 else 0.0)
            if p.get("Status") == "Resign": s -= 0.05
            if s > sc: best, sc = p, s
        by_tld = len(cand) > 0
        if best is not None and ((by_tld and sc >= 0.45) or sc >= 0.85):
            out.append(dict(r, SID=int(best["SID"]), cocok=best["Nama"], skor=round(sc, 2), status="Cocok" if sc >= 0.75 else "Cek nama"))
        else: out.append(dict(r, SID=None, cocok="", skor=round(sc, 2), status="Tidak ditemukan"))
    return out

def scan_to_rows(data, filename, psms=(4, 6)):
    """Coba beberapa mode segmentasi OCR per halaman, pakai yang menghasilkan baris petugas terbanyak."""
    pages = render_pages(data, filename); rows = []
    for i, im in enumerate(pages, 1):
        best = []
        for psm in psms:
            got = parse_lines(ocr_lines(im, psm), i)
            if len(got) > len(best): best = got
        rows += best
    return rows, pages
