import streamlit as st
import pandas as pd
import io
import time
import sqlite3

# --- Konfigurasi Awal dan Inisialisasi State ---
st.set_page_config(page_title="Pelaporan Kendala Agen", layout="centered", initial_sidebar_state="auto")

# Inisialisasi session state (hanya untuk alur UI, bukan data permanen)
if 'stage' not in st.session_state:
    st.session_state.stage = "search"
if 'current_report' not in st.session_state:
    st.session_state.current_report = {}
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'show_auth_form' not in st.session_state:
    st.session_state.show_auth_form = False

# --- Fungsi Database SQLite ---
DB_FILE = "laporan_kendala.db"

def init_db():
    """Membuat file database dan tabel jika belum ada."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Membuat tabel dengan kolom yang sesuai
    c.execute('''
        CREATE TABLE IF NOT EXISTS laporan (
            "Sold-to-Party ID" INTEGER,
            "Nama Agen" TEXT,
            "Sales Area" TEXT,
            "Wilayah Penyaluran" TEXT,
            "Kendala DDMS" TEXT, "Saran DDMS" TEXT,
            "Kendala SIMELON" TEXT, "Saran SIMELON" TEXT,
            "Kendala MAP" TEXT, "Saran MAP" TEXT,
            "Timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_report_to_db(report_dict):
    """Menambahkan satu baris laporan ke database."""
    conn = sqlite3.connect(DB_FILE)
    df_to_insert = pd.DataFrame([report_dict])
    # Menggunakan to_sql untuk cara yang aman dan mudah menambahkan data
    df_to_insert.to_sql('laporan', conn, if_exists='append', index=False)
    conn.close()

def get_all_reports():
    """Mengambil semua laporan dari database."""
    conn = sqlite3.connect(DB_FILE)
    # Menggunakan try-except untuk menangani kasus tabel kosong
    try:
        df = pd.read_sql_query("SELECT * FROM laporan", conn)
    except pd.io.sql.DatabaseError:
        df = pd.DataFrame() # Kembalikan DataFrame kosong jika tabel tidak ada/kosong
    conn.close()
    return df

# --- Fungsi Bantuan UI ---
def reset_session():
    st.session_state.stage = "search"
    st.session_state.current_report = {}
    st.rerun()

def finalize_and_save_report():
    """Menyimpan laporan ke DB dan mereset sesi."""
    if st.session_state.current_report:
        add_report_to_db(st.session_state.current_report)
    st.success("Laporan berhasil disimpan ke database pusat!")
    time.sleep(2)
    reset_session()

# --- Memuat Data dan Inisialisasi ---
@st.cache_data
def load_master_data(file_path):
    """Memuat data master agen dari file CSV."""
    try:
        time.sleep(1) # Simulasi loading
        return pd.read_csv(file_path)
    except FileNotFoundError:
        return None

# Tampilan loading awal
placeholder = st.empty()
with placeholder.container():
    st.markdown("""<style>.loading-container{display:flex;flex-direction:column;justify-content:center;align-items:center;height:80vh;}.loading-text{font-size:24px;font-weight:bold;color:#FF6A6A;text-align:center;}.loading-subtext{font-size:18px;color:#555555;text-align:center;}</style><div class="loading-container"><div class="loading-text">Mohon Menunggu</div><div class="loading-subtext">Menyiapkan aplikasi... ⏳</div></div>""", unsafe_allow_html=True)

# Inisialisasi database
init_db()
# Memuat data master
master_df = load_master_data("upload_nama_agen.xlsx - Master data agen (Maret 25).csv")

if master_df is None:
    placeholder.error("DATABASE MASTER AGEN TIDAK DITEMUKAN.")
    st.stop()

placeholder.empty()

# --- Tampilan Utama Aplikasi ---
st.title("📝 Formulir Pelaporan Kendala Agen")

# =============================================================================
# TAHAP 1: PENCARIAN AGEN
# =============================================================================
if st.session_state.stage == "search":
    st.header("1. Cari Data Agen")
    sold_to_party_id_str = st.text_input("Masukkan Sold-to-Party ID:", key="search_input")

    if sold_to_party_id_str:
        try:
            sold_to_party_id = int(sold_to_party_id_str)
            agent_data = master_df[master_df['soldtoparty'] == sold_to_party_id]

            if not agent_data.empty:
                agent_info = agent_data.iloc[0]
                st.session_state.current_report = {
                    "Sold-to-Party ID": int(agent_info['soldtoparty']),
                    "Nama Agen": agent_info['Nama Agen'],
                    "Sales Area": agent_info['Sales Area'],
                    "Wilayah Penyaluran": agent_info['Wilayah Penyaluran'],
                    "Kendala DDMS": "-", "Saran DDMS": "-",
                    "Kendala SIMELON": "-", "Saran SIMELON": "-",
                    "Kendala MAP": "-", "Saran MAP": "-",
                }
                st.session_state.stage = "report"
                st.rerun()
            else:
                st.warning("Sold-to-Party ID tidak ditemukan.")
        except ValueError:
            st.error("ID harus berupa angka.")
        except KeyError:
            st.error("Kolom 'soldtoparty' tidak ditemukan di file master.")

# =============================================================================
# TAHAP 2: PELAPORAN KENDALA
# =============================================================================
elif st.session_state.stage == "report":
    agent_name = st.session_state.current_report.get("Nama Agen", "N/A")
    sales_area = st.session_state.current_report.get("Sales Area", "N/A")
    wilayah_penyaluran = st.session_state.current_report.get("Wilayah Penyaluran", "N/A")

    st.info(f"""
    Anda sedang melaporkan untuk:
    - **Agen**: {agent_name}
    - **Sales Area**: {sales_area}
    - **Wilayah Penyaluran**: {wilayah_penyaluran}
    """)
    
    all_kendala = ["DDMS", "SIMELON", "MAP"]
    reported_kendala = [k.replace("Kendala ", "") for k, v in st.session_state.current_report.items() if k.startswith("Kendala") and v != "-"]
    available_kendala = [k for k in all_kendala if k not in reported_kendala]

    if not available_kendala:
        st.success("✔️ Semua jenis kendala telah dilaporkan untuk agen ini.")
        if st.button("Selesaikan dan Simpan Laporan"):
            finalize_and_save_report()
    else:
        st.header("2. Pilih dan Deskripsikan Kendala")
        selected_kendala = st.radio("Pilih satu jenis kendala:", available_kendala, key="kendala_radio")
        deskripsi = st.text_area(f"Deskripsikan kendala **{selected_kendala}**:", key="deskripsi_kendala")
        saran = st.text_area(f"Saran/Masukkan untuk kendala **{selected_kendala}**:", key="saran_kendala")

        if st.button("Simpan dan Lanjutkan", type="primary"):
            if not deskripsi:
                st.error("Deskripsi kendala tidak boleh kosong.")
            else:
                st.session_state.current_report[f"Kendala {selected_kendala}"] = deskripsi
                if saran:
                    st.session_state.current_report[f"Saran {selected_kendala}"] = saran
                else: # Pastikan kolom saran tidak kosong agar konsisten
                    st.session_state.current_report[f"Saran {selected_kendala}"] = "-"
                st.session_state.stage = "confirm"
                st.rerun()

    if st.button("Batalkan dan Mulai dari Awal"):
        reset_session()

# =============================================================================
# TAHAP 3: KONFIRMASI
# =============================================================================
elif st.session_state.stage == "confirm":
    agent_name = st.session_state.current_report.get("Nama Agen", "N/A")
    st.success(f"Laporan kendala untuk agen **{agent_name}** telah disimpan sementara.")
    
    all_kendala = ["DDMS", "SIMELON", "MAP"]
    reported_kendala = [k.replace("Kendala ", "") for k, v in st.session_state.current_report.items() if k.startswith("Kendala") and v != "-"]
    available_kendala = [k for k in all_kendala if k not in reported_kendala]

    st.write("---")
    if available_kendala:
        st.write("Apakah Anda ingin melaporkan kendala lain?")
        col1, col2 = st.columns(2)
        if col1.button("✅ Ya, Lanjutkan"):
            st.session_state.stage = "report"
            st.rerun()
        if col2.button("❌ Tidak, Selesaikan dan Simpan"):
            finalize_and_save_report()
    else:
        st.info("Semua jenis kendala telah dilaporkan.")
        if st.button("Selesaikan dan Simpan Laporan"):
            finalize_and_save_report()

# =============================================================================
# FITUR LAPORAN (TERPROTEKSI PASSWORD)
# =============================================================================
st.sidebar.markdown("---")
st.sidebar.header("Area Admin")

if st.session_state.auth:
    st.sidebar.success("Otentikasi Berhasil!")
    
    laporan_df = get_all_reports()

    if not laporan_df.empty:
        st.sidebar.write("Laporan Terkumpul:")
        # Menampilkan jumlah laporan
        st.sidebar.metric("Total Laporan Masuk", len(laporan_df))
        st.sidebar.dataframe(laporan_df)
        
        @st.cache_data
        def to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Laporan')
            return output.getvalue()

        excel_data = to_excel(laporan_df)

        st.sidebar.download_button(
            label="📥 Unduh Laporan (Excel)",
            data=excel_data,
            file_name='hasil_pelaporan_kendala.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    else:
        st.sidebar.write("Belum ada laporan yang disimpan di database.")
        
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.session_state.show_auth_form = False
        st.rerun()

elif st.session_state.show_auth_form:
    password = st.sidebar.text_input("Masukkan Kata Sandi:", type="password")
    if password:
        if password == "pertamina234*":
            st.session_state.auth = True
            st.session_state.show_auth_form = False
            st.rerun()
        else:
            st.sidebar.error("Kata sandi salah.")
else:
    if st.sidebar.button("Tampilkan Laporan"):
        st.session_state.show_auth_form = True
        st.rerun()

# --- Footer ---
footer_css = """<style>.footer{position:fixed;left:0;bottom:0;width:100%;background-color:transparent;color:#808080;text-align:center;padding:10px;font-size:14px;}</style>"""
st.markdown(footer_css, unsafe_allow_html=True)
st.markdown('<div class="footer">designed by aripili - 2025</div>', unsafe_allow_html=True)
