import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import urllib.parse
import os
from gtts import gTTS
import numpy as np
import scipy.io.wavfile as wav
import io
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
# 1. MOD: SOHBET VE ANALİZ
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

    dosya_icerigi = ""

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
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
                    st.warning("OCR sistemi tam çalışmadığı için yazı okunamadı.")
            
            if dosya_icerigi: st.info(f"📎 {yuklenen_dosya.name} başarıyla okundu.")
        except Exception as e: st.error(f"Dosya okunurken hata oluştu: {e}")

    if sorgu or dosya_icerigi:
        if sorgu:
            st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
            with st.chat_message("user"):
                st.markdown(sorgu)

        with st.spinner("Eymen-GPT düşünüyor..."):
            try:
                arama_metni = ""
                if sorgu:
                    try:
                        search_result = tavily.search(query=sorgu, search_depth="basic")
                        arama_metni = "\n".join([res["content"] for res in search_result["results"]])
                    except: st.warning("İnternet araması yapılamadı.")
                
                sistem_mesaji = "Sen çok gelişmiş bir Eymen-GPT asistanısın. Herhangi bir cevap vermeden önce, akıl yürütmeni MUTLAKA <dusunce> ve </dusunce> etiketleri arasına yaz. Düşünce kısmını bitirdikten sonra DIŞINA nihai cevabı yaz."
                
                kullanici_mesaji = ""
                if arama_metni: kullanici_mesaji += f"--- İNTERNET ARAMASI ---\n{arama_metni}\n\n"
                if dosya_icerigi: kullanici_mesaji += f"--- DOSYA İÇERİĞİ ---\n{dosya_icerigi[:35000]}\n\n"
                if sorgu: kullanici_mesaji += f"Soru: {sorgu}"
                else: kullanici_mesaji += "Soru: Lütfen yüklediğim bu dosyayı detaylıca analiz et ve özetle."

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
    cizdir_butonu = st.button("🖼️ Resmi Oluştur")
    
    if cizdir_butonu and resim_sorgu:
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
    st.write("Yazdığın her şeyi gerçekçi bir sesle sana okuyabilirim.")
    
    sesli_sorgu = st.text_input("Ne duymak istersin?", placeholder="Örn: Bana yıldızları anlat", key=f"sesli_input_{st.session_state.form_num}")
    oku_butonu = st.button("🎙️ Seslendir")

    if oku_butonu and sesli_sorgu:
        with st.spinner("Sesi kasede kaydediyorum..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr')
                dosya_yolu = "eymen_ses.mp3"
                tts.save(dosya_yolu)
                
                with open(dosya_yolu, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mp3')
                
                st.success("İşte sesin hazır! 🎧")
            except Exception as e:
                st.error(f"Seslendirme hatası: {e}")

# ==========================================
# 4. MOD: ULTRA GENİŞ MÜZİK MOTORU 🎵
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 Eymen-GPT Ultra Geniş Müzik Stüdyosu")
    st.write("Sınırsız ses aralığı, derin baslar, arka plan akorları ve uzun süreli döngüler!")
    
    muzik_sorgu = st.text_input("Nasıl bir şarkı yapalım?", placeholder="Örn: Kulüpte çalan çok sert bir rap veya yağmur altında çalan yavaş, hüzünlü bir parça", key=f"ultra_muzik_{st.session_state.form_num}")
    uret_butonu = st.button("🎧 Stüdyoyu Başlat")

    if uret_butonu and muzik_sorgu:
        with st.spinner("Devasa müzik altyapısı hesaplanıyor, tüm kanallar miksleniyor..."):
            try:
                # 1. Dev Nota Sözlüğünü Oluştur (C2'den B6'ya kadar Sınırsız Aralık)
                notalar_listesi = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                notalar_sozlugu = {"-": 0.0}
                for oktav in range(2, 7):
                    for i, nota in enumerate(notalar_listesi):
                        n = (oktav - 4) * 12 + (i - 9) # A4 (440Hz) referans alınarak
                        notalar_sozlugu[f"{nota}{oktav}"] = 440.0 * (2.0 ** (n / 12.0))

                # 2. LLM'den 32 adımlık devasa bir JSON iskeleti istiyoruz
                sistem_mesaji = """Sen efsanevi bir müzik prodüktörüsün. Kullanıcının ruh haline göre tam 32 adımlık (2 tam ölçü) bir müzik kalıbı yazacaksın.
                SADECE JSON FORMATINDA YAZ.
                {
                    "tempo": 120,
                    "davul": ["K", "H", "S", "H", ... 32 adet],
                    "bas": ["C3", "-", "C3", "-", ... 32 adet],
                    "akor": ["C4", "C4", "-", "-", ... 32 adet],
                    "melodi": ["C5", "-", "Eb5", "-", ... 32 adet]
                }
                Kurallar:
                1. Davul için: K(Kick), S(Snare), H(Hihat), C(Crash Zil), -(Boşluk). Rap için çok K ve S kullan, hüzünlü için seyrek tut.
                2. Notalar için C, C#, D, D#, E, F, F#, G, G#, A, A#, B kullan. (Örn: F#4, A#3).
                3. Bas kanalı C2 ile B3 arasında derin sesler olsun.
                4. Akor (Pad) kanalı C4 ile B4 arasında dolgu sesleri olsun.
                5. Melodi kanalı C5 ile B6 arasında ön planda çalan lead olsun.
                6. Bütün listelerin uzunluğu KESİNLİKLE 32 olmalıdır!
                """
                
                response = client.chat.completions.create(
                    model=secilen_model_id,
                    messages=[
                        {"role": "system", "content": sistem_mesaji},
                        {"role": "user", "content": muzik_sorgu}
                    ],
                    temperature=0.7
                )
                
                json_str = response.choices[0].message.content.strip()
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                sarki_verisi = json.loads(json_str)
                
                # 3. Ses Motoru Ayarları
                sample_rate = 44100
                adim_suresi = (60.0 / sarki_verisi.get("tempo", 100)) / 4.0 # Her adım (16th note)
                samples_per_step = int(sample_rate * adim_suresi)
                t = np.linspace(0, adim_suresi, samples_per_step, endpoint=False)
                
                # Sentezleyici Fonksiyonları (Çok daha zengin sesler)
                def kick(): return np.sin(2 * np.pi * np.linspace(150, 40, samples_per_step) * t) * np.exp(-15 * t) * 1.5
                def snare(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-25 * t) * 0.8
                def hihat(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-60 * t) * 0.3
                def crash(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-3 * t) * 0.6
                
                def synth_bas(frekans): # Derin Testere Dişi (Sawtooth)
                    if frekans == 0.0: return np.zeros(samples_per_step)
                    return 0.8 * (2 * (t * frekans - np.floor(t * frekans + 0.5))) * np.exp(-2 * t)
                    
                def synth_akor(frekans): # Yumuşak Pad (Sinüs Karışımı)
                    if frekans == 0.0: return np.zeros(samples_per_step)
                    return 0.4 * (np.sin(2 * np.pi * frekans * t) + 0.3 * np.sin(2 * np.pi * frekans * 2 * t))
                    
                def synth_melodi(frekans): # Parlak Kare Dalga (Square)
                    if frekans == 0.0: return np.zeros(samples_per_step)
                    return 0.6 * np.sign(np.sin(2 * np.pi * frekans * t)) * np.exp(-4 * t)

                # 4. Şarkıyı Sentezleme (32 adımı 4 kez tekrarlayıp uzun parça yapıyoruz)
                ana_ses = np.array([])
                tekrar_sayisi = 4 # 32 adımı 4 kez çal = 128 adım = Uzun şarkı!
                
                davullar = sarki_verisi.get("davul", ["-"]*32)
                baslar = sarki_verisi.get("bas", ["-"]*32)
                akorlar = sarki_verisi.get("akor", ["-"]*32)
                melodiler = sarki_verisi.get("melodi", ["-"]*32)
                
                toplam_adim = 32 * tekrar_sayisi
                
                for i in range(toplam_adim):
                    katman = np.zeros(samples_per_step)
                    idx = i % 32 # 32 adımda bir başa dön
                    
                    # Güvenlik için index kontrolü
                    d = davullar[idx] if idx < len(davullar) else "-"
                    b = baslar[idx] if idx < len(baslar) else "-"
                    a = akorlar[idx] if idx < len(akorlar) else "-"
                    m = melodiler[idx] if idx < len(melodiler) else "-"
                    
                    # Davullar
                    if d == "K": katman += kick()
                    elif d == "S": katman += snare()
                    elif d == "H": katman += hihat()
                    elif d == "C": katman += crash()
                    
                    # Enstrümanlar
                    katman += synth_bas(notalar_sozlugu.get(b, 0.0))
                    katman += synth_akor(notalar_sozlugu.get(a, 0.0))
                    katman += synth_melodi(notalar_sozlugu.get(m, 0.0))
                    
                    ana_ses = np.concatenate((ana_ses, katman))
                
                # Miksi Parlat (Mastering)
                max_val = np.max(np.abs(ana_ses))
                if max_val > 0:
                    ana_ses = np.int16(ana_ses / max_val * 32767)
                else:
                    ana_ses = np.int16(ana_ses)
                
                byte_io = io.BytesIO()
                wav.write(byte_io, sample_rate, ana_ses)
                
                st.audio(byte_io.getvalue(), format='audio/wav')
                st.success(f"Devasa Müzik Altyapısı Hazır! 🎧 (Tempo: {sarki_verisi.get('tempo', 100)} BPM)")
                
                with st.expander("🛠️ Stüdyo Notalarını İncele"):
                    st.json(sarki_verisi)
                    
            except Exception as e:
                st.error(f"Sentezleyici Hatası: Melodi oluştururken küçük bir pürüz çıktı, butona tekrar bas. Detay: {e}")
