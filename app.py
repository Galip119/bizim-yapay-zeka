import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import os
import io
from gtts import gTTS

# --- DOSYA OKUMA VE İŞLEME KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# =====================================================================
# EYMEN-GPT: ULTIMATE MEGA STUDIO & ASİSTAN ARAYÜZÜ
# =====================================================================

# Sayfa temel ayarları ve genişlik yapılandırması
st.set_page_config(
    layout="wide", 
    page_title="Eymen-GPT Ultimate", 
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# --- 1. OTURUM HAFIZASI (SESSION STATE) YÖNETİMİ ---
# Kullanıcının sohbet geçmişini, dosyalarını ve ürettiği medyaları kaybetmemesi için derin hafıza.
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False

# Dinamik anahtarlar
metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

# --- 2. GİZLİ API ANAHTARLARI VE SERVİS BAĞLANTILARI ---
try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except Exception as e:
    st.error("API Anahtarları bulunamadı. Lütfen Streamlit secrets ayarlarını kontrol edin.")
    st.stop()

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# --- 3. DESTEKLENEN YAPAY ZEKA MODELLERİ ---
MODELS = {
    "Mistral-8x7B (Hızlı)": "Mistral-8x7B",
    "GPT-4o Mini (Dengeli)": "gpt-4o-mini",
    "Llama-3.1-70B (Güçlü)": "meta-llama-3.1-70b-instruct",
    "Cohere Command R (Araştırmacı)": "cohere-command-r",
    "GPT-4o (En Zeki)": "gpt-4o"
}

# --- 4. YAN MENÜ (SIDEBAR) TASARIMI ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1183/1183140.png", width=100)
st.sidebar.title("⚙️ Sistem Kontrol Paneli")
st.sidebar.markdown("Eymen-GPT Ultimate Engine'e Hoş Geldin.")

uygulama_modu = st.sidebar.radio(
    "Aktif Modu Seçin:", 
    [
        "Sohbet & Veri Analizi 💬", 
        "Ressam Modu (Görsel Üretim) 🎨", 
        "Sesli Yanıt (Text-to-Speech) 🗣️", 
        "Müzisyen Modu (DSP Motoru) 🎵"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Model Ayarları")
st.sidebar.write("Kotası dolan modelden otomatik olarak yedek modellere geçiş yapılır. Çökme riski sıfırdır.")
secilen_model_adi = st.sidebar.selectbox("Birincil Yapay Zeka Modelini Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Tüm Sistem Hafızasını Temizle", use_container_width=True):
    st.session_state.mesaj_gecmisi = []
    st.session_state.dosya_bellegi = ""
    st.session_state.resim_hazir = False
    st.session_state.sesli_metin_hazir = False
    st.rerun()

st.title("Eymen-GPT Ultimate 🚀")
st.markdown("Güçlendirilmiş Çoklu Zeka, Sinyal İşleme ve Analiz Platformu")

# =====================================================================
# MOD 1: SOHBET, BELGE OKUMA VE İNTERNET ARAMASI
# =====================================================================
if uygulama_modu == "Sohbet & Veri Analizi 💬":
    st.info("İstediğin dosyayı yükleyebilir, analiz ettirebilir veya doğrudan internete bağlı şekilde sorular sorabilirsin.")
    
    # Gelişmiş Dosya Yükleyici
    yuklenen_dosya = st.file_uploader("Analiz Edilecek Dosyayı Yükle (İsteğe Bağlı)", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"])

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        icerik = ""
        with st.spinner(f"{yuklenen_dosya.name} işleniyor, veriler çıkartılıyor..."):
            try:
                # Metin ve Kod Dosyaları
                if dosya_adi.endswith((".txt", ".py", ".xml")): 
                    icerik = yuklenen_dosya.read().decode("utf-8")
                # PDF Dosyaları
                elif dosya_adi.endswith(".pdf"):
                    pdf_okuyucu = PdfReader(yuklenen_dosya)
                    icerik = "\n".join([sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()])
                # Word Dosyaları
                elif dosya_adi.endswith(".docx"):
                    doc = Document(yuklenen_dosya)
                    icerik = "\n".join([p.text for p in doc.paragraphs])
                # Excel Dosyaları
                elif dosya_adi.endswith(".xlsx"):
                    wb = openpyxl.load_workbook(yuklenen_dosya, data_only=True)
                    satirlar = []
                    for sayfa in wb.sheetnames:
                        ws = wb[sayfa]
                        satirlar.append(f"--- Sayfa: {sayfa} ---")
                        for satir in ws.iter_rows(values_only=True):
                            satir_filtreli = [str(hucre) for hucre in satir if hucre is not None]
                            if satir_filtreli: satirlar.append(" | ".join(satir_filtreli))
                    icerik = "\n".join(satirlar)
                # HTML Sayfaları
                elif dosya_adi.endswith((".html", ".htm")):
                    soup = BeautifulSoup(yuklenen_dosya.read().decode("utf-8"), "html.parser")
                    icerik = soup.get_text(separator="\n", strip=True)
                # JSON Verileri
                elif dosya_adi.endswith(".json"):
                    icerik = json.dumps(json.load(yuklenen_dosya), indent=2, ensure_ascii=False)
                # Görsel ve OCR (Optik Karakter Tanıma)
                elif dosya_adi.endswith((".png", ".jpg", ".jpeg")):
                    st.image(yuklenen_dosya, caption="Sisteme Yüklenen Görsel", width=300)
                    try: 
                        icerik = pytesseract.image_to_string(Image.open(yuklenen_dosya), lang="tur+eng")
                    except: 
                        st.warning("OCR okuyamadı. Tesseract yüklü olmayabilir.")
                
                if icerik:
                    st.session_state.dosya_bellegi = icerik
                    st.success(f"📎 {yuklenen_dosya.name} başarıyla veri tabanına alındı! Artık bu dosya hakkında sorular sorabilirsin.")
            except Exception as e: 
                st.error(f"Kritik Dosya Okuma Hatası: {e}")
    else:
        st.session_state.dosya_bellegi = ""

    # Ekrandaki Sohbet Geçmişini Render Etme
    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]):
            st.markdown(mesaj["content"])

    # Standart Sohbet Girdisi
    if sorgu := st.chat_input("Eymen-GPT'ye bir soru sor veya dosya hakkında komut ver..."):
        
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"): 
            st.markdown(sorgu)

        with st.spinner("Ağlar taranıyor, düşünce zinciri oluşturuluyor..."):
            try:
                arama_metni = ""
                try:
                    # Tavily ile Canlı İnternet Taraması
                    res = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([r["content"] for r in res["results"]])
                except: 
                    pass # İnternet araması başarısız olursa normal zekayla devam et
                
                sistem_mesaji = "Sen Eymen-GPT'sin. Çok zeki, mühendislik ve analiz yetenekleri üst düzey bir asistansın. Akıl yürütmeni <dusunce> etiketi içine detaylıca yaz, düşünce işlemi bittikten sonra etiket dışına nihai ve net cevabını yaz."
                k_msg = f"Soru/Komut: {sorgu}\n"
                
                # Yapay zekaya aktarılacak bağlamlar
                if arama_metni: 
                    k_msg += f"\n--- CANLI İNTERNET VERİSİ ---\n{arama_metni}\n"
                if st.session_state.dosya_bellegi: 
                    k_msg += f"\n--- KULLANICI DOSYA İÇERİĞİ ---\n{st.session_state.dosya_bellegi[:30000]}\n"

                msgs = [{"role": "system", "content": sistem_mesaji}] + st.session_state.mesaj_gecmisi[:-1] + [{"role": "user", "content": k_msg}]

                basarili = False
                yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
                
                # Çökme Korumalı Model Yönlendirmesi
                for model_id in yedek_modeller:
                    try:
                        response = client.chat.completions.create(
                            messages=msgs, 
                            model=model_id, 
                            temperature=0.6,
                            max_tokens=4000
                        )
                        basarili = True
                        break
                    except Exception as e: 
                        continue

                if basarili:
                    cevap = response.choices[0].message.content
                    d_blog = ""
                    
                    # Düşünce zincirini regex ile ayıkla
                    m = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', cevap, re.DOTALL | re.IGNORECASE)
                    if m:
                        d_blog = m.group(1).strip()
                        cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
                    
                    with st.chat_message("assistant"):
                        if d_blog:
                            with st.expander("🧠 Eymen-GPT'nin Düşünce Adımları (Zincir)"): 
                                st.write(d_blog)
                        st.markdown(cevap)
                else: 
                    st.error("Sunuculardaki tüm modellerin kotası dolu veya bağlantı kurulamıyor.")
            except Exception as e: 
                st.error(f"Cevap üretilirken kritik sistem hatası: {e}")

# =====================================================================
# MOD 2: RESSAM MODU (GÖRSEL ÜRETİM)
# =====================================================================
elif uygulama_modu == "Ressam Modu (Görsel Üretim) 🎨":
    st.markdown("### 🎨 Dijital Tuval: Hayal Gücünü Ekrana Yansıt")
    st.write("Yapay zeka motoru, verdiğin detaylı metinsel tasviri yüksek çözünürlüklü bir sanat eserine çevirir.")
    
    resim_sorgu = st.text_area("Çizilmesini istediğin sahneyi detaylıca tarif et:", height=100, placeholder="Örn: Neon ışıklı siberpunk bir şehirde, elinde kılıç tutan robotik bir savaşçı, sinematik ışıklandırma, 8k çözünürlük...")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        cizdir_butonu = st.button("🖼️ Görseli Sentezle", use_container_width=True)
    
    if cizdir_butonu and resim_sorgu:
        with st.spinner("Görsel motoru çalıştırılıyor, pikseller hesaplanıyor..."):
            guvenli_sorgu = urllib.parse.quote(resim_sorgu)
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{guvenli_sorgu}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
            
    if st.session_state.resim_hazir and st.session_state.son_resim_url:
        st.image(st.session_state.son_resim_url, caption=f"Prompt: {resim_sorgu}", use_container_width=True)
        st.success("Görsel başarıyla oluşturuldu! Resmi sağ tıklayıp veya basılı tutup cihazınıza kaydedebilirsiniz.")

# =====================================================================
# MOD 3: SESLİ YANIT VE METİN OKUMA (TEXT-TO-SPEECH)
# =====================================================================
elif uygulama_modu == "Sesli Yanıt (Text-to-Speech) 🗣️":
    st.markdown("### 🗣️ Sesli Asistan ve Metin Okuyucu")
    st.write("İstediğin herhangi bir uzun metni veya soruyu buraya yaz, sistem sana bunu sesli bir şekilde okusun ve indirilebilir bir MP3 dosyası olarak versin.")
    
    sesli_sorgu = st.text_area("Seslendirilmesini istediğiniz metni girin:", height=150, placeholder="Örn: Merhaba, ben Eymen-GPT. Bugün size yıldızların nasıl oluştuğunu anlatacağım...")
    
    col_ses1, col_ses2 = st.columns([1, 4])
    with col_ses1:
        seslendir_butonu = st.button("🎙️ Sese Çevir", use_container_width=True)
    
    if seslendir_butonu and sesli_sorgu:
        with st.spinner("Metin analiz ediliyor, akustik dalgalar (MP3) oluşturuluyor..."):
            try:
                # gTTS (Google Text-to-Speech) kütüphanesi ile sesi oluştur
                tts = gTTS(text=sesli_sorgu, lang='tr', slow=False)
                
                # Sesi geçici bir bellek tamponuna (BytesIO) kaydet ki diski yormasın
                ses_bellek = io.BytesIO()
                tts.write_to_fp(ses_bellek)
                ses_bellek.seek(0)
                
                st.session_state.son_ses_bytes = ses_bellek.getvalue()
                st.session_state.sesli_metin_hazir = True
                st.success("Ses sentezleme işlemi başarıyla tamamlandı!")
                
            except Exception as e:
                st.error(f"Ses sentezleme motorunda bir hata oluştu: {e}")
                
    if st.session_state.sesli_metin_hazir and st.session_state.son_ses_bytes:
        st.markdown("#### 🎧 Dinle ve İndir")
        st.audio(st.session_state.son_ses_bytes, format='audio/mp3')
        
        # Ekstra: Direkt indirme butonu
        st.download_button(
            label="💾 MP3 Olarak Cihaza İndir",
            data=st.session_state.son_ses_bytes,
            file_name="eymen_gpt_sesli_yanit.mp3",
            mime="audio/mp3",
            use_container_width=True
        )

# =====================================================================
# MOD 4: MÜZİSYEN MODU (NOMODELSMUSIC DEV DSP ENGINE)
# =====================================================================
elif uygulama_modu == "Müzisyen Modu (DSP Motoru) 🎵":
    st.markdown("### 🎵 NoModelsMusic Dev Stüdyo")
    st.write("Yapay zeka sadece notaları yazar, yerli üretim matematiksel DSP motorumuz ise sıfırdan MP3/WAV kalitesinde sesi oluşturur.")
    
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        muzik_sorgu = st.text_input("Şarkıyı detaylıca tarif et:", placeholder="Örn: 80s synthwave, hareketli bir bas ve arp lead, yağmur efektli...")
    with col_m2:
        hedef_dk = st.number_input("Şarkı Süresi (Dk)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

    if st.button("🎸 Müziği Üret ve Render Al", use_container_width=True) and muzik_sorgu:
        with st.spinner(f"Eymen-GPT orkestrasyonu kuruyor, NoModelsMusic {hedef_dk} dakikalık şarkıyı matematiksel olarak render ediyor..."):
            try:
                sistem_mesaji = """Sen efsanevi bir prodüktörsün. Kullanıcının hissine göre 16 adımlık DEV BİR MÜZİK İSKELETİ kur.
                SADECE GEÇERLİ JSON YAZ. Başka tek kelime etme.
                
                Kullanabileceğin Kanallar (Enstrümanlar):
                - Davullar: "kick_808", "kick_909", "kick_aco", "kick_pnc", "kick_lof", "kick_tec", "kick_dep", "snare_aco", "snare_ele", "snare_808", "snare_trp", "clap_bsc", "clap_rvb", "rimshot", "hihat_cl", "hihat_op", "cym_cr", "cym_rd", "tom_hi", "tom_lo", "bongo", "cowbell", "shaker", "claves"
                - Doğa/Oyun FX: "fx_wind", "fx_rain", "fx_ocean", "fx_thunder", "fx_fire", "fx_laser", "fx_explosion", "fx_jump", "fx_coin", "fx_helicopter", "fx_ufo", "fx_bird", "fx_dog", "fx_cricket", "fx_frog"
                - Bas (C1-B3): "bass_sub", "bass_808", "bass_slap", "bass_syn", "bass_res", "bass_acd", "bass_fm", "bass_wob", "bass_mog", "bass_frt"
                - Tuşlular (C3-B5): "piano_grd", "piano_rhd", "piano_dx7", "organ_ham", "organ_chu", "clavinet"
                - Gitar/Yaylı (C3-B6): "guit_aco", "guit_nyl", "guit_ovd", "guit_fuz", "harp", "str_syn", "violin", "cello"
                - Üflemeli (C4-B6): "flute", "trumpet", "brass", "sax", "pan_flu"
                - Lead/Pad/Pluck (C3-B7): "lead_saw", "lead_sqr", "lead_hvr", "lead_spr", "pad_wrm", "pad_cho", "pluck_sin", "pluck_fm", "arp_8bt"
                
                (Not: İstersen yukarıdaki kanalların sonuna "_2" ekleyerek alternatif varyasyonlarını da kullanabilirsin. Örn: "kick_808_2")

                Örnek Format:
                {
                    "tempo": 128,
                    "global_fx": ["chorus", "reverb", "flanger", "phaser", "compressor"],
                    "kick_808_2": ["K","-","K","-","K","-","K","-","K","-","K","-","K","-","K","-"],
                    "bass_res": ["C2","-","-","-","E2","-","-","-","G2","-","-","-","C2","-","-","-"],
                    "piano_grd": ["C4","-","-","-","E4","-","-","-","G4","-","-","-","C4","-","-","-"],
                    "fx_rain": ["E","-","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
                }
                Tüm array dizileri KESİNLİKLE 16 elemanlı olmalı. Davullar ve Efektler için K, S, E vb. Notalar için C1-B7 arası kullan.
                """
                
                basarili = False
                yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
                
                for model_id in yedek_modeller:
                    try:
                        response = client.chat.completions.create(
                            messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": muzik_sorgu}],
                            model=model_id, 
                            temperature=0.7
                        )
                        basarili = True
                        break
                    except: 
                        continue

                if basarili:
                    json_str = response.choices[0].message.content.strip()
                    # JSON'ı temizle
                    m = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if m: json_str = m.group(0)
                    
                    sarki_verisi = json.loads(json_str)
                    
                    # NoModelsMusic kütüphanesi çağrılıyor (Aynı klasörde NoModelsMusic.py olmalı)
                    import NoModelsMusic
                    ses_dosyasi = NoModelsMusic.motoru_calistir(sarki_verisi, hedef_dakika=hedef_dk)
                    
                    st.audio(ses_dosyasi, format='audio/wav')
                    st.success(f"🎵 {hedef_dk} Dakikalık Matematiksel Şarkı Hazır! (Tempo: {sarki_verisi.get('tempo', 120)} BPM)")
                    
                    st.download_button(
                        label="💾 Şarkıyı İndir (.WAV)",
                        data=ses_dosyasi,
                        file_name="NoModelsMusic_Sentez.wav",
                        mime="audio/wav",
                        use_container_width=True
                    )
                    
                    with st.expander("🛠️ Kullanılan Kanallar ve Notalar (JSON Gösterimi)"): 
                        st.json(sarki_verisi)
                else:
                    st.error("Yapay Zeka API bağlantısı sağlanamadı. Sunucular dolu olabilir.")
            except json.JSONDecodeError: 
                st.error("Yapay zeka notaları dizerken JSON formatında syntax hatası yaptı. Lütfen butona tekrar basın.")
            except ImportError:
                st.error("Kritik Hata: 'NoModelsMusic.py' dosyası ana dizinde bulunamadı! Lütfen DSP motoru dosyasının app.py ile aynı klasörde olduğundan emin ol.")
            except Exception as e: 
                st.error(f"Sistem Hatası: {e}")
