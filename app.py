# -*- coding: utf-8 -*-
"""Dose Monitoring - Mandaya Royal Hospital Puri.
Import -> isi protokol & dosis -> hitung & simpan -> unduh format BAPETEN."""
import os, io, json, base64, datetime as dt
import requests, pandas as pd, numpy as np, streamlit as st
import dose_core as dc

HERE = os.path.dirname(os.path.abspath(__file__))
def _f(name): return os.path.join(HERE, name)
LOGO, LOGO_W = _f("Mandaya Logo.png"), _f("Mandaya Logo White.png")
RS = "Mandaya Royal Hospital Puri"
st.set_page_config(page_title="Dose Monitoring - MRHP", page_icon=LOGO if os.path.exists(LOGO) else None, layout="wide")

def _b64(p):
    try: return base64.b64encode(open(p, "rb").read()).decode()
    except Exception: return ""

st.markdown("""<style>
:root{--navy:#073763;--teal:#1B7895;--soft:#F2F5F9;--line:#DCE5EE}
.block-container{padding-top:3.2rem !important;padding-bottom:3rem;max-width:1280px}
.hero{background:linear-gradient(120deg,#073763 0%,#0d5a86 60%,#1B7895 100%);border-radius:18px;padding:20px 26px;margin:0 0 16px 0;display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.hero img{height:46px;width:auto}
.hero .t{color:#fff;font-size:1.55rem;font-weight:700;line-height:1.15}
.hero .s{color:#cfe3f1;font-size:.9rem;margin-top:3px}
.badge{display:inline-block;border-radius:999px;padding:3px 12px;font-size:.78rem;font-weight:600;margin-left:auto}
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

def sb_get(mod):
    if not ONLINE: return pd.DataFrame()
    rows, off = [], 0
    while True:
        r = requests.get(f"{URL}/rest/v1/dose_entries", headers={**H, "Range": f"{off}-{off+999}"},
                         params={"modality": f"eq.{mod}", "select": "id,data", "order": "id"}, timeout=30)
        r.raise_for_status(); b = r.json(); rows += b
        if len(b) < 1000: break
        off += 1000
    return pd.DataFrame([{**x["data"], "_id": x["id"]} for x in rows])
def sb_replace(mod, df):
    clean = df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")
    recs = []
    for r in clean.to_dict("records"):
        r = {k: (None if (isinstance(v, float) and np.isnan(v)) or v is pd.NaT else (v.isoformat() if hasattr(v, "isoformat") else v)) for k, v in r.items()}
        if any(v not in (None, "") for v in r.values()): recs.append({"modality": mod, "data": r})
    if ONLINE:
        requests.delete(f"{URL}/rest/v1/dose_entries", headers=H, params={"modality": f"eq.{mod}"}, timeout=60).raise_for_status()
        for i in range(0, len(recs), 500):
            requests.post(f"{URL}/rest/v1/dose_entries", headers=H, data=json.dumps(recs[i:i+500]), timeout=60).raise_for_status()
    return len(recs)
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
st.markdown(f'<div class="hero">{f"<img src=data:image/png;base64,{logo}>" if logo else ""}<div><div class="t">Dose Monitoring Pasien</div>'
            f'<div class="s">{RS} · Departemen Radiologi · Laporan BAPETEN</div></div>{badge}</div>', unsafe_allow_html=True)

if PW and not st.session_state.get("dose_ok"):
    with st.container(border=True):
        st.markdown("**Masuk**")
        p = st.text_input("Password author", type="password")
        if st.button("Masuk", type="primary") and p == PW: st.session_state["dose_ok"] = True; st.rerun()
    st.stop()
if not ONLINE:
    st.info("**Mode lokal** — aplikasi tetap bisa dipakai (import, hitung, unduh), tetapi data hilang jika halaman ditutup. "
            "Hubungkan Supabase di *Settings → Secrets* agar data tersimpan permanen.")

if "cfg" not in st.session_state: st.session_state.cfg = cfg_load()
cfg = st.session_state.cfg
icons = {"GR": "🩻", "CT": "🌀", "CATH": "❤️", "DENTAL": "🦷"}
tabs = st.tabs([f"{icons[m]} {dc.MODS[m]['label']}" for m in dc.MODS] + ["⚙️ Parameter & Acuan"])

def template_xlsx(mod):
    spec = dc.MODS[mod]; b = io.BytesIO()
    pd.DataFrame(columns=spec["cols"]).to_excel(b, index=False); return b.getvalue()

for tab, mod in zip(tabs, dc.MODS):
    with tab:
        spec = dc.MODS[mod]; ex = spec["exam"]; key = f"df_{mod}"
        if key not in st.session_state:
            try: st.session_state[key] = sb_get(mod)
            except Exception as e: st.session_state[key] = pd.DataFrame(); st.warning(f"Gagal membaca data: {e}")
        ver = st.session_state.setdefault(f"ver_{mod}", 0)
        if st.session_state.get(f"flash_{mod}"): st.success(st.session_state.pop(f"flash_{mod}"))

        # 1 import
        with st.container(border=True):
            step(1, "Import data pasien", "Ekspor Google Form (.xlsx / .csv). Kolom dikenali otomatis.")
            c1, c2 = st.columns([3, 1])
            up = c1.file_uploader("Pilih file", type=["xlsx", "xls", "csv"], key=f"up_{mod}", label_visibility="collapsed")
            c2.download_button("Unduh template kolom", template_xlsx(mod), file_name=f"Template_{mod}.xlsx", key=f"tpl_{mod}", use_container_width=True)
            if up is not None and st.button("Tambahkan ke tabel", key=f"imp_{mod}", type="primary"):
                raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
                new, used = dc.map_columns(mod, raw)
                cur = st.session_state.get(f"cur_{mod}", st.session_state[key])
                st.session_state[key] = pd.concat([cur, new], ignore_index=True)
                st.session_state[f"ver_{mod}"] += 1
                st.session_state[f"flash_{mod}"] = f"{len(new)} baris berhasil diimpor. Kolom terbaca: " + ", ".join(used) + ". Lengkapi protokol & dosis di langkah 2."
                st.rerun()

        # 2 isi
        with st.container(border=True):
            step(2, "Isi protokol & dosis", "Klik sel untuk mengisi. Tambah baris baru di bagian bawah tabel.")
            base = st.session_state[key].copy()
            for c in spec["cols"]:
                if c not in base.columns: base[c] = None
            for c in ("Gender", "Kode Pasien", ex): base[c] = base[c].astype("object")
            show = base[spec["cols"] + [c for c in base.columns if c.startswith("_")]]
            cc = {ex: st.column_config.SelectboxColumn(ex, options=list(cfg["tpd"][mod]), width="medium"),
                  "Gender": st.column_config.SelectboxColumn("Gender", options=["M", "F"], width="small"), "_id": None}
            if "Tanggal" in show.columns:
                show["Tanggal"] = pd.to_datetime(show["Tanggal"], errors="coerce"); cc["Tanggal"] = st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY")
            edited = st.data_editor(show, num_rows="dynamic", column_config=cc, use_container_width=True, key=f"ed_{mod}_{ver}", height=340)
            st.session_state[f"cur_{mod}"] = edited

        # 3 hitung
        d = dc.compute(mod, edited.drop(columns=["_id"], errors="ignore"), cfg)
        okn = int((d["Cek"] == "OK").sum()); bad = len(d) - okn
        with st.container(border=True):
            step(3, "Hasil hitung & simpan", "Dosis turunan dihitung otomatis. Baris bermasalah ditandai di kolom Cek.")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total baris", len(d)); m2.metric("Valid", okn); m3.metric("Perlu dilengkapi", bad)
            m4.metric("Dewasa / Anak / Bayi", " / ".join(str(int((d["Kategori usia"] == k).sum())) for k in ("Dewasa", "Anak", "Bayi")))
            only_bad = st.toggle("Tampilkan hanya baris bermasalah", key=f"bad_{mod}", value=False)
            derived = [c for c in d.columns if c not in spec["cols"]]
            view = d[["Kode Pasien", ex] + derived]
            if only_bad: view = view[d["Cek"] != "OK"]
            st.dataframe(view, use_container_width=True, height=240, hide_index=True)
            if st.button("💾 Simpan data" if ONLINE else "💾 Simpan sementara (sesi ini)", key=f"sv_{mod}", type="primary"):
                try:
                    n = sb_replace(mod, edited); st.session_state[key] = edited; st.session_state[f"ver_{mod}"] += 1
                    st.session_state[f"flash_{mod}"] = f"{n} baris tersimpan." if ONLINE else f"{n} baris disimpan di sesi ini (mode lokal)."; st.rerun()
                except Exception as e: st.error(f"Gagal menyimpan: {e}")

        # 4 unduh
        with st.container(border=True):
            step(4, "Rekap & unduh format BAPETEN", "Median (Q2) dan Q3 per jenis pemeriksaan; acuan nasional hanya untuk Dewasa.")
            f1, f2, f3 = st.columns(3)
            kat = f1.selectbox("Kategori usia", ["Dewasa", "Anak", "Bayi", "Semua"], key=f"k_{mod}")
            dari = f2.date_input("Dari tanggal", value=None, key=f"d1_{mod}", format="DD/MM/YYYY")
            sampai = f3.date_input("Sampai tanggal", value=None, key=f"d2_{mod}", format="DD/MM/YYYY")
            rk = dc.rekap(mod, d[d["Cek"] == "OK"], cfg, kat, dari, sampai)
            if rk.empty: st.caption("Belum ada data valid untuk filter ini.")
            else:
                def _c(v):
                    return ("background-color:#F8D0D0;color:#9C1C1C;font-weight:600" if str(v).startswith("Di atas") else
                            "background-color:#D5EEDD;color:#1E6B3A;font-weight:600" if str(v).startswith("Sesuai") else "")
                fmt = {c: "{:.2f}" for c in rk.columns if c not in ("Jenis Pemeriksaan", "Jumlah Sampel", "Status")}
                sty = rk.style.format(fmt, na_rep="-"); sty = (sty.map if hasattr(sty, "map") else sty.applymap)(_c, subset=["Status"])
                st.dataframe(sty, use_container_width=True, hide_index=True)
            per = "semua" if not (dari or sampai) else f"{dari or '...'} s/d {sampai or '...'}"
            xl = dc.to_excel(mod, d, rk, cfg, dict(rs=RS, kategori=kat, periode=per))
            st.download_button("⬇️ Unduh Excel (Rekap + Data)", xl, file_name=f"Dosis_{mod}_{kat}_{dt.date.today():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{mod}", type="primary")

with tabs[-1]:
    with st.container(border=True):
        step("⚙", "Parameter umum", "Dipakai untuk kategori usia dan perhitungan INAK/ESAK.")
        c1, c2, c3 = st.columns(3)
        cfg["bayi_max"] = c1.number_input("Bayi: usia maks (th)", value=int(cfg["bayi_max"]))
        cfg["dewasa_min"] = c2.number_input("Dewasa: usia min (th)", value=int(cfg["dewasa_min"]))
        cfg["bsf"] = c3.number_input("BSF", value=float(cfg["bsf"]), step=0.01)
        u1, u2 = st.columns(2)
        un = ["mGy.cm2", "Gy.cm2"]
        cfg["unit_dap_cath"] = u1.selectbox("Satuan DAP input Cathlab", un, index=un.index(cfg["unit_dap_cath"]))
        cfg["unit_dap_dental"] = u2.selectbox("Satuan DAP input Dental", un, index=un.index(cfg["unit_dap_dental"]))
    with st.container(border=True):
        step("⚡", "Output tabung (kV vs µGy/mAs)", "Dari hasil uji; dipakai menghitung INAK. Minimal 3 titik.")
        o = st.data_editor(pd.DataFrame(cfg["out_pts"], columns=["kV", "uGy/mAs"]), num_rows="dynamic", key="outpts", hide_index=True)
        cfg["out_pts"] = o.dropna().values.tolist(); co = dc.fit_output(cfg["out_pts"])
        st.caption(("Kurva: y = %.5f·kV² + %.4f·kV + %.3f" % tuple(co)) if co else "Isi minimal 3 titik.")
    with st.container(border=True):
        step("🎯", "Daftar pemeriksaan & acuan nasional (TPD)", "Kosong = tidak dibandingkan. Verifikasi dengan TPD BAPETEN terbaru.")
        for mod in dc.MODS:
            with st.expander(dc.MODS[mod]["label"]):
                ks = ["INAK", "ESAK"] if mod == "GR" else ["CTDIvol", "DLP"] if mod == "CT" else ["DAP", "Kerma total"] if mod == "CATH" else ["DAP"]
                t = pd.DataFrame([{"Nama": n, **{k: v.get(k) for k in ks}} for n, v in cfg["tpd"][mod].items()], columns=["Nama"] + ks)
                e = st.data_editor(t, num_rows="dynamic", key=f"tpd_{mod}", use_container_width=True, hide_index=True)
                cfg["tpd"][mod] = {r["Nama"]: {k: float(r[k]) for k in ks if not pd.isna(r[k])} for _, r in e.iterrows() if isinstance(r["Nama"], str) and r["Nama"].strip()}
    if st.button("💾 Simpan parameter", type="primary"):
        try: cfg_save(cfg); st.success("Parameter tersimpan." if ONLINE else "Parameter dipakai selama sesi ini (mode lokal).")
        except Exception as e: st.error(f"Gagal: {e}")
