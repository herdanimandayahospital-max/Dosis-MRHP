# Dose Monitoring - Mandaya Royal Hospital Puri
Aplikasi Streamlit mandiri: import data pasien (Google Form) -> isi protokol & dosis -> hitung INAK/ESAK, CTDI/DLP, DAP -> simpan (Supabase) -> unduh Excel format BAPETEN.
1. Supabase > SQL Editor: jalankan `supabase_setup.sql`
2. Push semua file ini ke repo GitHub baru
3. share.streamlit.io > New app > pilih repo, main file `app.py`
4. Settings > Secrets: isi seperti `.streamlit/secrets.toml.contoh`
