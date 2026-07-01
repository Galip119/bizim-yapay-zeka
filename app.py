"""
EYMEX NEXUS-CORE (V13.0) 
"""
import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import io
import datetime
import logging
import time
import numpy as np
import scipy.signal as signal
from gtts import gTTS
import base64

# --- DOSYA OKUMA KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image

# =====================================================================
# 1. SİSTEM LOGLAMA VE AYARLARI
# =====================================================================
st.set_page_config(
    page_title="Eymex Nexus-Core Studio", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .main-title { color: #00d4ff; font-weight: bold; text-align: center; margin-bottom: 5px; text-shadow: 0 0 10px rgba(0,212,255,0.5); }
    .subtitle { color: #888; text-align: center; margin-bottom: 30px; font-size: 14px; }
    .log-box { background-color: #11141a; padding: 15px; border-radius: 8px; height: 350px; overflow-y: auto; color: #39ff14; font-family: 'Courier New', Courier, monospace; border: 1px solid #222; }
    .card { background-color: #1a1f2c; padding: 20px; border-radius: 10px; border: 1px solid #2e374a; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

class StreamlitLogHandler(logging.Handler):
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
# 2. DOSYA İŞLEYİCİ SINIFI
# =====================================================================
class DocumentProcessor:
    @staticmethod
    def process(file) -> str:
        name = file.name.lower()
        try:
            if name.endswith((".txt", ".py", ".xml", ".md", ".csv")): 
                return file.read().decode("utf-8")
            elif name.endswith(".pdf"):
                pdf = PdfReader(file)
                return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            elif name.endswith(".docx"):
                doc = Document(file)
                return "\n".join([p.text for p in doc.paragraphs])
            elif name.endswith(".xlsx"):
                wb = openpyxl.load_workbook(file, data_only=True)
                rows = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    rows.append(f"--- Sayfa: {sheet} ---")
                    for row in ws.iter_rows(values_only=True):
                        cells = [str(c) for c in row if c is not None]
                        if cells: rows.append(" | ".join(cells))
                return "\n".join(rows)
            return ""
        except Exception as e:
            raise Exception(f"Dosya okunamadı: {e}")

# =====================================================================
# 3. GÖMÜLÜ DSP MÜZİK MOTORU
# =====================================================================
class ColossusEngine:
    def __init__(self, sr=44100):
        self.sr = sr
        self.two_pi = 2 * np.pi

    def frekans_hesapla(self, nota_adi):
        notalar = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
        if not nota_adi or len(nota_adi) < 2 or nota_adi == "-": return 0.0
        nota = nota_adi[:-1]
        try: oktav = int(nota_adi[-1])
        except: return 440.0
        if nota not in notalar: return 0.0
        return 440.0 * (2.0 ** ((notalar[nota] + (oktav - 4) * 12) / 12.0))

    def sentezle(self, frekans, sure):
        t = np.linspace(0, sure, int(self.sr * sure), endpoint=False)
        if frekans == 0.0: return np.zeros_like(t)
        return np.sin(self.two_pi * frekans * t) * 0.3

    def render_composition(self, sarki_verisi, hedef_dakika=0.5):
        tempo = sarki_verisi.get("tempo", 120)
        adim_suresi = (60.0 / tempo) / 4.0
        adim_sample = int(self.sr * adim_suresi)
        dongu_sesi = np.zeros(adim_sample * 16)
        
        for kanal, notalar in sarki_verisi.items():
            if kanal == "tempo" or not isinstance(notalar, list): continue
            kanal_sesi = np.zeros(adim_sample * 16)
            for i, v in enumerate(notalar[:16]):
                if v == "-": continue
                parca = self.sentezle(self.frekans_hesapla(v), adim_suresi * 2)
                bitis = i * adim_sample + len(parca)
                if bitis <= len(kanal_sesi):
                    kanal_sesi[i * adim_sample:bitis] += parca
            dongu_sesi += kanal_sesi
            
        hedef_samples = int(hedef_dakika * 60 * self.sr)
        master_ses = np.tile(dongu_sesi, int(np.ceil(hedef_samples / len(dongu_sesi))))[:hedef_samples]
        max_val = np.max(np.abs(master_ses))
        if max_val > 0: master_ses = master_ses / max_val * 0.8
        return np.int16(master_ses * 32767)

engine = ColossusEngine()

# =====================================================================
# 4. DURUM YÖNETİMİ VE API YÜKLEMESİ
# =====================================================================
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "gorusme_gecmisi" not in st.session_state: st.session_state.gorusme_gecmisi = []

github_token = st.secrets.get("GITHUB_TOKEN", "")
tavily_key = st.secrets.get("TAVILY_API_KEY", "")

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key) if tavily_key else None

def get_vision_response(prompt, model_id="gpt-4o", image_bytes=None, system_prompt="", chat_history=[]):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        
    for h in chat_history:
        messages.append({"role": h["role"], "content": h["content"]})

    content_blocks = [{"type": "text", "text": prompt}]
    
    if image_bytes:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
        
    messages.append({"role": "user", "content": content_blocks})
    
    try:
        response = client.chat.completions.create(messages=messages, model=model_id, temperature=0.5)
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Modül Yanıt Veremedi. Detay: {e}"

def seslendir(metin):
    try:
        temiz_metin = re.sub(r'[*#_]', '', metin)[:500] # Hızlı okuma için ilk 500 karakter
        tts = gTTS(text=temiz_metin, lang='tr')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        return audio_io.getvalue()
    except:
        return None

# =====================================================================
# 5. YAN MENÜ & NAVİGASYON
# =====================================================================
with st.sidebar:
    st.title("⚙️ Kontrol Merkezi")
    uygulama_modu = st.radio("Mod Seçimi:", [
        "Görüntülü Konuşma (Vision+Ses) 🎥💬", 
        "Sohbet & Dosya Analizi 📄", 
        "Colossus Studio 🎹"
    ])
    
    if st.button("🧹 Hafızayı Boşalt", use_container_width=True):
        st.session_state.mesaj_gecmisi = []
        st.session_state.gorusme_gecmisi = []
        st.session_state.dosya_bellegi = ""
        st.rerun()

st.markdown("<h1 class='main-title'>Eymex Nexus-Core 🚀</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Real-Time Multimodal GPT-4o Vision & DSP Processing Engine</div>", unsafe_allow_html=True)

SISTEM_KIMLIGI = "Sen, kurucu yazılımcı Galip Eymen Demircioğlu tarafından geliştirilmiş 'Eymex Nexus-Core' yapay zeka modelisin. Bilimsel, net ve profesyonel cevaplar verirsin."

# =====================================================================
# MOD 1: GÖRÜNTÜLÜ KONUŞMA (VISION + VOICE CHAT)
# =====================================================================
if uygulama_modu == "Görüntülü Konuşma (Vision+Ses) 🎥💬":
    st.markdown("<div class='card'><h3>🎥 Görüntülü Asistan Modu</h3>Kameranı açık tut, gördüğü şeye dair seninle sesli ve yazılı olarak konuşsun.</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        kamera_kare = st.camera_input("Kamerayı Başlat")
        kullanici_sesi = st.text_input("Senin Mesajın:", placeholder="Gördüğün şey hakkında ne düşünüyorsun?")
        
    with col2:
        st.markdown("### 💬 Asistan Yanıtı")
        
        if kamera_kare and kullanici_sesi:
            with st.spinner("Görüntü ve sesin işleniyor..."):
                img_bytes = kamera_kare.read()
                
                cevap = get_vision_response(
                    prompt=kullanici_sesi, 
                    model_id="gpt-4o", 
                    image_bytes=img_bytes,
                    system_prompt=SISTEM_KIMLIGI,
                    chat_history=st.session_state.gorusme_gecmisi[-4:] # Son 4 mesajı hatırla
                )
                
                st.session_state.gorusme_gecmisi.append({"role": "user", "content": kullanici_sesi})
                st.session_state.gorusme_gecmisi.append({"role": "assistant", "content": cevap})
                
                st.info(cevap)
                
                ses_verisi = seslendir(cevap)
                if ses_verisi:
                    st.audio(ses_verisi, format='audio/mp3', autoplay=True)

# =====================================================================
# MOD 2: SOHBET & DOSYA ANALİZİ
# =====================================================================
elif uygulama_modu == "Sohbet & Dosya Analizi 📄":
    st.markdown("<div class='card'><h3>📚 Akıllı Doküman ve Dosya Odası</h3>Her türlü dosyayı yükle ve doğrudan içeriği hakkında sohbet et.</div>", unsafe_allow_html=True)
    
    yuklenen_dosya = st.file_uploader("Dosya Enjekte Et:", type=["txt", "pdf", "docx", "xlsx", "py", "html", "json", "png", "jpg", "jpeg", "csv"])
    
    if yuklenen_dosya is not None:
        name = yuklenen_dosya.name.lower()
        if name.endswith((".png", ".jpg", ".jpeg")):
            st.image(yuklenen_dosya.read(), width=200, caption="Görsel Hafızaya Alındı")
        else:
            with st.spinner("Doküman verileri ayıklanıyor..."):
                st.session_state.dosya_bellegi = DocumentProcessor.process(yuklenen_dosya)
                st.success("📝 Doküman asistan belleğine entegre edildi!")

    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]): st.markdown(mesaj["content"])

    if sorgu := st.chat_input("Hafızadaki veriyi analiz ettir..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"): st.markdown(sorgu)
        
        with st.spinner("Eymex Nexus-Core işliyor..."):
            full_prompt = f"Kullanıcı İstemi: {sorgu}\n"
            if st.session_state.dosya_bellegi: full_prompt += f"\n[Hafızadaki Doküman]:\n{st.session_state.dosya_bellegi[:25000]}\n"
            
            cevap = get_vision_response(
                prompt=full_prompt, 
                model_id="gpt-4o", 
                system_prompt=SISTEM_KIMLIGI,
                chat_history=st.session_state.mesaj_gecmisi[:-1]
            )
            
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
            with st.chat_message("assistant"): st.markdown(cevap)

# =====================================================================
# MOD 3: COLOSSUS PRO STUDIO
# =====================================================================
elif uygulama_modu == "Colossus Studio 🎹":
    st.markdown("### 🎹 Sinyal Tabanlı AI Müzik İstasyonu")
    if st.button("🚀 Örnek Beat Sentezle", use_container_width=True):
        with st.spinner("Ses işleniyor..."):
            şablon_veri = {
                "tempo": 120,
                "kick": ["C2","-","C2","-","C2","-","C2","-","C2","-","C2","-","C2","-","C2","-"]
            }
            wav_data = engine.render_composition(şablon_veri)
            st.audio(wav_data, format='audio/wav')
