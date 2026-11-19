# -*- coding: utf-8 -*-
"""Aplikasi Dose Monitoring (mandiri): import -> isi protokol & dosis -> hitung & simpan -> unduh format BAPETEN."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, pandas as pd, numpy as np, streamlit as st
import dose_core as dc

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Mandaya Logo.png")
st.set_page_config(page_title="Dose Monitoring - MRHP", page_icon=LOGO if os.path.exists(LOGO) else "☢️", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1250px}
h1,h2,h3{color:#073763}
.stButton>button,.stDownloadButton>button{border-radius:10px;min-height:2.8rem}
@media (max-width:768px){.block-container{padding:.8rem .6rem}}
</style>""", unsafe_allow_html=True)
RS = "Mandaya Royal Hospital Puri"

def _sec(k, d=""):
    try: return st.secrets[k]
    except Exception: return d
URL, KEY, PW = _sec("SUPABASE_URL").rstrip("/"), _sec("SUPABASE_KEY"), _sec("AUTHOR_PASSWORD")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}

def sb_ok(): return bool(URL and KEY)
def sb_get(mod):
    rows, off = [], 0
    while True:
        r = requests.get(f"{URL}/rest/v1/dose_entries", headers={**H, "Range": f"{off}-{off+999}"},
                         params={"modality": f"eq.{mod}", "select": "id,data", "order": "id"}, timeout=30)
        r.raise_for_status(); b = r.json(); rows += b
        if len(b) < 1000: break
        off += 1000
    df = pd.DataFrame([{**x["data"], "_id": x["id"]} for x in rows])
    return df
def sb_replace(mod, df):
    """Simpan: hapus data modalitas lalu tulis ulang (sederhana & konsisten dengan tabel yang diedit)."""
    clean = df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")
    recs = []
    for r in clean.to_dict("records"):
        r = {k: (None if (isinstance(v, float) and np.isnan(v)) or v is pd.NaT else (v.isoformat() if hasattr(v, "isoformat") else v)) for k, v in r.items()}
        if any(v not in (None, "") for v in r.values()): recs.append({"modality": mod, "data": r})
    requests.delete(f"{URL}/rest/v1/dose_entries", headers=H, params={"modality": f"eq.{mod}"}, timeout=60).raise_for_status()
    for i in range(0, len(recs), 500):
        requests.post(f"{URL}/rest/v1/dose_entries", headers=H, data=json.dumps(recs[i:i+500]), timeout=60).raise_for_status()
    return len(recs)
def cfg_load():
    try:
        r = requests.get(f"{URL}/rest/v1/dose_config", headers=H, params={"id": "eq.main", "select": "data"}, timeout=20); r.raise_for_status()
        return dc.merge_cfg(r.json()[0]["data"] if r.json() else None)
    except Exception: return dc.merge_cfg(None)
def cfg_save(cfg):
    h = {**H, "Prefer": "resolution=merge-duplicates,return=minimal"}
    requests.post(f"{URL}/rest/v1/dose_config", headers=h, data=json.dumps({"id": "main", "data": cfg}), timeout=20).raise_for_status()

if os.path.exists(LOGO): st.image(LOGO, width=190)
st.title("Dose Monitoring Pasien")
st.caption(f"{RS} · Departemen Radiologi · Data → hitung → simpan → unduh format BAPETEN")

# --- login (password author yang sama dengan aplikasi PMI)
if PW and not st.session_state.get("dose_ok"):
    p = st.text_input("Password author", type="password")
    if st.button("Masuk") and p == PW: st.session_state["dose_ok"] = True; st.rerun()
    st.stop()
if not sb_ok():
    st.error("SUPABASE_URL / SUPABASE_KEY belum diisi di Secrets. Halaman ini tidak dapat menyimpan data."); st.stop()

if "cfg" not in st.session_state: st.session_state.cfg = cfg_load()
cfg = st.session_state.cfg
tabs = st.tabs([dc.MODS[m]["label"] for m in dc.MODS] + ["⚙️ Parameter & Acuan"])

for tab, mod in zip(tabs, dc.MODS):
    with tab:
        spec = dc.MODS[mod]; ex = spec["exam"]; key = f"df_{mod}"
        if key not in st.session_state:
            try: st.session_state[key] = sb_get(mod)
            except Exception as e: st.session_state[key] = pd.DataFrame(); st.warning(f"Gagal membaca data: {e}")
        ver = st.session_state.setdefault(f"ver_{mod}", 0)
        if st.session_state.get(f"flash_{mod}"): st.success(st.session_state.pop(f"flash_{mod}"))
        st.markdown("**1 · Import data pasien** (ekspor Google Form: .xlsx / .csv)")
        up = st.file_uploader("Pilih file", type=["xlsx", "xls", "csv"], key=f"up_{mod}")
        if up is not None and st.button("Tambahkan ke tabel", key=f"imp_{mod}"):
            raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
            new, used = dc.map_columns(mod, raw)
            cur = st.session_state.get(f"cur_{mod}", st.session_state[key])
            st.session_state[key] = pd.concat([cur, new], ignore_index=True)
            st.session_state[f"ver_{mod}"] += 1
            st.session_state[f"flash_{mod}"] = f"{len(new)} baris berhasil diimpor. Kolom terbaca: " + ", ".join(used) + ". Lengkapi protokol & dosis, lalu klik Simpan."
            st.rerun()
        st.markdown("**2 · Isi protokol & dosis**  (baris baru bisa ditambah di bagian bawah tabel)")
        base = st.session_state[key].copy()
        for c in spec["cols"]:
            if c not in base.columns: base[c] = None
        for c in ("Gender", "Kode Pasien", ex): base[c] = base[c].astype("object")
        show = base[spec["cols"] + [c for c in base.columns if c.startswith("_")]]
        cc = {ex: st.column_config.SelectboxColumn(ex, options=list(cfg["tpd"][mod]), help="Pilih dari daftar atau ketik di Parameter"),
              "Gender": st.column_config.SelectboxColumn("Gender", options=["M", "F"]), "_id": None}
        if "Tanggal" in show.columns: show["Tanggal"] = pd.to_datetime(show["Tanggal"], errors="coerce"); cc["Tanggal"] = st.column_config.DateColumn("Tanggal")
        edited = st.data_editor(show, num_rows="dynamic", column_config=cc, use_container_width=True, key=f"ed_{mod}_{ver}", height=360)
        st.session_state[f"cur_{mod}"] = edited
        st.markdown("**3 · Hitung & simpan**")
        d = dc.compute(mod, edited.drop(columns=["_id"], errors="ignore"), cfg)
        okn = int((d["Cek"] == "OK").sum()); st.write(f"Baris: **{len(d)}** · Valid: **{okn}** · Perlu dilengkapi: **{len(d)-okn}**")
        derived = [c for c in d.columns if c not in spec["cols"]]
        st.dataframe(d[["Kode Pasien"] + derived], use_container_width=True, height=240)
        if st.button("💾 Simpan ke database", key=f"sv_{mod}", type="primary"):
            try: n = sb_replace(mod, edited); st.session_state[key] = edited; st.session_state[f"ver_{mod}"] += 1; st.session_state[f"flash_{mod}"] = f"{n} baris tersimpan."; st.rerun()
            except Exception as e: st.error(f"Gagal menyimpan: {e}")
        st.markdown("**4 · Unduh format BAPETEN**")
        c1, c2, c3 = st.columns(3)
        kat = c1.selectbox("Kategori usia", ["Dewasa", "Anak", "Bayi", "Semua"], key=f"k_{mod}")
        dari = c2.date_input("Dari tanggal", value=None, key=f"d1_{mod}"); sampai = c3.date_input("Sampai tanggal", value=None, key=f"d2_{mod}")
        rk = dc.rekap(mod, d[d["Cek"] == "OK"], cfg, kat, dari, sampai)
        st.dataframe(rk, use_container_width=True)
        per = "semua" if not (dari or sampai) else f"{dari or '...'} s/d {sampai or '...'}"
        xl = dc.to_excel(mod, d, rk, cfg, dict(rs=RS, kategori=kat, periode=per))
        st.download_button("⬇️ Unduh Excel (Rekap + Data)", xl, file_name=f"Dosis_{mod}_{kat}_{dt.date.today():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{mod}")

with tabs[-1]:
    st.subheader("Parameter")
    c1, c2, c3 = st.columns(3)
    cfg["bayi_max"] = c1.number_input("Bayi: usia maks (th)", value=int(cfg["bayi_max"]))
    cfg["dewasa_min"] = c2.number_input("Dewasa: usia min (th)", value=int(cfg["dewasa_min"]))
    cfg["bsf"] = c3.number_input("BSF", value=float(cfg["bsf"]), step=0.01)
    u1, u2 = st.columns(2)
    cfg["unit_dap_cath"] = u1.selectbox("Satuan DAP input Cathlab", ["mGy.cm2", "Gy.cm2"], index=["mGy.cm2", "Gy.cm2"].index(cfg["unit_dap_cath"]))
    cfg["unit_dap_dental"] = u2.selectbox("Satuan DAP input Dental", ["mGy.cm2", "Gy.cm2"], index=["mGy.cm2", "Gy.cm2"].index(cfg["unit_dap_dental"]))
    st.markdown("**Output tabung (kV vs µGy/mAs)** — dipakai untuk INAK")
    o = st.data_editor(pd.DataFrame(cfg["out_pts"], columns=["kV", "uGy/mAs"]), num_rows="dynamic", key="outpts")
    cfg["out_pts"] = o.dropna().values.tolist(); co = dc.fit_output(cfg["out_pts"])
    st.caption("y = %.5f·kV² + %.4f·kV + %.3f" % co if co else "Isi minimal 3 titik.")
    st.markdown("**Daftar pemeriksaan & acuan nasional (TPD)** — kosong = tidak dibandingkan. Nilai awal dari file database Anda; verifikasi dengan TPD BAPETEN.")
    for mod in dc.MODS:
        with st.expander(dc.MODS[mod]["label"]):
            keys = [("INAK", "ESAK")] if mod == "GR" else [("CTDIvol", "DLP")] if mod == "CT" else [("DAP", "Kerma total")] if mod == "CATH" else [("DAP",)]
            ks = list(keys[0])
            t = pd.DataFrame([{"Nama": n, **{k: v.get(k) for k in ks}} for n, v in cfg["tpd"][mod].items()], columns=["Nama"] + ks)
            e = st.data_editor(t, num_rows="dynamic", key=f"tpd_{mod}", use_container_width=True)
            cfg["tpd"][mod] = {r["Nama"]: {k: (None if pd.isna(r[k]) else float(r[k])) for k in ks if not pd.isna(r[k])} for _, r in e.iterrows() if isinstance(r["Nama"], str) and r["Nama"].strip()}
    if st.button("💾 Simpan parameter", type="primary"):
        try: cfg_save(cfg); st.success("Parameter tersimpan.")
        except Exception as e: st.error(f"Gagal: {e}")
