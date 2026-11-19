"""Logika murni Dose Monitoring (tanpa Streamlit) - dapat diuji terpisah."""
import io, numpy as np, pandas as pd

ID_COLS = ["Kode Pasien","Nama","Gender","Umur","Berat Badan","Tanggal","Jenis Periksa","Deskripsi RIS","Visit No"]
_D = {"GR": ["Posisi","Proyeksi","FDD","kV","mA","s","mAs"], "CT": ["No of Phase","CTDIvol","DLP"],
      "MAMMO": ["kV","mAs","Ketebalan kompresi","AGD"], "FLURO": ["Fluoro detik","DAP","Kerma total"],
      "CATH": ["Fluoro detik","DAP","Kerma total"], "DENTAL": ["kV","mAs","FSD","DAP"]}
MODS = {
 "GR": dict(label="Radiografi Umum", exam="Jenis Periksa", cols=ID_COLS+_D["GR"], dose=_D["GR"],
   metrics=[("INAK","INAK (mGy)","0.00"),("ESAK","ESAK (mGy)","0.00")]),
 "CT": dict(label="CT Scan", exam="Jenis Periksa", cols=ID_COLS+_D["CT"], dose=_D["CT"],
   metrics=[("CTDIvol","CTDIvol (mGy)","0.0"),("DLP","DLP (mGy.cm)","0")]),
 "MAMMO": dict(label="Mamografi", exam="Jenis Periksa", cols=ID_COLS+_D["MAMMO"], dose=_D["MAMMO"],
   metrics=[("AGD","AGD (mGy)","0.00")]),
 "FLURO": dict(label="Fluoroskopi", exam="Jenis Periksa", cols=ID_COLS+_D["FLURO"], dose=_D["FLURO"],
   metrics=[("DAP_Gy","DAP (Gy.cm2)","0.0"),("Kerma total","Kerma total (mGy)","0"),("Fluoro menit","Fluoro (menit)","0.0")]),
 "CATH": dict(label="Cathlab", exam="Jenis Periksa", cols=ID_COLS+_D["CATH"], dose=_D["CATH"],
   metrics=[("DAP_Gy","DAP (Gy.cm2)","0.0"),("Kerma total","Kerma total (mGy)","0"),("Fluoro menit","Fluoro (menit)","0.0")]),
 "DENTAL": dict(label="Dental", exam="Jenis Periksa", cols=ID_COLS+_D["DENTAL"], dose=_D["DENTAL"],
   metrics=[("DAP_mGy","DAP (mGy.cm2)","0.0")]),
}
DEFAULT_CFG = dict(
  bayi_max=4, dewasa_min=15, bsf=1.35,
  out_pts=[[60,61.1],[70,70.8],[80,81.8],[90,91.3],[100,103.3]],
  unit_dap_cath="mGy.cm2", unit_dap_dental="mGy.cm2",
  tpd={  # modalitas -> {nama: {metrik: nilai}}
   "GR": {"CHEST":{"INAK":0.3,"ESAK":0.4},"KNEE":{"INAK":0.3,"ESAK":0.4},"LSPINE":{"INAK":3.1,"ESAK":4.4},"HAND":{"INAK":0.1,"ESAK":0.2},
          "FOOT":{"INAK":0.2,"ESAK":0.3},"PELVIS":{"INAK":1.4,"ESAK":1.8},"ANKLE":{"INAK":0.4,"ESAK":0.5},"SHOULDER":{"INAK":0.3,"ESAK":0.4},
          "ELBOW":{"INAK":0.2,"ESAK":0.3},"CSPINE":{"INAK":0.5,"ESAK":0.7},"ABDOMEN":{"INAK":1.4,"ESAK":2.0},"SKULL":{},"LEG":{"INAK":0.2,"ESAK":0.3}},
   "CT": {"CT SCAN Brain":{"CTDIvol":60,"DLP":2500},"CT SCAN Sinus Paranasalis":{"CTDIvol":60,"DLP":1275},"CT SCAN Neck with Contrast":{"CTDIvol":50,"DLP":2600},
          "CT SCAN Thorax":{"CTDIvol":16,"DLP":810},"CT SCAN Thorax with Contrast":{"CTDIvol":16,"DLP":810},"CT SCAN Calcium Score":{"CTDIvol":16,"DLP":810},
          "CT SCAN Included Coronary CTA":{"CTDIvol":47,"DLP":1200},"CT SCAN Angiography Cerebral":{"CTDIvol":47,"DLP":1200},
          "CT SCAN Whole Abdomen":{"CTDIvol":20,"DLP":1775},"CT SCAN Whole Abdomen with Contrast":{"CTDIvol":20,"DLP":1360},
          "CT SCAN Urografi":{"CTDIvol":17,"DLP":830},"CT SCAN Urografi with Contrast":{"CTDIvol":20,"DLP":1360}},
   "MAMMO": {"MAMMOGRAFI 2D":{},"MAMMOGRAFI 3D (TOMOSYNTHESIS)":{}},
   "FLURO": {},
   "CATH": {n:{} for n in ["CAG","CAG STANDBY PCI","CAG STANDBY PCI + iFR","PRIMARY PCI","PTA","DSA CEREBRAL","ABLASI","CDL TUNNEL","PERMANENT PACEMAKER","EVAR","TACE","EMBOLISASI"]},
   "DENTAL": {n:{} for n in ["PANORAMIK","CBCT","CEPHALO","INTRAORAL"]}})

def merge_cfg(saved):
    c = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_CFG.items()}
    if saved: c.update({k: v for k, v in saved.items() if k in c})
    return c

def fit_output(pts):
    """Kurva kuadrat output tabung: (a,b,c) dari [[kV, uGy/mAs],...]. Min. 3 titik."""
    p = [(float(a), float(b)) for a, b in pts if a not in (None, "") and b not in (None, "")]
    if len(p) < 3: return None
    x, y = zip(*p)
    return tuple(np.polyfit(x, y, 2))

def age_cat(age, bayi_max=4, dewasa_min=15):
    try:
        if age is None or str(age).strip() == "": return ""
        a = float(age)
    except (ValueError, TypeError):
        return ""
    if np.isnan(a): return ""
    return "Bayi" if a <= bayi_max else ("Anak" if a < dewasa_min else "Dewasa")

def _num(s): return pd.to_numeric(s, errors="coerce")

def compute(mod, df, cfg):
    """Tambah kolom Kategori usia + dosis turunan + Cek. Tidak mengubah input."""
    d = df.copy()
    for c in MODS[mod]["cols"]:
        if c not in d.columns: d[c] = np.nan
    d["Kategori usia"] = [age_cat(a, cfg["bayi_max"], cfg["dewasa_min"]) for a in d["Umur"]]
    if mod == "GR":
        mas = _num(d["mAs"]); mas = mas.fillna(_num(d["mA"]) * _num(d["s"]))
        d["mAs dipakai"] = mas
        co = fit_output(cfg["out_pts"])
        kv = _num(d["kV"])
        if co: d["INAK"] = (co[0]*kv**2 + co[1]*kv + co[2]) * mas / 1000
        else: d["INAK"] = np.nan
        d["ESAK"] = d["INAK"] * float(cfg["bsf"])
        need = d["INAK"].isna()
        msg_need = "kV / mAs belum lengkap"
    elif mod == "CT":
        need = _num(d["CTDIvol"]).isna() | _num(d["DLP"]).isna(); msg_need = "CTDI / DLP belum lengkap"
    elif mod == "MAMMO":
        need = _num(d["AGD"]).isna(); msg_need = "AGD belum lengkap"
    elif mod in ("CATH", "FLURO"):
        dap = _num(d["DAP"])
        d["DAP_Gy"] = dap if cfg["unit_dap_cath"] == "Gy.cm2" else dap / 1000
        d["Fluoro menit"] = _num(d["Fluoro detik"]) / 60
        need = dap.isna() | _num(d["Kerma total"]).isna(); msg_need = "DAP / kerma belum lengkap"
    else:
        dap = _num(d["DAP"])
        d["DAP_mGy"] = dap if cfg["unit_dap_dental"] == "mGy.cm2" else dap * 1000
        need = dap.isna(); msg_need = "DAP belum lengkap"
    ex = MODS[mod]["exam"]; known = set(cfg["tpd"].get(mod, {}))
    chk = np.where(d["Kategori usia"] == "", "Umur kosong / tidak valid",
          np.where(~d[ex].astype(str).str.strip().isin(known), "Jenis periksa tidak ada di daftar",
          np.where(need, msg_need, "OK")))
    d["Cek"] = chk
    d[ex] = d[ex].astype(str).str.strip().replace({"nan": ""})
    return d

def rekap(mod, d, cfg, kategori="Dewasa", dari=None, sampai=None, exams=None):
    """Tabel Q2/Q3 lokal per jenis periksa + acuan (hanya Dewasa)."""
    ex = MODS[mod]["exam"]; m = MODS[mod]["metrics"]
    x = d.copy()
    if kategori != "Semua": x = x[x["Kategori usia"] == kategori]
    if "Tanggal" in x.columns and (dari or sampai):
        t = pd.to_datetime(x["Tanggal"], errors="coerce")
        if dari: x = x[t >= pd.Timestamp(dari)]
        t = pd.to_datetime(x["Tanggal"], errors="coerce")
        if sampai: x = x[t < pd.Timestamp(sampai) + pd.Timedelta(days=1)]
    rows = []
    for name in (exams if exams else list(dict.fromkeys(list(cfg["tpd"].get(mod, {})) + sorted(x[ex].dropna().unique())))):
        g = x[x[ex] == name]; first = _num(g[m[0][0]]); n = int(first.notna().sum())
        if n == 0: continue
        r = {"Jenis Pemeriksaan": name, "Jumlah Sampel": n}; over = []; anyref = False
        for key, lab, _ in m:
            v = _num(g[key]).dropna()
            r[f"{lab} Median (Q2)"] = float(np.percentile(v, 50)) if len(v) else np.nan
            r[f"{lab} Q3 (P75)"] = float(np.percentile(v, 75)) if len(v) else np.nan
            ref = cfg["tpd"].get(mod, {}).get(name, {}).get(key.replace("DAP_Gy","DAP").replace("DAP_mGy","DAP")) if key != "Fluoro menit" else None
            if key != "Fluoro menit":
                r[f"{lab} Acuan"] = ref if kategori == "Dewasa" else np.nan
                if kategori == "Dewasa" and ref not in (None, ""):
                    anyref = True
                    if r[f"{lab} Q3 (P75)"] > float(ref): over.append(lab)
        r["Status"] = "-" if kategori != "Dewasa" else ("Acuan belum diisi" if not anyref else ("Di atas acuan: " + ", ".join(over) if over else "Sesuai acuan"))
        rows.append(r)
    return pd.DataFrame(rows)


# ====================== IMPORT RIS ======================
import re
RIS_MAP = {"RN":"Kode Pasien","PATIENT NAME":"Nama","GENDER":"Gender","AGE":"Umur","WEIGHT":"Berat Badan","CHECK IN DATE":"Tanggal",
           "DESCRIPTION":"Deskripsi RIS","VISIT NO.":"Visit No","MODALITY":"MOD_RIS"}
IGNORED = ["ULTRASOUND","MRI","PET","SPECT","THERAPY","NON-RADIOLOGY","OT"]

def read_ris(file):
    """Baca ekspor RIS: cari baris judul (yang memuat 'MODALITY' & 'DESCRIPTION') otomatis."""
    name = getattr(file, "name", "").lower()
    if name.endswith(".csv"):
        raw = pd.read_csv(file, header=None, dtype=object)
    else:
        raw = pd.read_excel(file, header=None, dtype=object)
    for i in range(min(40, len(raw))):
        vals = [str(v).strip().upper() for v in raw.iloc[i].tolist()]
        if "MODALITY" in vals and "DESCRIPTION" in vals:
            df = raw.iloc[i+1:].copy(); df.columns = vals; df = df.dropna(how="all"); return df.reset_index(drop=True)
    raise ValueError("Baris judul tidak ditemukan. Pastikan file memuat kolom MODALITY dan DESCRIPTION.")

_GR_RULES = [("TSPINE", r"THORACO|THORACAL|THORACOLUM|TORAKOLUM"), ("LSPINE", r"LUMBOSACRAL|LUMBAL|LUMBAR|LS SPINE|L-S"), ("CSPINE", r"CERVICAL|SERVIKAL"),
 ("LONG LIMB", r"FULL SPINE|LONG LIMB|SCOLIOSIS|SKOLIOSIS|WHOLE SPINE"), ("CHEST", r"THORAX|CHEST|PARU|COR\b|HEART"), ("KNEE", r"KNEE|GENU|LUTUT"),
 ("HAND", r"MANUS|HAND|FINGER|JARI"), ("FOOT", r"PEDIS|FOOT|CALCANEUS|TOE"), ("PELVIS", r"PELVI|HIP|SACRO|SI JOINT"), ("ABDOMEN", r"ABDOMEN|BNO|BOF"),
 ("SKULL", r"SKULL|CRANIUM|KEPALA|CRANIAL|MASTOID|ORBITA|NASAL|MANDIBULA|FACIAL"), ("SINUS", r"SINUS|WATERS"), ("ANKLE", r"ANKLE"), ("LEG", r"CRURIS|TIBIA|LEG\b|FIBULA"),
 ("SHOULDER", r"SHOULDER|BAHU|SCAPULA"), ("ELBOW", r"ELBOW|SIKU"), ("WRIST", r"WRIST|PERGELANGAN"), ("FEMUR", r"FEMUR"), ("HUMERUS", r"HUMERUS"),
 ("ANTEBRAKHI", r"ANTEBRA|FOREARM|RADIUS|ULNA"), ("CLAVICLE", r"CLAVIC"), ("COCCYX", r"COCCY|COXY")]
_DENT = [("PANORAMIK", r"PANORAM"), ("CEPHALO", r"CEPH"), ("CBCT", r"CBCT|CONE BEAM"), ("INTRAORAL", r"INTRA ?ORAL|PERIAPICAL|BITE ?WING|OCCLUSAL")]
GR_ALIAS = {"CLAVICLE": "CLAVICLE"}

def _clean(desc, prefix):
    t = re.sub(r"\s+", " ", str(desc)).strip()
    return re.sub(r"^" + re.escape(prefix) + r"\s+", "", t, flags=re.I)

def classify(mod_ris, desc):
    """Kembalikan (modalitas dosis | None, nama pemeriksaan standar)."""
    m = str(mod_ris).strip().upper(); u = str(desc).upper()
    if m == "GENERAL X-RAY":
        for std, pat in _DENT:
            if re.search(pat, u): return "DENTAL", std
        for std, pat in _GR_RULES:
            if re.search(pat, u): return "GR", std
        return "GR", _clean(desc, "GENERAL X-RAY").upper()
    if m == "CT SCAN":
        t = _clean(desc, "CT SCAN")
        if re.search(r"CALCIUM", t, re.I): return "CT", "CT SCAN Calcium Score"
        if re.search(r"CORONARY", t, re.I): return "CT", "CT SCAN Included Coronary CTA"
        return "CT", "CT SCAN " + t
    if m == "MAMMOGRAPHY":
        return "MAMMO", ("MAMMOGRAFI 3D (TOMOSYNTHESIS)" if re.search(r"3D|TOMO", u) else "MAMMOGRAFI 2D")
    if m == "FLUOROSCOPY": return "FLURO", _clean(desc, "FLUOROSCOPY")
    return None, ""

def parse_ris(raw):
    """RIS mentah -> (DataFrame rapi dgn kolom Modalitas, ringkasan)."""
    df = raw.rename(columns=RIS_MAP)
    for c in RIS_MAP.values():
        if c not in df.columns: df[c] = None
    cl = [classify(m, d) for m, d in zip(df["MOD_RIS"], df["Deskripsi RIS"])]
    df["Modalitas"] = [c[0] for c in cl]; df["Jenis Periksa"] = [c[1] for c in cl]
    skipped = df[df["Modalitas"].isna()]["MOD_RIS"].astype(str).str.upper().value_counts().to_dict()
    df = df[df["Modalitas"].notna()].copy()
    df["Gender"] = df["Gender"].astype(str).str.upper().str[0].map({"M": "M", "F": "F"})
    df["Umur"] = pd.to_numeric(df["Umur"], errors="coerce")
    w = pd.to_numeric(df["Berat Badan"], errors="coerce"); df["Berat Badan"] = w.where(w > 0)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")
    df["Nama"] = df["Nama"].astype(str).str.strip().replace({"nan": None})
    df["_key"] = (df["Kode Pasien"].astype(str) + "|" + df["Visit No"].astype(str) + "|" + df["Deskripsi RIS"].astype(str).str.strip() + "|" + df["Tanggal"].astype(str))
    df = df.drop_duplicates("_key")
    keep = ["Modalitas", "_key"] + ID_COLS
    return df[keep].reset_index(drop=True), skipped

def empty_master():
    cols = ["_rid", "Modalitas", "_key"] + ID_COLS + sorted({c for v in _D.values() for c in v})
    return pd.DataFrame(columns=cols)

def add_rows(master, new):
    """Gabungkan hasil import; lewati baris yang sudah ada (berdasar _key). Kembalikan (master, baris_baru)."""
    exist = set(master["_key"].dropna()) if "_key" in master.columns else set()
    n = new[~new["_key"].isin(exist)].copy()
    start = int(pd.to_numeric(master["_rid"], errors="coerce").max() + 1) if len(master) and master["_rid"].notna().any() else 0
    n["_rid"] = range(start, start + len(n))
    out = pd.concat([master, n], ignore_index=True) if len(master) else n.reindex(columns=empty_master().columns)
    return out, n

def register_exams(cfg, newrows):
    """Tambahkan nama pemeriksaan baru ke daftar acuan (acuan kosong)."""
    for mod, g in newrows.groupby("Modalitas"):
        lst = cfg["tpd"].setdefault(mod, {})
        for n in g["Jenis Periksa"].dropna().unique():
            lst.setdefault(n, {})
    return cfg

def apply_edits(master, shown_ids, edited, mod):
    """Terapkan hasil edit tabel (subset) ke master: ubah, hapus, dan tambah baris."""
    m = master.copy(); e = edited.copy()
    e["_rid"] = pd.to_numeric(e.get("_rid"), errors="coerce")
    kept = set(e["_rid"].dropna().astype(int))
    m = m[~((m["_rid"].astype(int).isin(set(shown_ids))) & (~m["_rid"].astype(int).isin(kept)))]
    old = e[e["_rid"].notna()].copy(); old["_rid"] = old["_rid"].astype(int)
    m = m.set_index(m["_rid"].astype(int))
    for col in old.columns:
        if col == "_rid": continue
        if col not in m.columns: m[col] = None
        m[col] = m[col].astype(object)
        m.loc[old["_rid"].values, col] = old[col].astype(object).values
    m = m.reset_index(drop=True)
    new = e[e["_rid"].isna()].copy()
    new = new[new.drop(columns=["_rid"]).notna().any(axis=1)]
    if len(new):
        start = int(pd.to_numeric(m["_rid"], errors="coerce").max() + 1) if len(m) else 0
        new["_rid"] = range(start, start + len(new)); new["Modalitas"] = mod
        m = pd.concat([m, new], ignore_index=True)
    return m

# ====================== EXCEL BAPETEN ======================
def to_excel(mod, d, rekaps, cfg, meta, include_name=False):
    """rekaps: {judul: DataFrame}. Sheet: Rekap per kategori usia, Data (nilai), Parameter."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter as L
    wb = Workbook(); wb.remove(wb.active)
    navy = PatternFill("solid", fgColor="073763"); thin = Side(style="thin", color="B7C4D4"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    def put(sh, df, r0):
        for j, c in enumerate(df.columns, 1):
            h = sh.cell(r0, j, c); h.fill = navy; h.font = Font(bold=True, color="FFFFFF"); h.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center"); h.border = bd
            w = max(12, min(40, max([len(str(c))] + [len(str(v)) for v in df[c].head(200)]) + 2)); sh.column_dimensions[L(j)].width = w
        for i, row in enumerate(df.itertuples(index=False), r0 + 1):
            for j, v in enumerate(row, 1):
                if v is pd.NaT: v = None
                if isinstance(v, float) and np.isnan(v): v = None
                if isinstance(v, np.integer): v = int(v)
                if isinstance(v, np.floating): v = float(v)
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
                c = sh.cell(i, j, v); c.border = bd
                if isinstance(v, float): c.number_format = "0.00"
                if hasattr(v, "year"): c.number_format = "dd/mm/yyyy"
        sh.row_dimensions[r0].height = 40
    for title, rk in rekaps.items():
        ws = wb.create_sheet(f"Rekap {title}"[:31])
        ws["A1"] = f"Rekap Dosis Pasien {MODS[mod]['label']} - Laporan BAPETEN"; ws["A1"].font = Font(size=14, bold=True, color="073763")
        ws["A2"] = f"{meta.get('rs','')} | Kategori usia: {title} | Periode: {meta.get('periode','semua')}"
        ws["A3"] = "Median (Q2) dan persentil-75 (Q3) lokal; acuan nasional hanya untuk Dewasa."; ws["A3"].font = Font(italic=True, size=9, color="5C7691")
        put(ws, rk if len(rk) else pd.DataFrame({"Info": ["Tidak ada data valid"]}), 5); ws.column_dimensions["A"].width = 38
    drop = ["Deskripsi RIS", "Visit No"] + ([] if include_name else ["Nama"])
    dd = d.drop(columns=[c for c in drop if c in d.columns])
    wd = wb.create_sheet("Data"); put(wd, dd, 1); wd.freeze_panes = "A2"; wd.auto_filter.ref = wd.dimensions
    wp = wb.create_sheet("Parameter"); rows = [("BSF", cfg["bsf"]), ("Bayi maks (th)", cfg["bayi_max"]), ("Dewasa min (th)", cfg["dewasa_min"])]
    co = fit_output(cfg["out_pts"])
    if co: rows.append(("Koefisien output a,b,c", f"{co[0]:.5f}, {co[1]:.4f}, {co[2]:.3f}"))
    for i, (a, b) in enumerate(rows, 1): wp.cell(i, 1, a).font = Font(bold=True); wp.cell(i, 2, b)
    wp.column_dimensions["A"].width = 26
    bio = io.BytesIO(); wb.save(bio); return bio.getvalue()
