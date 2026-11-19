"""Logika murni Dose Monitoring (tanpa Streamlit) - dapat diuji terpisah."""
import io, numpy as np, pandas as pd

MODS = {
 "GR": dict(label="Radiografi Umum", exam="Jenis Periksa",
   cols=["Kode Pasien","Gender","Umur","Berat Badan","Posisi","Proyeksi","FDD","kV","mA","s","mAs","Tanggal","Jenis Periksa"],
   metrics=[("INAK","INAK (mGy)","0.00"),("ESAK","ESAK (mGy)","0.00")]),
 "CT": dict(label="CT Scan", exam="Jenis Periksa",
   cols=["Kode Pasien","Gender","Umur","Berat Badan","No of Phase","CTDIvol","DLP","Tanggal","Jenis Periksa"],
   metrics=[("CTDIvol","CTDIvol (mGy)","0.0"),("DLP","DLP (mGy.cm)","0")]),
 "CATH": dict(label="Cathlab", exam="Pemeriksaan",
   cols=["Kode Pasien","Gender","Umur","Berat Badan","Fluoro detik","DAP","Kerma total","Tanggal","Pemeriksaan"],
   metrics=[("DAP_Gy","DAP (Gy.cm2)","0.0"),("Kerma total","Kerma total (mGy)","0"),("Fluoro menit","Fluoro (menit)","0.0")]),
 "DENTAL": dict(label="Dental", exam="Pemeriksaan",
   cols=["Kode Pasien","Gender","Umur","Berat Badan","kV","mAs","FSD","DAP","Tanggal","Pemeriksaan"],
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
    elif mod == "CATH":
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

def rekap(mod, d, cfg, kategori="Dewasa", dari=None, sampai=None):
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
    for name in cfg["tpd"].get(mod, {}):
        g = x[x[ex] == name]; first = _num(g[m[0][0]]); n = int(first.notna().sum())
        if n == 0: continue
        r = {"Jenis Pemeriksaan": name, "Jumlah Sampel": n}; over = []; anyref = False
        for key, lab, _ in m:
            v = _num(g[key]).dropna()
            r[f"{lab} Median (Q2)"] = float(np.percentile(v, 50)) if len(v) else np.nan
            r[f"{lab} Q3 (P75)"] = float(np.percentile(v, 75)) if len(v) else np.nan
            ref = cfg["tpd"][mod][name].get(key.replace("DAP_Gy","DAP").replace("DAP_mGy","DAP")) if key != "Fluoro menit" else None
            if key != "Fluoro menit":
                r[f"{lab} Acuan"] = ref if kategori == "Dewasa" else np.nan
                if kategori == "Dewasa" and ref not in (None, ""):
                    anyref = True
                    if r[f"{lab} Q3 (P75)"] > float(ref): over.append(lab)
        r["Status"] = "-" if kategori != "Dewasa" else ("Acuan belum diisi" if not anyref else ("Di atas acuan: " + ", ".join(over) if over else "Sesuai acuan"))
        rows.append(r)
    return pd.DataFrame(rows)

def map_columns(mod, raw):
    """Cocokkan kolom hasil ekspor Google Form ke kolom standar (nama mirip / case-insensitive)."""
    alias = {"umur":"Umur","age":"Umur","usia":"Umur","gender":"Gender","jenis kelamin":"Gender","kode pasien":"Kode Pasien","mrn":"Kode Pasien",
             "no rm":"Kode Pasien","berat badan":"Berat Badan","bb":"Berat Badan","weight":"Berat Badan","kv":"kV","ma":"mA","mas":"mAs","s":"s",
             "fdd":"FDD","tanggal":"Tanggal","timestamp":"Tanggal","date":"Tanggal","dlp":"DLP","dap":"DAP","ctdi":"CTDIvol","ctdivol":"CTDIvol",
             "average ctdivol":"CTDIvol","jenis periksa":"Jenis Periksa","exam":"Jenis Periksa","pemeriksaan":"Pemeriksaan","fsd":"FSD",
             "posisi":"Posisi","proyeksi":"Proyeksi","kerma total":"Kerma total","fluoro":"Fluoro detik","no of phase":"No of Phase"}
    out = pd.DataFrame(index=raw.index); used = {}
    for c in raw.columns:
        k = str(c).strip().lower()
        t = alias.get(k)
        if t is None:
            for std in MODS[mod]["cols"]:
                if std.lower() == k: t = std
        if t and t in MODS[mod]["cols"] and t not in used:
            out[t] = raw[c]; used[t] = c
    # form GR sering memakai 'Jenis Periksa'; Cath/Dental memakai 'Pemeriksaan'
    ex = MODS[mod]["exam"]
    if ex not in out.columns:
        for alt in ("Jenis Periksa", "Pemeriksaan"):
            if alt in out.columns: out[ex] = out.pop(alt)
    return out, used

def to_excel(mod, d, rk, cfg, meta):
    """Excel format laporan: Rekap + Data (nilai, bukan rumus) + Parameter."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter as L
    wb = Workbook(); ws = wb.active; ws.title = "Rekap"
    navy = PatternFill("solid", fgColor="073763"); thin = Side(style="thin", color="B7C4D4"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws["A1"] = f"Rekap Dosis Pasien {MODS[mod]['label']} - Laporan BAPETEN"; ws["A1"].font = Font(size=14, bold=True, color="073763")
    ws["A2"] = f"{meta.get('rs','')} | Kategori usia: {meta.get('kategori')} | Periode: {meta.get('periode','semua')}"
    ws["A3"] = "Median (Q2) dan persentil-75 (Q3) lokal; acuan nasional hanya untuk Dewasa."
    ws["A3"].font = Font(italic=True, size=9, color="5C7691")
    def put(sh, df, r0):
        for j, c in enumerate(df.columns, 1):
            h = sh.cell(r0, j, c); h.fill = navy; h.font = Font(bold=True, color="FFFFFF"); h.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center"); h.border = bd
            sh.column_dimensions[L(j)].width = max(12, min(34, len(str(c)) + 2))
        for i, row in enumerate(df.itertuples(index=False), r0 + 1):
            for j, v in enumerate(row, 1):
                if isinstance(v, float) and np.isnan(v): v = None
                if isinstance(v, (np.integer,)): v = int(v)
                if isinstance(v, (np.floating,)): v = float(v)
                c = sh.cell(i, j, v); c.border = bd
                if isinstance(v, float): c.number_format = "0.00"
        sh.row_dimensions[r0].height = 40
    put(ws, rk, 5); ws.column_dimensions["A"].width = 36
    wd = wb.create_sheet("Data"); put(wd, d.drop(columns=[c for c in ("Nama",) if c in d.columns]), 1); wd.freeze_panes = "A2"; wd.auto_filter.ref = wd.dimensions
    wp = wb.create_sheet("Parameter"); wp["A1"], wp["B1"] = "BSF", cfg["bsf"]; wp["A2"], wp["B2"] = "Bayi maks (th)", cfg["bayi_max"]; wp["A3"], wp["B3"] = "Dewasa min (th)", cfg["dewasa_min"]
    co = fit_output(cfg["out_pts"])
    if co: wp["A4"], wp["B4"] = "Koefisien output a,b,c", f"{co[0]:.5f}, {co[1]:.4f}, {co[2]:.3f}"
    bio = io.BytesIO(); wb.save(bio); return bio.getvalue()
