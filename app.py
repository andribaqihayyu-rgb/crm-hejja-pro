import streamlit as st
import datetime
import requests
import urllib.parse
import pandas as pd
import re

st.set_page_config(page_title="CRM Hejja Pro", page_icon="🚀", layout="wide")

# 🔴 URL Web App Apps Script
URL_GOOGLE_SHEET = "https://script.google.com/macros/s/AKfycbx59Pa9kqwmlwHDyJSIebIrwAKUvnyCy-ABDUfhFNvptavicpD000QP6bOLcDyqi-Lh/exec"

SENARAI_SKU_DROPDOWN = [
    "Hegula+ Travel Pack",
    "Hegula+ 1 Pouch",
    "Hegula+ 2 Pouch",
    "Hegula+ 4 Pouch",
    "Hecafe+ 1 Pouch",
    "Hecafe+ 3 Pouch",
    "Hegrano 1 Pouch",
    "Hegrano 3 Pouch"
]

# 👥 DATABASE LOGIN STAFF SALES
USER_CREDENTIALS = {
    "hana": {"password": "hanahejja", "nama_penuh": "Hana (Admin)", "role": "admin"},
    "ain": {"password": "ainhejja", "nama_penuh": "Ain", "role": "staff"},
    "fana": {"password": "fanahejja", "nama_penuh": "Fana", "role": "staff"},
    "qu": {"password": "quhejja", "nama_penuh": "Qu", "role": "staff"}
}

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "username" not in st.session_state: st.session_state["username"] = ""
if "role" not in st.session_state: st.session_state["role"] = ""
if "nama_penuh" not in st.session_state: st.session_state["nama_penuh"] = ""

# ==========================================
# 🧠 FUNGSI KITARAN REPEAT SALES PELANGGAN
# ==========================================
def dapatkan_config_produk(sku_nama):
    sku_clean = str(sku_nama).strip()
    sku_lower = sku_clean.lower()
    config_default = {"hari": 30, "panggilan": sku_clean}
    if not sku_clean: return config_default
    senarai_angka = re.findall(r'\d+', sku_clean)
    kuantiti = int(senarai_angka[0]) if senarai_angka else 1
    if "travel" in sku_lower: return {"hari": 30, "panggilan": sku_clean}
    elif "hegula" in sku_lower:
        base_hari = 30 if "botol" in sku_lower else 90
        return {"hari": base_hari * kuantiti, "panggilan": sku_clean}
    elif "hecafe" in sku_lower or "hcafe" in sku_lower:
        return {"hari": 15 * kuantiti, "panggilan": sku_clean}
    elif "hegrano" in sku_lower:
        return {"hari": 15 * kuantiti, "panggilan": sku_clean}
    return config_default

# ==========================================
# 📊 FUNGSI MATRIKS PRESTASI SALES (KHAS ADMIN)
# ==========================================
def bina_matriks_produk(senarai_data):
    if not senarai_data:
        return pd.DataFrame(columns=["HEGULA", "HEGRANO", "HECAFE PLUS", "Jumlah"])
    df = pd.DataFrame(senarai_data)
    def kategorikan_jenama(sku_string):
        text = str(sku_string).lower()
        if "hegula" in text: return "HEGULA"
        elif "hegrano" in text: return "HEGRANO"
        elif "hecafe" in text or "hcafe" in text: return "HECAFE PLUS"
        return "LAIN-LAIN"
    df['Kategori Produk'] = df['sku'].apply(kategorikan_jenama)
    matriks = pd.crosstab(df['pic'], df['Kategori Produk'])
    for produk_wajib in ["HEGULA", "HEGRANO", "HECAFE PLUS"]:
        if produk_wajib not in matriks.columns:
            matriks[produk_wajib] = 0
    matriks['Jumlah'] = matriks.get('HEGULA', 0) + matriks.get('HEGRANO', 0) + matriks.get('HECAFE PLUS', 0) + matriks.get('LAIN-LAIN', 0)
    lajur_susunan = ["HEGULA", "HEGRANO", "HECAFE PLUS"]
    if "LAIN-LAIN" in matriks.columns and matriks["LAIN-LAIN"].sum() > 0:
        lajur_susunan.append("LAIN-LAIN")
    lajur_susunan.append("Jumlah")
    return matriks[lajur_susunan]

# ==========================================
# 🔒 PAPARAN LOGIN
# ==========================================
if not st.session_state["logged_in"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_login_1, col_login_2, col_login_3 = st.columns([1, 2, 1])
    with col_login_2:
        with st.container(border=True):
            st.title("🚀 CRM Hejja HQ")
            st.subheader("Sila Log Masuk Sesi Kerja")
            input_user = st.text_input("ID Pengguna (Username):").strip().lower()
            input_pass = st.text_input("Kata Laluan (Password):", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔑 Log Masuk", use_container_width=True):
                if input_user in USER_CREDENTIALS and USER_CREDENTIALS[input_user]["password"] == input_pass:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = input_user
                    st.session_state["role"] = USER_CREDENTIALS[input_user]["role"]
                    st.session_state["nama_penuh"] = USER_CREDENTIALS[input_user]["nama_penuh"]
                    st.success("Log masuk berjaya!")
                    st.rerun()
                else: st.error("ID Pengguna atau Kata Laluan salah.")
    st.stop()

# ==========================================
# 👈 MENU NAVIGASI (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("🧭 CRM Hejja HQ")
    st.write(f"👤 Pengguna: **{st.session_state['nama_penuh']}**")
    st.write(f"🔑 Akses: `{st.session_state['role'].upper()}`")
    st.markdown("---")
    senarai_menu = ["➕ Daftar Jualan Baru", "🚨 Kaunter Follow-Up SKU", "📁 Bulk Upload Excel"]
    pilihan_menu = st.radio("MENU UTAMA", senarai_menu)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("🚪 Log Keluar Sistem", use_container_width=True):
        st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# HALAMAN 1: BORANG DAFTAR JUALAN BARU
# ==========================================
if pilihan_menu == "➕ Daftar Jualan Baru":
    st.title("📊 Rekod Jualan Baru")
    col1, col2 = st.columns(2)
    with col1:
        tarikh = st.date_input("Tarikh Beli/Masuk Lead:", datetime.date.today())
        nama = st.text_input("Nama Pelanggan:", placeholder="Contoh: Ahmad")
        no_telefon = st.text_input("Nombor Telefon (Mula 60):", placeholder="Contoh: 60123456789")
        sku_pilihan = st.selectbox("Pilih SKU / Produk:", SENARAI_SKU_DROPDOWN)
    with col2:
        platform = st.selectbox("Platform:", ["WhatsApp", "TikTok Live", "TikTok Shop", "Website", "Lain-lain"])
        if st.session_state["role"] == "admin":
            pic = st.text_input("PIC Staff:", value=st.session_state["nama_penuh"])
        else:
            pic = st.text_input("PIC Staff:", value=st.session_state["nama_penuh"], disabled=True)
        amaun = st.number_input("Amaun Jualan (RM):", min_value=0.0, step=1.0)
        status = st.selectbox("Status:", ["Selesai (Paid)", "Lead Baru", "Follow-up"])
    alamat = st.text_area("Alamat Pelanggan:", placeholder="Masukkan alamat penuh penghantaran di sini...")

    if st.button("💾 Simpan Rekod", use_container_width=True):
        if nama and pic and no_telefon:
            data_pelanggan = {
                "tarikh": str(tarikh), "nama": nama, "platform": platform, 
                "pic": pic, "amaun": amaun, "status": status, "telefon": no_telefon, 
                "sku": sku_pilihan, "alamat": alamat
            }
            with st.spinner("Tengah simpan..."):
                try:
                    respon = requests.post(URL_GOOGLE_SHEET, json=data_pelanggan)
                    if respon.status_code == 200: st.success(f"Rekod {nama} disimpan!"); st.balloons()
                    else: st.error("Gagal simpan data.")
                except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Sila pastikan Nama, No Telefon dan PIC diisi!")

# ==========================================
# HALAMAN 2: PUSAT FOLLOW-UP SALES TEAM
# ==========================================
elif pilihan_menu == "🚨 Kaunter Follow-Up SKU":
    st.title("🚨 Pusat Kawalan Tindakan Follow-Up")
    with st.spinner("Tengah menarik data dari Google Sheets..."):
        try:
            respon_data = requests.get(URL_GOOGLE_SHEET)
            if respon_data.status_code == 200:
                senarai_customer = respon_data.json()
                hari_ini = datetime.date.today()
                
                senarai_lead_baru = []
                senarai_repeat_order = []
                
                for cust_raw in senarai_customer:
                    cust = {str(k).lower().replace(" ", "").strip(): v for k, v in cust_raw.items()}
                    tarikh_val = cust.get('tarikh') or cust.get('tarikhbeli') or ''
                    status_val = str(cust.get('status') or '').strip().lower()
                    sku_val = cust.get('sku') or cust.get('produk') or ''
                    telefon_val = str(cust.get('telefon') or '').replace(".0", "")
                    nama_val = cust.get('nama') or 'Pelanggan'
                    pic_val = cust.get('pic') or '-'
                    alamat_val = cust.get('alamat') or 'Tiada Alamat'
                    
                    if not status_val: continue
                    
                    if "lead" in status_val:
                        senarai_lead_baru.append({'nama': nama_val, 'sku': sku_val, 'pic': pic_val, 'tarikh': str(tarikh_val).split('T')[0], 'telefon': telefon_val, 'alamat': alamat_val})
                    elif "selesai" in status_val or "paid" in status_val or "follow" in status_val:
                        if not tarikh_val or str(tarikh_val).strip() == "": continue
                        config_produk = dapatkan_config_produk(sku_val)
                        tarikh_bersih = str(tarikh_val).split('T')[0].strip()
                        tarikh_beli = None
                        for format_tarikh in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                            try: tarikh_beli = datetime.datetime.strptime(tarikh_bersih, format_tarikh).date(); break
                            except ValueError: continue
                        if tarikh_beli is None: continue
                        tarikh_stok_habis = tarikh_beli + datetime.timedelta(days=config_produk["hari"])
                        if hari_ini >= tarikh_stok_habis:
                            senarai_repeat_order.append({'nama': nama_val, 'sku': sku_val, 'pic': pic_val, 'telefon': telefon_val, 'alamat': alamat_val, 'tarikh_stok_habis': tarikh_stok_habis, 'panggilan_produk': config_produk["panggilan"], 'tarikh_beli_formatted': tarikh_beli.strftime('%d/%m/%Y')})

                # ==========================================
                # 📊 SEKSYEN RINGKASAN DATA UNTUK ADMIN (HANA)
                # ==========================================
                if st.session_state["role"] == "admin":
                    st.markdown("### 📊 Papan Prestasi Tugasan Pasukan Jualan")
                    col_matriks_1, col_matriks_2 = st.columns(2)
                    with col_matriks_1:
                        with st.container(border=True):
                            st.markdown("🎯 **Matriks 1: Jumlah Lead Baru Tunggu Di-Close (Ikut Staff & Produk)**")
                            jadual_lead = bina_matriks_produk(senarai_lead_baru)
                            st.dataframe(jadual_lead, use_container_width=True)
                    with col_matriks_2:
                        with st.container(border=True):
                            st.markdown("🛒 **Matriks 2: Jumlah Pelanggan Matang Perlu Re-Order (Ikut Staff & Produk)**")
                            jadual_repeat = bina_matriks_produk(senarai_repeat_order)
                            st.dataframe(jadual_repeat, use_container_width=True)
                    st.markdown("---")

                # ==========================================
                # 🔒 TAPISAN AKSES DATA STAFF
                # ==========================================
                senarai_lead_dipapar = [l for l in senarai_lead_baru if st.session_state["role"] == "admin" or st.session_state["username"].lower() in str(l['pic']).lower()]
                senarai_repeat_dipapar = [r for r in senarai_repeat_order if st.session_state["role"] == "admin" or st.session_state["username"].lower() in str(r['pic']).lower()]

                if st.session_state["role"] != "admin":
                    st.info(f"📋 Menampilkan senarai tugasan follow-up di bawah jagaan **{st.session_state['nama_penuh']}** sahaja.")

                # ----------------------------------------------------
                # 🎯 BAHAGIAN 1: SENARAI LEAD BARU TUGASAN TEAM
                # ----------------------------------------------------
                st.subheader("🎯 1. Senarai Lead Baru (Perlu Di-Close Segera)")
                if len(senarai_lead_dipapar) > 0:
                    data_lead_terkumpul = {}
                    for lead in senarai_lead_dipapar:
                        nama_pic = lead['pic']
                        sku_text = str(lead['sku']).lower()
                        if "hegula" in sku_text: kat_prod = "HEGULA"
                        elif "hegrano" in sku_text: kat_prod = "HEGRANO"
                        elif "hecafe" in sku_text or "hcafe" in sku_text: kat_prod = "HECAFE PLUS"
                        else: kat_prod = "LAIN-LAIN"
                        if nama_pic not in data_lead_terkumpul:
                            data_lead_terkumpul[nama_pic] = {"HEGULA": [], "HEGRANO": [], "HECAFE PLUS": [], "LAIN-LAIN": []}
                        data_lead_terkumpul[nama_pic][kat_prod].append(lead)
                    
                    for nama_pic, pecahan_produk in data_lead_terkumpul.items():
                        total_lead_pic = sum(len(v) for v in pecahan_produk.values())
                        with st.expander(f"👤 PIC: **{nama_pic}** — ({total_lead_pic} Lead Menunggu Tindakan Close)", expanded=True):
                            tab_l_hegula, tab_l_hegrano, tab_l_hecafe, tab_l_lain = st.tabs(["🔴 HEGULA", "🟢 HEGRANO", "🟤 HECAFE PLUS", "📦 LAIN-LAIN"])
                            
                            with tab_l_hegula:
                                if pecahan_produk["HEGULA"]:
                                    for lead in pecahan_produk["HEGULA"]:
                                        with st.container(border=True):
                                            col_l1, col_l2 = st.columns([3, 1])
                                            with col_l1:
                                                st.write(f"👤 **Nama Pelanggan:** {lead['nama']} | 📦 **Minat SKU:** `{lead['sku']}`")
                                                st.write(f"📅 Masuk: `{lead['tarikh']}` | 🏠 Alamat: *{lead['alamat']}*")
                                            with col_l2:
                                                ayat_lead = f"Salam {lead['nama']}, saya dari Hejja HQ. Hari tu ada berminat nak tahu pasal produk {lead['sku']} kan? Ada apa-apa soalan atau bantuan yang boleh saya bantu untuk mudahkan urusan anda? 😊"
                                                st.link_button("📲 Close Lead", f"https://wa.me/{lead['telefon']}?text={urllib.parse.quote(ayat_lead)}", type="secondary", use_container_width=True)
                                else: st.caption("🎉 Bersih! Tiada lead baharu untuk HEGULA.")
                                    
                            with tab_l_hegrano:
                                if pecahan_produk["HEGRANO"]:
                                    for lead in pecahan_produk["HEGRANO"]:
                                        with st.container(border=True):
                                            col_l1, col_l2 = st.columns([3, 1])
                                            with col_l1: st.write(f"👤 **Nama Pelanggan:** {lead['nama']} | 📦 **Minat SKU:** `{lead['sku']}`")
                                            with col_l2:
                                                ayat_lead = f"Salam {lead['nama']}, saya dari Hejja HQ. Hari tu ada berminat nak tahu pasal produk {lead['sku']} kan? Ada apa-apa soalan atau bantuan yang boleh saya bantu untuk mudahkan urusan anda? 😊"
                                                st.link_button("📲 Close Lead", f"https://wa.me/{lead['telefon']}?text={urllib.parse.quote(ayat_lead)}", type="secondary", use_container_width=True)
                                else: st.caption("🎉 Bersih! Tiada lead baharu untuk HEGRANO.")
                                    
                            with tab_l_hecafe:
                                if pecahan_produk["HECAFE PLUS"]:
                                    for lead in pecahan_produk["HECAFE PLUS"]:
                                        with st.container(border=True):
                                            col_l1, col_l2 = st.columns([3, 1])
                                            with col_l1: st.write(f"👤 **Nama Pelanggan:** {lead['nama']} | 📦 **Minat SKU:** `{lead['sku']}`")
                                            with col_l2:
                                                ayat_lead = f"Salam {lead['nama']}, saya dari Hejja HQ. Hari tu ada berminat nak tahu pasal produk {lead['sku']} kan? Ada apa-apa soalan atau bantuan yang boleh saya bantu untuk mudahkan urusan anda? 😊"
                                                st.link_button("📲 Close Lead", f"https://wa.me/{lead['telefon']}?text={urllib.parse.quote(ayat_lead)}", type="secondary", use_container_width=True)
                                else: st.caption("🎉 Bersih! Tiada lead baharu untuk HECAFE PLUS.")
                                    
                            with tab_l_lain:
                                if pecahan_produk["LAIN-LAIN"]:
                                    for lead in pecahan_produk["LAIN-LAIN"]:
                                        with st.container(border=True):
                                            col_l1, col_l2 = st.columns([3, 1])
                                            with col_l1: st.write(f"👤 **Nama Pelanggan:** {lead['nama']} | 📦 **Minat SKU:** `{lead['sku']}`")
                                            with col_l2:
                                                ayat_lead = f"Salam {lead['nama']}, saya dari Hejja HQ. Hari tu ada berminat nak tahu pasal produk kan? Ada apa-apa bantuan yang boleh saya bantu? 😊"
                                                st.link_button("📲 Close Lead", f"https://wa.me/{lead['telefon']}?text={urllib.parse.quote(ayat_lead)}", type="secondary", use_container_width=True)
                                else: st.caption("Tiada senarai untuk lain-lain SKU.")
                else: st.info("Tiada jualan berstatus 'Lead Baru' buat masa ini.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # ----------------------------------------------------
                # 🛒 BAHAGIAN 2: FOLLOW-UP DATABASE REPEAT ORDER
                # ----------------------------------------------------
                st.subheader("🛒 2. Database Re-Order (Follow-Up Pelanggan Sedia Ada)")
                if len(senarai_repeat_dipapar) > 0:
                    data_terkumpul = {}
                    for cust in senarai_repeat_dipapar:
                        nama_pic = cust['pic']
                        sku_text = str(cust['sku']).lower()
                        if "hegula" in sku_text: kat_prod = "HEGULA"
                        elif "hegrano" in sku_text: kat_prod = "HEGRANO"
                        elif "hecafe" in sku_text or "hcafe" in sku_text: kat_prod = "HECAFE PLUS"
                        else: kat_prod = "LAIN-LAIN"
                        if nama_pic not in data_terkumpul:
                            data_terkumpul[nama_pic] = {"HEGULA": [], "HEGRANO": [], "HECAFE PLUS": [], "LAIN-LAIN": []}
                        data_terkumpul[nama_pic][kat_prod].append(cust)
                    
                    for nama_pic, pecahan_produk in data_terkumpul.items():
                        total_followup_pic = sum(len(v) for v in pecahan_produk.values())
                        with st.expander(f"👤 PIC: **{nama_pic}** — ({total_followup_pic} Klien Matang Perlu Hubungi Semula)", expanded=True):
                            tab_hegula, tab_hegrano, tab_hecafe, tab_lain = st.tabs(["🔴 HEGULA", "🟢 HEGRANO", "🟤 HECAFE PLUS", "📦 LAIN-LAIN"])
                            
                            with tab_hegula:
                                if pecahan_produk["HEGULA"]:
                                    for cust in pecahan_produk["HEGULA"]:
                                        with st.container(border=True):
                                            col_r1, col_r2 = st.columns([3, 1])
                                            with col_r1:
                                                st.write(f"👤 **Pelanggan:** {cust['nama']} | 📦 **SKU Terakhir:** `{cust['sku']}`")
                                                st.write(f"📅 Anggaran Bekalan Habis: `{cust['tarikh_stok_habis'].strftime('%d/%m/%Y')}` (Belian terakhir {cust['tarikh_beli_formatted']})")
                                            with col_r2:
                                                ayat_repeat = f"Salam {cust['nama']}, saya dari Hejja HQ. Saja nak tanya, {cust['panggilan_produk']} yang dibeli hari tu dah nak habis ke? Nak saya bantu uruskan order baharu untuk bulan ni? 😊"
                                                st.link_button("📲 Hubungi Re-Order", f"https://wa.me/{cust['telefon']}?text={urllib.parse.quote(ayat_repeat)}", type="primary", use_container_width=True)
                                else: st.caption("🎉 Bagus! Tiada pelanggan HEGULA perlu di-follow up hari ini.")
                                    
                            with tab_hegrano:
                                if pecahan_produk["HEGRANO"]:
                                    for cust in pecahan_produk["HEGRANO"]:
                                        with st.container(border=True):
                                            col_r1, col_r2 = st.columns([3, 1])
                                            with col_r1: st.write(f"👤 **Pelanggan:** {cust['nama']} | 📦 **SKU Terakhir:** `{cust['sku']}`")
                                            with col_r2:
                                                ayat_repeat = f"Salam {cust['nama']}, saya dari Hejja HQ. Saja nak tanya, {cust['panggilan_produk']} yang dibeli hari tu dah nak habis ke? Nak saya bantu uruskan order baharu untuk bulan ni? 😊"
                                                st.link_button("📲 Hubungi Re-Order", f"https://wa.me/{cust['telefon']}?text={urllib.parse.quote(ayat_repeat)}", type="primary", use_container_width=True)
                                else: st.caption("🎉 Bagus! Tiada pelanggan HEGRANO perlu di-follow up hari ini.")
                                    
                            with tab_hecafe:
                                if pecahan_produk["HECAFE PLUS"]:
                                    for cust in pecahan_produk["HECAFE PLUS"]:
                                        with st.container(border=True):
                                            col_r1, col_r2 = st.columns([3, 1])
                                            with col_r1: st.write(f"👤 **Pelanggan:** {cust['nama']} | 📦 **SKU Terakhir:** `{cust['sku']}`")
                                            with col_r2:
                                                ayat_repeat = f"Salam {cust['nama']}, saya dari Hejja HQ. Saja nak tanya, {cust['panggilan_produk']} yang dibeli hari tu dah nak habis ke? Nak saya bantu uruskan order baharu untuk bulan ni? 😊"
                                                st.link_button("📲 Hubungi Re-Order", f"https://wa.me/{cust['telefon']}?text={urllib.parse.quote(ayat_repeat)}", type="primary", use_container_width=True)
                                else: st.caption("🎉 Bagus! Tiada pelanggan HECAFE PLUS perlu di-follow up hari ini.")
                                    
                            with tab_lain:
                                if pecahan_produk["LAIN-LAIN"]:
                                    for cust in pecahan_produk["LAIN-LAIN"]:
                                        with st.container(border=True):
                                            col_r1, col_r2 = st.columns([3, 1])
                                            with col_r1: st.write(f"👤 **Pelanggan:** {cust['nama']} | 📦 **SKU Terakhir:** `{cust['sku']}`")
                                            with col_r2:
                                                ayat_repeat = f"Salam {cust['nama']}, saya dari Hejja HQ. Saja nak tanya pasal produk yang dibeli hari tu dah nak habis ke? 😊"
                                                st.link_button("📲 Hubungi Re-Order", f"https://wa.me/{cust['telefon']}?text={urllib.parse.quote(ayat_repeat)}", type="primary", use_container_width=True)
                                else: st.caption("Tiada senarai untuk lain-lain SKU.")
                else: st.success("Semua database repeat pelanggan bersih! Tiada tugasan re-order matang buat hari ini.")
        except Exception as e: st.error(f"Error: {e}")

# ==========================================
# HALAMAN 3: BULK UPLOAD EXCEL (SALES DATA)
# ==========================================
elif pilihan_menu == "📁 Bulk Upload Excel":
    st.title("📁 Muat Naik Data Sales Secara Pukal")
    if st.session_state["role"] == "admin":
        st.warning("⚡ **Mod Admin:** Anda boleh memuat naik data jualan untuk mana-mana staff jualan mengikut lajur fail.")
    else:
        st.info(f"🔒 **Mod Staff ({st.session_state['nama_penuh']}):** Semua data jualan akan dikunci automatik ke nama anda.")
    
    data_template = {
        "Tarikh": ["2026-05-26", "2026-05-27"], "Nama Pelanggan": ["Ahmad Abu", "Siti Aminah"], "Platform": ["TikTok Live", "WhatsApp"],
        "PIC Staff": ["Diisi jika Admin", "Diisi jika Admin"], "Amaun Jualan": [150.00, 0.00], "Status": ["Selesai (Paid)", "Lead Baru"], 
        "No Telefon": ["60123456789", "60198765432"], "SKU Produk": ["Hegula+ 1 Pouch", "Hegrano 1 Pouch"], "Alamat": ["No 123, Jalan Melati, KL", "No 45, Kampung Baru, Selangor"]
    }
    df_template = pd.DataFrame(data_template)
    csv_bytes = df_template.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download Template Excel/CSV Sales Baru", data=csv_bytes, file_name="Template_CRM_Sales_Hejja.csv", mime="text/csv", use_container_width=True)
    
    st.markdown("---")
    fail_diupload = st.file_uploader("Pilih fail template sales yang telah lengkap (.csv atau .xlsx):", type=["xlsx", "csv"])
    
    if fail_diupload is not None:
        try:
            df = pd.read_csv(fail_diupload) if fail_diupload.name.endswith('.csv') else pd.read_excel(fail_diupload)
            
            # KESELAMATAN: Tukar semua nama lajur fail yang di-upload menjadi huruf kecil & buang whitespace
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            st.subheader("👀 Pratinjau Data Jualan")
            st.dataframe(df)
            total_data = len(df)
            st.write(f"Jumlah rekod dikesan: **{total_data} baris jualan**")
            
            if st.button("🚀 Sah & Hantar Semua Data Sales ke Google Sheets", use_container_width=True):
                bulk_data = []
                for index, row in df.iterrows():
                    # Padankan mapping lajur dengan selamat (case-insensitive)
                    tarikh_val = row.get('tarikh') if pd.notna(row.get('tarikh')) else datetime.date.today()
                    nama_val = row.get('nama pelanggan') or row.get('nama') or 'Pelanggan Pukal'
                    platform_val = row.get('platform') if pd.notna(row.get('platform')) else 'Lain-lain'
                    amaun_val = float(row.get('amaun jualan') or row.get('amaun') or 0.0)
                    status_asal = str(row.get('status')).strip() if pd.notna(row.get('status')) else "Lead Baru"
                    telefon_val = str(row.get('no telefon') or row.get('telefon')).replace(".0", "").strip()
                    sku_val = str(row.get('sku produk') or row.get('sku'))
                    alamat_row = str(row.get('alamat')) if pd.notna(row.get('alamat')) else ""
                    
                    if st.session_state["role"] == "admin":
                        pic_row = str(row.get('pic staff') or row.get('pic')) if pd.notna(row.get('pic staff') or row.get('pic')) else st.session_state["nama_penuh"]
                    else:
                        pic_row = st.session_state["nama_penuh"]
                    
                    bulk_data.append({
                        "tarikh": str(tarikh_val).split()[0], "nama": str(nama_val), "platform": str(platform_val), 
                        "pic": pic_row, "amaun": amaun_val, "status": status_asal, "telefon": telefon_val, 
                        "sku": sku_val, "alamat": alamat_row
                    })
                    
                with st.spinner(f"Sedang memproses {total_data} data jualan..."):
                    respon = requests.post(URL_GOOGLE_SHEET, json=bulk_data)
                    if respon.status_code == 200: 
                        st.success(f"Berjaya memasukkan {total_data} rekod jualan!")
                        st.balloons()
                    else: 
                        st.error("Gagal hantar data pukal. Sila semak Apps Script anda.")
        except Exception as e: 
            st.error(f"Ralat format fail jualan: {e}")