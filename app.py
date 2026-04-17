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

# --- 2. SISTEM KEAMANAN (LOGIN) ---
if "user_aktif" not in st.session_state:
    st.session_state.user_aktif = None

# --- TAMPILAN LOGIN ---
if st.session_state.user_aktif is None:
    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], .main { overflow: hidden !important; height: 100vh !important; }
        [data-testid="block-container"] { padding-top: 15vh !important; }
        [data-testid="stHeader"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    col_kiri, col_tengah, col_kanan = st.columns([1, 1.2, 1])
    with col_tengah:
        st.markdown("<h2 style='text-align: center;'>Login Sistem Barcode Generator</h2>", unsafe_allow_html=True) 
        email_input = st.text_input("Email:")
        pass_input = st.text_input("Password:", type="password")
        if st.button("Masuk", use_container_width=True):
            if email_input in st.secrets["akun_karyawan"] and st.secrets["akun_karyawan"][email_input] == pass_input:
                st.session_state.user_aktif = email_input
                st.rerun()
            else:
                st.error("Login Gagal.")
    st.stop() 

# ==========================================
# ZONA AMAN - SETELAH LOGIN
# ==========================================
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0j1XxibRYHMNqJO02qBbn0rXJtt9BdO5PpynKDu-RKPh7RFlxYn4BGnOQCNknSa8z1kiUf7ieXGiW/pub?output=csv"

st.markdown("""
<style>
div[data-testid="stButton"] > button { width: 100% !important; }
div[data-testid="stDownloadButton"] > button,
div[data-testid="stAlert"] { width: 450px !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# PERBAIKAN LOADING & ANTI ERROR (STRIPPER EXTRA)
@st.cache_data(ttl=600) 
def load_database():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        return df.fillna("-").apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")
        return None

df_master = load_database()

st.title("🏷️ Generator Barcode Produksi - LY Aja")
st.divider()

# --- FUNGSI GENERATE LABEL (2.5 cm x 0.7 cm) ---
def generate_label(teks_cetak, data_barcode):
    DPI = 600
    w_px = int((2.5 / 2.54) * DPI)  
    h_px = int((0.7 / 2.54) * DPI)  

    margin_x = 12       
    margin_top = 6      
    margin_bottom = 6   
    spacing = 4         

    codes = encode(data_barcode, columns=4, security_level=1) 
    img_bc = render_image(codes, scale=3, ratio=3, padding=0)
    
    canvas = Image.new('RGB', (w_px, h_px), 'white')
    draw = ImageDraw.Draw(canvas)
    
    ukuran_font_px = 24 
    try:
        font_baru = ImageFont.truetype("arialbd.ttf", ukuran_font_px)
    except:
        font_baru = ImageFont.load_default()

    bbox_full = draw.textbbox((0,0), teks_cetak, font=font_baru)
    text_h_baru = bbox_full[3] - bbox_full[1]

    barcode_end_y = h_px - margin_bottom - text_h_baru - spacing
    available_bc_h = barcode_end_y - margin_top

    new_bc_w = w_px - (margin_x * 2) 
    new_bc_h = int(available_bc_h)

    bc_res = img_bc.resize((new_bc_w, new_bc_h), Image.Resampling.LANCZOS)
    canvas.paste(bc_res, (margin_x, margin_top))

    ruang_sisa_y_start = barcode_end_y + spacing
    ruang_sisa_h = h_px - ruang_sisa_y_start
    target_center_y_text = ruang_sisa_y_start + (ruang_sisa_h / 2)
    pos_y_text = target_center_y_text - (text_h_baru / 2) - bbox_full[1]

    chars = list(teks_cetak)
    total_char_width = sum([draw.textlength(c, font=font_baru) for c in chars])
    ruang_kosong = new_bc_w - total_char_width
    spasi_antar_huruf = ruang_kosong / (len(chars) - 1) if len(chars) > 1 else 0

    current_x = margin_x
    for c in chars:
        draw.text((current_x, pos_y_text), c, fill='black', font=font_baru)
        current_x += draw.textlength(c, font=font_baru) + spasi_antar_huruf
    
    return canvas

zip_data_sementara = None
zip_nama_file = ""
pesan_sukses = ""

if df_master is not None and not df_master.empty:
    with st.sidebar:
        st.header("⚙️ Konfigurasi")
        
        # Filter bertingkat yang aman
        kategori_sel = st.selectbox("Kategori", df_master['Kategori'].unique())
        df_filtered_kat = df_master[df_master['Kategori'] == kategori_sel]
        
        varian_sel = st.selectbox("Varian", df_filtered_kat['Varian'].unique())
        df_filtered_var = df_filtered_kat[df_filtered_kat['Varian'] == varian_sel]
        
        ukuran_sel = st.selectbox("Ukuran", df_filtered_var['Ukuran'].unique())
        
        # Ambil baris pertama yang cocok
        row_terpilih = df_filtered_var[df_filtered_var['Ukuran'] == ukuran_sel].iloc[0]
        
        st.text_input("Kemasan", value=row_terpilih['Kemasan'], disabled=True)
        st.divider()
        lokasi = st.selectbox("Lokasi", ["J", "B"])
        tz_wib = pytz.timezone('Asia/Jakarta')
        tanggal_prod = st.date_input("Tgl Produksi", value=datetime.datetime.now(tz_wib).date())
        jumlah_cetak = st.number_input("Jumlah", min_value=1, max_value=500, value=10)

        yy, mm, dd = tanggal_prod.strftime("%y"), tanggal_prod.strftime("%m"), tanggal_prod.strftime("%d")
        tgl_silang = f"{yy[0]}{mm[0]}{dd[0]}{yy[1]}{mm[1]}{dd[1]}"
        
        # Variabel Aman untuk SKU (Logika 1KG Dihapus)
        kode_kat = str(row_terpilih['Kode_Kategori']).strip()
        uk_str = str(row_terpilih['Ukuran']).split(" ")[0].upper().strip()
        
        kode_var = "" if str(row_terpilih['Kode_Varian']).strip() == "-" else f"-{str(row_terpilih['Kode_Varian']).strip()}"
        sku_prefix = f"{kode_kat}-{uk_str}{kode_var}"

        if st.button("🚀 GENERATE SEMUA", use_container_width=True):
            teks_progress = "Mempersiapkan mesin cetak..."
            bar_proses = st.progress(0, text=teks_progress)
            
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
                    
                    persentase = int((i / jumlah_cetak) * 100)
                    bar_proses.progress(i / jumlah_cetak, text=f"Sedang menggambar Barcode {i} dari {jumlah_cetak} ({persentase}%)")
            
            bar_proses.empty()
            zip_data_sementara = zip_buffer.getvalue()
            
            # Membersihkan nama file khusus untuk Windows (Mencegah Karakter Ilegal)
            safe_sku = sku_prefix.replace("/", "_").replace("&", "_dan_").replace("\\", "_").replace(":", "")
            zip_nama_file = f"Barcode_LYAja_{safe_sku}_{tgl_silang}.zip"
            pesan_sukses = f"Berhasil memproses {jumlah_cetak} Barcode."

        st.divider()
        if st.button("🔴 Logout"):
            st.session_state.user_aktif = None
            st.rerun()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Pratinjau")
        teks_label = f"{kode_kat}{lokasi}{tgl_silang}01"
        data_scan = f"{sku_prefix}-{lokasi}{tgl_silang}01"
        
        preview_img = generate_label(teks_label, data_scan)
        st.image(preview_img, caption="PDF417 Ori (2.5 x 0.7 cm, Font 24)", width=450)
        
        if zip_data_sementara is not None:
            st.success(pesan_sukses)
            st.download_button("📥 DOWNLOAD ZIP", data=zip_data_sementara, file_name=zip_nama_file)

    with col2:
        st.subheader("📋 Detail SKU")
        st.info(f"**Scan Isi:** `{data_scan}`\n\n**Varian:** {varian_sel}")
else:
    st.warning("Menunggu database / Gagal Menarik Data...")