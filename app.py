# -*- coding: utf-8 -*-
"""Monitoring Dosis Pasien dan Dosis Pekerja Radiasi - Mandaya Royal Hospital Puri.
Import -> isi protokol & dosis -> hitung & simpan -> unduh format BAPETEN."""
import os, io, json, base64, datetime as dt
import requests, pandas as pd, numpy as np, streamlit as st
import dose_core as dc
try: import scan_core as sc
except Exception: sc = None

HERE = os.path.dirname(os.path.abspath(__file__))
def _f(name): return os.path.join(HERE, name)
LOGO, LOGO_W = _f("Mandaya Logo.png"), _f("Mandaya Logo White.png")
RS = "Mandaya Royal Hospital Puri"
st.set_page_config(page_title="Monitoring Dosis Pasien & Pekerja Radiasi - MRHP", page_icon=LOGO if os.path.exists(LOGO) else None, layout="wide", initial_sidebar_state="expanded")

def _b64(p):
    try: return base64.b64encode(open(p, "rb").read()).decode()
    except Exception: return ""

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');
html,body,.stApp,.stApp :where(p,span,div,label,button,input,textarea,select,h1,h2,h3,h4,h5,h6,li,a,td,th,small,b,strong):not([data-testid="stIconMaterial"]):not(.material-icons){font-family:'Lexend',sans-serif !important}
:root{--navy:#073763;--teal:#1B7895;--soft:#F2F5F9;--line:#DCE5EE}
.block-container{padding-top:3.2rem !important;padding-bottom:3rem;max-width:1280px}
.hero{background:linear-gradient(120deg,#073763 0%,#0d5a86 60%,#1B7895 100%);border-radius:18px;padding:22px 26px;margin:0 0 16px 0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;text-align:center}
.hero img{height:46px;width:auto}
.hero .t{color:#fff;font-size:1.55rem;font-weight:700;line-height:1.15}
.hero .s{color:#cfe3f1;font-size:.9rem;margin-top:3px}
.badge{display:inline-block;border-radius:999px;padding:3px 12px;font-size:.78rem;font-weight:600;margin-left:0;margin-top:2px}
.b-ok{background:#d5eedd;color:#1e6b3a}.b-warn{background:#fff0cc;color:#8a5a00}
.step{display:flex;align-items:center;gap:10px;margin:2px 0 8px 0}
.step .n{background:var(--navy);color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem;flex:none}
.step .h{font-weight:700;color:var(--navy);font-size:1.05rem}
.step .d{color:#5C7691;font-size:.85rem}
[data-testid="stMetric"]{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
[data-testid="stMetricValue"]{color:var(--navy)}
.stButton>button,.stDownloadButton>button{border-radius:10px;min-height:2.7rem;font-weight:600}
div[data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap}
button[data-baseweb="tab"]{border-radius:10px 10px 0 0;padding:8px 16px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#073763 0%,#0b4a78 100%)}
[data-testid="stSidebar"] *{color:#fff}
[data-testid="stSidebarHeader"]{height:2.2rem;min-height:0;padding:.4rem .8rem 0}
[data-testid="stSidebarUserContent"]{padding-top:0 !important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.3rem}
.side-logo{text-align:center;margin:-6px 0 14px 0;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,.18)}
.side-logo img{width:185px;max-width:88%}
[data-testid="stSidebar"] .stButton>button>div{width:100%;justify-content:flex-start !important;text-align:left !important}
[data-testid="stSidebar"] .stButton>button p{text-align:left !important;width:100%}
[data-testid="stSidebar"] .stButton>button{width:calc(100% - 10px);margin-left:10px;justify-content:flex-start;text-align:left;background:transparent;border:1px solid transparent;color:#fff;border-radius:12px;min-height:2.7rem;padding:.35rem 1rem;font-size:.97rem}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,.12);border-color:rgba(255,255,255,.25);color:#fff}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:#fff;color:#073763;border-color:#fff}
[data-testid="stSidebar"] .stButton>button[kind="primary"] p{color:#073763 !important;font-weight:700}
div[data-testid="stRadio"] div[role="radiogroup"]{gap:8px;flex-wrap:wrap}
div[data-testid="stRadio"] div[role="radiogroup"]>label>div:first-child{display:none}
div[data-testid="stRadio"] div[role="radiogroup"]>label{background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:6px 16px;cursor:pointer}
div[data-testid="stRadio"] div[role="radiogroup"]>label:hover{border-color:var(--teal)}
div[data-testid="stRadio"] div[role="radiogroup"]>label:has(input:checked){background:var(--navy);border-color:var(--navy)}
div[data-testid="stRadio"] div[role="radiogroup"]>label:has(input:checked) p{color:#fff !important;font-weight:600}
.drl{display:flex;flex-direction:column;gap:10px}
.drl-leg{display:flex;gap:18px;font-size:.82rem;color:#5C7691;flex-wrap:wrap}.drl-leg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.drl-row{display:grid;grid-template-columns:minmax(150px,1.1fr) 3fr minmax(130px,.8fr);gap:14px;align-items:center;padding:8px 12px;background:#F8FAFC;border:1px solid #E3EBF3;border-radius:12px}
.drl-n{font-weight:600;color:#073763;font-size:.9rem;word-break:break-word}.rn{font-weight:400;color:#5C7691;font-size:.75rem}.rn.warn{color:#8a5a00;background:#fff0cc;border-radius:6px;padding:0 5px}
.bar{display:flex;align-items:center;gap:8px;margin:3px 0}
.trk{flex:1;height:16px;background:#EAF0F6;border-radius:6px;overflow:hidden}
.trk div{height:100%;border-radius:6px}.b1{background:#073763}.b2{background:#9ccbe0}
.bar span{width:58px;text-align:right;font-size:.78rem;font-weight:600;color:#073763}
.rb{display:inline-block;border-radius:999px;padding:3px 10px;font-size:.78rem;font-weight:600;white-space:nowrap}
.rb.ok{background:#d5eedd;color:#1e6b3a}.rb.bad{background:#f8d0d0;color:#9c1c1c}.rb.na{background:#eceff3;color:#5C7691}
@media (max-width:768px){.drl-row{grid-template-columns:1fr}}
.side-t{display:flex;align-items:center;gap:8px;font-size:.74rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8fd3ea !important;margin:26px 0 8px 2px;padding:0 4px 8px 4px;border-bottom:1px solid rgba(255,255,255,.2)}
.side-t::before{content:"";width:4px;height:14px;border-radius:2px;background:#7fd1ea}
.side-logo+div .side-t,[data-testid="stSidebar"] .side-logo ~ div:first-of-type .side-t{margin-top:6px}
.side-card{background:rgba(255,255,255,.1);border-radius:12px;padding:12px 16px;margin-top:18px;font-size:.85rem;line-height:1.5}
@media (max-width:768px){.block-container{padding:3rem .6rem 2rem !important}.hero{padding:14px 16px}.hero .t{font-size:1.2rem}.badge{margin-left:0}}
</style>""", unsafe_allow_html=True)

def step(n, title, desc=""):
    st.markdown(f'<div class="step"><div class="n">{n}</div><div><div class="h">{title}</div><div class="d">{desc}</div></div></div>', unsafe_allow_html=True)

def _sec(k, d=""):
    try: return st.secrets[k]
    except Exception: return d
URL, KEY, PW = str(_sec("SUPABASE_URL")).rstrip("/"), _sec("SUPABASE_KEY"), _sec("AUTHOR_PASSWORD")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
ONLINE = bool(URL and KEY)

def _rec(r):
    out = {}
    for k, v in r.items():
        if k in ("_rid", "Modalitas"): continue
        if v is pd.NaT or (isinstance(v, float) and np.isnan(v)) or v is None: out[k] = None
        elif isinstance(v, (pd.Timestamp, dt.datetime, dt.date)): out[k] = v.isoformat()
        elif isinstance(v, (np.integer,)): out[k] = int(v)
        elif isinstance(v, (np.floating,)): out[k] = float(v)
        else: out[k] = v
    return out
def sb_get_all():
    frames = []
    if ONLINE:
        for mod in dc.MODS:
            rows, off = [], 0
            while True:
                r = requests.get(f"{URL}/rest/v1/dose_entries", headers={**H, "Range": f"{off}-{off+999}"},
                                 params={"modality": f"eq.{mod}", "select": "data", "order": "id"}, timeout=40)
                r.raise_for_status(); b = r.json(); rows += [x["data"] for x in b]
                if len(b) < 1000: break
                off += 1000
            if rows:
                g = pd.DataFrame(rows); g["Modalitas"] = mod; frames.append(g)
    m = pd.concat(frames, ignore_index=True) if frames else dc.empty_master()
    for c in dc.empty_master().columns:
        if c not in m.columns: m[c] = None
    m["_rid"] = range(len(m)); m["Tanggal"] = pd.to_datetime(m["Tanggal"], errors="coerce")
    return m
def sb_post(mod, df):
    recs = [{"modality": mod, "data": _rec(r)} for r in df.to_dict("records")]
    for i in range(0, len(recs), 500):
        requests.post(f"{URL}/rest/v1/dose_entries", headers=H, data=json.dumps(recs[i:i+500]), timeout=90).raise_for_status()
def sb_replace(mod, df):
    if not ONLINE: return len(df)
    requests.delete(f"{URL}/rest/v1/dose_entries", headers=H, params={"modality": f"eq.{mod}"}, timeout=90).raise_for_status()
    sb_post(mod, df); return len(df)
def cfg_load():
    if not ONLINE: return dc.merge_cfg(None)
    try:
        r = requests.get(f"{URL}/rest/v1/dose_config", headers=H, params={"id": "eq.main", "select": "data"}, timeout=20); r.raise_for_status()
        return dc.merge_cfg(r.json()[0]["data"] if r.json() else None)
    except Exception: return dc.merge_cfg(None)
def cfg_save(cfg):
    if not ONLINE: return
    h = {**H, "Prefer": "resolution=merge-duplicates,return=minimal"}
    requests.post(f"{URL}/rest/v1/dose_config", headers=h, data=json.dumps({"id": "main", "data": cfg}), timeout=20).raise_for_status()

# ---------- header
logo = _b64(LOGO_W)
badge = '<span class="badge b-ok">● Database terhubung</span>' if ONLINE else '<span class="badge b-warn">● Mode lokal (belum tersimpan permanen)</span>'
st.markdown(f'<div class="hero">{f"<img src=data:image/png;base64,{logo}>" if logo else ""}<div><div class="t">Monitoring Dosis Pasien dan Dosis Pekerja Radiasi</div>'
            f'<div class="s">{RS} · Departemen Radiologi · Laporan BAPETEN</div></div>{badge}</div>', unsafe_allow_html=True)

if PW and not st.session_state.get("dose_ok"):
    with st.container(border=True):
        st.markdown("**Masuk**")
        p = st.text_input("Password author", type="password")
        if st.button("Masuk", type="primary") and p == PW: st.session_state["dose_ok"] = True; st.rerun()
    st.stop()
if not ONLINE:
    st.info("**Mode lokal** — semua fitur bisa dipakai, tetapi data hilang jika halaman ditutup. Hubungkan Supabase di *Settings → Secrets* agar tersimpan permanen.")

def sb_get_mod(mod):
    if not ONLINE: return None
    rows, off = [], 0
    while True:
        r = requests.get(f"{URL}/rest/v1/dose_entries", headers={**H, "Range": f"{off}-{off+999}"}, params={"modality": f"eq.{mod}", "select": "data", "order": "id"}, timeout=40)
        r.raise_for_status(); b = r.json(); rows += [x["data"] for x in b]
        if len(b) < 1000: break
        off += 1000
    return pd.DataFrame(rows)
def load_staff():
    try:
        ro, sd = sb_get_mod("STAFF"), sb_get_mod("STAFFDOSE")
    except Exception as e:
        st.warning(f"Gagal membaca data pekerja: {e}"); ro = sd = None
    ro = dc.empty_roster() if ro is None or ro.empty else ro; sd = dc.empty_sdose() if sd is None or sd.empty else sd
    for c_ in dc.ROSTER_COLS:
        if c_ not in ro.columns: ro[c_] = None
    for c_ in dc.SDOSE_COLS:
        if c_ not in sd.columns: sd[c_] = None
    return ro[dc.ROSTER_COLS].copy(), sd[dc.SDOSE_COLS].copy()
if "staff" not in st.session_state: st.session_state.staff, st.session_state.sdose = load_staff()
if "cfg" not in st.session_state: st.session_state.cfg = cfg_load()
if "master" not in st.session_state:
    try: st.session_state.master = sb_get_all()
    except Exception as e: st.session_state.master = dc.empty_master(); st.warning(f"Gagal membaca database: {e}")
cfg = st.session_state.cfg; master = st.session_state.master
if st.session_state.get("flash"): st.success(st.session_state.pop("flash"))

MENU = ["Import Data", "Database Dosis Pasien", "Download BAPETEN", "Dashboard", "⚙️ Parameter"]
M_ISI, M_REKAP, M_KELOLA = "Isi Dosis Pekerja", "Rekap Dosis Pekerja", "Kelola Petugas"
GROUPS = [("Dosis Pasien", MENU[:4]), ("Dosis Pekerja Radiasi", [M_ISI, M_REKAP, M_KELOLA]), ("Pengaturan", [MENU[4]])]
with st.sidebar:
    if logo: st.markdown(f'<div class="side-logo"><img src="data:image/png;base64,{logo}"></div>', unsafe_allow_html=True)
    if "menu" not in st.session_state: st.session_state["menu"] = MENU[0]
    for g_, items_ in GROUPS:
        if g_: st.markdown(f'<div class="side-t">{g_}</div>', unsafe_allow_html=True)
        for m_ in items_:
            if st.button(m_, key=f"nav_{m_}", type="primary" if st.session_state["menu"] == m_ else "secondary", use_container_width=True):
                st.session_state["menu"] = m_; st.rerun()
    menu = st.session_state["menu"]
    tot = len(master)
    st.markdown(f'<div class="side-card"><b>Database</b><br>{tot:,} data pasien<br>'
                + ("● terhubung ke Supabase" if ONLINE else "● mode lokal (belum permanen)") + '</div>', unsafe_allow_html=True)
icons = {"GR": "🩻", "CT": "🌀", "MAMMO": "🎀", "FLURO": "💧", "CATH": "❤️", "DENTAL": "🦷"}
def modlabel(m): return f"{icons[m]} {dc.MODS[m]['label']}"

def in_period(d, dari, sampai):
    if "Tanggal" not in d.columns or not (dari or sampai): return d
    t = pd.to_datetime(d["Tanggal"], errors="coerce"); ok = pd.Series(True, index=d.index)
    if dari: ok &= t >= pd.Timestamp(dari)
    if sampai: ok &= t < pd.Timestamp(sampai) + pd.Timedelta(days=1)
    return d[ok]

def computed(mod):
    g = master[master["Modalitas"] == mod]
    return dc.compute(mod, g[["_rid"] + dc.MODS[mod]["cols"]].reset_index(drop=True), cfg)

# =================================================== MENU 1
if menu == MENU[0]:
    with st.container(border=True):
        step(1, "Import data dari RIS", "Unggah file ekspor Daily Case by Modality (.xlsx / .csv). Baris judul dikenali otomatis.")
        up = st.file_uploader("Pilih file RIS", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
        if up is not None:
            try:
                raw = dc.read_ris(up); new, skipped = dc.parse_ris(raw)
                c = st.columns(3)
                c[0].metric("Baris di file", f"{len(raw):,}"); c[1].metric("Berdosis (dipilah)", f"{len(new):,}"); c[2].metric("Diabaikan", f"{sum(skipped.values()):,}")
                prev = new["Modalitas"].value_counts().rename_axis("Modalitas").reset_index(name="Jumlah")
                prev["Modalitas"] = prev["Modalitas"].map(lambda m: dc.MODS[m]["label"])
                c1, c2 = st.columns(2)
                c1.markdown("**Akan masuk ke database**"); c1.dataframe(prev, hide_index=True, use_container_width=True)
                c2.markdown("**Diabaikan (tidak memakai radiasi pengion / bukan dosis pasien)**")
                c2.dataframe(pd.DataFrame(list(skipped.items()), columns=["Modalitas RIS", "Jumlah"]), hide_index=True, use_container_width=True)
                mode = st.radio("Mode import", ["Tambahkan ke data yang ada", "Ganti data (hapus data modalitas yang ada di file, lalu isi dari file)"], key="imp_mode")
                ganti = mode.startswith("Ganti"); ok_ganti = True
                if ganti:
                    mods_f = sorted(new["Modalitas"].unique()); n_del = int(master["Modalitas"].isin(mods_f).sum())
                    st.warning(f"Mode Ganti menghapus {n_del:,} data yang sudah ada pada modalitas: {', '.join(dc.MODS[m]['label'] for m in mods_f)}, termasuk dosis yang sudah Anda isi.")
                    ok_ganti = st.checkbox("Saya mengerti, hapus data lama dan ganti dengan isi file ini")
                if st.button("Proses & ganti database" if ganti else "Proses & tambahkan ke database", type="primary", disabled=not ok_ganti):
                    with st.spinner("Memproses..."):
                        base = master[~master["Modalitas"].isin(new["Modalitas"].unique())].reset_index(drop=True) if ganti else master
                        master2, added = dc.add_rows(base, new)
                        dc.register_exams(cfg, added)
                        if ONLINE:
                            if ganti:
                                for mod in new["Modalitas"].unique(): sb_replace(mod, added[added["Modalitas"] == mod])
                            else:
                                for mod, g in added.groupby("Modalitas"): sb_post(mod, g)
                            cfg_save(cfg)
                    st.session_state.master = master2
                    st.session_state["flash"] = (f"{len(added):,} data menggantikan data lama." if ganti else f"{len(added):,} data baru ditambahkan, {len(new)-len(added):,} dilewati karena sudah ada.") + " Lanjut ke menu Database Dosis Pasien untuk mengisi dosis."
                    st.rerun()
            except Exception as e:
                st.error(f"File tidak dapat dibaca: {e}")
    with st.container(border=True):
        st.markdown("**Isi database saat ini**")
        if len(master) == 0: st.caption("Database masih kosong.")
        else:
            cnt = master["Modalitas"].value_counts()
            cols = st.columns(len(cnt))
            for col, (m, n) in zip(cols, cnt.items()): col.metric(modlabel(m), f"{n:,}")
    st.caption("Pemilahan otomatis: GENERAL X-RAY → Radiografi Umum (Panoramic/CBCT/Cephalo → Dental), CT SCAN → CT, MAMMOGRAPHY → Mamografi, FLUOROSCOPY → Fluoroskopi. "
               "Nama pemeriksaan disamakan ke nama baku (mis. Thorax AP/PA → CHEST). Data ganda (RN + Visit + Pemeriksaan + Tanggal sama) dilewati.")

# =================================================== MENU 2
elif menu == MENU[1]:
    present = [m for m in dc.MODS if (master["Modalitas"] == m).any()] or list(dc.MODS)
    mod = st.radio("Modalitas", present, horizontal=True, format_func=modlabel, key="m2mod")
    spec = dc.MODS[mod]; ex = spec["exam"]
    d_all = computed(mod)
    okn = int((d_all["Cek"] == "OK").sum()); filled = int(d_all[spec["dose"]].notna().any(axis=1).sum()) if len(d_all) else 0
    with st.container(border=True):
        step(2, f"Database dosis pasien · {dc.MODS[mod]['label']}", "Isi protokol & dosis pada kolom putih. Kolom abu-abu dihitung otomatis.")
        k = st.columns(4); k[0].metric("Total pasien", f"{len(d_all):,}"); k[1].metric("Dosis terisi", f"{filled:,}"); k[2].metric("Valid (siap lapor)", f"{okn:,}")
        k[3].metric("Dewasa / Anak / Bayi", " / ".join(str(int((d_all['Kategori usia'] == x).sum())) for x in ("Dewasa", "Anak", "Bayi")))
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        exams = f1.multiselect("Jenis pemeriksaan", sorted(d_all[ex].dropna().unique()), key=f"fx_{mod}", placeholder="Semua")
        kat = f2.selectbox("Kategori usia", ["Semua", "Dewasa", "Anak", "Bayi"], key=f"fk_{mod}")
        stt = f3.selectbox("Status", ["Semua", "Belum diisi", "Sudah diisi", "Bermasalah"], key=f"fs_{mod}")
        cari = f4.text_input("Cari nama / RN", key=f"fc_{mod}")
        g1, g2 = st.columns(2)
        dari = g1.date_input("Dari tanggal", value=None, key=f"fd1_{mod}", format="DD/MM/YYYY"); sampai = g2.date_input("Sampai tanggal", value=None, key=f"fd2_{mod}", format="DD/MM/YYYY")
        v = d_all
        if exams: v = v[v[ex].isin(exams)]
        if kat != "Semua": v = v[v["Kategori usia"] == kat]
        has = v[spec["dose"]].notna().any(axis=1)
        if stt == "Belum diisi": v = v[~has]
        elif stt == "Sudah diisi": v = v[has]
        elif stt == "Bermasalah": v = v[v["Cek"] != "OK"]
        v = in_period(v, dari, sampai)
        if cari:
            q = cari.lower(); v = v[v["Nama"].astype(str).str.lower().str.contains(q, regex=False) | v["Kode Pasien"].astype(str).str.lower().str.contains(q, regex=False)]
        PS = 200; pages = max(1, -(-len(v) // PS))
        p1, p2 = st.columns([1, 3]); pg = p1.number_input("Halaman", 1, pages, 1, key=f"pg_{mod}")
        p2.caption(f"{len(v):,} baris sesuai filter · halaman {pg} dari {pages} · {PS} baris per halaman")
        page = v.iloc[(pg - 1) * PS: pg * PS]
        derived = [c for c in d_all.columns if c not in spec["cols"] + ["_rid"]]
        gray = ["Kode Pasien", "Nama", "Deskripsi RIS", "Visit No"] + derived
        sig = hash((tuple(exams), kat, stt, cari, str(dari), str(sampai), pg, len(master), st.session_state.get(f"ver_{mod}", 0)))
        show = page[["_rid"] + spec["cols"] + derived].copy()
        cc = {"_rid": None, "Visit No": None}
        cc["Gender"] = st.column_config.SelectboxColumn("Gender", options=["M", "F"], width="small")
        cc[ex] = st.column_config.SelectboxColumn(ex, options=sorted(set(cfg["tpd"].get(mod, {})) | set(d_all[ex].dropna())), width="medium")
        cc["Tanggal"] = st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY")
        cc["Umur"] = st.column_config.NumberColumn("Umur", width="small")
        edited = st.data_editor(show, num_rows="dynamic", column_config=cc, disabled=gray, use_container_width=True, hide_index=True, height=420, key=f"ed_{mod}_{sig}")
        b1, b2 = st.columns([1, 3])
        if b1.button("💾 Simpan perubahan" if ONLINE else "💾 Simpan (sesi ini)", type="primary", key=f"sv_{mod}"):
            try:
                keep_cols = ["_rid"] + spec["cols"]
                m2 = dc.apply_edits(master, page["_rid"].astype(int).tolist(), edited[keep_cols], mod)
                n = sb_replace(mod, m2[m2["Modalitas"] == mod])
                st.session_state.master = m2; st.session_state[f"ver_{mod}"] = st.session_state.get(f"ver_{mod}", 0) + 1
                st.session_state["flash"] = f"Tersimpan. {n:,} data {dc.MODS[mod]['label']} di database."; st.rerun()
            except Exception as e: st.error(f"Gagal menyimpan: {e}")
        b2.caption("Tips: filter *Belum diisi* + satu jenis pemeriksaan agar pengisian dosis lebih cepat. Perubahan baru tersimpan setelah menekan tombol Simpan.")

# =================================================== MENU 3
elif menu == MENU[2]:
    present = [m for m in dc.MODS if (master["Modalitas"] == m).any()]
    if not present:
        st.info("Database masih kosong. Mulai dari menu Import Data.")
    else:
        with st.container(border=True):
            step(3, "Download format BAPETEN", "Satu file per jenis pemeriksaan dan kategori usia, kolomnya sama dengan template Target BAPETEN.")
            mod = st.radio("Modalitas", present, horizontal=True, format_func=modlabel, key="m3mod")
            spec = dc.MODS[mod]; ex = spec["exam"]
            d = computed(mod); dv = d[d["Cek"] == "OK"]
            c1, c2 = st.columns([2, 1])
            exams = c1.multiselect("Jenis pemeriksaan", sorted(dv[ex].dropna().unique()), key=f"x3_{mod}", placeholder="Semua jenis pemeriksaan")
            kat = c2.selectbox("Kategori usia", ["Dewasa", "Anak", "Bayi", "Semua kategori"], key=f"k3_{mod}")
            g1, g2, g3 = st.columns(3)
            dari = g1.date_input("Dari tanggal", value=None, key=f"d13_{mod}", format="DD/MM/YYYY"); sampai = g2.date_input("Sampai tanggal", value=None, key=f"d23_{mod}", format="DD/MM/YYYY")
            incl = g3.checkbox("Sertakan nama pasien", value=False, help="Kolom Nama pada template BAPETEN bersifat opsional ('Jika Ada'). Default dikosongkan; Kode Pasien (RN) tetap diisi.")
            bb = g3.checkbox("Sertakan data tanpa berat badan", value=False, help="Berat badan wajib di template BAPETEN. Di RIS banyak yang bernilai 0 (kosong).")
            sel = in_period(dv, dari, sampai)
            cats = ["Dewasa", "Anak", "Bayi"] if kat == "Semua kategori" else [kat]
            per = "semua" if not (dari or sampai) else f"{dari or '...'} s/d {sampai or '...'}"
            if mod not in dc.BAPETEN_FORM:
                st.warning("Template BAPETEN untuk Dental belum tersedia. Unduhan memakai format Excel internal (Rekap + Data). Kirim template Dental bila sudah ada.")
                rekaps = {c: dc.rekap(mod, sel, cfg, c, dari, sampai, exams or None) for c in cats}
                data_out = sel[sel[ex].isin(exams)] if exams else sel
                if kat != "Semua kategori": data_out = data_out[data_out["Kategori usia"] == kat]
                xl = dc.to_excel(mod, data_out.drop(columns=["_rid"], errors="ignore"), rekaps, cfg, dict(rs=RS, periode=per), include_name=incl)
                st.download_button("⬇️ Download Excel", xl, file_name=f"Dosis_{mod}_{kat.replace(' ', '')}_{dt.date.today():%Y%m%d}.xlsx", type="primary", disabled=len(data_out) == 0,
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                combos, dropped = dc.bapeten_combos(mod, sel, exams, cats, require_bb=not bb)
                m = st.columns(3); m[0].metric("File yang dihasilkan", len(combos)); m[1].metric("Total baris data", f"{sum(c['n'] for c in combos):,}")
                m[2].metric("Dikecualikan (data wajib kosong)", f"{dropped:,}", help="Dosis lengkap tetapi Gender / Umur / Berat Badan (dan fase CT) kosong.")
                if not combos:
                    st.caption("Belum ada data yang memenuhi syarat. Isi dosis di menu Database Dosis Pasien terlebih dahulu.")
                else:
                    tbl = pd.DataFrame([{"Jenis pemeriksaan": c["exam"], "Kategori usia": c["kategori"], "Jumlah data": c["n"],
                                         "Keterangan": "OK" if c["n"] >= 10 else "Kurang dari 10 data (minimal BAPETEN)"} for c in combos])
                    st.dataframe(tbl, use_container_width=True, hide_index=True)
                    if len(combos) == 1:
                        c0 = combos[0]
                        st.download_button("⬇️ Download Excel BAPETEN", dc.bapeten_xlsx(mod, c0["df"], incl), file_name=dc.bapeten_filename(mod, c0), type="primary",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.download_button(f"⬇️ Download {len(combos)} file BAPETEN (ZIP)", dc.bapeten_zip(mod, combos, incl),
                                           file_name=f"BAPETEN_{dc.BAPETEN_FORM[mod]}_{dt.date.today():%Y%m%d}.zip", type="primary", mime="application/zip")
                        if len(combos) <= 15:
                            with st.expander("Atau unduh satu per satu"):
                                for i, c in enumerate(combos):
                                    st.download_button(f"{c['exam']} · {c['kategori']} ({c['n']})", dc.bapeten_xlsx(mod, c["df"], incl), file_name=dc.bapeten_filename(mod, c),
                                                       key=f"one_{mod}_{i}", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.caption("Format: Excel (.xlsx) dengan header dan susunan kolom seperti template Target BAPETEN. Jika portal BAPETEN meminta .xls, buka file lalu Simpan sebagai Excel 97-2003.")
        if mod in dc.BAPETEN_FORM:
            with st.expander("Rekap internal: median (Q2) dan Q3 terhadap acuan (bukan untuk BAPETEN)"):
                rk = dc.rekap(mod, sel, cfg, "Dewasa" if kat == "Semua kategori" else kat, dari, sampai, exams or None)
                if rk.empty: st.caption("Tidak ada data valid untuk filter ini.")
                else:
                    def _c(x): return ("background-color:#F8D0D0;color:#9C1C1C;font-weight:600" if str(x).startswith("Di atas") else
                                      "background-color:#D5EEDD;color:#1E6B3A;font-weight:600" if str(x).startswith("Sesuai") else "")
                    fmt = {col: "{:.2f}" for col in rk.columns if col not in ("Jenis Pemeriksaan", "Jumlah Sampel", "Status")}
                    sty = rk.style.format(fmt, na_rep="-"); sty = (sty.map if hasattr(sty, "map") else sty.applymap)(_c, subset=["Status"])
                    st.dataframe(sty, use_container_width=True, hide_index=True)

# =================================================== MENU 4 DASHBOARD
elif menu == MENU[3]:
    present = [m for m in dc.MODS if (master["Modalitas"] == m).any()]
    if not present:
        st.info("Database masih kosong. Mulai dari menu Import Data.")
    else:
        with st.container(border=True):
            step(4, "Dashboard DRL", "Typical value lokal (median / Quartil 2) dibandingkan dengan DRL nasional. Hanya data valid (dosis lengkap) yang dihitung.")
            mod = st.radio("Modalitas", present, horizontal=True, format_func=modlabel, key="m4mod")
            spec = dc.MODS[mod]; ex = spec["exam"]
            d = computed(mod); dv = d[d["Cek"] == "OK"]
            f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
            kat = f1.selectbox("Kategori usia", ["Dewasa", "Anak", "Bayi", "Semua"], key=f"k4_{mod}")
            dari = f2.date_input("Dari tanggal", value=None, key=f"d14_{mod}", format="DD/MM/YYYY"); sampai = f3.date_input("Sampai tanggal", value=None, key=f"d24_{mod}", format="DD/MM/YYYY")
            exams = f4.multiselect("Jenis pemeriksaan", sorted(dv[ex].dropna().unique()), key=f"x4_{mod}", placeholder="Semua jenis pemeriksaan")
            if kat != "Dewasa": st.caption("DRL nasional hanya berlaku untuk dewasa, sehingga perbandingan hanya tampil pada kategori Dewasa.")
            rk = dc.rekap(mod, dv, cfg, kat, dari, sampai, exams or None)
        if rk.empty:
            st.info("Belum ada data valid untuk filter ini. Isi dosis di menu Database Dosis Pasien terlebih dahulu.")
        else:
            labs = [lab for _, lab, _ in spec["metrics"] if f"{lab} Acuan" in rk.columns]
            main = labs[0] if labs else spec["metrics"][0][1]
            _ov = pd.Series(False, index=rk.index); _hr = pd.Series(False, index=rk.index)
            for lab_ in labs:
                a_ = pd.to_numeric(rk[f"{lab_} Acuan"], errors="coerce"); q_ = pd.to_numeric(rk[f"{lab_} Median (Q2)"], errors="coerce")
                _hr |= a_.notna(); _ov |= (a_.notna() & (q_ > a_))
            if kat != "Dewasa": _ov[:] = False; _hr[:] = False
            over = int(_ov.sum()); okc = int((_hr & ~_ov).sum()); noref = len(rk) - over - okc
            k = st.columns(4)
            k[0].metric("Total pemeriksaan valid", f"{int(rk['Jumlah Sampel'].sum()):,}"); k[1].metric("Jenis pemeriksaan", len(rk))
            k[2].metric("Di atas DRL nasional", int(over)); k[3].metric("Sesuai / belum ada acuan", f"{int(okc)} / {int(noref)}")
            with st.container(border=True):
                if len(labs) > 1: lab = st.radio("Parameter dosis", labs, horizontal=True, key=f"p4_{mod}")
                else: lab = main
                st.markdown(f"**{lab}** · urut dari rasio tertinggi terhadap nasional")
                q = rk.copy(); acc = f"{lab} Acuan"
                if acc in q.columns: q["_r"] = pd.to_numeric(q[f"{lab} Median (Q2)"], errors="coerce") / pd.to_numeric(q[acc], errors="coerce"); q = q.sort_values("_r", ascending=False, na_position="last")
                st.markdown(dc.drl_svg(q, lab), unsafe_allow_html=True)
                with st.expander("Rincian rasio per pemeriksaan"):
                    st.markdown(dc.drl_html(q, lab), unsafe_allow_html=True)
                st.caption("Typical value = median (Quartil 2) dosis lokal. Batang biru tua = lokal, merah = lokal melebihi nasional, biru muda = DRL nasional. Persentase > 100% berarti typical value lokal melebihi DRL nasional. n < 10 berarti sampel belum cukup untuk dijadikan typical value.")
            with st.expander("Tabel lengkap (Q2, Q3, nasional)"):
                fmt = {c_: "{:.2f}" for c_ in rk.columns if c_ not in ("Jenis Pemeriksaan", "Jumlah Sampel", "Status")}
                st.dataframe(rk.style.format(fmt, na_rep="-"), use_container_width=True, hide_index=True)

# =================================================== DOSIS PEKERJA
elif menu in (M_ISI, M_REKAP, M_KELOLA):
    roster, sdose = st.session_state.staff, st.session_state.sdose
    labels = cfg.get("periods", dc.DEFAULT_CFG["periods"]); units_all = list(dict.fromkeys(list(cfg.get("staff_units", [])) + sorted(roster["Unit"].dropna().unique())))
    def persist(ro=None, sd=None):
        if ro is not None: st.session_state.staff = ro; sb_replace("STAFF", ro)
        if sd is not None: st.session_state.sdose = sd; sb_replace("STAFFDOSE", sd)
    if roster.empty:
        with st.container(border=True):
            step("👥", "Data petugas masih kosong", "Muat data awal dari rekap PDF 2021–2026 (petugas aktif dan yang sudah tidak aktif, 6 unit) atau tambah petugas manual di menu Kelola Petugas.")
            if st.button("Muat data awal dari rekap PDF", type="primary"):
                ro, sd = dc.seed_staff(); persist(ro, sd); st.session_state["flash"] = f"{len(ro)} petugas dan {len(sd)} data dosis dimuat."; st.rerun()
    # ---------------------------------------------- isi dosis
    if menu == M_ISI and not roster.empty:
        with st.container(border=True):
            step("🧾", "Isi dosis pekerja radiasi", "Isi dosis TLD (mSv) per periode seperti rekap tahunan. Selain angka boleh: n/a, Pergantian TLD, Penambahan TLD Baru, Resign.")
            c1, c2 = st.columns(2)
            tahun = c1.number_input("Tahun", 2015, 2100, dt.date.today().year, key="s_tahun")
            unit = c2.selectbox("Unit", units_all, key="s_unit")
            tbl = dc.staff_year(roster, sdose, tahun, unit)
            tbl["Status"] = [dc.staff_status(t, n) for t, n in zip(tbl["Total"], tbl["NBD"])]
            ver = st.session_state.setdefault("s_ver", 0)
            cc = {"SID": None, "Unit": None, "No TLD": st.column_config.TextColumn("No TLD", width="small"), "Nama": st.column_config.TextColumn("Nama Petugas", width="large"),
                  "NBD": st.column_config.NumberColumn("NBD RS (mSv)", min_value=0.0, format="%g", width="small"), "Total": st.column_config.NumberColumn("Total 1 Tahun (mSv)", format="%g"),
                  "Status": st.column_config.TextColumn("Status")}
            for i, p in enumerate(dc.PK): cc[p] = st.column_config.TextColumn(labels[i] if i < len(labels) else p, width="small", help=f"Periode {i+1}")
            show = tbl.copy()
            for p in dc.PK: show[p] = show[p].astype(object)
            ed = st.data_editor(show, column_config=cc, disabled=["No TLD", "Nama", "Total", "Status"], use_container_width=True, hide_index=True, key=f"s_ed_{tahun}_{unit}_{ver}", height=min(520, 60 + 36 * max(3, len(show))))
            if len(tbl) == 0: st.caption("Belum ada petugas di unit ini. Tambahkan di menu Kelola Petugas.")
            if st.button("💾 Simpan dosis", type="primary", key="s_save"):
                try:
                    persist(sd=dc.staff_save_year(sdose, tahun, ed[["SID"] + dc.PK + ["NBD"]], cfg.get("nbd_rs", 10.0)))
                    st.session_state["s_ver"] = ver + 1; st.session_state["flash"] = f"Dosis {unit} tahun {tahun} tersimpan."; st.rerun()
                except Exception as e: st.error(f"Gagal menyimpan: {e}")
            st.caption("Total dihitung otomatis dari semua periode yang berisi angka. Status 'Melebihi NBD RS' muncul bila total di atas pembatas dosis RS.")
        # ---------- isi otomatis dari scan
        with st.container(border=True):
            step("📄", "Isi otomatis dari scan laporan TLD", "Unggah scan laporan satu periode (3 bulan). Dibaca dengan OCR, lalu Anda cek dulu sebelum diisikan ke tabel.")
            if sc is None or not sc.tesseract_ok():
                st.warning("OCR belum aktif di server ini. Tambahkan file `packages.txt` berisi `tesseract-ocr` dan `pypdfium2` di `requirements.txt`, lalu Reboot app.")
            else:
                a1, a2, a3 = st.columns([2, 1, 1])
                upl = a1.file_uploader("Scan laporan (PDF / JPG / PNG)", type=["pdf", "jpg", "jpeg", "png"], key="scan_up")
                pidx = a2.selectbox("Periode yang diisi", list(range(5)), format_func=lambda i: f"{i+1}. {labels[i] if i < len(labels) else 'P'+str(i+1)}", key="scan_p")
                mode = a3.selectbox("Kolom angka dosis", ["Angka pertama", "Angka kedua", "Angka ketiga", "Angka terakhir"], key="scan_mode",
                                    help="Jika laporan punya beberapa kolom angka (mis. Hp(10), Hp(0.07)), pilih kolom yang berisi dosis periode.")
                if upl is not None and st.button("Baca scan", key="scan_go"):
                    with st.spinner("Membaca scan (OCR)..."):
                        try:
                            rows_, pages_, raw_ = sc.scan_to_rows(upl.getvalue(), upl.name)
                            st.session_state["scan"] = dict(rows=sc.match_roster(rows_, roster), name=upl.name, img=pages_[0] if pages_ else None, n_pages=len(pages_), raw=raw_)
                        except Exception as e_: st.error(f"Scan tidak dapat dibaca: {e_}")
                S = st.session_state.get("scan")
                if S:
                    with st.expander("Hasil OCR mentah (untuk diagnosa)"):
                        for pg_, ls_, lo_ in S.get("raw", []):
                            st.caption(f"Halaman {pg_} · {len(ls_)} baris terbaca" + (" · mode longgar (format No TLD tidak dikenali)" if lo_ else ""))
                            st.code("\n".join(ls_[:80]) or "(tidak ada teks terbaca)")
                    if not S["rows"]:
                        st.error("Tidak ada baris petugas yang terbaca. Cek hasil OCR mentah di atas: bila teks kosong atau acak, scan kurang tajam (butuh sekitar 150 dpi ke atas) atau halaman miring/gelap. Bila teks terbaca tetapi tidak ada angka dosis berdesimal, kirim contoh scan agar format kolomnya bisa ditambahkan.")
                    else:
                        cur_old = sdose[(pd.to_numeric(sdose["Tahun"], errors="coerce") == int(tahun))].set_index(pd.to_numeric(sdose["SID"], errors="coerce")) if len(sdose) else None
                        recs = []
                        for r_ in S["rows"]:
                            old = ""
                            if r_["SID"] is not None and cur_old is not None and r_["SID"] in cur_old.index:
                                v_ = cur_old.loc[r_["SID"], dc.PK[pidx]]; old = "" if v_ is None or (isinstance(v_, float) and pd.isna(v_)) else str(v_)
                            recs.append({"Pakai": r_["status"] == "Cocok" and sc.pick(r_["nums"], mode) is not None, "No TLD (scan)": r_["tld"], "Nama (scan)": r_["nama"],
                                         "Petugas cocok": r_["cocok"], "Status": r_["status"], "Dosis (mSv)": sc.pick(r_["nums"], mode), "Nilai lama": old,
                                         "Angka terbaca": " | ".join("n/a" if x is None else f"{x:g}" for x in r_["nums"]), "_sid": r_["SID"]})
                        pv = pd.DataFrame(recs)
                        matched = {x for x in pv["_sid"].dropna().astype(int)}
                        act = roster[(roster["Status"].fillna("Aktif") != "Resign")]
                        missing = act[~act["SID"].astype(int).isin(matched)]
                        q = st.columns(4); q[0].metric("Baris terbaca", len(pv)); q[1].metric("Cocok", int((pv["Status"] == "Cocok").sum()))
                        q[2].metric("Perlu dicek nama", int((pv["Status"] == "Cek nama").sum())); q[3].metric("Tidak ditemukan", int((pv["Status"] == "Tidak ditemukan").sum()))
                        if len(missing): st.warning(f"{len(missing)} petugas aktif tidak terbaca di scan (mungkin terlewat OCR atau ada di halaman lain): " + ", ".join(missing["Nama"].astype(str).head(12)) + (" ..." if len(missing) > 12 else ""))
                        edp = st.data_editor(pv, hide_index=True, use_container_width=True, key=f"scan_ed_{S['name']}_{mode}_{pidx}",
                                             disabled=["No TLD (scan)", "Nama (scan)", "Petugas cocok", "Status", "Nilai lama", "Angka terbaca"],
                                             column_config={"_sid": None, "Pakai": st.column_config.CheckboxColumn("Pakai", width="small"), "Dosis (mSv)": st.column_config.NumberColumn("Dosis (mSv)", format="%g")})
                        if S.get("img") is not None:
                            with st.expander("Lihat gambar scan (halaman 1) untuk membandingkan"): st.image(S["img"], use_container_width=True)
                        use = edp[edp["Pakai"] & edp["_sid"].notna() & edp["Dosis (mSv)"].notna()]
                        ow = int((use["Nilai lama"].astype(str).str.strip().ne("") & (use["Nilai lama"].astype(str) != use["Dosis (mSv)"].map(lambda x: f"{x:g}"))).sum())
                        if ow: st.info(f"{ow} baris akan menimpa nilai lama yang berbeda.")
                        b1, b2 = st.columns([1, 3])
                        if b1.button(f"Isi {len(use)} dosis ke periode {pidx+1}", type="primary", key="scan_fill", disabled=len(use) == 0):
                            sd = sdose
                            for _, u_ in use.iterrows(): sd = dc.staff_set_period(sd, int(u_["_sid"]), int(tahun), pidx, float(u_["Dosis (mSv)"]), cfg.get("nbd_rs", 10.0))
                            persist(sd=sd); st.session_state.pop("scan", None); st.session_state["s_ver"] = ver + 1
                            st.session_state["flash"] = f"{len(use)} dosis dari scan diisikan ke periode {pidx+1} tahun {int(tahun)}. Cek tabel lalu pastikan sudah tersimpan."; st.rerun()
                        b2.caption("Hanya baris dengan status Cocok yang otomatis dicentang. Baris 'Cek nama' perlu Anda periksa dulu. Data baru masuk setelah klik tombol Isi.")
    # ---------------------------------------------- rekap
    elif menu == M_REKAP and not roster.empty:
        yrs = sorted(set(pd.to_numeric(sdose["Tahun"], errors="coerce").dropna().astype(int)) | {dt.date.today().year}, reverse=True)
        with st.container(border=True):
            step("📋", "Rekap dosis pekerja radiasi", "Format sama dengan rekapitulasi tahunan: per unit, per periode, total 1 tahun.")
            tahun = st.selectbox("Tahun", yrs, key="r_tahun")
            tbl = dc.staff_year(roster, sdose, tahun)
            tbl["Status"] = [dc.staff_status(t, n) for t, n in zip(tbl["Total"], tbl["NBD"])]
            real = tbl[~tbl["Nama"].astype(str).str.lower().str.startswith("kontrol")]
            k = st.columns(4); k[0].metric("Jumlah petugas", len(real)); k[1].metric("Dosis kolektif (mSv)", f"{real['Total'].sum():.3f}")
            k[2].metric("Rata-rata per petugas", f"{real['Total'].mean():.3f}" if len(real) else "-")
            mx = real.loc[real["Total"].idxmax()] if len(real) else None
            k[3].metric("Tertinggi (mSv)", f"{mx['Total']:g}" if mx is not None else "-", help=str(mx["Nama"]) if mx is not None else None)
            over = int((real["Status"] == "Melebihi NBD RS").sum())
            if over: st.warning(f"{over} petugas melebihi NBD RS pada tahun {tahun}.")
        if len(real):
            nbd = float(cfg.get("nbd_rs", 10.0))
            with st.container(border=True):
                avg = real.groupby("Unit")["Total"].mean().round(3).sort_values(ascending=False)
                st.markdown(dc.bar_svg(f"Rata-rata dosis per unit · {tahun}", list(avg.index), list(avg.values), ref=nbd), unsafe_allow_html=True)
                top = real.sort_values("Total", ascending=False).head(10)
                st.markdown(dc.bar_svg(f"10 petugas dengan dosis tertinggi · {tahun}", [str(x) for x in top["Nama"]], list(top["Total"]), ref=nbd), unsafe_allow_html=True)
        with st.container(border=True):
            for u, g in tbl.groupby("Unit", sort=False):
                st.markdown(f"**{u}**")
                v = g[["No TLD", "Nama"] + dc.PK + ["NBD", "Total", "Status"]].copy(); v.columns = ["No TLD", "Nama Petugas"] + [labels[i] if i < len(labels) else p for i, p in enumerate(dc.PK)] + ["NBD RS (mSv)", "Total 1 Tahun (mSv)", "Status"]
                v.insert(0, "No", range(1, len(v) + 1))
                _seen = {}; _cols = []
                for _c in v.columns:   # nama periode boleh kembar (mis. Des-Feb ada 2x) -> beri penanda agar tabel valid
                    _seen[_c] = _seen.get(_c, 0) + 1; _cols.append(_c if _seen[_c] == 1 else f"{_c} ({_seen[_c]})")
                v.columns = _cols
                st.dataframe(v, use_container_width=True, hide_index=True)
            d1, d2 = st.columns(2)
            d1.download_button("⬇️ Download Excel", dc.staff_excel(tahun, tbl, labels), file_name=f"Rekap_Dosis_Pekerja_{tahun}.xlsx", type="primary", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            try: d2.download_button("⬇️ Download PDF", dc.staff_pdf(tahun, tbl, labels, RS), file_name=f"Rekap_Dosis_Pekerja_{tahun}.pdf", mime="application/pdf")
            except Exception as e: d2.caption(f"PDF belum tersedia: {e}")
        with st.expander("Total dosis per petugas lintas tahun"):
            allt = pd.concat([dc.staff_year(roster, sdose, y_).assign(Tahun=y_) for y_ in sorted(set(pd.to_numeric(sdose["Tahun"], errors="coerce").dropna().astype(int)))], ignore_index=True) if len(sdose) else pd.DataFrame()
            if len(allt): st.dataframe(allt.pivot_table(index=["Unit", "Nama"], columns="Tahun", values="Total", aggfunc="sum").reset_index(), use_container_width=True, hide_index=True)
    # ---------------------------------------------- kelola petugas
    elif menu == M_KELOLA:
        with st.container(border=True):
            step("👥", "Daftar petugas", "Ubah data langsung di tabel (nama, No TLD, unit, status Aktif / Resign), tambah baris baru di bawah, lalu simpan.")
            ver = st.session_state.setdefault("k_ver", 0)
            cfgc = {"SID": None, "Unit": st.column_config.SelectboxColumn("Unit", options=units_all, width="medium"), "Status": st.column_config.SelectboxColumn("Status", options=["Aktif", "Resign"], width="small"),
                    "Nama": st.column_config.TextColumn("Nama Petugas", width="large")}
            ed = st.data_editor(roster, column_config=cfgc, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"k_ed_{ver}", height=380)
            if st.button("💾 Simpan daftar petugas", type="primary", key="k_save"):
                try:
                    e = ed.copy(); sid0 = dc.next_sid(roster)
                    miss = e["SID"].isna(); e.loc[miss, "SID"] = range(sid0, sid0 + int(miss.sum())); e["SID"] = e["SID"].astype(int)
                    e = e[e["Nama"].astype(str).str.strip().ne("") & e["Nama"].notna()]
                    persist(ro=e.reset_index(drop=True)); st.session_state["k_ver"] = ver + 1; st.session_state["flash"] = f"{len(e)} petugas tersimpan."; st.rerun()
                except Exception as e_: st.error(f"Gagal menyimpan: {e_}")
        def lab(r_): return f"{r_['Nama']} — {r_['No TLD']} ({r_['Unit']})"
        c1, c2 = st.columns(2)
        with c1, st.container(border=True):
            step("➕", "Tambah petugas baru", "Periode sebelum mulai bertugas otomatis ditandai 'Penambahan TLD Baru'.")
            with st.form("f_add", clear_on_submit=True):
                n1 = st.text_input("Nama petugas"); n2 = st.text_input("No TLD"); n3 = st.selectbox("Unit", units_all)
                f1, f2 = st.columns(2); n4 = f1.number_input("Tahun mulai", 2015, 2100, dt.date.today().year); n5 = f2.selectbox("Mulai periode", range(len(labels)), format_func=lambda i: f"{i+1}. {labels[i]}")
                if st.form_submit_button("Tambahkan", type="primary"):
                    if not n1.strip(): st.error("Nama petugas wajib diisi.")
                    else:
                        sid = dc.next_sid(roster); ro = pd.concat([roster, pd.DataFrame([{"SID": sid, "No TLD": n2.strip() or None, "Nama": n1.strip(), "Unit": n3, "Status": "Aktif", "Catatan": None}])], ignore_index=True)
                        sd = dc.mark_before(sdose, sid, n4, int(n5), "Penambahan TLD Baru", cfg.get("nbd_rs", 10.0)) if int(n5) > 0 else sdose
                        persist(ro, sd); st.session_state["k_ver"] = ver + 1; st.session_state["flash"] = f"{n1.strip()} ditambahkan."; st.rerun()
        with c2, st.container(border=True):
            step("🔄", "Ganti TLD petugas", "No TLD diperbarui dan periode sebelumnya ditandai 'Pergantian TLD'.")
            if roster.empty: st.caption("Belum ada petugas.")
            else:
                with st.form("f_swap", clear_on_submit=True):
                    opts = {int(r_["SID"]): lab(r_) for _, r_ in roster.iterrows()}
                    g1 = st.selectbox("Petugas", list(opts), format_func=lambda i: opts[i]); g2 = st.text_input("No TLD baru")
                    h1, h2 = st.columns(2); g3 = h1.number_input("Tahun", 2015, 2100, dt.date.today().year); g4 = h2.selectbox("TLD baru mulai periode", range(len(labels)), format_func=lambda i: f"{i+1}. {labels[i]}")
                    if st.form_submit_button("Ganti TLD", type="primary"):
                        if not g2.strip(): st.error("No TLD baru wajib diisi.")
                        else:
                            ro = roster.copy(); m_ = ro["SID"].astype(int) == int(g1); old = ro.loc[m_, "No TLD"].iloc[0]
                            ro.loc[m_, "No TLD"] = g2.strip(); ro.loc[m_, "Catatan"] = f"TLD {old} diganti {g2.strip()} ({g3})"
                            sd = dc.mark_before(sdose, g1, g3, int(g4), "Pergantian TLD", cfg.get("nbd_rs", 10.0)) if int(g4) > 0 else sdose
                            persist(ro, sd); st.session_state["k_ver"] = ver + 1; st.session_state["flash"] = f"No TLD {opts[int(g1)].split(' — ')[0]} diganti menjadi {g2.strip()}."; st.rerun()

# =================================================== PARAMETER
elif menu == MENU[4]:
    with st.container(border=True):
        step("⚙", "Parameter umum", "Dipakai untuk kategori usia dan perhitungan INAK/ESAK.")
        c1, c2, c3 = st.columns(3)
        cfg["bayi_max"] = c1.number_input("Bayi: usia maks (th)", value=int(cfg["bayi_max"]))
        cfg["dewasa_min"] = c2.number_input("Dewasa: usia min (th)", value=int(cfg["dewasa_min"]))
        cfg["bsf"] = c3.number_input("BSF", value=float(cfg["bsf"]), step=0.01)
        cfg["nbd_rs"] = st.number_input("NBD / pembatas dosis RS pekerja (mSv per tahun)", value=float(cfg.get("nbd_rs", 10.0)), step=0.5)
        u1, u2 = st.columns(2); un = ["mGy.cm2", "Gy.cm2"]
        cfg["unit_dap_cath"] = u1.selectbox("Satuan DAP input Cathlab / Fluoroskopi", un, index=un.index(cfg["unit_dap_cath"]))
        cfg["unit_dap_dental"] = u2.selectbox("Satuan DAP input Dental", un, index=un.index(cfg["unit_dap_dental"]))
    with st.container(border=True):
        step("⚡", "Output tabung (kV vs µGy/mAs)", "Dari hasil uji; dipakai menghitung INAK. Minimal 3 titik.")
        o = st.data_editor(pd.DataFrame(cfg["out_pts"], columns=["kV", "uGy/mAs"]), num_rows="dynamic", key="outpts", hide_index=True)
        cfg["out_pts"] = o.dropna().values.tolist(); co = dc.fit_output(cfg["out_pts"])
        st.caption(("Kurva: y = %.5f·kV² + %.4f·kV + %.3f" % tuple(co)) if co else "Isi minimal 3 titik.")
    with st.container(border=True):
        step("🎯", "Daftar pemeriksaan & acuan nasional (TPD)", "Kosong = tidak dibandingkan. Nama baru dari import otomatis masuk di sini. Verifikasi dengan TPD BAPETEN terbaru.")
        for mod in dc.MODS:
            with st.expander(dc.MODS[mod]["label"]):
                ks = ["INAK", "ESAK"] if mod == "GR" else ["CTDIvol", "DLP"] if mod == "CT" else ["MGD"] if mod == "MAMMO" else ["DAP", "Kerma total"] if mod in ("CATH", "FLURO") else ["DAP"]
                t = pd.DataFrame([{"Nama": n, **{k_: v.get(k_) for k_ in ks}} for n, v in cfg["tpd"].get(mod, {}).items()], columns=["Nama"] + ks)
                e = st.data_editor(t, num_rows="dynamic", key=f"tpd_{mod}", use_container_width=True, hide_index=True)
                cfg["tpd"][mod] = {r["Nama"]: {k_: float(r[k_]) for k_ in ks if not pd.isna(r[k_])} for _, r in e.iterrows() if isinstance(r["Nama"], str) and r["Nama"].strip()}
    if st.button("💾 Simpan parameter", type="primary"):
        try: cfg_save(cfg); st.success("Parameter tersimpan." if ONLINE else "Parameter dipakai selama sesi ini (mode lokal).")
        except Exception as e: st.error(f"Gagal: {e}")
