import streamlit as st
import pandas as pd
from pdf417gen import encode, render_image
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import datetime
import pytz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="LY Aja Barcode Generator", page_icon="🏷️", layout="wide")

# --- 2. SISTEM KEAMANAN (MULTI-USER LOGIN) ---
if "user_aktif" not in st.session_state:
    st.session_state.user_aktif = None

if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

# Layar Login (Updated: Perbaikan Posisi Teks dalam Input)
# --- LAYAR LOGIN (Minimalis & Validasi Per Field) ---
if st.session_state.user_aktif is None:
    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], .main {
            overflow: hidden !important;
            height: 100vh !important;
        }
        [data-testid="block-container"] {
            padding-top: 15vh !important; 
        }
        [data-testid="stHeader"] { display: none !important; }
        
        /* CSS untuk teks validasi merah yang halus */
        .error-text {
            color: #ff4b4b;
            font-size: 0.85rem;
            margin-top: -15px;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    col_kiri, col_tengah, col_kanan = st.columns([1, 1.2, 1])

    with col_tengah:
        st.markdown("<h2 style='text-align: center;'>Login Sistem Barcode Generator</h2>", unsafe_allow_html=True) 
        st.markdown("<p style='text-align: center;'>Akses terbatas untuk akun terdaftar.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Inisialisasi variabel error
        error_email = ""
        error_pass = ""

        email_input = st.text_input("Email:", help="Masukkan email terdaftar")
        # Placeholder untuk error email
        container_email = st.empty()

        pass_input = st.text_input("Password:", type="password")
        # Placeholder untuk error password
        container_pass = st.empty()
        
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Masuk", use_container_width=True):
            # Logika Validasi
            if not email_input:
                error_email = "Email wajib diisi."
            elif email_input not in st.secrets["akun_karyawan"]:
                error_email = "Email tidak terdaftar dalam sistem."
            
            if not pass_input:
                error_pass = "Password wajib diisi."
            elif email_input in st.secrets["akun_karyawan"] and st.secrets["akun_karyawan"][email_input] != pass_input:
                error_pass = "Password salah."

            # Tampilkan Error jika ada
            if error_email:
                container_email.markdown(f"<p class='error-text'>{error_email}</p>", unsafe_allow_html=True)
            if error_pass:
                container_pass.markdown(f"<p class='error-text'>{error_pass}</p>", unsafe_allow_html=True)

            # Jika tidak ada error, baru login
            if not error_email and not error_pass:
                st.session_state.user_aktif = email_input
                st.rerun()
                
    st.stop() # Hentikan eksekusi script sampai sini jika belum login

# ==========================================
# ZONA AMAN - HANYA BISA DIAKSES SETELAH LOGIN
# ==========================================

# Link Database CSV Google Sheets Anda
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0j1XxibRYHMNqJO02qBbn0rXJtt9BdO5PpynKDu-RKPh7RFlxYn4BGnOQCNknSa8z1kiUf7ieXGiW/pub?output=csv"

st.markdown("""
<style>
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button { max-width: 450px !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60) 
def load_database():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        # --- PERBAIKAN BUG SEL KOSONG ---
        df = df.fillna("-") 
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")
        return None

df_master = load_database()

def generate_label(teks_cetak, data_barcode):
    DPI = 600
    w_px = int((2.0 / 2.54) * DPI)  
    h_px = int((0.45 / 2.54) * DPI)  
    margin_x, margin_top, margin_bottom, spacing = 12, 10, 10, 4         

    codes = encode(data_barcode, columns=2, security_level=1) 
    img_bc = render_image(codes, scale=10, ratio=3, padding=0)
    canvas = Image.new('RGB', (w_px, h_px), 'white')
    draw = ImageDraw.Draw(canvas)
    
    try: font_baru = ImageFont.truetype("arialbd.ttf", 25)
    except: font_baru = ImageFont.load_default()

    text_h = 25 
    barcode_end_y = h_px - margin_bottom - text_h - spacing
    available_bc_h = barcode_end_y - margin_top
    new_bc_w = w_px - (margin_x * 2)

    bc_res = img_bc.resize((new_bc_w, int(available_bc_h)), Image.Resampling.NEAREST)
    canvas.paste(bc_res, (margin_x, margin_top))

    chars = list(teks_cetak)
    total_char_width = sum([draw.textlength(c, font=font_baru) for c in chars])
    ruang_kosong = new_bc_w - total_char_width
    spasi_antar_huruf = ruang_kosong / (len(chars) - 1) if len(chars) > 1 else 0

    pos_y_text = h_px - margin_bottom - text_h + 2
    current_x = margin_x
    for c in chars:
        draw.text((current_x, pos_y_text), c, fill='black', font=font_baru)
        current_x += draw.textlength(c, font=font_baru) + spasi_antar_huruf
    return canvas

# --- UI SIDEBAR UTAMA ---
if df_master is not None:
    with st.sidebar:
        st.success(f"👤 Login sebagai: **{st.session_state.user_aktif.split('@')[0]}**")
        st.header("⚙️ Konfigurasi Produksi")
        
        list_kategori = df_master['Kategori'].unique()
        kategori_sel = st.selectbox("Kategori Produk", list_kategori)
        df_filtered = df_master[df_master['Kategori'] == kategori_sel]

        list_varian = df_filtered['Varian'].unique()
        varian_sel = st.selectbox("Varian", list_varian)
        df_filtered = df_filtered[df_filtered['Varian'] == varian_sel]

        list_ukuran = df_filtered['Ukuran'].unique()
        ukuran_sel = st.selectbox("Ukuran", list_ukuran)
        row_terpilih = df_filtered[df_filtered['Ukuran'] == ukuran_sel].iloc[0]
        
        st.text_input("Jenis Kemasan (Auto)", value=row_terpilih['Kemasan'], disabled=True)
        st.divider()
        
        lokasi = st.selectbox("Lokasi Produksi", ["J", "B"], help="J=Jogja, B=Bogor")
        # Mengunci zona waktu ke WIB (Waktu Indonesia Barat)
        tz_wib = pytz.timezone('Asia/Jakarta')
        tanggal_prod = st.date_input("Tanggal Produksi", value=datetime.datetime.now(tz_wib).date())
        jumlah_cetak = st.number_input("Jumlah Barcode", min_value=1, max_value=500, value=10)

        yy, mm, dd = tanggal_prod.strftime("%y"), tanggal_prod.strftime("%m"), tanggal_prod.strftime("%d")
        tgl_silang = f"{yy[0]}{mm[0]}{dd[0]}{yy[1]}{mm[1]}{dd[1]}"

        kode_kat = row_terpilih['Kode_Kategori']
        kode_var = "" if str(row_terpilih['Kode_Varian']) == "-" else f"-{row_terpilih['Kode_Varian']}"
        uk_str = str(row_terpilih['Ukuran']).split(" ")[0]
        if "Kg" in str(row_terpilih['Ukuran']): uk_str = "1KG"

        sku_prefix = f"{kode_kat}-{uk_str}{kode_var}"
        
        st.divider()
        if st.button("🔴 Keluar (Log Out)", use_container_width=True):
            st.session_state.user_aktif = None
            st.rerun()

    # --- LAYAR UTAMA APLIKASI ---
    tab1, tab2 = st.tabs(["🏷️ Generator Barcode", "📊 Audit Trail (Riwayat)"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Pratinjau Barcode")
            teks_label = f"{kode_kat}{lokasi}{tgl_silang}01"
            data_scan = f"{sku_prefix}-{lokasi}{tgl_silang}01"
            
            preview_img = generate_label(teks_label, data_scan)
            st.image(preview_img, caption="Ukuran Fisik: 2 x 0.45 cm (DPI 600)", width=450)
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 GENERATE SEMUA BARCODE", use_container_width=True):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    for i in range(1, jumlah_cetak + 1):
                        batch = str(i).zfill(2)
                        t_label = f"{kode_kat}{lokasi}{tgl_silang}{batch}"
                        d_scan = f"{sku_prefix}-{lokasi}{tgl_silang}{batch}"
                        img = generate_label(t_label, d_scan)
                        buf = io.BytesIO()
                        img.save(buf, format="PNG", dpi=(600, 600))
                        zip_file.writestr(f"Label_{t_label}.png", buf.getvalue())
                
                # --- SISTEM PENCATATAN LOG (AUDIT TRAIL) ---
                waktu_sekarang = datetime.datetime.now(tz_wib).strftime("%Y-%m-%d %H:%M:%S")
                log_baru = {
                    "Waktu": waktu_sekarang,
                    "Operator": st.session_state.user_aktif,
                    "Produk SKU": sku_prefix,
                    "Lokasi": lokasi,
                    "Tgl Cetak (Asli)": tanggal_prod.strftime("%d-%m-%Y"),
                    "Jumlah": f"{jumlah_cetak} Pcs"
                }
                st.session_state.audit_log.insert(0, log_baru) 
                
                st.success(f"Berhasil memproses {jumlah_cetak} Barcode.")
                st.download_button(label="📥 DOWNLOAD ZIP", data=zip_buffer.getvalue(), 
                                   file_name=f"Produksi_{sku_prefix}_{tgl_silang}.zip", use_container_width=True)

        with col2:
            st.subheader("📋 Detail SKU")
            st.info(f"**Scan:** `{data_scan}`\n\n**Varian:** {varian_sel}\n\n**Ukuran:** {ukuran_sel}\n\n**Kemasan:** {row_terpilih['Kemasan']}")

    with tab2:
        st.subheader("📊 Riwayat Cetak Hari Ini")
        st.write("Catatan aktivitas ini hanya tersimpan selama server aktif untuk keperluan audit pabrik.")
        
        if len(st.session_state.audit_log) > 0:
            df_log = pd.DataFrame(st.session_state.audit_log)
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("Belum ada aktivitas pencetakan Barcode saat ini.")
else:
    st.warning("Menunggu koneksi database...")