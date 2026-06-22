import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
from gtts import gTTS

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

st.set_page_config(layout="wide", page_title="Eymen-GPT Ultimate", initial_sidebar_state="expanded")

# --- OTURUM HAFIZASI ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None

metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except:
    st.error("API Anahtarları eksik! Lütfen Streamlit secrets ayarlarını kontrol edin.")
    st.stop()

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

MODELS = {
    "Mistral-8x7B (Hızlı)": "Mistral-8x7B",
    "GPT-4o Mini (Dengeli)": "gpt-4o-mini",
    "Llama-3.1-70B (Güçlü)": "meta-llama-3.1-70b-instruct",
    "Cohere Command R (Araştırmacı)": "cohere-command-r",
    "GPT-4o (En Zeki)": "gpt-4o"
}

st.sidebar.title("⚙️ Sistem Ayarları")
uygulama_modu = st.sidebar.radio("Mod Seçimi:", ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Sesli Yanıt 🗣️", "Müzisyen Modu 🎵"])

st.sidebar.markdown("---")
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

if st.sidebar.button("🧹 Sistemi Temizle", use_container_width=True):
    st.session_state.mesaj_gecmisi = []
    st.session_state.dosya_bellegi = ""
    st.session_state.resim_hazir = False
    st.session_state.sesli_metin_hazir = False
    st.rerun()

st.title("Eymen-GPT Ultimate 🚀")

# ==========================================
# 1. MOD: SOHBET VE ANALİZ
# ==========================================
if uygulama_modu == "Sohbet & Analiz 💬":
    yuklenen_dosya = st.file_uploader("Dosya Yükle", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"])

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        icerik = ""
        with st.spinner("Dosya işleniyor..."):
            try:
                if dosya_adi.endswith((".txt", ".py", ".xml")): icerik = yuklenen_dosya.read().decode("utf-8")
                elif dosya_adi.endswith(".pdf"):
                    pdf_okuyucu = PdfReader(yuklenen_dosya)
                    icerik = "\n".join([sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()])
                elif dosya_adi.endswith(".docx"):
                    doc = Document(yuklenen_dosya)
                    icerik = "\n".join([p.text for p in doc.paragraphs])
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
                elif dosya_adi.endswith((".html", ".htm")):
                    soup = BeautifulSoup(yuklenen_dosya.read().decode("utf-8"), "html.parser")
                    icerik = soup.get_text(separator="\n", strip=True)
                elif dosya_adi.endswith(".json"):
                    icerik = json.dumps(json.load(yuklenen_dosya), indent=2, ensure_ascii=False)
                elif dosya_adi.endswith((".png", ".jpg", ".jpeg")):
                    st.image(yuklenen_dosya, width=300)
                    try: icerik = pytesseract.image_to_string(Image.open(yuklenen_dosya), lang="tur+eng")
                    except: st.warning("OCR çalışmadı.")
                
                if icerik:
                    st.session_state.dosya_bellegi = icerik
                    st.success(f"📎 {yuklenen_dosya.name} hafızaya alındı!")
            except Exception as e: st.error(f"Hata: {e}")
    else:
        st.session_state.dosya_bellegi = ""

    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]): st.markdown(mesaj["content"])

    if sorgu := st.chat_input("Sorunu yaz..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"): st.markdown(sorgu)

        with st.spinner("Düşünüyor..."):
            try:
                arama_metni = ""
                try:
                    res = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([r["content"] for r in res["results"]])
                except: pass
                
                sistem_mesaji = "Sen Eymen-GPT'sin. Akıl yürütmeni <dusunce> etiketi içine yaz, sonra cevabı ver."
                k_msg = f"Soru: {sorgu}\n"
                if arama_metni: k_msg += f"İNTERNET: {arama_metni}\n"
                if st.session_state.dosya_bellegi: k_msg += f"DOSYA: {st.session_state.dosya_bellegi[:30000]}\n"

                msgs = [{"role": "system", "content": sistem_mesaji}] + st.session_state.mesaj_gecmisi[:-1] + [{"role": "user", "content": k_msg}]

                basarili = False
                for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                    try:
                        response = client.chat.completions.create(messages=msgs, model=model_id, temperature=0.6)
                        basarili = True
                        break
                    except: continue

                if basarili:
                    cevap = response.choices[0].message.content
                    d_blog = ""
                    m = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', cevap, re.DOTALL | re.IGNORECASE)
                    if m:
                        d_blog = m.group(1).strip()
                        cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
                    with st.chat_message("assistant"):
                        if d_blog:
                            with st.expander("Düşünce Adımları"): st.write(d_blog)
                        st.markdown(cevap)
                else: st.error("Modeller çöktü.")
            except Exception as e: st.error(f"Hata: {e}")

# ==========================================
# 2. MOD: RESSAM MODU
# ==========================================
elif uygulama_modu == "Ressam Modu 🎨":
    resim_sorgu = st.text_input("Neyin resmini çizmek istersin?")
    if st.button("Resmi Oluştur", use_container_width=True) and resim_sorgu:
        with st.spinner("Çiziliyor..."):
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(resim_sorgu)}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
    if st.session_state.resim_hazir:
        st.image(st.session_state.son_resim_url, use_container_width=True)

# ==========================================
# 3. MOD: SESLİ YANIT
# ==========================================
elif uygulama_modu == "Sesli Yanıt 🗣️":
    sesli_sorgu = st.text_area("Seslendirilecek metni girin:", height=150)
    if st.button("🎙️ Sese Çevir", use_container_width=True) and sesli_sorgu:
        with st.spinner("Ses oluşturuluyor..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr', slow=False)
                ses_bellek = io.BytesIO()
                tts.write_to_fp(ses_bellek)
                ses_bellek.seek(0)
                st.session_state.son_ses_bytes = ses_bellek.getvalue()
                st.session_state.sesli_metin_hazir = True
            except Exception as e: st.error(f"Hata: {e}")
            
    if st.session_state.sesli_metin_hazir:
        st.audio(st.session_state.son_ses_bytes, format='audio/mp3')
        st.download_button(label="💾 MP3 Olarak İndir", data=st.session_state.son_ses_bytes, file_name="eymen_ses.mp3", mime="audio/mp3", use_container_width=True)

# ==========================================
# 4. MOD: MÜZİSYEN MODU (SADECE MP3)
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 NoModelsMusic Dev Stüdyo")
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        muzik_sorgu = st.text_input("Şarkıyı tarif et:", placeholder="Örn: 80s synthwave, hareketli...")
    with col_m2:
        hedef_dk = st.number_input("Süre (Dk)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

    if st.button("🎸 Müziği Üret (Sadece MP3)", use_container_width=True) and muzik_sorgu:
        with st.spinner(f"{hedef_dk} dakikalık şarkı bestelenip MP3 formatına sıkıştırılıyor..."):
            try:
                sistem_mesaji = """Sen usta bir prodüktörsün. Kullanıcının hissine göre 16 adımlık DEV BİR MÜZİK İSKELETİ kur.
                SADECE GEÇERLİ JSON YAZ.
                Kullanabileceğin Kanallar:
                - Davullar: "kick_808", "kick_909", "kick_aco", "kick_pnc", "kick_lof", "kick_tec", "kick_dep", "snare_aco", "snare_ele", "snare_808", "snare_trp", "clap_bsc", "clap_rvb", "rimshot", "hihat_cl", "hihat_op", "cym_cr", "cym_rd", "tom_hi", "tom_lo", "bongo", "cowbell", "shaker", "claves"
                - Doğa/Oyun FX: "fx_wind", "fx_rain", "fx_ocean", "fx_thunder", "fx_fire", "fx_laser", "fx_explosion", "fx_jump", "fx_coin", "fx_helicopter", "fx_ufo", "fx_bird", "fx_dog", "fx_cricket", "fx_frog"
                - Bas (C1-B3): "bass_sub", "bass_808", "bass_slap", "bass_syn", "bass_res", "bass_acd", "bass_fm", "bass_wob", "bass_mog", "bass_frt"
                - Tuşlular (C3-B5): "piano_grd", "piano_rhd", "piano_dx7", "organ_ham", "organ_chu", "clavinet"
                - Gitar/Yaylı (C3-B6): "guit_aco", "guit_nyl", "guit_ovd", "guit_fuz", "harp", "str_syn", "violin", "cello"
                - Üflemeli (C4-B6): "flute", "trumpet", "brass", "sax", "pan_flu"
                - Lead/Pad/Pluck (C3-B7): "lead_saw", "lead_sqr", "lead_hvr", "lead_spr", "pad_wrm", "pad_cho", "pluck_sin", "pluck_fm", "arp_8bt"
                
                (Not: Kanalların sonuna "_2" eklenebilir. Örn: "kick_808_2")
                
                Tüm array dizileri 16 elemanlı olmalı. Notalar C1-B7 arası.
                """
                
                basarili = False
                for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                    try:
                        response = client.chat.completions.create(
                            messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": muzik_sorgu}],
                            model=model_id, temperature=0.7
                        )
                        basarili = True
                        break
                    except: continue

                if basarili:
                    json_str = response.choices[0].message.content.strip()
                    m = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if m: json_str = m.group(0)
                    
                    sarki_verisi = json.loads(json_str)
                    
                    import NoModelsMusic
                    ses_dosyasi_wav = NoModelsMusic.motoru_calistir(sarki_verisi, hedef_dakika=hedef_dk)
                    
                    from pydub import AudioSegment
                    
                    wav_io = io.BytesIO(ses_dosyasi_wav)
                    ses_segmenti = AudioSegment.from_wav(wav_io)
                    
                    mp3_io = io.BytesIO()
                    ses_segmenti.export(mp3_io, format="mp3", bitrate="192k")
                    ses_dosyasi_mp3 = mp3_io.getvalue()
                    
                    st.audio(ses_dosyasi_mp3, format='audio/mp3')
                    st.success("🎵 Şarkı Hazır!")
                    
                    st.download_button(
                        label="💾 .MP3 Olarak İndir",
                        data=ses_dosyasi_mp3,
                        file_name="NoModelsMusic_Sarki.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
                    
                    with st.expander("🛠️ Kanallar (JSON)"): st.json(sarki_verisi)
                else: st.error("Bağlantı hatası.")
            except Exception as e: st.error(f"Hata: {e}")
