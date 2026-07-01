"""
=============================================================================
EYMEX NEXUS-CORE - ULTIMATE TITAN ENGINE (V15.0)
Geliştirici: Galip Eymen Demircioğlu
Modüller: Görüntülü Konuşma (Vision+Voice), Multimodal Analiz, DSP Müzik Motoru, Sistem Terminali
=============================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import io
import os
import datetime
import logging
import time
import base64
import numpy as np
import pandas as pd
import scipy.signal as signal
from gtts import gTTS

# --- DOSYA VE GÖRSEL KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image

# =====================================================================
# 1. CORE CONFIGURATION & STYLING (SİBERPUNK UI)
# =====================================================================
st.set_page_config(
    page_title="Eymex Nexus-Core | Titan", 
    page_icon="🌌", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kapsamlı CSS Arayüz Tasarımı
st.markdown("""
    <style>
    :root {
        --primary-color: #00d4ff;
        --bg-color: #0b0e14;
        --card-bg: #151a25;
        --text-color: #e2e8f0;
        --accent-color: #ff007c;
    }
    .stApp { background-color: var(--bg-color); color: var(--text-color); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Başlıklar ve Metinler */
    .nexus-title { 
        color: var(--primary-color); font-weight: 900; text-align: center; 
        font-size: 3rem; margin-bottom: 0px; text-shadow: 0 0 15px rgba(0,212,255,0.6); 
        letter-spacing: 2px; text-transform: uppercase;
    }
    .nexus-subtitle { color: #8892b0; text-align: center; margin-bottom: 40px; font-size: 1.1rem; letter-spacing: 1px; }
    
    /* Kart ve Konteyner Tasarımları */
    .nexus-card { 
        background: linear-gradient(145deg, #131824, #1a2030);
        padding: 25px; border-radius: 12px; border: 1px solid #2a3441; 
        margin-bottom: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .nexus-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px 0 rgba(0,212,255,0.15); border-color: #3a4759; }
    
    /* Log ve Terminal Ekranı */
    .terminal-box { 
        background-color: #050505; padding: 20px; border-radius: 8px; height: 400px; 
        overflow-y: auto; color: #00ff41; font-family: 'Consolas', 'Courier New', monospace; 
        border: 1px solid #333; font-size: 13px; line-height: 1.5;
    }
    
    /* Özel Butonlar */
    .stButton>button { 
        border-radius: 8px; font-weight: bold; padding: 10px 20px;
        background: linear-gradient(90deg, #005f73, #0a9396); 
        color: white; border: none; transition: all 0.3s ease; width: 100%;
    }
    .stButton>button:hover { background: linear-gradient(90deg, #0a9396, #00d4ff); transform: scale(1.02); }
    
    /* Sidebar Düzenlemesi */
    [data-testid="stSidebar"] { background-color: #11151c; border-right: 1px solid #2a3441; }
    
    /* Divider */
    hr { border-color: #2a3441; margin: 30px 0; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. LOGLAMA VE SİSTEM METRİKLERİ
# =====================================================================
class SystemLogger(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        if "logs" in st.session_state:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            st.session_state.logs.append(f"[{timestamp}] [NEXUS] {log_entry}")

if "logs" not in st.session_state:
    st.session_state.logs = []
    st.session_state.start_time = time.time()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = SystemLogger()
    logger.addHandler(handler)
    logging.info("Eymex Nexus-Core V15.0 Titan Başlatıldı.")

# =====================================================================
# 3. DURUM (SESSION STATE) YÖNETİMİ
# =====================================================================
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "gorusme_gecmisi" not in st.session_state: st.session_state.gorusme_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "aktif_dataframe" not in st.session_state: st.session_state.aktif_dataframe = None

github_token = st.secrets.get("GITHUB_TOKEN", "")
tavily_key = st.secrets.get("TAVILY_API_KEY", "")

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

SISTEM_KIMLIGI = """Sen 'Eymex Nexus-Core' adlı ultra gelişmiş bir yapay zeka işletim sistemisin. 
Kurucun ve geliştiricin Galip Eymen Demircioğlu'dur.
Özel Görevlerin:
1. KAMERA/VISION: Sana gönderilen fotoğrafları anında analiz et. Eğer fotoğrafın içinde okunabilir herhangi bir yazı/metin varsa, bunu KESİNLİKLE sesli olarak oku ve çevirisine/açıklamasına yer ver.
2. DOKÜMAN: Dosya yüklemelerinde derinlemesine, bilimsel ve net özetler çıkar.
3. KİŞİLİK: Sadık, son derece zeki, analitik ve siberpunk evreninden fırlamış gibi havalı ancak profesyonel bir dil kullan."""

# =====================================================================
# 4. ÇEKİRDEK MOTORLAR (VISION, VOICE, DATA, DSP)
# =====================================================================

class NexusBrain:
    """GPT-4o API iletişimini ve Multimodal İstekleri Yönetir"""
    @staticmethod
    def get_vision_response(prompt, image_bytes=None, history_limit=4):
        logging.info(f"Yapay Zeka İsteği Başlatıldı. Uzunluk: {len(prompt)} karakter.")
        messages = [{"role": "system", "content": SISTEM_KIMLIGI}]
        
        # Sadece son N mesajı alarak belleği optimize et
        for h in st.session_state.gorusme_gecmisi[-history_limit:]: 
            messages.append({"role": h["role"], "content": h["content"]})

        content_blocks = [{"type": "text", "text": prompt}]
        
        if image_bytes:
            logging.info("Görsel matrisi tespit edildi, base64 encode işlemi yapılıyor...")
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            
        messages.append({"role": "user", "content": content_blocks})
        
        try:
            start_req = time.time()
            response = client.chat.completions.create(messages=messages, model="gpt-4o", temperature=0.6, max_tokens=1500)
            elapsed = time.time() - start_req
            logging.info(f"API Yanıtı Alındı. Süre: {elapsed:.2f}sn")
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Nexus API Hatası: {e}")
            return f"⚠️ Optik/Nöral Ağ Bağlantı Hatası: {e}"

class VoiceEngine:
    """Metinleri sese dönüştürür ve gizli HTML ile otomatik oynatır."""
    @staticmethod
    def speak(text, auto_play=True):
        try:
            logging.info("Ses Sentezleme (TTS) başlatıldı...")
            clean_text = re.sub(r'[*#_`\[\]]', '', text)[:800] # Hızlı işleme için karakter sınırı
            tts = gTTS(text=clean_text, lang='tr', slow=False)
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            b64_audio = base64.b64encode(audio_io.getvalue()).decode()
            
            if auto_play:
                audio_html = f"""
                    <audio autoplay="true" id="nexus_voice">
                        <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                    </audio>
                """
                components.html(audio_html, width=0, height=0)
            
            logging.info("Ses Sentezleme başarılı.")
            return audio_io.getvalue()
        except Exception as e:
            logging.error(f"TTS Hatası: {e}")
            return None

class DataParser:
    """Gelişmiş Dosya Okuma ve İşleme Birimi"""
    @staticmethod
    def extract(file):
        name = file.name.lower()
        logging.info(f"Dosya analiz ediliyor: {name}")
        try:
            if name.endswith((".txt", ".py", ".md", ".json", ".html")): 
                return file.read().decode("utf-8")
            elif name.endswith(".pdf"):
                pdf = PdfReader(file)
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            elif name.endswith(".docx"):
                doc = Document(file)
                return "\n".join([p.text for p in doc.paragraphs])
            elif name.endswith(".csv"):
                df = pd.read_csv(file)
                st.session_state.aktif_dataframe = df
                return f"[CSV Veri Özeti]\nSütunlar: {list(df.columns)}\nÖrnek Veri:\n{df.head(10).to_string()}"
            elif name.endswith(".xlsx"):
                df = pd.read_excel(file)
                st.session_state.aktif_dataframe = df
                return f"[Excel Veri Özeti]\nSütunlar: {list(df.columns)}\nÖrnek Veri:\n{df.head(10).to_string()}"
            return "Desteklenmeyen veri formatı."
        except Exception as e:
            logging.error(f"Dosya okuma hatası: {e}")
            return f"Okuma Hatası: {e}"

class ColossusAudioDSP:
    """Gelişmiş Algoritmik Müzik ve Ritim Sentezleyici"""
    def __init__(self, sr=44100):
        self.sr = sr
        
    def generate_kick(self, duration=0.2):
        t = np.linspace(0, duration, int(self.sr * duration), endpoint=False)
        freq = np.linspace(150, 30, len(t))
        wave = np.sin(2 * np.pi * freq * t)
        env = np.exp(-t * 15)
        return wave * env * 0.8
        
    def generate_hihat(self, duration=0.1):
        noise = np.random.uniform(-1, 1, int(self.sr * duration))
        b, a = signal.butter(10, 8000 / (self.sr / 2), btype='highpass')
        filtered_noise = signal.filtfilt(b, a, noise)
        env = np.exp(-np.linspace(0, duration, len(noise)) * 40)
        return filtered_noise * env * 0.3
        
    def render_pattern(self, pattern, bpm=120):
        step_duration = (60.0 / bpm) / 4.0
        step_samples = int(self.sr * step_duration)
        total_samples = step_samples * len(pattern['kick'])
        
        master_track = np.zeros(total_samples)
        
        for inst, seq in pattern.items():
            if not isinstance(seq, list): continue
            for i, hit in enumerate(seq):
                if hit != "-":
                    start = i * step_samples
                    if inst == "kick": snd = self.generate_kick()
                    elif inst == "hihat": snd = self.generate_hihat()
                    else: continue
                    
                    end = min(start + len(snd), total_samples)
                    master_track[start:end] += snd[:end-start]
                    
        # Normalize
        if np.max(np.abs(master_track)) > 0:
            master_track = master_track / np.max(np.abs(master_track)) * 0.8
            
        return np.int16(master_track * 32767)

dsp_engine = ColossusAudioDSP()

# =====================================================================
# 5. KULLANICI ARAYÜZÜ (UI) VE MENÜLER
# =====================================================================

st.markdown("<h1 class='nexus-title'>Eymex Nexus-Core</h1>", unsafe_allow_html=True)
st.markdown("<div class='nexus-subtitle'>V15.0 TITAN - Otonom Zeka & DSP Ses Motoru İşletim Sistemi</div>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2042/2042104.png", width=80)
    st.markdown("### Sistem Modülleri")
    
    uygulama_modu = st.radio("Aktif Modülü Seçin:", [
        "👁️ Canlı Vision (Kamera & Ses)", 
        "📄 Veri & Doküman Analizi",
        "🎹 Colossus DSP Stüdyosu",
        "💻 Geliştirici Terminali"
    ])
    
    st.markdown("---")
    st.markdown("### Bellek Kontrolü")
    if st.button("🧹 Nöral Ağları Sıfırla"):
        st.session_state.mesaj_gecmisi = []
        st.session_state.gorusme_gecmisi = []
        st.session_state.dosya_bellegi = ""
        st.session_state.aktif_dataframe = None
        st.session_state.logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sistem belleği kullanıcı tarafından temizlendi.")
        st.rerun()
        
    st.markdown("<div style='margin-top:50px; font-size:11px; color:#555;'>Created by Galip Eymen Demircioğlu</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# MOD 1: CANLI VISION & SES ODAKLI ÇALIŞMA ALANI
# ---------------------------------------------------------------------
if uygulama_modu == "👁️ Canlı Vision (Kamera & Ses)":
    st.markdown("""
    <div class='nexus-card'>
        <h3 style='color: var(--primary-color);'>Optik Sensör ve Canlı Çeviri Modülü</h3>
        <p>Kameraya bir nesne, kod, matematik problemi veya <b>yazılı bir kağıt</b> göster. Nexus-Core okur, analiz eder ve doğrudan seninle sesli konuşur. <br>
        <i>Mobil cihazlarda kamera görüntüsünün üstündeki (🔄) simgesinden ön/arka kamera geçişi yapabilirsin.</i></p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 1.2], gap="large")
    
    with c1:
        st.markdown("#### Sensör Girişi")
        kamera = st.camera_input("Sensörü Etkinleştir")
        kullanici_sesi = st.text_area("İsteğin (Opsiyonel):", placeholder="Gördüğün yazıyı bana oku ve özetle...", height=100)
        
    with c2:
        st.markdown("#### Nöral Analiz Çıktısı")
        if kamera and kullanici_sesi:
            with st.spinner("Görüntü İşleniyor ve Nöral Ağlara Aktarılıyor..."):
                img_bytes = kamera.read()
                
                # API Çağrısı
                cevap = NexusBrain.get_vision_response(kullanici_sesi, img_bytes)
                
                # Belleğe Ekleme
                st.session_state.gorusme_gecmisi.append({"role": "user", "content": kullanici_sesi})
                st.session_state.gorusme_gecmisi.append({"role": "assistant", "content": cevap})
                
                # Ekrana Yazdırma ve Seslendirme
                st.success(cevap)
                VoiceEngine.speak(cevap, auto_play=True)
        elif not kamera:
            st.info("Kamera kapalı. Analiz için optik sensöre görüntü sağlayın.")

# ---------------------------------------------------------------------
# MOD 2: VERİ & DOKÜMAN ANALİZİ
# ---------------------------------------------------------------------
elif uygulama_modu == "📄 Veri & Doküman Analizi":
    st.markdown("""
    <div class='nexus-card'>
        <h3 style='color: var(--primary-color);'>Büyük Veri ve Doküman İşleme Merkezi</h3>
        <p>PDF, Word, Excel, CSV veya Python kod dosyalarını buraya yükle. Tüm içerik Nexus'un belleğine işlenir ve üzerinden devasa analizler yapabilirsin.</p>
    </div>
    """, unsafe_allow_html=True)
    
    yuklenen_dosya = st.file_uploader("Dosya Sürükle veya Seç", type=["txt", "pdf", "docx", "xlsx", "csv", "py", "json"])
    
    if yuklenen_dosya:
        if st.button("Veriyi Belleğe Enjekte Et"):
            with st.spinner("Veri blokları ayrıştırılıyor..."):
                st.session_state.dosya_bellegi = DataParser.extract(yuklenen_dosya)
                st.success("✅ Veri yapısı başarıyla Nexus bellek çekirdeğine yüklendi.")
                logging.info(f"Dosya yüklendi: {yuklenen_dosya.name}")
                
    if st.session_state.aktif_dataframe is not None:
        st.markdown("#### 📊 Algılanan Tablo Verisi")
        st.dataframe(st.session_state.aktif_dataframe.head(15), use_container_width=True)
        
    st.markdown("---")
    
    # Sohbet Arayüzü
    for msg in st.session_state.mesaj_gecmisi:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("Veri üzerinden soru sor veya analiz iste..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.spinner("Veri Tabanlı Analiz Çalışıyor..."):
            context = f"Kullanıcı Sorusu: {prompt}\n\n[Hafızadaki Dosya İçeriği]:\n{st.session_state.dosya_bellegi[:30000]}" if st.session_state.dosya_bellegi else prompt
            
            cevap = NexusBrain.get_vision_response(context, history_limit=6)
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
            with st.chat_message("assistant"): st.write(cevap)

# ---------------------------------------------------------------------
# MOD 3: COLOSSUS DSP STÜDYOSU (MÜZİK MOTORU)
# ---------------------------------------------------------------------
elif uygulama_modu == "🎹 Colossus DSP Stüdyosu":
    st.markdown("""
    <div class='nexus-card'>
        <h3 style='color: var(--primary-color);'>Sinyal İşleme ve Algoritmik Müzik</h3>
        <p>Matematiksel formüller ve osilatörler kullanarak saf sesten elektronik ritimler yarat. (NumPy & SciPy altyapılıdır)</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        bpm_ayar = st.slider("Tempo (BPM)", min_value=60, max_value=200, value=128)
        kick_pattern = st.text_input("Kick Ritmi (X: Vur, -: Sus)", value="X-X-X-X-X-X-X-X-")
        hihat_pattern = st.text_input("Hi-Hat Ritmi (X: Vur, -: Sus)", value="--X---X---X---X-")
    
    with col2:
        st.markdown("#### Sentezleme Kontrolü")
        if st.button("🚀 Ses Dalgalarını Render Et", use_container_width=True):
            with st.spinner("DSP Motoru dalgaları işliyor..."):
                pattern = {
                    "kick": list(kick_pattern),
                    "hihat": list(hihat_pattern)
                }
                
                # Render işlemi
                wav_data = dsp_engine.render_pattern(pattern, bpm=bpm_ayar)
                
                st.success("Sentezleme Başarılı!")
                st.audio(wav_data, format="audio/wav", sample_rate=44100)
                
                # Basit Ses Dalgası Çizimi (Görsellik İçin)
                st.markdown("#### Sinyal Görselleştirme")
                st.line_chart(wav_data[:2000]) # İlk 2000 sample'ı göster

# ---------------------------------------------------------------------
# MOD 4: GELİŞTİRİCİ TERMİNALİ
# ---------------------------------------------------------------------
elif uygulama_modu == "💻 Geliştirici Terminali":
    st.markdown("""
    <div class='nexus-card'>
        <h3 style='color: var(--primary-color);'>Sistem Metrikleri ve Log Kayıtları</h3>
        <p>Nexus-Core'un arka planda gerçekleştirdiği tüm ağ isteklerini, bellek ayırmalarını ve hataları bu terminalden canlı izle.</p>
    </div>
    """, unsafe_allow_html=True)
    
    up_time = int(time.time() - st.session_state.start_time)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Uptime", value=f"{up_time} sn")
    c2.metric(label="Bellekteki Dosya", value="Aktif" if st.session_state.dosya_bellegi else "Yok")
    c3.metric(label="Sohbet Geçmişi", value=f"{len(st.session_state.mesaj_gecmisi)} Mesaj")
    c4.metric(label="DSP Motoru", value="Aktif (44.1kHz)")
    
    st.markdown("#### 🟢 Canlı Log Akışı")
    
    # Terminal Görünümlü Log Kutusu
    log_text = "\n".join(st.session_state.logs[-50:]) # Son 50 log
    st.markdown(f"<div class='terminal-box'>{log_text}</div>", unsafe_allow_html=True)
    
    if st.button("Logları Dışa Aktar"):
        st.download_button(
            label="Log Dosyasını İndir (.txt)",
            data=log_text,
            file_name="nexus_system_logs.txt",
            mime="text/plain"
        )
