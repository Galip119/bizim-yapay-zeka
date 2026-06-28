"""
EYMEN-GPT & COLOSSUS MUSIC STUDIO - ULTIMATE EDITION (V11) 
Bu arayüz, gelişmiş AI asistan özelliklerini ve 
ColossusEngine DSP Müzik Motorunu tek bir çatı altında birleştirir.
"""
import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
import datetime
import logging
import time  # <-- Eksik olan ve sistemi kilitleyen kütüphane eklendi!
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
import soundfile as sf
import subprocess
from gtts import gTTS

# --- DOSYA OKUMA KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# =====================================================================
# 1. SİSTEM LOGLAMA VE AYARLARI
# =====================================================================
st.set_page_config(
    page_title="Colossus Ultimate Studio", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS Tasarımı
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .main-title { color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 30px; }
    .log-box { background-color: #1e1e1e; padding: 15px; border-radius: 8px; height: 350px; overflow-y: auto; color: #00ff00; font-family: 'Courier New', Courier, monospace; border: 1px solid #333; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

class StreamlitLogHandler(logging.Handler):
    """Logları Streamlit arayüzüne aktarmak için özel işleyici."""
    def emit(self, record):
        log_entry = self.format(record)
        if "logs" in st.session_state:
            st.session_state.logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {log_entry}")

if "logs" not in st.session_state:
    st.session_state.logs = []
    handler = StreamlitLogHandler()
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

# =====================================================================
# 2. DOSYA İŞLEYİCİ SINIFI (OOP Tasarım)
# =====================================================================
class DocumentProcessor:
    """Yüklenen farklı formattaki dosyaları metne çeviren yardımcı sınıf."""
    
    @staticmethod
    def process(file) -> str:
        name = file.name.lower()
        content = ""
        try:
            if name.endswith((".txt", ".py", ".xml", ".md", ".csv")): 
                content = file.read().decode("utf-8")
            elif name.endswith(".pdf"):
                pdf = PdfReader(file)
                content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            elif name.endswith(".docx"):
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            elif name.endswith(".xlsx"):
                wb = openpyxl.load_workbook(file, data_only=True)
                rows = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    rows.append(f"--- Sayfa: {sheet} ---")
                    for row in ws.iter_rows(values_only=True):
                        cells = [str(c) for c in row if c is not None]
                        if cells: rows.append(" | ".join(cells))
                content = "\n".join(rows)
            elif name.endswith((".html", ".htm")):
                soup = BeautifulSoup(file.read().decode("utf-8"), "html.parser")
                content = soup.get_text(separator="\n", strip=True)
            elif name.endswith(".json"):
                content = json.dumps(json.load(file), indent=2, ensure_ascii=False)
            elif name.endswith((".png", ".jpg", ".jpeg")):
                st.image(file, width=300, caption="Yüklenen Görsel")
                try: 
                    content = pytesseract.image_to_string(Image.open(file), lang="tur+eng")
                except Exception as e: 
                    logging.warning(f"OCR Başarısız: {e}")
                    content = "Görsel okunamadı. Tesseract kurulu olmayabilir."
            return content
        except Exception as e:
            logging.error(f"Dosya işleme hatası ({name}): {e}")
            raise Exception(f"Dosya okunamadı: {e}")

# =====================================================================
# 3. GÖMÜLÜ DSP MÜZİK MOTORU (ColossusEngine v2)
# =====================================================================
class ColossusEngine:
    """Numpy tabanlı matematiksel sinyal işleme ve müzik sentezleme motoru."""
    
    def __init__(self, sr=44100):
        self.sr = sr
        self.two_pi = 2 * np.pi
        self.stats = {"total_renders": 0, "start_time": time.time()}
        logging.info("ColossusEngine v2.0 Başlatıldı.")

    def get_version_info(self):
        return {"version": "v2.0 Pro", "build": "2026.06", "author": "Eymen-GPT"}
        
    def validate_system_health(self):
        uptime = time.time() - self.stats["start_time"]
        return {
            "system_status": "OK",
            "uptime_seconds": uptime,
            "modules_loaded": ["Oscillators", "Envelopes", "Drums", "FX_Chain", "Sequencer"]
        }

    def frekans_hesapla(self, nota_adi):
        """Müzikal nota adını (örn: C4, D#3) Hertz (Hz) cinsinden frekansa çevirir."""
        notalar = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, 
                   "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
        if not nota_adi or len(nota_adi) < 2 or nota_adi == "-": return 0.0
        nota = nota_adi[:-1]
        oktav = int(nota_adi[-1])
        if nota not in notalar: return 0.0
        n = notalar[nota] + (oktav - 4) * 12
        return 440.0 * (2.0 ** (n / 12.0))

    def adsr_zarfi(self, uzunluk_sample, a=0.05, d=0.1, s=0.7, r=0.2):
        """Sese dinamik kazandırmak için Attack, Decay, Sustain, Release zarfı oluşturur."""
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
        """Belirli bir dalga formunda (Sine, Square, Saw) ses sentezler."""
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
        return dalga * zarf * 0.5 

    def davul_üret(self, tip, sure):
        """Kik (K), Snare (S) ve Hi-Hat (H) gibi perküsyon seslerini matematiksel olarak üretir."""
        t = np.linspace(0, sure, int(self.sr * sure), endpoint=False)
        zarf = np.exp(-t * 15)
        
        if tip == "K": 
            frekans_dususu = np.linspace(150, 40, len(t))
            ses = np.sin(self.two_pi * frekans_dususu * t) * zarf
        elif tip == "S": 
            noise = np.random.uniform(-1, 1, len(t))
            ton = np.sin(self.two_pi * 180 * t)
            ses = (noise * 0.7 + ton * 0.3) * np.exp(-t * 25)
        elif tip == "H": 
            noise = np.random.uniform(-1, 1, len(t))
            ses = noise * np.exp(-t * 40) * 0.5
        else:
            ses = np.zeros_like(t)
        return ses

    def apply_delay(self, audio, delay_ms=300, feedback=0.4):
        """Sese yankı (Delay) efekti ekler."""
        delay_samples = int(self.sr * (delay_ms / 1000.0))
        out_audio = np.copy(audio)
        if delay_samples < len(audio):
            for i in range(delay_samples, len(audio)):
                out_audio[i] += out_audio[i - delay_samples] * feedback
        return out_audio

    def render_composition(self, sarki_verisi, hedef_dakika=1.0, master_volume=0.8, fx_chain=None):
        """JSON formatındaki notaları tam bir şarkıya dönüştürür (Sequencer & Mixer)."""
        logging.info("Render işlemi başlatıldı.")
        self.stats["total_renders"] += 1
        
        tempo = sarki_verisi.get("tempo", 120)
        adim_suresi = (60.0 / tempo) / 4.0 
        adim_sample = int(self.sr * adim_suresi)
        toplam_adim = 16
        dongu_sesi = np.zeros(adim_sample * toplam_adim)
        
        # Kanalları İşle
        for kanal, notalar in sarki_verisi.items():
            if kanal in ["tempo", "global_fx"]: continue
            if not isinstance(notalar, list) or len(notalar) != 16: continue
            
            kanal_sesi = np.zeros(adim_sample * toplam_adim)
            for i, v in enumerate(notalar):
                if v == "-": continue
                
                baslangic = i * adim_sample
                
                # Enstrüman Tespiti
                if "kick" in kanal.lower() or "snare" in kanal.lower() or "hihat" in kanal.lower() or "drum" in kanal.lower():
                    d_tip = "K" if "kick" in kanal.lower() else "S" if "snare" in kanal.lower() else "H"
                    parca = self.davul_üret(d_tip, adim_suresi * 2)
                elif "bass" in kanal.lower():
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 2, "saw")
                elif "lead" in kanal.lower() or "pluck" in kanal.lower():
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 1.5, "square")
                else: 
                    frekans = self.frekans_hesapla(v)
                    parca = self.sentezle(frekans, adim_suresi * 2, "sine")
                
                bitis = baslangic + len(parca)
                if bitis > len(kanal_sesi):
                    kanal_sesi[baslangic:] += parca[:len(kanal_sesi)-baslangic]
                else:
                    kanal_sesi[baslangic:bitis] += parca
            
            dongu_sesi += kanal_sesi

        # Efekt Zinciri (FX Chain)
        if fx_chain and "Delay" in fx_chain:
            logging.info("Delay efekti uygulanıyor...")
            dongu_sesi = self.apply_delay(dongu_sesi, delay_ms=400, feedback=0.3)

        # Şarkıyı Hedef Süreye Kadar Tekrarla (Looping)
        hedef_saniye = int(hedef_dakika * 60)
        hedef_samples = hedef_saniye * self.sr
        tekrar_sayisi = int(np.ceil(hedef_samples / len(dongu_sesi)))
        master_ses = np.tile(dongu_sesi, tekrar_sayisi)[:hedef_samples]
        
        # Mastering (Normalize & Gain)
        max_val = np.max(np.abs(master_ses))
        if max_val > 0:
            master_ses = master_ses / max_val * master_volume 
            
        logging.info("Render başarıyla tamamlandı.")
        return np.int16(master_ses * 32767)

# Motoru Başlat (Cache ile performansı koru)
@st.cache_resource
def get_engine():
    return ColossusEngine()

engine = get_engine()

# =====================================================================
# 4. DURUM (STATE) YÖNETİMİ
# =====================================================================
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None
if "current_audio" not in st.session_state: st.session_state.current_audio = None
if "render_count" not in st.session_state: st.session_state.render_count = 0

# =====================================================================
# 5. API ANAHTARLARI VE İSTEMCİ KURULUMU
# =====================================================================
try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except KeyError:
    st.error("❌ API anahtarları bulunamadı! Lütfen '.streamlit/secrets.toml' dosyasını kontrol et.")
    st.stop()

# LLM İstemcisi
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
# Arama İstemcisi
tavily = TavilyClient(api_key=tavily_key)

MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

# =====================================================================
# 6. YAN MENÜ (SIDEBAR) & NAVİGASYON
# =====================================================================
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    uygulama_modu = st.radio("Sistem Modunu Seçin:", [
        "Sohbet & Analiz 💬", 
        "Ressam Modu 🎨", 
        "Sesli Yanıt 🗣️", 
        "Colossus Studio 🎹"
    ])

    st.markdown("---")
    secilen_model_adi = st.selectbox("LLM Modeli:", list(MODELS.keys()))
    secilen_model_id = MODELS[secilen_model_adi]

    if st.button("🧹 Sistemi Temizle", use_container_width=True):
        st.session_state.mesaj_gecmisi = []
        st.session_state.dosya_bellegi = ""
        st.session_state.resim_hazir = False
        st.session_state.sesli_metin_hazir = False
        st.session_state.current_audio = None
        st.session_state.logs = []
        logging.info("Sistem belleği temizlendi.")
        st.rerun()
        
    st.markdown("---")
    st.caption("Colossus Engine © 2026")
    st.caption(f"Sistem Durumu: Çevrimiçi")

# Ana Başlık
st.markdown("<h1 class='main-title'>Eymen-Gpt (Eymex Nexus-Core) 🚀</h1>", unsafe_allow_html=True)

# =====================================================================
# MOD 1: SOHBET VE VERİ ANALİZİ
# =====================================================================
if uygulama_modu == "Sohbet & Analiz 💬":
    st.markdown("### 📚 Akıllı Veri Asistanı")
    yuklenen_dosya = st.file_uploader("Bir belge veya görsel yükleyin", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg", "csv", "md"])

    if yuklenen_dosya is not None:
        with st.spinner("Dosya analiz ediliyor..."):
            try:
                icerik = DocumentProcessor.process(yuklenen_dosya)
                if icerik:
                    st.session_state.dosya_bellegi = icerik
                    st.success(f"📎 {yuklenen_dosya.name} başarıyla hafızaya alındı!")
                    logging.info(f"Dosya yüklendi: {yuklenen_dosya.name}")
            except Exception as e:
                st.error(str(e))

    # Mesaj Geçmişini Göster
    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]): 
            st.markdown(mesaj["content"])

    # Yeni Sorgu
    if sorgu := st.chat_input("Bana bir soru sor veya analiz iste..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"): 
            st.markdown(sorgu)

        with st.spinner("Eymex Nexus-Core (Eymen-Gpt) düşünüyor..."):
            try:
                # İnternet Araması Entegrasyonu
                arama_metni = ""
                try:
                    res = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([r["content"] for r in res["results"]])
                except Exception as e: 
                    logging.warning(f"Arama yapılamadı: {e}")
                
                # Prompt Hazırlığı
                sistem_mesaji = """Sen, fütüristik teknoloji markası 'Eymex Nexus' çatısı altında, kurucu yazılımcı Galip Eymen Demircioğlu tarafından özel olarak geliştirilmiş 'Eymex Nexus - Core' adında gelişmiş bir yapay zeka modelisin. Kullanıcı sana adını, kim olduğunu veya seni kimin yaptığını sorduğunda her zaman: 'Ben, Galip Eymen Demircioğlu tarafından Eymex Nexus markası altında geliştirilen Eymex Nexus - Core yapay zeka modeliyim.' şeklinde net, kurumsal ve profesyonel bir yanıt vermelisin. Akıl yürütmeni her zaman <dusunce> etiketi içine yaz, sonra cevabı net bir şekilde ver."""
                
                k_msg = f"Kullanıcının Sorusu: {sorgu}\n"

                if arama_metni: k_msg += f"İNTERNET KAYNAKLARI: {arama_metni}\n"
                if st.session_state.dosya_bellegi: k_msg += f"YÜKLENEN DOSYA İÇERİĞİ: {st.session_state.dosya_bellegi[:25000]}\n"

                msgs = [{"role": "system", "content": sistem_mesaji}] + st.session_state.mesaj_gecmisi[:-1] + [{"role": "user", "content": k_msg}]

                # LLM Çağrısı (Yedek modellerle)
                basarili = False
                for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                    try:
                        response = client.chat.completions.create(messages=msgs, model=model_id, temperature=0.7)
                        basarili = True
                        break
                    except Exception as e: 
                        logging.warning(f"Model {model_id} başarısız: {e}")
                        continue

                if basarili:
                    cevap = response.choices[0].message.content
                    d_blog = ""
                    # Düşünce bloklarını ayrıştır
                    m = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', cevap, re.DOTALL | re.IGNORECASE)
                    if m:
                        d_blog = m.group(1).strip()
                        cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
                    with st.chat_message("assistant"):
                        if d_blog:
                            with st.expander("🤔 Eymen Nexus-Core Ne Düşündü?"): st.write(d_blog)
                        st.markdown(cevap)
                else: 
                    st.error("Tüm modeller çöktü. Lütfen tekrar deneyin.")
            except Exception as e: 
                st.error(f"Beklenmeyen Hata: {e}")

# =====================================================================
# MOD 2: RESSAM MODU (Metinden Görsele)
# =====================================================================
elif uygulama_modu == "Ressam Modu 🎨":
    st.markdown("### 🎨 AI Görsel Oluşturucu")
    st.write("Hayalindeki resmi detaylıca tarif et, yapay zeka senin için anında çizsin.")
    
    resim_sorgu = st.text_input("Görsel Açıklaması (Prompt):", placeholder="Örn: Siberpunk bir şehirde yağmur altında yürüyen robot dedektif...")
    if st.button("🖼️ Görseli Üret", use_container_width=True) and resim_sorgu:
        with st.spinner("Tuval hazırlanıyor, boyalar karıştırılıyor..."):
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(resim_sorgu)}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
            logging.info(f"Görsel üretildi: {resim_sorgu}")
            
    if st.session_state.resim_hazir:
        st.image(st.session_state.son_resim_url, use_container_width=True, caption="Oluşturulan Şaheser")

# =====================================================================
# MOD 3: SESLİ YANIT (TTS)
# =====================================================================
elif uygulama_modu == "Sesli Yanıt 🗣️":
    st.markdown("### 🗣️ Metin Seslendirme Motoru")
    sesli_sorgu = st.text_area("Seslendirilmesini istediğiniz metni buraya yazın:", height=150)
    
    if st.button("🎙️ Seslendir", use_container_width=True) and sesli_sorgu:
        with st.spinner("Stüdyoda ses kaydı alınıyor..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr', slow=False)
                ses_bellek = io.BytesIO()
                tts.write_to_fp(ses_bellek)
                ses_bellek.seek(0)
                st.session_state.son_ses_bytes = ses_bellek.getvalue()
                st.session_state.sesli_metin_hazir = True
                logging.info("Metin başarıyla sese çevrildi.")
            except Exception as e: 
                st.error(f"Ses dönüştürme hatası: {e}")
                logging.error(f"TTS Hatası: {e}")
            
    if st.session_state.sesli_metin_hazir:
        st.success("Ses başarıyla oluşturuldu!")
        st.audio(st.session_state.son_ses_bytes, format='audio/mp3')
        st.download_button(
            label="💾 MP3 Olarak İndir", 
            data=st.session_state.son_ses_bytes, 
            file_name="Eymen_Sentezlenen_Ses.mp3", 
            mime="audio/mp3", 
            use_container_width=True
        )

# =====================================================================
# MOD 4: COLOSSUS PRO STUDIO (Müzik Sentezleyici)
# =====================================================================
elif uygulama_modu == "Colossus Studio 🎹":
    # 4 Alt Sekme Tasarımı
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎚️ AI Studio", "📚 Kütüphane & Ayarlar", "📋 Log Konsolu"])

    # --- SEKME 1: DASHBOARD ---
    with tab1:
        st.markdown("### 🎛️ Colossus DSP Motoru Durumu")
        st.info("ColossusEngine v2 aktif ve hizmete hazır. Sistem verileri aşağıda listelenmiştir.")
        status = engine.validate_system_health()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Render Sayısı", engine.stats["total_renders"])
        col2.metric("Sistem Uptime", f"{int(status['uptime_seconds'])} Saniye")
        col3.metric("Motor Sağlığı", status['system_status'])
        
        st.write("Yüklenen DSP Modülleri:", ", ".join(status['modules_loaded']))

    # --- SEKME 2: AI STUDIO (Besteleme) ---
    with tab2:
        st.markdown("### 🎹 Yapay Zeka Destekli Besteci")
        istek = st.text_area("Şarkı fikrini tarif et:", placeholder="Örn: 120 bpm hızında, synth bass ve 808 davulları olan siberpunk bir beat...")
        
        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            hedef_dk = st.number_input("Süre (Dakika)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
        with col_m2:
            master_vol = st.slider("Master Ses Seviyesi (Gain)", 0.1, 1.0, 0.8)

        # Aktif Efektleri Al
        aktif_fx = st.session_state.get("aktif_fx", ["Delay"])

        if st.button("🚀 Müziği Bestele ve Sentezle", use_container_width=True) and istek:
            with st.spinner("AI Notaları yazıyor ve DSP motoru sesi sentezliyor..."):
                try:
                    # 1. Aşama: Yapay Zekadan JSON Notalarını Al
                    sistem_mesaji = """Sen uzman bir yapay zeka müzisyenisin. 16 adımlık bir sequencer için JSON formatında nota iskeleti kur.
                    Davul için: K (Kick), S (Snare), H (Hi-hat)
                    Notalar için: C3, D#4, vb.
                    Format: { "tempo": 120, "kick": ["K","-","K","-","K","-","K","-","K","-","K","-","K","-","K","-"], "bass": ["C2","-","-","-","E2","-","-","-","G2","-","-","-","C2","-","-","-"] }
                    SADECE JSON YAZ."""
                    
                    basarili = False
                    for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                        try:
                            response = client.chat.completions.create(
                                messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": istek}],
                                model=model_id, temperature=0.7
                            )
                            basarili = True
                            break
                        except Exception as e: 
                            logging.warning(f"Müzik yapay zekası {model_id} çöktü: {e}")
                            continue

                    if basarili:
                        json_str = response.choices[0].message.content.strip()
                        m = re.search(r'\{.*\}', json_str, re.DOTALL)
                        if m: json_str = m.group(0)
                        sarki_verisi = json.loads(json_str)
                        logging.info("JSON Notaları başarıyla çekildi.")
                        
                        # 2. Aşama: ColossusEngine'de Render
                        ses_verisi = engine.render_composition(
                            sarki_verisi, 
                            hedef_dakika=hedef_dk, 
                            master_volume=master_vol,
                            fx_chain=aktif_fx
                        )
                        
                        # 3. Aşama: WAV Dosyasına Çevirme
                        byte_io = io.BytesIO()
                        wav.write(byte_io, engine.sr, ses_verisi)
                        ses_bytes = byte_io.getvalue()
                        st.session_state.current_audio = ses_bytes
                        st.session_state.render_count += 1
                        
                        st.success("🎵 Şarkı Başarıyla Sentezlendi!")
                        st.audio(ses_bytes, format='audio/wav')
                        
                        # MP3 Dönüştürme Denemesi (İsteğe Bağlı)
                        try:
                            proc = subprocess.run(['ffmpeg', '-i', 'pipe:0', '-f', 'mp3', '-b:a', '192k', 'pipe:1'],
                                                  input=ses_bytes, capture_output=True, check=True)
                            st.download_button(label="💾 Şarkıyı İndir (.MP3)", data=proc.stdout, file_name=f"Colossus_Beste_{st.session_state.render_count}.mp3", mime="audio/mp3", use_container_width=True)
                        except:
                            st.download_button(label="💾 Şarkıyı İndir (.WAV)", data=ses_bytes, file_name=f"Colossus_Beste_{st.session_state.render_count}.wav", mime="audio/wav", use_container_width=True)
                        
                        with st.expander("🛠️ Yazılan Notalar (JSON)"): 
                            st.json(sarki_verisi)
                    else: 
                        st.error("Model bağlantı hatası.")
                except Exception as e: 
                    st.error(f"Render sırasında hata oluştu: {e}")
                    logging.error(f"Studio Error: {e}")

    # --- SEKME 3: KÜTÜPHANE VE AYARLAR ---
    with tab3:
        st.markdown("### 📚 Stüdyo Enstrüman ve Efekt Ayarları")
        c1, c2 = st.columns(2)
        with c1:
            st.write("#### 🎹 Aktif Sentezleyiciler")
            st.checkbox("Sine Wave (Klasik Lead)", value=True, disabled=True)
            st.checkbox("Sawtooth Wave (Agresif Bass)", value=True, disabled=True)
            st.checkbox("Square Wave (Retro Pluck)", value=True, disabled=True)
            st.checkbox("Drum Machine (K/S/H)", value=True, disabled=True)
            st.caption("Not: Bu dalga formları ColossusEngine içinde gömülü olarak aktiftir.")
            
        with c2:
            st.write("#### 🎛️ Master Efekt Zinciri (FX)")
            st.session_state.aktif_fx = st.multiselect(
                "Uygulanacak efektleri seçin:", 
                ["Delay", "Reverb", "Compressor"], 
                default=["Delay"]
            )
            st.caption("Reverb ve Compressor özellikleri gelecek güncellemelerde eklenecektir.")

    # --- SEKME 4: LOG KONSOLU ---
    with tab4:
        st.markdown("### 📋 Sistem Logları (Real-Time)")
        if st.button("🗑️ Logları Temizle"):
            st.session_state.logs = []
            st.rerun()
            
        log_area = st.empty()
        with log_area.container():
            st.markdown("<div class='log-box'>", unsafe_allow_html=True)
            for log in st.session_state.logs:
                st.text(log)
            st.markdown("</div>", unsafe_allow_html=True)

