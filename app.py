import csv
import io
import sqlite3

import pandas as pd
import streamlit as st

# ==============================
# 1. DATABASE
# ==============================
DB_FILE = "pasca_makesta.db"

DAFTAR_LOMBA = [
    "Lomba Cerdas Cermat",
    "Lomba Gobak Sodor",
    "Lomba Voli Air",
    "Lomba Paduan Suara",
]


def koneksi():
    return sqlite3.connect(DB_FILE)


def buat_tabel():
    with koneksi() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS pendaftaran (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lomba TEXT NOT NULL,
                ranting TEXT NOT NULL,
                jumlah_tim INTEGER NOT NULL
            )
            """
        )
        kolom = [r[1] for r in db.execute("PRAGMA table_info(pendaftaran)")]
        if "peserta" not in kolom:
            db.execute("ALTER TABLE pendaftaran ADD COLUMN peserta TEXT NOT NULL DEFAULT ''")


def simpan(lomba, ranting, jumlah, peserta):
    with koneksi() as db:
        db.execute(
            "INSERT INTO pendaftaran (lomba, ranting, jumlah_tim, peserta) VALUES (?, ?, ?, ?)",
            (lomba, ranting, jumlah, peserta),
        )


def ambil_data(filter_lomba="Semua Lomba", kata_kunci=""):
    query = "SELECT id, lomba, ranting, jumlah_tim, peserta FROM pendaftaran WHERE (ranting LIKE ? OR peserta LIKE ?)"
    param = [f"%{kata_kunci}%", f"%{kata_kunci}%"]
    if filter_lomba != "Semua Lomba":
        query += " AND lomba = ?"
        param.append(filter_lomba)
    query += " ORDER BY id DESC"
    with koneksi() as db:
        return db.execute(query, param).fetchall()


def hapus(daftar_id):
    with koneksi() as db:
        db.executemany("DELETE FROM pendaftaran WHERE id = ?", [(i,) for i in daftar_id])


def csv_bytes():
    with koneksi() as db:
        data = db.execute(
            "SELECT lomba, ranting, peserta, jumlah_tim FROM pendaftaran ORDER BY lomba, ranting"
        ).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Cabang Lomba", "Asal Ranting", "Nama Peserta", "Jumlah Tim"])
    w.writerows([(a, b, p.replace("\n", ", "), j) for a, b, p, j in data])
    return buf.getvalue().encode("utf-8-sig")


def password_admin():
    try:
        return st.secrets.get("ADMIN_PASSWORD", None)
    except Exception:
        return None


# ==============================
# 2. TAMPILAN
# ==============================
st.set_page_config(page_title="Registrasi Pasca Makesta 2026", page_icon="🏆", layout="centered")
buat_tabel()

st.markdown(
    "<h1 style='text-align:center;color:#174D3C;margin-bottom:0'>PASCA MAKESTA 2026</h1>"
    "<p style='text-align:center'>Sistem Registrasi Lomba</p>",
    unsafe_allow_html=True,
)

# --- Formulir pendaftaran ---
st.subheader("Formulir Pendaftaran")
with st.form("form_daftar", clear_on_submit=True):
    lomba = st.selectbox("Cabang Lomba", DAFTAR_LOMBA)
    ranting = st.text_input("Asal Ranting")
    peserta = st.text_area(
        "Nama Peserta",
        placeholder="Tulis satu nama per baris",
        help="Tulis satu nama peserta per baris.",
    )
    jumlah = st.number_input("Jumlah Tim", min_value=1, value=1, step=1)
    kirim = st.form_submit_button("Simpan Pendaftaran", type="primary")

if kirim:
    daftar_nama = [n.strip() for n in peserta.splitlines() if n.strip()]
    if not ranting.strip() or not daftar_nama:
        st.warning("Semua data wajib diisi!")
    else:
        simpan(lomba, ranting.strip(), int(jumlah), "\n".join(daftar_nama))
        st.success("Pendaftaran berhasil disimpan!")

# --- Area panitia (data hanya terlihat setelah login) ---
st.divider()
with st.expander("🔒 Panel Panitia"):
    sandi_benar = password_admin()
    if not sandi_benar:
        st.info("Password panitia belum diatur (ADMIN_PASSWORD di Secrets).")
    else:
        sandi = st.text_input("Password panitia", type="password")
        if sandi == sandi_benar:
            st.subheader("Daftar Pendaftar")
            c1, c2 = st.columns(2)
            filter_lomba = c1.selectbox("Filter lomba", ["Semua Lomba"] + DAFTAR_LOMBA)
            kata_kunci = c2.text_input("Cari ranting / peserta").strip()

            data = ambil_data(filter_lomba, kata_kunci)
            tabel = pd.DataFrame(
                [(n, b[1], b[2], b[4].replace("\n", ", "), b[3]) for n, b in enumerate(data, start=1)],
                columns=["No.", "Cabang Lomba", "Asal Ranting", "Nama Peserta", "Jumlah Tim"],
            )
            st.dataframe(tabel, hide_index=True, use_container_width=True)
            st.caption(f"Jumlah pendaftaran: {len(data)}")

            st.download_button(
                "⬇️ Ekspor CSV",
                data=csv_bytes(),
                file_name="data_pendaftaran_pasca_makesta.csv",
                mime="text/csv",
            )

            semua = ambil_data()
            opsi = {f"{r[1]} | {r[2]} | {r[3]} tim (#{r[0]})": r[0] for r in semua}
            pilih = st.multiselect("Pilih data yang ingin dihapus", list(opsi))
            if st.button("Hapus Data Terpilih") and pilih:
                hapus([opsi[p] for p in pilih])
                st.success("Data dihapus.")
                st.rerun()
        elif sandi:
            st.error("Password salah.")
