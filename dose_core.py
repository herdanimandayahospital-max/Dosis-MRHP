"""Logika murni Dose Monitoring (tanpa Streamlit) - dapat diuji terpisah."""
import io, numpy as np, pandas as pd

ID_COLS = ["Kode Pasien","Nama","Gender","Umur","Berat Badan","Tanggal","Jenis Periksa","Deskripsi RIS","Visit No"]
_D = {"GR": ["Posisi","Proyeksi","FDD","kV","mA","s","mAs"], "CT": ["No of Phase","CTDIvol","DLP"],
      "MAMMO": ["Proyeksi","Grid","AEC","kV","mA","s","mAs","Sudut DBT","Tebal kompresi","DAP","ESAK","MGD"],
      "FLURO": ["Fluoro detik","Laju frame","Jumlah frame","DAP","Laju kerma udara","Kerma total","Akses"],
      "CATH": ["Fluoro detik","Laju frame","Jumlah frame","DAP","Laju kerma udara","Kerma total","Akses"], "DENTAL": ["kV","mAs","FSD","DAP"]}
MODS = {
 "GR": dict(label="Radiografi Umum", exam="Jenis Periksa", cols=ID_COLS+_D["GR"], dose=_D["GR"],
   metrics=[("INAK","INAK (mGy)","0.00"),("ESAK","ESAK (mGy)","0.00")]),
 "CT": dict(label="CT Scan", exam="Jenis Periksa", cols=ID_COLS+_D["CT"], dose=_D["CT"],
   metrics=[("CTDIvol","CTDIvol (mGy)","0.0"),("DLP","DLP (mGy.cm)","0")]),
 "MAMMO": dict(label="Mamografi", exam="Jenis Periksa", cols=ID_COLS+_D["MAMMO"], dose=_D["MAMMO"],
   metrics=[("MGD","MGD (mGy)","0.00")]),
 "FLURO": dict(label="Fluoroskopi", exam="Jenis Periksa", cols=ID_COLS+_D["FLURO"], dose=_D["FLURO"],
   metrics=[("DAP_Gy","DAP (Gy.cm2)","0.0"),("Kerma total","Kerma total (mGy)","0"),("Fluoro menit","Fluoro (menit)","0.0")]),
 "CATH": dict(label="Cathlab", exam="Jenis Periksa", cols=ID_COLS+_D["CATH"], dose=_D["CATH"],
   metrics=[("DAP_Gy","DAP (Gy.cm2)","0.0"),("Kerma total","Kerma total (mGy)","0"),("Fluoro menit","Fluoro (menit)","0.0")]),
 "DENTAL": dict(label="Dental", exam="Jenis Periksa", cols=ID_COLS+_D["DENTAL"], dose=_D["DENTAL"],
   metrics=[("DAP_mGy","DAP (mGy.cm2)","0.0")]),
}
DEFAULT_CFG = dict(
  staff_units=["Cath-Lab","OT","Radiologi","Poli Gigi","Poli BMD","Kedokteran Nuklir"], periods=["Des-Feb","Mar-Mei","Jun-Agt","Sep-Nov","Des-Feb"], nbd_rs=10.0,
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
        mas = _num(d["mAs"]); d["mAs dipakai"] = mas.fillna(_num(d["mA"]) * _num(d["s"]))
        need = _num(d["MGD"]).isna(); msg_need = "MGD belum lengkap"
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
    for c in sorted({c for v in _D.values() for c in v}):
        if c in out.columns: out[c] = out[c].astype(object)
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


# ====================== FORMAT RESMI BAPETEN (Target_*.xls) ======================
# header = teks persis template; src = kolom sumber (None = kosong)
def _H(*a): return list(a)
BAPETEN = {
 "GR": dict(title=None, note=None, hh=30, foot_to=13, headers=[
    ("No", None, 5.6), ("Kode Pasien", "Kode Pasien", 17.1), ("Nama Pasien", "Nama", 20.4), ("Gender\n[Male atau Female]", "Gender", 19.4), ("Umur \n(th)", "Umur", 11.8),
    ("Berat Badan \n(kg)", "Berat Badan", 12.7), ("Posisi\n[Standing atau Supine]", "Posisi", 24.3), ("Proyeksi", "Proyeksi", 12.7), ("FDD\n(cm)", "FDD", 8.4),
    ("kV", "kV", 7.0), ("mA", "mA", 7.4), ("s", "s", 9.3), ("mAs", "mAs dipakai", 9.4)]),
 "CT": dict(title=None, note="Note: Silahkan isi semua form dengan data sample pasien (minimal 10 data) berdasarkan kelompok umur yang telah dibuat pada setting data survey Anda. ",
    hh=30, foot_to=9, headers=[
    ("No", None, 5.6), ("Kode Pasien\n(Jika Ada)", "Kode Pasien", 23.1), ("Nama Pasien\n(Jika Ada)", "Nama", 30.9), ("Gender *\n[Male atau Female]", "Gender", 20.3),
    ("Umur * \n(th)", "Umur", 16.7), ("Berat Badan *\n(kg)", "Berat Badan", 19.9), ("No of Phase *\n[ 0/1/2/3/>=4 ]", "No of Phase", 20.6),
    ("Average CTDI *\n(mGy)", "CTDIvol", 23.6), ("Total DLP *\n(mGy cm)", "DLP", 19.0)]),
 "MAMMO": dict(title="FORM MAMOGRAFI DENGAN INDIKATOR DOSIS", note="Note: (1) Gunakan simbol titik (.) untuk angka desimal. contoh: 2.05  (2) Untuk tipe pilihan, silahkan isikan sesuai dengan pilihan yang telah disediakan",
    hh=30, foot_to=13, headers=[
    ("No", None, 5.6), ("Kode Pasien", "Kode Pasien", 17.6), ("Nama Pasien", "Nama", 17.7), ("Gender\n[Male atau Female]", "Gender", 21.6), ("Umur \n(th)", "Umur", 11.7),
    ("Berat Badan \n(kg)", "Berat Badan", 12.1), ("Pilih Proyeksi\n[LCC/LMLO/RCC/RMLO]", "Proyeksi", 24.4), ("Pilih Grid\n[Y/N]", "Grid", 12.7), ("Pilih AEC\n[On/Off]", "AEC", 12.7),
    ("kV", "kV", 8.0), ("mA", "mA", 7.0), ("s", "s", 7.3), ("mAs", "mAs dipakai", 8.6), ("\u03a3 Projection Angle of DBT", "Sudut DBT", 18.1),
    ("T, Tebal Kompresi (mm)", "Tebal kompresi", 17.9), ("DAP (mGy.cm2)", "DAP", 13.0), ("ESAK (mGy)", "ESAK", 14.3), ("MGD (mGy)", "MGD", 12.0)]),
 "IR": dict(title=None, note="Note: Kateter masuk melalui Radial [R] atau Femoral [F] atau Others [O] ", hh=45, foot_to=11, headers=[
    ("No", None, 5.6), ("Kode Pasien", "Kode Pasien", 17.1), ("Nama Pasien", "Nama", 20.4), ("Gender\n[Male atau Female]", "Gender", 19.4), ("Umur \n(th)", "Umur", 11.8),
    ("Berat Badan \n(kg)", "Berat Badan", 12.7), ("Fluoro Total \n(detik)", "Fluoro detik", 16.7), ("Laju Frame\n(fr/s)", "Laju frame", 14.7), ("Jumlah\n(frame/citra)", "Jumlah frame", 16.0),
    ("DAP\n ( Gy.cm2)", "DAP_Gy", 22.6), ("Laju Kerma Udara \n(mGy/jam)", "Laju kerma udara", 17.6), ("Kerma Total \n(mGy)", "Kerma total", 13.3), ("Kateter masuk via \n(R/F/O)", "Akses", 15.6)]),
}
BAPETEN_FORM = {"GR": "GR", "CT": "CT", "MAMMO": "MAMMO", "CATH": "IR", "FLURO": "IR"}   # DENTAL: template belum ada

def _clean_val(v):
    if v is None or v is pd.NaT: return None
    if isinstance(v, float) and np.isnan(v): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)):
        v = float(v); return int(v) if v.is_integer() else round(v, 4)
    return v

def bapeten_xlsx(mod, df, include_name=False):
    """Satu file sesuai template resmi BAPETEN (header, catatan, lebar kolom, kotak data, footer)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter as L
    sp = BAPETEN[BAPETEN_FORM[mod]]; n = len(sp["headers"]); ws = (wb := Workbook()).active; ws.title = "Sheet1"
    thin = Side(style="thin"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    if sp["title"]:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n); c = ws.cell(1, 1, sp["title"])
        c.font = Font(name="Calibri", size=11, bold=True); c.fill = PatternFill("solid", fgColor="FFCC99"); c.alignment = Alignment(horizontal="center")
        for j in range(1, n + 1): ws.cell(1, j).fill = PatternFill("solid", fgColor="FFCC99")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n); c = ws.cell(2, 1, "DATA SURVEY")
    c.font = Font(name="Calibri", size=20, bold=True); c.alignment = Alignment(horizontal="center"); ws.row_dimensions[2].height = 26.25
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=n)
    if sp["note"]: c = ws.cell(3, 1, sp["note"]); c.font = Font(name="Calibri", size=11); c.alignment = Alignment(horizontal="left")
    ws.row_dimensions[4].height = sp["hh"]
    for j, (h, src, w) in enumerate(sp["headers"], 1):
        c = ws.cell(4, j, h); c.font = Font(name="Calibri", size=11, bold=True); c.fill = PatternFill("solid", fgColor="CCCCFF")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = bd; ws.column_dimensions[L(j)].width = w
    d = df.copy()
    if "Gender" in d.columns: d["Gender"] = d["Gender"].map({"M": "Male", "F": "Female"}).fillna(d["Gender"])
    if not include_name and "Nama" in d.columns: d["Nama"] = None
    rows = max(len(d), 30)
    for i in range(rows):
        r = 5 + i
        for j, (h, src, w) in enumerate(sp["headers"], 1):
            v = (i + 1) if (src is None and i < len(d)) else (_clean_val(d.iloc[i][src]) if (src and i < len(d) and src in d.columns) else None)
            c = ws.cell(r, j, v); c.border = bd; c.font = Font(name="Calibri", size=11)
    fr = 5 + rows + 1
    ws.merge_cells(start_row=fr, start_column=1, end_row=fr, end_column=sp["foot_to"]); c = ws.cell(fr, 1, "Badan Pengawas Tenaga Nuklir (BAPETEN)")
    c.font = Font(name="Calibri", size=11, bold=True); c.alignment = Alignment(horizontal="center")
    ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0; ws.sheet_properties.pageSetUpPr.fitToPage = True
    bio = io.BytesIO(); wb.save(bio); return bio.getvalue()

def _slug(t): return re.sub(r"[^A-Za-z0-9]+", "_", str(t)).strip("_")[:60] or "x"

REQ = ["Gender", "Umur", "Berat Badan"]
def bapeten_combos(mod, dv, exams, cats, require_bb=True):
    """dv = data valid (Cek OK). Hasil: list dict(exam, kategori, df, n). Syarat wajib: gender, umur, BB (+ fase CT)."""
    ex = MODS[mod]["exam"]; out = []; req = REQ + (["No of Phase"] if mod == "CT" else [])
    if not require_bb: req = [c for c in req if c != "Berat Badan"]
    ok = dv.copy()
    for c in req: ok = ok[ok[c].notna() & (ok[c].astype(str).str.strip() != "")] if c in ok.columns else ok.iloc[0:0]
    names = exams or sorted(ok[ex].dropna().unique())
    for e in names:
        for k in cats:
            g = ok[(ok[ex] == e) & (ok["Kategori usia"] == k)]
            if len(g): out.append(dict(exam=e, kategori=k, df=g.sort_values("Tanggal") if "Tanggal" in g.columns else g, n=len(g)))
    return out, len(dv) - len(ok)

def bapeten_zip(mod, combos, include_name=False):
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for c in combos: z.writestr(bapeten_filename(mod, c), bapeten_xlsx(mod, c["df"], include_name))
    return bio.getvalue()

def bapeten_filename(mod, c): return f"BAPETEN_{BAPETEN_FORM[mod]}_{_slug(c['exam'])}_{c['kategori']}.xlsx"


# ====================== DASHBOARD DRL ======================
def _fv(v):
    v = float(v); return f"{v:,.0f}" if abs(v) >= 100 else (f"{v:.1f}" if abs(v) >= 10 else f"{v:.2f}")

def drl_html(rk, lab):
    """Bar HTML: DRL lokal (typical value = median Q2) vs DRL nasional per jenis pemeriksaan."""
    q2c, acc, nc = f"{lab} Median (Q2)", f"{lab} Acuan", "Jumlah Sampel"
    if rk is None or rk.empty or q2c not in rk.columns: return ""
    vals = [v for v in rk[q2c].tolist() + (rk[acc].tolist() if acc in rk.columns else []) if v is not None and not pd.isna(v)]
    mx = max(vals) if vals else 1.0
    out = ['<div class="drl"><div class="drl-leg"><span><i style="background:#073763"></i>DRL lokal (typical value = Q2)</span><span><i style="background:#9ccbe0"></i>DRL nasional</span></div>']
    for _, r in rk.iterrows():
        q2 = r[q2c]; ref = r[acc] if acc in rk.columns else None
        has_ref = ref is not None and not pd.isna(ref) and float(ref) > 0
        ratio = (q2 / float(ref) * 100) if (has_ref and not pd.isna(q2)) else None
        badge = ('<span class="rb na">acuan belum diisi</span>' if ratio is None else
                 f'<span class="rb {"bad" if ratio > 100 else "ok"}">{ratio:.0f}% dari nasional</span>')
        n = int(r[nc]); small = f' <span class="rn">n={n}</span>' + (' <span class="rn warn">n&lt;10</span>' if n < 10 else "")
        w1 = 0 if pd.isna(q2) else max(1.5, float(q2) / mx * 100)
        bars = f'<div class="bar"><div class="trk"><div class="b1" style="width:{w1:.1f}%"></div></div><span>{_fv(q2) if not pd.isna(q2) else "-"}</span></div>'
        if has_ref: bars += f'<div class="bar"><div class="trk"><div class="b2" style="width:{max(1.5, float(ref)/mx*100):.1f}%"></div></div><span>{_fv(ref)}</span></div>'
        out.append(f'<div class="drl-row"><div class="drl-n">{str(r["Jenis Pemeriksaan"])}{small}</div><div class="drl-b">{bars}</div><div class="drl-r">{badge}</div></div>')
    out.append("</div>"); return "".join(out)


def _nice_max(v):
    if v <= 0: return 1.0
    e = 10 ** np.floor(np.log10(v)); f = v / e
    return float((1 if f <= 1 else 2 if f <= 2 else 2.5 if f <= 2.5 else 5 if f <= 5 else 10) * e)

def drl_svg(rk, lab):
    """Grafik batang vertikal berkelompok: Q2 lokal vs DRL nasional per jenis pemeriksaan (SVG)."""
    import textwrap, html as _h
    q2c, acc = f"{lab} Median (Q2)", f"{lab} Acuan"
    if rk is None or rk.empty or q2c not in rk.columns: return ""
    r = rk.reset_index(drop=True); n = len(r)
    q = pd.to_numeric(r[q2c], errors="coerce"); a = pd.to_numeric(r[acc], errors="coerce") if acc in r.columns else pd.Series([np.nan] * n)
    top = _nice_max(float(max(q.max(skipna=True) if q.notna().any() else 0, a.max(skipna=True) if a.notna().any() else 0)) * 1.08)
    gw, bw = 96, 26; ml, mr, mt, mb = 52, 16, 74, 78
    W = max(560, ml + mr + gw * n); H = 360; ph = H - mt - mb
    y = lambda v: mt + ph - (v / top) * ph
    s = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" font-family="Lexend,sans-serif" role="img" aria-label="Grafik {_h.escape(lab)}">']
    for i in range(6):
        v = top * i / 5; yy = y(v)
        s.append(f'<line x1="{ml}" x2="{W-mr}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#E3EBF3"/><text x="{ml-8}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="#5C7691">{v:g}</text>')
    s.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#9fb3c8"/>')
    for i in range(n):
        cx = ml + gw * i + gw / 2; name = str(r.loc[i, "Jenis Pemeriksaan"]); nn = int(r.loc[i, "Jumlah Sampel"])
        has = not pd.isna(a[i]); v1 = q[i]
        over = has and not pd.isna(v1) and v1 > a[i]
        x1 = cx - bw - 2 if has else cx - bw / 2
        if not pd.isna(v1):
            col = "#c0392b" if over else "#073763"
            s.append(f'<rect x="{x1:.1f}" y="{y(v1):.1f}" width="{bw}" height="{max(1, y(0)-y(v1)):.1f}" rx="3" fill="{col}"><title>{_h.escape(name)} - lokal Q2: {_fv(v1)} (n={nn})</title></rect>'
                     f'<text x="{x1+bw/2:.1f}" y="{y(v1)-5:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="{col}">{_fv(v1)}</text>')
        if has:
            x2 = cx + 2
            s.append(f'<rect x="{x2:.1f}" y="{y(a[i]):.1f}" width="{bw}" height="{max(1, y(0)-y(a[i])):.1f}" rx="3" fill="#9ccbe0"><title>{_h.escape(name)} - nasional: {_fv(a[i])}</title></rect>'
                     f'<text x="{x2+bw/2:.1f}" y="{y(a[i])-5:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="#2b6f8e">{_fv(a[i])}</text>')
        short = name.replace("CT SCAN ", "")
        lines = textwrap.wrap(short, 15)[:3]
        if len(textwrap.wrap(short, 15)) > 3: lines[-1] = lines[-1][:12] + "…"
        for k, ln in enumerate(lines):
            s.append(f'<text x="{cx:.1f}" y="{y(0)+16+k*13:.1f}" text-anchor="middle" font-size="11" fill="#073763">{_h.escape(ln)}</text>')
        s.append(f'<text x="{cx:.1f}" y="{y(0)+16+len(lines)*13:.1f}" text-anchor="middle" font-size="10" fill="{"#8a5a00" if nn < 10 else "#7b8da1"}">n={nn}{" (&lt;10)" if nn < 10 else ""}</text>')
    s.append(f'<text x="{ml}" y="22" font-size="16" font-weight="700" fill="#073763">Perbandingan DRL Lokal dengan DRL Nasional</text>'
             f'<text x="{ml}" y="40" font-size="11" fill="#5C7691">{_h.escape(lab)} · lokal = typical value (median / Quartil 2)</text>')
    lx = ml
    for col, txt, wd in (("#073763", "DRL lokal (Q2)", 120), ("#c0392b", "Lokal melebihi nasional", 170), ("#9ccbe0", "DRL nasional", 110)):
        s.append(f'<rect x="{lx}" y="50" width="12" height="12" rx="3" fill="{col}"/><text x="{lx+18}" y="60" font-size="11" fill="#073763">{txt}</text>'); lx += wd
    s.append("</svg>")
    leg = ""
    return f'{leg}<div style="overflow-x:auto;padding-bottom:6px">{"".join(s)}</div>'


# ====================== DOSIS PEKERJA / STAFF ======================
import json as _json, os as _os
PK = ["P1", "P2", "P3", "P4", "P5"]
SPECIAL = ["n/a", "Pergantian TLD", "Penambahan TLD Baru", "Resign"]
ROSTER_COLS = ["SID", "No TLD", "Nama", "Unit", "Status", "Catatan"]
SDOSE_COLS = ["Tahun", "SID"] + PK + ["NBD", "Catatan"]

def sval(v):
    """Angka mSv dari isian (boleh koma). Teks khusus (n/a, Resign, ...) -> None."""
    if v is None or (isinstance(v, float) and np.isnan(v)): return None
    try: return float(str(v).strip().replace(",", "."))
    except ValueError: return None

def staff_total(row):
    return round(sum(x for x in (sval(row.get(p)) for p in PK) if x is not None), 4)

def empty_roster(): return pd.DataFrame(columns=ROSTER_COLS)
def empty_sdose(): return pd.DataFrame(columns=SDOSE_COLS)

def next_sid(roster): return int(pd.to_numeric(roster["SID"], errors="coerce").max() + 1) if len(roster) and roster["SID"].notna().any() else 1

def seed_staff():
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "seed_pekerja.json")
    if not _os.path.exists(p): return empty_roster(), empty_sdose()
    d = _json.load(open(p, encoding="utf-8"))
    st_ = {int(k): v for k, v in d.get("status", {}).items()}
    r = pd.DataFrame([{"SID": x["sid"], "No TLD": x["tld"], "Nama": x["nama"], "Unit": x["unit"], "Status": st_.get(x["sid"], "Aktif"), "Catatan": None} for x in d["roster"]])
    s = pd.DataFrame([{"Tahun": x["Tahun"], "SID": x["SID"], **{k: (x[k] if x[k] != "" else None) for k in PK}, "NBD": x["NBD"], "Catatan": None} for x in d["dose"]])
    return r, s

def staff_year(roster, sdose, tahun, unit=None):
    """Tabel isian satu tahun (semua petugas aktif + yang punya data di tahun itu), format rekap PDF."""
    r = roster.copy()
    if unit: r = r[r["Unit"] == unit]
    d = sdose[pd.to_numeric(sdose["Tahun"], errors="coerce") == int(tahun)] if len(sdose) else sdose
    has = set(pd.to_numeric(d["SID"], errors="coerce").dropna().astype(int)) if len(d) else set()
    r = r[(r["Status"].fillna("Aktif") != "Resign") | r["SID"].astype(int).isin(has)] if len(r) else r
    m = r.merge(d.drop(columns=["Tahun"], errors="ignore").assign(SID=lambda x: pd.to_numeric(x["SID"], errors="coerce")) if len(d) else pd.DataFrame(columns=["SID"] + PK + ["NBD"]),
                on="SID", how="left", suffixes=("", "_d"))
    for p in PK:
        if p not in m.columns: m[p] = None
    if "NBD" not in m.columns: m["NBD"] = None
    m["NBD"] = pd.to_numeric(m["NBD"], errors="coerce")
    m["Total"] = [staff_total(x) for x in m.to_dict("records")]
    return m[["SID", "Unit", "No TLD", "Nama"] + PK + ["NBD", "Total"]].reset_index(drop=True)

def staff_save_year(sdose, tahun, edited, default_nbd=10.0):
    """Gabungkan hasil edit satu tahun ke tabel dosis (ganti baris SID yang sama)."""
    e = edited.copy(); e["SID"] = pd.to_numeric(e["SID"], errors="coerce").astype(int)
    keep = sdose[~((pd.to_numeric(sdose["Tahun"], errors="coerce") == int(tahun)) & (pd.to_numeric(sdose["SID"], errors="coerce").isin(e["SID"])))] if len(sdose) else sdose
    new = pd.DataFrame({"Tahun": int(tahun), "SID": e["SID"].values, **{p: e[p].values for p in PK}, "NBD": pd.to_numeric(e["NBD"], errors="coerce").fillna(default_nbd).values, "Catatan": None})
    new = new[new[PK].notna().any(axis=1) | (new["SID"] > 0)]
    return pd.concat([keep, new], ignore_index=True)

def staff_status(total, nbd):
    nbd = nbd if (nbd is not None and not pd.isna(nbd)) else 10.0
    return "Melebihi NBD RS" if total > nbd else "Normal"

def mark_before(sdose, sid, tahun, start_idx, label, nbd=10.0):
    """Periode sebelum start_idx (0-4) yang masih kosong diberi label (mis. 'Pergantian TLD')."""
    s = sdose.copy(); m = (pd.to_numeric(s["Tahun"], errors="coerce") == int(tahun)) & (pd.to_numeric(s["SID"], errors="coerce") == int(sid))
    if not m.any():
        s = pd.concat([s, pd.DataFrame([{"Tahun": int(tahun), "SID": int(sid), **{p: None for p in PK}, "NBD": nbd, "Catatan": None}])], ignore_index=True)
        m = (pd.to_numeric(s["Tahun"], errors="coerce") == int(tahun)) & (pd.to_numeric(s["SID"], errors="coerce") == int(sid))
    for p in PK[:start_idx]:
        s.loc[m, p] = s.loc[m, p].apply(lambda v: label if (v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() == "") else v)
    return s

def staff_excel(tahun, tbl, labels):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook(); ws = wb.active; ws.title = f"Rekap {tahun}"
    thin = Side(style="thin", color="7F7F7F"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws["A1"] = f"Rekap Dosis Pekerja Radiasi Tahun {tahun}"; ws["A1"].font = Font(size=14, bold=True); ws.merge_cells("A1:J1"); ws["A1"].alignment = Alignment(horizontal="center")
    r = 3
    hdr = ["No", "No TLD", "Nama Petugas"] + labels + ["NBD RS (mSv)", "Total Dosis Dalam 1 Tahun (mSv)"]
    for unit, g in tbl.groupby("Unit", sort=False):
        ws.cell(r, 1, unit).font = Font(bold=True); ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(hdr))
        for j in range(1, len(hdr) + 1): ws.cell(r, j).fill = PatternFill("solid", fgColor="DCE6F1")
        ws.cell(r, 1).alignment = Alignment(horizontal="center"); r += 1
        ws.cell(r, 4, "Dosis (mSv)").font = Font(bold=True); ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=3 + len(labels)); ws.cell(r, 4).alignment = Alignment(horizontal="center"); r += 1
        for j, h in enumerate(hdr, 1):
            c = ws.cell(r, j, h); c.font = Font(bold=True); c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = bd
        r += 1
        for i, x in enumerate(g.to_dict("records"), 1):
            vals = [i, x["No TLD"], x["Nama"]] + [(sval(x[p]) if sval(x[p]) is not None else (x[p] if x[p] not in (None, "") and not (isinstance(x[p], float) and np.isnan(x[p])) else None)) for p in PK] + [x["NBD"], x["Total"]]
            for j, v in enumerate(vals, 1):
                c = ws.cell(r, j, v); c.border = bd; c.alignment = Alignment(horizontal="left" if j == 3 else "center")
                if j == len(vals): c.fill = PatternFill("solid", fgColor="BDD7EE")
                if j == len(vals) - 1: c.fill = PatternFill("solid", fgColor="D9D9D9")
            r += 1
        r += 1
    for col, w in zip("ABCDEFGHIJ", (5, 16, 40, 11, 11, 11, 11, 11, 13, 20)): ws.column_dimensions[col].width = w
    bio = io.BytesIO(); wb.save(bio); return bio.getvalue()

def staff_pdf(tahun, tbl, labels, rs=""):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    bio = io.BytesIO(); doc = SimpleDocTemplate(bio, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    st = getSampleStyleSheet(); el = [Paragraph(f"<b>Rekapitulasi Dosis Pekerja Radiasi Tahun {tahun}</b>", st["Title"])]
    if rs: el.append(Paragraph(rs, st["Normal"]))
    for unit, g in tbl.groupby("Unit", sort=False):
        el += [Spacer(1, 10), Paragraph(f"<b>{unit}</b>", st["Heading3"])]
        data = [["No", "No TLD", "Nama Petugas"] + labels + ["NBD RS\n(mSv)", "Total 1 Tahun\n(mSv)"]]
        for i, x in enumerate(g.to_dict("records"), 1):
            cell = lambda v: "" if (v is None or (isinstance(v, float) and np.isnan(v))) else (f"{sval(v):g}" if sval(v) is not None else str(v))
            data.append([i, x["No TLD"], x["Nama"]] + [cell(x[p]) for p in PK] + [f"{x['NBD']:g}" if not pd.isna(x["NBD"]) else "", f"{x['Total']:g}"])
        t = Table(data, repeatRows=1, colWidths=[24, 70, 210] + [58] * len(labels) + [52, 78])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CCCCFF")), ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("ALIGN", (2, 1), (2, -1), "LEFT"), ("BACKGROUND", (-2, 1), (-2, -1), colors.HexColor("#D9D9D9")),
                               ("BACKGROUND", (-1, 1), (-1, -1), colors.HexColor("#BDD7EE")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        el.append(t)
    doc.build(el); return bio.getvalue()

def bar_svg(title, labels, values, ref=None, ref_label="NBD RS", unit="mSv", color="#073763"):
    """Grafik batang sederhana (SVG) dengan garis acuan putus-putus."""
    import html as _h
    n = len(labels); gw = 70; ml, mr, mt, mb = 52, 16, 52, 70; W = max(520, ml + mr + gw * n); H = 330; ph = H - mt - mb
    top = _nice_max(max([float(v) for v in values] + ([float(ref)] if ref else [0])) * 1.12 or 1); y = lambda v: mt + ph - (v / top) * ph
    s = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" font-family="Lexend,sans-serif">',
         f'<text x="{ml}" y="22" font-size="16" font-weight="700" fill="#073763">{_h.escape(title)}</text>']
    for i in range(6):
        v = top * i / 5; s.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#E3EBF3"/><text x="{ml-8}" y="{y(v)+4:.1f}" text-anchor="end" font-size="11" fill="#5C7691">{v:g}</text>')
    for i, (lb, v) in enumerate(zip(labels, values)):
        cx = ml + gw * i + gw / 2; v = float(v); col = "#c0392b" if (ref and v > ref) else color
        s.append(f'<rect x="{cx-16:.1f}" y="{y(v):.1f}" width="32" height="{max(1, y(0)-y(v)):.1f}" rx="3" fill="{col}"><title>{_h.escape(str(lb))}: {v:g} {unit}</title></rect><text x="{cx:.1f}" y="{y(v)-5:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="{col}">{v:g}</text>')
        import textwrap
        for k, ln in enumerate(textwrap.wrap(str(lb), 11)[:3]): s.append(f'<text x="{cx:.1f}" y="{y(0)+15+k*12:.1f}" text-anchor="middle" font-size="10.5" fill="#073763">{_h.escape(ln)}</text>')
    if ref:
        s.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(ref):.1f}" y2="{y(ref):.1f}" stroke="#c0392b" stroke-dasharray="6 4"/><text x="{W-mr}" y="{y(ref)-5:.1f}" text-anchor="end" font-size="11" fill="#c0392b">{_h.escape(ref_label)} {ref:g} {unit}</text>')
    s.append("</svg>"); return f'<div style="overflow-x:auto">{"".join(s)}</div>'
