-- Jalankan di Supabase > SQL Editor (sekali saja)
create table if not exists dose_entries (
  id bigserial primary key,
  modality text not null,            -- GR | CT | CATH | DENTAL
  data jsonb not null,               -- satu baris pasien
  created_at timestamptz default now()
);
create index if not exists dose_entries_mod on dose_entries (modality);
create table if not exists dose_config (
  id text primary key,               -- 'main'
  data jsonb not null,
  updated_at timestamptz default now()
);
alter table dose_entries enable row level security;
alter table dose_config enable row level security;
-- sama seperti tabel PMI: akses lewat key yang tersimpan di Streamlit secrets
create policy "dose_entries_all" on dose_entries for all using (true) with check (true);
create policy "dose_config_all" on dose_config for all using (true) with check (true);
