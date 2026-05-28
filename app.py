import streamlit as st
import requests
import datetime
import pandas as pd
import math
import json
import re
import time

# ==========================================
# CONFIGURATION & DATABASE LINK
# ==========================================
URL_GOOGLE_SHEET = "https://script.google.com/macros/s/AKfycbzSEatbLRT_wZBlz1etpJHNi-vRzqN-cnNnOtBw2JYAOPWNzKIIhB5T1pEiLx1kc_L4/exec"

st.set_page_config(page_title="CRM Hejja Pro", page_icon="🚀", layout="wide")

# ==========================================
# 🛡️ PINTASAN KESELAMATAN JSON (ANTI-CRASH)
# ==========================================
def tukar_ke_json_selamat(teks_mentah):
    try:
        teks_bersih = re.sub(r'\b(nan|NaN|inf|-inf)\b', 'null', teks_mentah)
        return json.loads(teks_bersih)
    except Exception as e:
        st.error(f"⚠️ Kegagalan kritikal semasa dekod data: {str(e)}")
        return []

def bersihkan_untuk_json(obj):
    if isinstance(obj, dict):
        return {str(k): bersihkan_untuk_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [bersihkan_untuk_json(x) for x in obj]
    elif pd.isna(obj):
        return ""
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    else:
        val_str = str(obj).strip()
        if val_str.lower() in ['nan', 'null', 'none', 'nat', 'undefined']:
            return ""
        return obj

def dapatkan_config_produk(sku):
    sku_clean = str(sku).strip().lower()
    if "hegula" in sku_clean:
        if "3" in sku_clean: return {"hari": 270, "panggilan": "Masa untuk repeat order 3 Pouches Hegula!"}
        return {"hari": 90, "panggilan": "Masa untuk repeat order 1 Pouch Hegula!"}
    elif "hegrano" in sku_clean:
        return {"hari": 30, "panggilan": "Stok Hegrano sebulan dah nak habis, jom follow-up!"}
    elif "coffee" in sku_clean or "kopi" in sku_clean:
        return {"hari": 14, "panggilan": "Kopi Hejja dah seminggu lebih, jom ajak repeat order!"}
    return {"hari": 60, "panggilan": "Produk Hejja Pro dah matang, masa untuk bertanya khabar!"}

def proses_data_crm():
    try:
        respon_data = requests.get(f"{URL_GOOGLE_SHEET}?action=ambil_sales")
        if respon_data.status_code != 200:
            return None, None, "Gagal berhubung dengan database server Google."
        
        senarai_customer = tukar_ke_json_selamat(respon_data.text)
        if not senarai_customer:
            return [], [], None
            
        hari_ini = datetime.date.today()
        senarai_lead_baru = []
        pemetaan_pembelian_terkini = {}
        
        for cust_raw in senarai_customer:
            if not cust_raw: continue
            cust_cleaned = {}
            for k, v in cust_raw.items():
                key_clean = str(k).lower().replace(" ", "").strip()
                val_clean = "" if v is None else str(v).strip()
                if val_clean.lower() in ["nan", "null", "undefined", "nat", "none"]:
                    val_clean = ""
                cust_cleaned[key_clean] = val_clean
            
            tarikh_val = cust_cleaned.get('tarikh') or cust_cleaned.get('tarikhbeli') or ''
            status_val = cust_cleaned.get('status', '').lower()
            sku_val = cust_cleaned.get('sku') or cust_cleaned.get('produk') or ''
            telefon_val = cust_cleaned.get('telefon', '').replace(".0", "").replace("+", "").replace("-", "").strip()
            nama_val = cust_cleaned.get('nama') or cust_cleaned.get('namapelangan') or ''
            if not nama_val or nama_val.lower() == 'nan': nama_val = 'Pelanggan'
            
            pic_val = cust_cleaned.get('pic') or '-'
            alamat_val = cust_cleaned.get('alamat') or 'Tiada Alamat'
            
            if not status_val or not telefon_val or telefon_val.lower() == 'nan' or telefon_val == "": 
                continue
            
            if "lead" in status_val:
                senarai_lead_baru.append({
                    'nama': nama_val, 'sku': sku_val, 'pic': pic_val, 
                    'tarikh': tarikh_val.split('T')[0], 'telefon': telefon_val, 'alamat': alamat_val,
                    'jenis_fu': 'Lead Baru (Belum Close)', '_raw': cust_raw
                })
            
            elif "selesai" in status_val or "paid" in status_val or "follow" in status_val:
                if not tarikh_val or tarikh_val.strip() == "": continue
                
                tarikh_bersih = tarikh_val.split('T')[0].strip()
                tarikh_beli = None
                for format_tarikh in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                    try: 
                        tarikh_beli = datetime.datetime.strptime(tarikh_bersih, format_tarikh).date()
                        break
                    except ValueError: continue
                
                if tarikh_beli is None: continue
                
                if telefon_val not in pemetaan_pembelian_terkini:
                    pemetaan_pembelian_terkini[telefon_val] = cust_cleaned
                    pemetaan_pembelian_terkini[telefon_val]['_tarikh_obj'] = tarikh_beli
                else:
                    if tarikh_beli > pemetaan_pembelian_terkini[telefon_val]['_tarikh_obj']:
                        pemetaan_pembelian_terkini[telefon_val] = cust_cleaned
                        pemetaan_pembelian_terkini[telefon_val]['_tarikh_obj'] = tarikh_beli

        senarai_repeat_order = []
        for tel, data_terkini in pemetaan_pembelian_terkini.items():
            sku_val = data_terkini.get('sku') or data_terkini.get('produk') or ''
            tarikh_beli = data_terkini['_tarikh_obj']
            pic_val = data_terkini.get('pic') or '-'
            nama_val = data_terkini.get('nama') or data_terkini.get('namapelangan') or 'Pelanggan'
            
            config_produk = dapatkan_config_produk(sku_val)
            tarikh_stok_habis = tarikh_beli + datetime.timedelta(days=config_produk["hari"])
            
            if hari_ini >= tarikh_stok_habis:
                senarai_repeat_order.append({
                    'nama': nama_val, 'sku': sku_val, 'pic': pic_val, 
                    'telefon': tel, 'alamat': data_terkini.get('alamat') or 'Tiada Alamat', 
                    'tarikh_stok_habis': tarikh_stok_habis, 'panggilan_produk': config_produk["panggilan"], 
                    'tarikh_beli_formatted': tarikh_beli.strftime('%d/%m/%Y'),
                    'jenis_fu': 'Matang (Masa Repeat Order)', '_raw': data_terkini
                })
        return senarai_lead_baru, senarai_repeat_order, None
    except Exception as e:
        return None, None, str(e)

# ==========================================
# USER AUTHENTICATION
# ==========================================
USER_CREDENTIALS = {
    "admin": {"password": "123", "role": "admin", "nama": "Hana (Admin)"},
    "ain": {"password": "111", "role": "staff", "nama": "Ain"},
    "fana": {"password": "222", "role": "staff", "nama": "Fana"},
    "qu": {"password": "333", "role": "staff", "nama": "Qu"}
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["nama_penuh"] = ""

if not st.session_state["logged_in"]:
    st.title("🔒 Log Masuk Sistem CRM Hejja Pro")
    username_input = st.text_input("Username:").strip().lower()
    password_input = st.text_input("Password:", type="password")
    
    if st.button("Masuk Sistem 🚀", use_container_width=True):
        if username_input in USER_CREDENTIALS and USER_CREDENTIALS[username_input]["password"] == password_input:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username_input
            st.session_state["role"] = USER_CREDENTIALS[username_input]["role"]
            st.session_state["nama_penuh"] = USER_CREDENTIALS[username_input]["nama"]
            st.rerun()
        else:
            st.error("❌ Username atau Password salah!")
    st.stop()

# ==========================================
# 🎯 SIDEBAR NAVIGATION (LISTING MENU)
# ==========================================
st.sidebar.title(f"Hi, {st.session_state['nama_penuh']}!")
st.sidebar.write(f"Akses: **{st.session_state['role'].upper()}**")
st.sidebar.markdown("---")

# Menggunakan st.sidebar.radio supaya menu tersenarai penuh (listing) di sebelah kiri
st.sidebar.markdown("### 📋 MENU UTAMA")
pilihan_menu = st.sidebar.radio(
    label="Pilih Halaman:",
    options=[
        "📝 Borang Jualan Manual",
        "🚨 Kaunter Follow-Up SKU",
        "🚀 Eksport Bulk Blaster",
        "📥 Peti Data Ralat",
        "📊 Muat Naik Pukal (Bulk Upload)"
    ],
    label_visibility="collapsed" # Sembunyikan label kecil untuk kekemasan
)

st.sidebar.markdown("---")
if st.sidebar.button("Log Keluar 🚪", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

# ==========================================
# HALAMAN 1: BORANG JUALAN MANUAL
# ==========================================
if pilihan_menu == "📝 Borang Jualan Manual":
    st.title("📝 Borang Kemas Kini Jualan Baru")
    
    with st.form("borang_sales", clear_on_submit=True):
        tarikh = st.date_input("Tarikh Jualan:", datetime.date.today())
        nama = st.text_input("Nama Pelanggan / Prospek:").strip()
        platform = st.selectbox("Platform Jualan:", ["WhatsApp New", "WhatsApp Rep", "Website New", "Website Rep", "Membership New", "Membership Rep"])
        pic = st.session_state["nama_penuh"]
        amaun = st.number_input("Amaun Jualan (RM):", min_value=0.0, format="%.2f")
        status = st.selectbox("Status Pelanggan:", ["Lead Baru", "Selesai (Paid)", "Follow-Up Tambahan"])
        telefon = st.text_input("No Telefon Pelanggan (Contoh: 60123456789):").strip()
        sku = st.text_input("SKU Produk / Variasi:").strip()
        alamat = st.text_area("Alamat Penghantaran:").strip()
        
        hantar = st.form_submit_with_button("Simpan Data Jualan 💾", use_container_width=True)
        
        if hantar:
            if not nama or not telefon:
                st.error("❌ Nama dan No Telefon pelanggan wajib diisi!")
            else:
                data_payload = {
                    "tarikh": str(tarikh), "nama": nama, "platform": platform, "pic": pic,
                    "amaun": float(amaun), "status": status, "telefon": telefon, "sku": sku, "alamat": alamat,
                    "is_error": False, "sebab_ralat": ""
                }
                try:
                    payload_final = bersihkan_untuk_json(data_payload)
                    respon = requests.post(URL_GOOGLE_SHEET, json=payload_final)
                    if respon.status_code == 200:
                        st.success(f"🎉 Data {nama} berjaya dihantar!")
                    else:
                        st.error("❌ Gagal hantar ke server database.")
                except Exception as e:
                    st.error(f"❌ Ralat sistem: {str(e)}")

# ==========================================
# HALAMAN 2: KAUNTER FOLLOW-UP SKU
# ==========================================
elif pilihan_menu == "🚨 Kaunter Follow-Up SKU":
    st.title("🚨 Kaunter Semakan Tugasan Follow-Up Harian")
    with st.spinner("Tengah menarik data terkini..."):
        leads, repeats, ralat = proses_data_crm()
        if ralat:
            st.error(f"❌ Ralat Sistem: {ralat}")
        else:
            tab1, tab2 = st.tabs(["🎯 1. Senarai Lead Baru", "🛒 2. Database Re-Order"])
            
            with tab1:
                if not leads: st.write("Tiada lead baru.")
                else:
                    for lead in leads:
                        if st.session_state["role"] != "admin" and lead['pic'].lower() != st.session_state["nama_penuh"].lower(): continue
                        st.markdown(f"### 👤 {lead['nama']} (PIC: {lead['pic']})")
                        st.write(f"📱 Telefon: {lead['telefon']} | 📦 SKU: {lead['sku']}")
                        st.markdown("---")
            with tab2:
                if not repeats: st.write("Tiada pelanggan matang hari ini.")
                else:
                    for rep in repeats:
                        if st.session_state["role"] != "admin" and rep['pic'].lower() != st.session_state["nama_penuh"].lower(): continue
                        st.markdown(f"### 🛒 {rep['nama']} (PIC: {rep['pic']})")
                        st.write(f"📱 Telefon: {rep['telefon']} | 📦 Jangkaan Habis: {rep['tarikh_stok_habis'].strftime('%d/%m/%Y')}")
                        st.markdown("---")

# ==========================================
# HALAMAN 3: EXSPORT BULK BLASTER (KATEGORI MUTLAK)
# ==========================================
elif pilihan_menu == "🚀 Eksport Bulk Blaster":
    st.title("🚀 Hub Eksport Data Khas WhatsApp Bulk Blaster")
    
    with st.spinner("Menyusun senarai mengikut kategori..."):
        leads, repeats, ralat = proses_data_crm()
        
        if ralat: 
            st.error(f"❌ Ralat: {ralat}")
        else:
            semua_aktif_fu = (leads or []) + (repeats or [])
            
            # 1. Definisi fungsi kategori (Pastikan ni sama dengan 'dapatkan_config_produk')
            def tentukan_kategori(sku_text):
                s = str(sku_text).lower()
                if "hegula" in s: return "Hegula"
                if "hegrano" in s: return "Hegrano"
                if "hecafe" in s or "coffee" in s or "kopi" in s: return "Hecafe"
                return "Lain-lain"

            # 2. Assign kategori kepada setiap data
            for f in semua_aktif_fu:
                f['kategori_produk'] = tentukan_kategori(f['sku'])
            
            # 3. Tab pilihan (Lebih senang nampak pecahan)
            tab_hegula, tab_hegrano, tab_hecafe, tab_lain = st.tabs(["Hegula", "Hegrano", "Hecafe", "Lain-lain"])
            
            # Fungsi untuk display tab
            def display_kategori(kategori_nama, tab_obj):
                with tab_obj:
                    data_filter = [f for f in semua_aktif_fu if f['kategori_produk'] == kategori_nama]
                    
                    # Filter PIC (kecuali admin)
                    if st.session_state["role"] != "admin":
                        data_filter = [f for f in data_filter if str(f['pic']).lower() == st.session_state["nama_penuh"].lower()]
                    
                    if not data_filter:
                        st.info(f"Tiada data untuk {kategori_nama}.")
                    else:
                        st.write(f"📊 Jumlah {kategori_nama}: **{len(data_filter)} pelanggan**")
                        df_b = pd.DataFrame(data_filter)
                        st.dataframe(df_b[['nama', 'telefon', 'sku', 'jenis_fu', 'pic']], use_container_width=True)
                        
                        csv = df_b.to_csv(index=False).encode('utf-8')
                        st.download_button(f"📥 Download {kategori_nama}.csv", csv, f"blaster_{kategori_nama}.csv", "text/csv")

            # Papar tab
            display_kategori("Hegula", tab_hegula)
            display_kategori("Hegrano", tab_hegrano)
            display_kategori("Hecafe", tab_hecafe)
            display_kategori("Lain-lain", tab_lain)
# ==========================================
# HALAMAN 4: PETI DATA RALAT
# ==========================================
elif pilihan_menu == "📥 Peti Data Ralat":
    st.title("📥 Peti Kuarantin Data Ralat")
    nama_pic_semasa = st.session_state["nama_penuh"]
    
    try:
        respon_ralat = requests.get(f"{URL_GOOGLE_SHEET}?action=ambil_ralat&pic={nama_pic_semasa}")
        if respon_ralat.status_code == 200:
            senarai_ralat = tukar_ke_json_selamat(respon_ralat.text)
            if not senarai_ralat:
                st.success("🎉 Tiada rekod data ralat untuk anda.")
            else:
                for item in senarai_ralat:
                    if not item: continue
                    def filter_str(v):
                        s = str(v).strip()
                        return "" if s.lower() in ["nan", "null", "undefined", "none"] else s

                    with st.expander(f"❌ Baris {item.get('row_index')} | Nama: {filter_str(item.get('Nama Pelangan') or item.get('Nama'))}"):
                        with st.form(f"form_b_{item.get('row_index')}"):
                            new_tarikh = st.text_input("Tarikh:", filter_str(item.get('Tarikh')))
                            new_nama = st.text_input("Nama Pelanggan:", filter_str(item.get('Nama Pelangan') or item.get('Nama')))
                            new_platform = st.selectbox("Platform:", ["WhatsApp New", "WhatsApp Rep", "Website New", "Website Rep"])
                            
                            try: float_am = float(item.get('Amaun', 0))
                            except: float_am = 0.0
                            if math.isnan(float_am) or math.isinf(float_am): float_am = 0.0
                            
                            new_amaun = st.number_input("Amaun (RM):", min_value=0.0, value=float_am)
                            new_status = st.text_input("Status:", filter_str(item.get('Status')))
                            new_telefon = st.text_input("No Telefon:", filter_str(item.get('Telefon')))
                            new_sku = st.text_input("SKU:", filter_str(item.get('SKU')))
                            new_alamat = st.text_area("Alamat:", filter_str(item.get('Alamat')))
                            
                            if st.form_submit_with_button("💾 Sahkan & Bersihkan Data"):
                                if not new_telefon.strip(): st.error("No Telefon wajib diisi!")
                                else:
                                    clean_payload = {
                                        "tarikh": str(new_tarikh), "nama": str(new_nama), "platform": str(new_platform), "pic": str(nama_pic_semasa),
                                        "amaun": float(new_amaun), "status": str(new_status), "telefon": str(new_telefon), "sku": str(new_sku), "alamat": str(new_alamat),
                                        "is_error": False, "sebab_ralat": ""
                                    }
                                    payload_final = bersihkan_untuk_json(clean_payload)
                                    if requests.post(URL_GOOGLE_SHEET, json=payload_final).status_code == 200:
                                        requests.get(f"{URL_GOOGLE_SHEET}?action=padam_ralat&index={item.get('row_index')}")
                                        st.success("Data Berjaya Diperbaiki!")
                                        st.rerun()
        else: st.error("Gagal berhubung ke server.")
    except Exception as e: st.error(f"Ralat Peti Kuarantin: {str(e)}")

# ==========================================
# HALAMAN 5: BULK UPLOAD (ANTI-TIMEOUT CHUNKING + PROGRESS TRACKER)
# ==========================================
elif pilihan_menu == "📊 Muat Naik Pukal (Bulk Upload)":
    st.title("📊 Sistem Muat Naik Data Jualan Pukal (CSV/Excel)")
    
    fail_diupload = st.file_uploader("Pilih Fail Excel atau CSV:", type=['csv', 'xlsx'])
    
    if fail_diupload is not None:
        try:
            if fail_diupload.name.endswith('.csv'): 
                df_raw = pd.read_csv(fail_diupload)
            else: 
                df_raw = pd.read_excel(fail_diupload)
            
            df = df_raw.copy()
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            for col in df.columns:
                df[col] = df[col].apply(lambda x: "" if pd.isna(x) or str(x).strip().lower() in ["nan", "null", "undefined", "none"] else str(x).strip())
            
            st.write(f"👀 **Pratonton Fail (Total: {len(df)} Baris Data Dikesan):**")
            st.dataframe(df, use_container_width=True)
            
            if st.button("🚀 Sah & Hantar Semua Data Sales ke Google Sheets", use_container_width=True):
                bulk_data = []
                for index, row in df.iterrows():
                    
                    def ambil_kolum(senarai_nama_lajur, default_value=""):
                        for nama in senarai_nama_lajur:
                            if nama in row and str(row[nama]).strip() != "":
                                val = str(row[nama]).strip()
                                if val.lower() in ['nan', 'null', 'undefined', 'none']:
                                    return default_value
                                return val
                        return default_value

                    tarikh_str = ambil_kolum(['tarikh', 'tarikhbeli', 'tarikh jualan'], str(datetime.date.today()))
                    nama_val = ambil_kolum(['nama pelangan', 'nama pelanggan', 'nama'], 'Pelanggan Pukal')
                    platform_val = ambil_kolum(['platform'], 'Lain-lain')
                    status_asal = ambil_kolum(['status', 'status pelanggan'], 'Lead Baru')
                    sku_val = ambil_kolum(['sku', 'sku produk', 'produk'], '')
                    alamat_row = ambil_kolum(['alamat', 'alamat penghantaran'], '')
                    pic_row = ambil_kolum(['pic'], st.session_state["nama_penuh"])
                    
                    is_error = False
                    sebab_ralat = ""
                    
                    raw_amaun = ambil_kolum(['amaun', 'amaun jualan', 'harga'], '')
                    if raw_amaun == "":
                        amaun_val = 0.0
                        is_error = True
                        sebab_ralat += "[Amaun Kosong] "
                    else:
                        try: 
                            raw_amaun_clean = str(raw_amaun).replace("RM", "").replace(",", "").strip()
                            amaun_val = float(raw_amaun_clean)
                            if math.isnan(amaun_val) or math.isinf(amaun_val):
                                amaun_val = 0.0
                                is_error = True
                                sebab_ralat += "[Amaun NaN] "
                        except:
                            amaun_val = 0.0
                            is_error = True
                            sebab_ralat += "[Format Amaun Salah] "
                            
                    telefon_val = ambil_kolum(['telefon', 'no telefon', 'nombor telefon', 'phone'], '')
                    telefon_val = telefon_val.replace(".0", "").replace("+", "").replace("-", "").strip()
                    
                    if telefon_val == "" or telefon_val.lower() in ['nan', 'null']:
                        telefon_val = ""
                        is_error = True
                        sebab_ralat += "[No Telefon Kosong] "
                    
                    bulk_data.append({
                        "tarikh": str(tarikh_str), "nama": str(nama_val), "platform": str(platform_val), 
                        "pic": str(pic_row), "amaun": float(amaun_val), "status": str(status_asal), "telefon": str(telefon_val), 
                        "sku": str(sku_val), "alamat": str(alamat_row), "is_error": bool(is_error), "sebab_ralat": str(sebab_ralat)
                    })
                
                CHUNK_SIZE = 200
                total_data = len(bulk_data)
                
                progress_bar = st.progress(0.0)
                status_teks = st.empty()
                
                sukses_hantar = True
                masa_mula = time.time()
                
                for i in range(0, total_data, CHUNK_SIZE):
                    chunk = bulk_data[i:i + CHUNK_SIZE]
                    chunk_bersih = bersihkan_untuk_json(chunk)
                    
                    peratus_siap = min((i + CHUNK_SIZE) / total_data, 1.0)
                    peratus_paparan = int(peratus_siap * 100)
                    
                    masa_berlalu = time.time() - masa_mula
                    kadar_kelajuan = (i + len(chunk)) / masa_berlalu
                    baki_data = total_data - (i + len(chunk))
                    
                    if kadar_kelajuan > 0:
                        baki_masa_saat = baki_data / kadar_kelajuan
                        baki_minit = int(baki_masa_saat // 60)
                        baki_saat = int(baki_masa_saat % 60)
                        eta_teks = f"{baki_minit} min {baki_saat} saat" if baki_minit > 0 else f"{baki_saat} saat"
                    else:
                        eta_teks = "Mengira..."

                    status_teks.markdown(f"""
                    🔄 **Status Muat Naik: {peratus_paparan}% Selesai** 📦 Sedang memproses baris `{i+1}` hingga `{min(i+CHUNK_SIZE, total_data)}` daripada `{total_data}` baris.  
                    ⏱️ Anggaran masa berbaki: **{eta_teks}**
                    """)
                    
                    progress_bar.progress(peratus_siap)
                    
                    try:
                        hantar_respon = requests.post(URL_GOOGLE_SHEET, json=chunk_bersih)
                        if hantar_respon.status_code != 200:
                            sukses_hantar = False
                            st.error(f"❌ Gagal pada kumpulan baris {i+1} - {min(i+CHUNK_SIZE, total_data)}")
                            break
                    except Exception as e:
                        sukses_hantar = False
                        st.error(f"❌ Ralat rangkaian pada baris {i+1}: {str(e)}")
                        break
                
                if sukses_hantar:
                    masa_total = time.time() - masa_mula
                    total_minit = int(masa_total // 60)
                    total_saat = int(masa_total % 60)
                    
                    status_teks.empty()
                    progress_bar.empty()
                    
                    st.success(f"🎉 **Selesai 100%!** Kesemua {total_data} data berjaya dimasukkan dalam masa {total_minit} minit {total_saat} saat!")
                    st.balloons()

        except Exception as e:
            st.error(f"❌ Ralat Muat Naik: {str(e)}")