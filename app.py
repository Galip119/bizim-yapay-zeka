import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
from gtts import gTTS

# --- DOSYA OKUMA KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# =====================================================================
# 🛠️ GÖMÜLÜ DEV DSP MÜZİK MOTORU (Sentezleyici ve Sequencer)
# =====================================================================
class ColossusEngine:
    def __init__(self, sr=44100):
        self.sr = sr
        self.two_pi = 2 * np.pi

    def frekans_hesapla(self, nota_adi):
        """ Notaları (C4, D#3 vb.) frekansa (Hz) çevirir """
        notalar = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, 
                   "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
        if not nota_adi or len(nota_adi) < 2 or nota_adi == "-": return 0.0
        nota = nota_adi[:-1]
        oktav = int(nota_adi[-1])
        if nota not in notalar: return 0.0
        n = notalar[nota] + (oktav - 4) * 12
        return 440.0 * (2.0 ** (n / 12.0))

    def adsr_zarfi(self, uzunluk_sample, a=0.05, d=0.1, s=0.7, r=0.2):
        """ Sesin zamanla sönümlenmesini sağlayan ADSR zarfı """
        a_len = int(uzunluk_sample * a)
        d_len = int(uzunluk_sample * d)
        r_len = int(uzunluk_sample * r)
        s_len = uzunluk_sample - a_len - d_len - r_len
        if s_len < 0: s_len = 0
        
        attack = np.linspace(0, 1, a_len)
        decay = np.linspace(1, s, d_len)
        sustain = np.ones(s_len) * s
        release = np.linspace(s, 0, r_len)
        return np.concatenate([attack, decay, sustain, release])

    def sentezle(self, frekans, sure, dalga_tipi="sine"):
        """ Temel dalga formlarını üretir """
        t = np.linspace(0, sure, int(self.sr * sure), endpoint=False)
        if frekans == 0.0: return np.zeros_like(t)
        
        if dalga_tipi == "sine":
            dalga = np.sin(self.two_pi * frekans * t)
        elif dalga_tipi == "square":
            dalga = signal.square(self.two_pi * frekans * t)
        elif dalga_tipi == "saw":
            dalga = signal.sawtooth(self.two_pi * frekans * t)
        elif dalga_tipi == "noise":
            dalga = np.random.uniform(-1, 1, len(t))
        else:
            dalga = np.sin(self.two_pi * frekans * t)
            
        zarf = self.adsr_zarfi(len(dalga))
        return dalga * zarf * 0.5 # Ana ses seviyesini %50'de tut

    def davul_üret(self, tip, sure):
        """ Matematiksel davul (Kick, Snare, Hihat) modellemeleri """
        t = np.linspace(0, sure, int(self.sr * sure), endpoint=False)
        zarf = np.exp(-t * 15) # Hızlı sönümleme
        
        if tip == "K": # Kick (808 tarzı)
            frekans_dususu = np.linspace(150, 40, len(t))
            ses = np.sin(self.two_pi * frekans_dususu * t) * zarf
        elif tip == "S": # Snare
            noise = np.random.uniform(-1, 1, len(t))
            ton = np.sin(self.two_pi * 180 * t)
            ses = (noise * 0.7 + ton * 0.3) * np.exp(-t * 25)
        elif tip == "H": # Hi-Hat
            noise = np.random.uniform(-1, 1, len(t))
            ses = noise * np.exp(-t * 40) * 0.5
        else:
            ses = np.zeros_like(t)
        return ses

    def render(self, sarki_verisi, hedef_dakika=2):
        """ JSON dizilimini sese çeviren ana render motoru """
        tempo = sarki_verisi.get("tempo", 120)
        adim_suresi = (60.0 / tempo) / 4.0 # 16'lık nota süresi
        adim_sample = int(self.sr * adim_suresi)
        toplam_adim = 16
        dongu_sesi = np.zeros(adim_sample * toplam_adim)
        
        # Sadece bilinen kanalları işle
        for kanal, notalar in sarki_verisi.items():
            if kanal == "tempo" or kanal == "global_fx": continue
            if not isinstance(notalar, list) or len(notalar) != 16: continue
            
            kanal_sesi = np.zeros(adim_sample * toplam_adim)
            for i, v in enumerate(notalar):
                if v == "-": continue
                
                # Vuruşun başlayacağı zamanı hesapla
                baslangic = i * adim_sample
                
                # Kanal tipine göre ses üret (Davullar vs Melodiler)
                if "kick" in kanal.lower() or "snare" in kanal.lower() or "hihat" in kanal.lower():
                    # Harfleri davul tipine çevir
                    d_tip = "K" if "kick" in kanal.lower() else "S" if "snare" in kanal.lower() else "H"
                    parca = self.davul_üret(d_tip, adim_suresi * 2)
                elif "bass" in kanal.lower():
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 2, "saw")
                elif "lead" in kanal.lower() or "pluck" in kanal.lower():
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 1.5, "square")
                else: # Varsayılan (Piyano/Sine)
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 2, "sine")
                
                # Sesi kanala miksle (Taşmaları önleyerek)
                bitis = baslangic + len(parca)
                if bitis > len(kanal_sesi):
                    kanal_sesi[baslangic:] += parca[:len(kanal_sesi)-baslangic]
                else:
                    kanal_sesi[baslangic:bitis] += parca
            
            dongu_sesi += kanal_sesi

        # Döngüyü hedef dakikaya uzat
        hedef_saniye = int(hedef_dakika * 60)
        hedef_samples = hedef_saniye * self.sr
        tekrar_sayisi = int(np.ceil(hedef_samples / len(dongu_sesi)))
        
        master_ses = np.tile(dongu_sesi, tekrar_sayisi)[:hedef_samples]
        
        # Clipping (Patlama) önleme
        max_val = np.max(np.abs(master_ses))
        if max_val > 0:
            master_ses = master_ses / max_val * 0.9 # Normalize et
            
        master_ses = np.int16(master_ses * 32767)
        
        byte_io = io.BytesIO()
        wav.write(byte_io, self.sr, master_ses)
        return byte_io.getvalue()

# =====================================================================
# EYMEN-GPT: ULTIMATE MEGA STUDIO & ASİSTAN ARAYÜZÜ
# =====================================================================
st.set_page_config(layout="wide", page_title="Eymen-GPT Ultimate", initial_sidebar_state="expanded")

# --- OTURUM HAFIZASI ---
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None

# --- API ANAHTARLARI ---
try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except:
    st.error("❌ API anahtarları bulunamadı!")
    st.stop()

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

# --- YAN MENÜ ---
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
                    pdf = PdfReader(yuklenen_dosya)
                    icerik = "\n".join([sayfa.extract_text() for sayfa in pdf.pages if sayfa.extract_text()])
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
                            hucreler = [str(hucre) for hucre in satir if hucre is not None]
                            if hucreler: satirlar.append(" | ".join(hucreler))
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
# 4. MOD: MÜZİSYEN MODU (TÜMLEŞİK SÜRÜM)
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 Dahili DSP Müzik Stüdyosu")
    st.write("Yapay zekanın yazdığı notalar, kodun içindeki matematiksel osilatörler kullanılarak anında sese dönüştürülür.")
    
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        muzik_sorgu = st.text_input("Şarkıyı tarif et:", placeholder="Örn: 80s synthwave, 120 bpm, hareketli bas ve davul...")
    with col_m2:
        hedef_dk = st.number_input("Süre (Dk)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

    if st.button("🎸 Müziği Üret", use_container_width=True) and muzik_sorgu:
        with st.spinner(f"{hedef_dk} dakikalık şarkı sentezleniyor..."):
            try:
                # 1. Aşama: Yapay Zekadan Notaları Al
                sistem_mesaji = """Sen müzisyen bir yapay zekasın. 16 adımlık bir JSON dizi iskeleti kur.
                Davul vurmak için K, S, H harflerini, notalar için C3, D#4 gibi değerleri kullan.
                Örnek Format:
                {
                    "tempo": 128,
                    "kick_808": ["K","-","K","-","K","-","K","-","K","-","K","-","K","-","K","-"],
                    "bass_syn": ["C2","-","-","-","E2","-","-","-","G2","-","-","-","C2","-","-","-"]
                }
                Sadece geçerli JSON yaz."""
                
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
                    
                    # 2. Aşama: Dahili Motoru Çalıştır (Dış dosya yok, doğrudan osilatörler devrede!)
                    motor = ColossusEngine()
                    ses_dosyasi_wav = motor.render(sarki_verisi, hedef_dakika=hedef_dk)
                    
                    # 3. Aşama: MP3 çevirisiyle uğraşmadan garantili WAV oynat
                    st.audio(ses_dosyasi_wav, format='audio/wav')
                    st.success("🎵 Şarkı Başarıyla Sentezlendi!")
                    
                    st.download_button(
                        label="💾 Şarkıyı İndir (.WAV)",
                        data=ses_dosyasi_wav,
                        file_name="Eymen_Muzik_Sentez.wav",
                        mime="audio/wav",
                        use_container_width=True
                    )
                    
                    with st.expander("🛠️ Kanallar (JSON)"): st.json(sarki_verisi)
                else: st.error("Bağlantı hatası.")
            except Exception as e: st.error(f"Hata: {e}")
