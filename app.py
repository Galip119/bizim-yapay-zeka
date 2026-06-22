import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import urllib.parse
import os
from gtts import gTTS
import re

from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

st.set_page_config(layout="centered", page_title="Eymen-GPT Gelişmiş")

# --- OTURUM HAFIZASI ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "cevap_hazir" not in st.session_state: st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state: st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state: st.session_state.son_dusunce = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""

metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

st.sidebar.title("⚙️ Ayarlar")

uygulama_modu = st.sidebar.radio("Mod Seçimi:", ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Sesli Yanıt Modu 🗣️", "Müzisyen Modu 🎵"])

st.sidebar.markdown("---")
st.sidebar.write("Kotası biten modelden otomatik olarak diğerine geçilir.")
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

if st.sidebar.button("🧹 Sohbet Geçmişini Temizle"):
    st.session_state.mesaj_gecmisi = []
    st.rerun()

st.title("Eymen-GPT 🚀")

# ==========================================
# 1. MOD: SOHBET VE ANALİZ (HATASIZ DOSYA BELLEĞİ)
# ==========================================
if uygulama_modu == "Sohbet & Analiz 💬":
    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]):
            st.markdown(mesaj["content"])

    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        sorgu = st.chat_input("Bana bir şeyler sor...", key=metin_anahtari)
    with col2:
        yuklenen_dosya = st.file_uploader("Dosya Analizi", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"], label_visibility="collapsed", key=dosya_anahtari)

    # Dosyayı hafızada tutmak için sistem
    if "dosya_bellegi" not in st.session_state:
        st.session_state.dosya_bellegi = ""

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        dosya_icerigi = ""
        try:
            if dosya_adi.endswith((".txt", ".py")): dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            elif dosya_adi.endswith(".pdf"):
                pdf_okuyucu = PdfReader(yuklenen_dosya)
                dosya_icerigi = "\n".join([sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()])
            elif dosya_adi.endswith(".docx"):
                doc = Document(yuklenen_dosya)
                dosya_icerigi = "\n".join([p.text for p in doc.paragraphs])
            elif dosya_adi.endswith(".xlsx"):
                wb = openpyxl.load_workbook(yuklenen_dosya, data_only=True)
                excel_metni = []
                for sayfa in wb.sheetnames:
                    ws = wb[sayfa]
                    excel_metni.append(f"--- Sayfa: {sayfa} ---")
                    for satir in ws.iter_rows(values_only=True):
                        satir_filtreli = [str(hucre) for hucre in satir if hucre is not None]
                        if satir_filtreli: excel_metni.append(" | ".join(satir_filtreli))
                dosya_icerigi = "\n".join(excel_metni)
            elif dosya_adi.endswith((".html", ".htm")):
                ham_html = yuklenen_dosya.read().decode("utf-8")
                soup = BeautifulSoup(ham_html, "html.parser")
                dosya_icerigi = soup.get_text(separator="\n", strip=True)
            elif dosya_adi.endswith(".json"):
                veri = json.load(yuklenen_dosya)
                dosya_icerigi = json.dumps(veri, indent=2, ensure_ascii=False)
            elif dosya_adi.endswith(".xml"):
                dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            elif dosya_adi.endswith((".png", ".jpg", ".jpeg")):
                st.image(yuklenen_dosya, caption="Yüklenen Resim", width=200)
                try:
                    resim = Image.open(yuklenen_dosya)
                    dosya_icerigi = pytesseract.image_to_string(resim, lang="tur+eng")
                except:
                    st.warning("OCR sistemi çalışmadığı için resimdeki yazı okunamadı.")
            
            if dosya_icerigi:
                # İçeriği Streamlit'in hafızasına kazıyoruz
                st.session_state.dosya_bellegi = dosya_icerigi
                st.success(f"📎 {yuklenen_dosya.name} başarıyla hafızaya alındı!")
                
                # Kullanıcı soru yazmakla uğraşmasın diye direkt buton
                if st.button("📄 Bu Dosyayı Analiz Et / Özetle"):
                    sorgu = "Lütfen yüklediğim bu dosyayı detaylıca analiz et ve özetle."
                    
        except Exception as e: st.error(f"Dosya okunurken hata oluştu: {e}")
    else:
        # Dosya çarpı işaretine basılıp silinirse hafızayı da temizle
        st.session_state.dosya_bellegi = ""

    # Yapay zeka soruyu ve bellekteki dosyayı işliyor
    if sorgu:
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"):
            st.markdown(sorgu)

        with st.spinner("Eymen-GPT düşünüyor..."):
            try:
                arama_metni = ""
                try:
                    search_result = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([res["content"] for res in search_result["results"]])
                except: pass
                
                sistem_mesaji = "Sen çok gelişmiş bir Eymen-GPT asistanısın. Herhangi bir cevap vermeden önce, akıl yürütmeni MUTLAKA <dusunce> ve </dusunce> etiketleri arasına yaz. Düşünce kısmını bitirdikten sonra DIŞINA nihai cevabı yaz."
                
                kullanici_mesaji = ""
                if arama_metni: kullanici_mesaji += f"--- İNTERNET ARAMASI ---\n{arama_metni}\n\n"
                
                # Hafızada dosya varsa prompt'a ekle
                if st.session_state.dosya_bellegi: 
                    kullanici_mesaji += f"--- DOSYA İÇERİĞİ ---\n{st.session_state.dosya_bellegi[:35000]}\n\n"
                    
                kullanici_mesaji += f"Soru: {sorgu}"

                api_mesajlari = [{"role": "system", "content": sistem_mesaji}]
                for msg in st.session_state.mesaj_gecmisi[:-1]:
                    api_mesajlari.append(msg)
                api_mesajlari.append({"role": "user", "content": kullanici_mesaji})

                yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
                basarili_oldu = False
                
                for aktif_model in yedek_modeller:
                    try:
                        response = client.chat.completions.create(
                            messages=api_mesajlari,
                            model=aktif_model, temperature=0.6
                        )
                        basarili_oldu = True
                        break 
                    except: continue
                
                if not basarili_oldu: st.error("Tüm modellerin kotası dolmuş veya bir bağlantı hatası var.")
                else:
                    ham_cevap = response.choices[0].message.content
                    dusunce_blogu, temiz_cevap = "", ham_cevap
                    
                    match = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', ham_cevap, re.DOTALL | re.IGNORECASE)
                    if match:
                        dusunce_blogu = match.group(1).strip()
                        temiz_cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', ham_cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": temiz_cevap})
                    
                    with st.chat_message("assistant"):
                        if dusunce_blogu:
                            with st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster"): 
                                st.write(dusunce_blogu)
                        st.markdown(temiz_cevap)

            except Exception as e: st.error(f"Bir hata oluştu: {e}")

# ==========================================
# 2. MOD: RESSAM MODU
# ==========================================
elif uygulama_modu == "Ressam Modu 🎨":
    st.markdown("### 🎨 Hayal Gücünü Ekrana Yansıt")
    resim_sorgu = st.text_input("Neyin resmini çizmek istersin?", placeholder="Örn: Yağmurlu bir gecede yürüyen fütüristik kedi", key=f"resim_input_{st.session_state.form_num}")
    if st.button("🖼️ Resmi Oluştur") and resim_sorgu:
        with st.spinner("Tuval hazırlanıyor, boyalar karıştırılıyor..."):
            guvenli_sorgu = urllib.parse.quote(resim_sorgu)
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{guvenli_sorgu}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
            st.session_state.form_num += 1
            st.rerun()
    if st.session_state.resim_hazir and st.session_state.son_resim_url:
        st.image(st.session_state.son_resim_url, caption="İşte oluşturulan resim!", use_container_width=True)

# ==========================================
# 3. MOD: SESLİ YANIT MODU
# ==========================================
elif uygulama_modu == "Sesli Yanıt Modu 🗣️":
    st.markdown("### 🗣️ Eymen-GPT Sesli Asistan")
    sesli_sorgu = st.text_input("Ne duymak istersin?", placeholder="Örn: Bana yıldızları anlat", key=f"sesli_input_{st.session_state.form_num}")
    if st.button("🎙️ Seslendir") and sesli_sorgu:
        with st.spinner("Sesi kasede kaydediyorum..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr')
                tts.save("eymen_ses.mp3")
                with open("eymen_ses.mp3", "rb") as audio_file:
                    st.audio(audio_file.read(), format='audio/mp3')
            except Exception as e:
                st.error(f"Seslendirme hatası: {e}")

# ==========================================
# 4. MOD: NOMODELSMUSIC V4 MEGA STÜDYO 🎵
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 NoModelsMusic V4 Mega Stüdyo")
    st.write("100'den fazla ses, hayvanlar, doğa efektleri ve devasa şarkılar. Üstelik artık şarkının kaç dakika olacağını SEN seçiyorsun!")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        muzik_sorgu = st.text_input("Şarkıyı ve ambiyansı tarif et:", placeholder="Örn: Yağmur altında kedi miyavlamalı hüzünlü piyano...", key=f"nomodels_{st.session_state.form_num}")
    with col2:
        sarki_suresi = st.number_input("Süre (Dakika)", min_value=1, max_value=10, value=2, step=1)
        
    uret_butonu = st.button("🎧 Mega Stüdyoyu Başlat")

    if uret_butonu and muzik_sorgu:
        with st.spinner(f"Eymen-GPT orkestrayı kuruyor, NoModelsMusic tam {sarki_suresi} dakikalık parçayı renderlıyor..."):
            try:
                sistem_mesaji = """Sen usta bir prodüktörsün. Kullanıcının verdiği hisse göre 16 adımlık BİR MÜZİK İSKELETİ kur.
                SADECE GEÇERLİ JSON YAZ.
                Kullanabileceğin Kanallar:
                - Kick/Davul: "kick_808", "kick_909", "kick_acoustic", "kick_punchy", "kick_lofi", "kick_techno", "kick_deep"
                - Trampet/Clap: "snare_acoustic", "snare_electronic", "snare_808", "snare_trap", "clap_basic", "clap_layered", "rimshot"
                - Zil/Hihat: "hihat_closed", "hihat_open", "hihat_808", "hihat_trap", "crash_cymbal", "ride_cymbal", "splash_cymbal"
                - Perküsyon: "tom_high", "tom_mid", "tom_low", "bongo_high", "bongo_low", "cowbell", "woodblock", "shaker", "tambourine", "triangle_perc", "claves", "guiro", "maracas"
                - Bas (C1-B3): "sub_bass", "slap_bass", "synth_bass", "reese_bass", "acid_bass", "fm_bass", "upright_bass", "fretless_bass", "moog_bass", "wobble_bass"
                - Piyano/Tuşlu (C3-B5): "grand_piano", "upright_piano", "rhodes_piano", "wurlitzer", "dx7_piano", "clavinet", "harpsichord", "celesta", "church_organ", "hammond_organ", "reed_organ"
                - Yaylı/Nefesli (C3-B6): "violin", "cello", "contrabass", "pizzicato", "harp", "timpani", "brass_section", "french_horn", "trumpet", "trombone", "tuba", "synth_strings", "mellotron", "flute_acoustic", "clarinet", "oboe", "bassoon", "piccolo", "recorder", "pan_flute", "sax_alto", "sax_tenor", "sax_baritone"
                - Gitar (C2-B5): "acoustic_guitar", "nylon_guitar", "electric_clean", "electric_overdrive", "electric_distortion", "electric_fuzz", "electric_muted", "banjo", "ukulele", "sitar"
                - Elektronik Lead/Pad (C3-B7): "saw_lead", "square_lead", "sine_pluck", "trance_gate_pad", "warm_pad", "choir_pad_synth", "sweep_pad", "scifi_fx", "arp_8bit", "chiptune_square", "hoover_lead", "supersaw"
                - Doğa/Ambiyans (E): "wind_howl", "rain_drops", "ocean_waves", "thunder_strike", "fire_crackle"
                - Hayvanlar (E): "bird_chirp", "dog_bark", "cat_meow", "cricket_chirp", "frog_croak", "wolf_howl", "fly_buzz"
                - Oyun FX (E): "fx_laser_pew", "fx_coin_pickup", "fx_jump", "fx_explosion", "fx_helicopter"

                Örnek:
                {
                    "tempo": 125,
                    "kick_808": ["K","-","K","-","K","-","K","-","K","-","K","-","K","-","K","-"],
                    "cat_meow": ["-","-","E","-","-","-","E","-","-","-","E","-","-","-","E","-"],
                    "grand_piano": ["C4","-","-","-","C4","-","-","-","C4","-","-","-","C4","-","-","-"]
                }
                Tüm listeler KESİNLİKLE 16 elemanlı olmalı. Davullar ve Efektler için E, K, S vb. Notalar için C1-B7 arası.
                """
                
                response = client.chat.completions.create(
                    model=secilen_model_id,
                    messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": muzik_sorgu}],
                    temperature=0.8
                )
                
                json_str = response.choices[0].message.content.strip()
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    
                sarki_verisi = json.loads(json_str)
                
                import NoModelsMusic
                ses_dosyasi = NoModelsMusic.motoru_calistir(sarki_verisi, hedef_dakika=sarki_suresi)
                
                st.audio(ses_dosyasi, format='audio/wav')
                st.success(f"🎵 NoModelsMusic {sarki_suresi} Dakikalık Parçayı Hazırladı! (Tempo: {sarki_verisi.get('tempo', 120)} BPM)")
                
                with st.expander("🛠️ Eymen'in Dev Stüdyo Kayıtlarını İncele"):
                    st.json(sarki_verisi)
                    
            except json.JSONDecodeError:
                st.error("Yapay zeka devasa enstrümanları dizerken hata yaptı. Lütfen tekrar dene.")
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")
