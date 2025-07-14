import streamlit as st
import pandas as pd
import io
import time

# --- Konfigurasi Awal dan Inisialisasi State ---
st.set_page_config(page_title="Pelaporan Kendala Agen", layout="centered", initial_sidebar_state="auto")

# Inisialisasi session state untuk menyimpan semua data yang dibutuhkan selama sesi
if 'laporan_df' not in st.session_state:
    st.session_state.laporan_df = pd.DataFrame()
if 'stage' not in st.session_state:
    st.session_state.stage = "search"
if 'current_report' not in st.session_state:
    st.session_state.current_report = {}
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'show_auth_form' not in st.session_state:
    st.session_state.show_auth_form = False

# --- Fungsi Bantuan ---
def reset_session():
    st.session_state.stage = "search"
    st.session_state.current_report = {}
    st.rerun()

def finalize_report():
    if st.session_state.current_report:
        report_to_add = pd.DataFrame([st.session_state.current_report])
        st.session_state.laporan_df = pd.concat([st.session_state.laporan_df, report_to_add], ignore_index=True)
    st.success("Laporan lengkap telah disimpan. Anda bisa memulai laporan baru.")
    reset_session()

# --- Memuat Data dengan Cache dan Pesan Loading ---
@st.cache_data
def load_data(file_path):
    """Fungsi ini hanya akan dijalankan sekali untuk memuat data."""
    try:
        # simulasi waktu loading agar pesan terlihat
        time.sleep(2) 
        return pd.read_csv(file_path)
    except FileNotFoundError:
        return None

# PENAMBAHAN 1: Tampilan loading yang lebih baik
placeholder = st.empty()
with placeholder.container():
    st.markdown("""
    <style>
    .loading-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 80vh; /* Memenuhi tinggi layar */
    }
    .loading-text {
        font-size: 24px;
        font-weight: bold;
        color: #FF6A6A;
        text-align: center;
    }
    .loading-subtext {
        font-size: 18px;
        color: #555555;
        text-align: center;
    }
    </style>
    <div class="loading-container">
        <div class="loading-text">Mohon Menunggu</div>
        <div class="loading-subtext">Sedang menyiapkan data... ⏳</div>
    </div>
    """, unsafe_allow_html=True)

master_df = load_data("upload_nama_agen.xlsx - Master data agen (Maret 25).csv")

if master_df is None:
    placeholder.error("DATABASE TIDAK DITEMUKAN: Pastikan file 'upload_nama_agen.xlsx - Master data agen (Maret 25).csv' ada di folder yang sama.")
    st.stop()

# Hapus placeholder setelah data dimuat
placeholder.empty()


# --- Tampilan Utama Aplikasi ---
st.title("Survey Kendala DDMS-MAP-SIMELON")

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
                # PENAMBAHAN 2: Struktur diubah untuk menampung saran terpisah
                st.session_state.current_report = {
                    "Sold-to-Party ID": agent_info['soldtoparty'],
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
    Bantu kami untuk merekap kendala yang dialami oleh Agen Anda:
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
            finalize_report()
    else:
        st.header("2. Pilih dan Deskripsikan Kendala")
        selected_kendala = st.radio("Pilih satu jenis kendala:", available_kendala, key="kendala_radio")
        
        deskripsi = st.text_area(f"Deskripsikan kendala **{selected_kendala}**:", key="deskripsi_kendala")
        # PENAMBAHAN 2: Kotak saran spesifik untuk kendala yang dipilih
        saran = st.text_area(f"Saran/Masukkan untuk kendala **{selected_kendala}**:", key="saran_kendala")

        if st.button("Simpan dan Lanjutkan", type="primary"):
            if not deskripsi:
                st.error("Deskripsi kendala tidak boleh kosong.")
            else:
                # PENAMBAHAN 2: Menyimpan deskripsi dan saran ke kolom terpisah
                st.session_state.current_report[f"Kendala {selected_kendala}"] = deskripsi
                if saran:
                    st.session_state.current_report[f"Saran {selected_kendala}"] = saran
                
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
        if col2.button("❌ Tidak, Selesaikan"):
            finalize_report()
    else:
        st.info("Semua jenis kendala telah dilaporkan.")
        if st.button("Selesaikan Laporan"):
            finalize_report()

# =============================================================================
# FITUR LAPORAN (TERPROTEKSI PASSWORD)
# =============================================================================
st.sidebar.markdown("---")
st.sidebar.header("Area Admin Pertamina")

if st.session_state.auth:
    st.sidebar.success("Otentikasi Berhasil!")
    if not st.session_state.laporan_df.empty:
        st.sidebar.write("Laporan Terkumpul:")
        st.sidebar.dataframe(st.session_state.laporan_df)
        
        @st.cache_data
        def to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Laporan')
            return output.getvalue()

        excel_data = to_excel(st.session_state.laporan_df)

        st.sidebar.download_button(
            label="📥 Unduh Laporan (Excel)",
            data=excel_data,
            file_name='hasil_pelaporan_kendala.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    else:
        st.sidebar.write("Belum ada laporan yang disimpan.")
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
footer_css = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: transparent;
    color: #808080;
    text-align: center;
    padding: 10px;
    font-size: 14px;
}
</style>
"""
st.markdown(footer_css, unsafe_allow_html=True)
st.markdown('<div class="footer">designed by aripili - 2025</div>', unsafe_allow_html=True)