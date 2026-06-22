import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
import subprocess
import tempfile
from gtts import gTTS

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

st.set_page_config(
    layout="wide",
    page_title="Eymen-GPT Ultimate",
    initial_sidebar_state="expanded"
)

# =========================
# OTURUM HAFIZASI
# =========================
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None

# =========================
# API ANAHTARLARI
# =========================
try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except:
    st.error("❌ API anahtarları bulunamadı!")
    st.stop()

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# =========================
# MODELLER
# =========================
MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ Sistem Ayarları")
uygulama_modu = st.sidebar.radio(
    "Mod Seçimi:",
    ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Sesli Yanıt 🗣️", "Müzisyen Modu 🎵"]
)
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

if st.sidebar.button("🧹 Sistemi Temizle", use_container_width=True):
    st.session_state.mesaj_gecmisi = []
    st.session_state.dosya_bellegi = ""
    st.rerun()

st.title("Eymen-GPT Ultimate 🚀")

# ==================================================
# 1. MOD: SOHBET VE ANALİZ
# ==================================================
if uygulama_modu == "Sohbet & Analiz 💬":
    yuklenen_dosya = st.file_uploader("Dosya Yükle", type=["txt", "pdf", "docx", "xlsx", "py", "html", "json", "png", "jpg"])
    
    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        icerik = ""
        with st.spinner("Dosya işleniyor..."):
            try:
                if dosya_adi.endswith((".txt", ".py", ".xml")):
                    icerik = yuklenen_dosya.read().decode("utf-8")
                elif dosya_adi.endswith(".pdf"):
                    pdf = PdfReader(yuklenen_dosya)
                    icerik = "\n".join([sayfa.extract_text() for sayfa in pdf.pages if sayfa.extract_text()])
                elif dosya_adi.endswith(".docx"):
                    doc = Document(yuklenen_dosya)
                    icerik = "\n".join([p.text for p in doc.paragraphs])
                elif dosya_adi.endswith(".xlsx"):
                    wb = openpyxl.load_workbook(yuklenen_dosya, data_only=True)
                    icerik = "\n".join([f"Sayfa: {s} | " + " | ".join([str(c) for c in r if c]) for s in wb.sheetnames for r in wb[s].iter_rows(values_only=True)])
                
                if icerik:
                    st.session_state.dosya_bellegi = icerik
                    st.success("📎 Dosya hafızaya alındı!")
            except Exception as e:
                st.error(f"Hata: {e}")

    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]):
            st.markdown(mesaj["content"])

    if sorgu := st.chat_input("Sorunu yaz..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        with st.chat_message("user"): st.markdown(sorgu)

# ==========================================
# 3. MOD: SESLİ YANIT
# ==========================================
elif uygulama_modu == "Sesli Yanıt 🗣️":
    sesli_sorgu = st.text_area("Seslendirilecek metni girin:", height=150)
    if st.button("🎙️ Sese Çevir", use_container_width=True) and sesli_sorgu:
        tts = gTTS(text=sesli_sorgu, lang="tr")
        ses_bellek = io.BytesIO()
        tts.write_to_fp(ses_bellek)
        st.session_state.son_ses_bytes = ses_bellek.getvalue()
        st.session_state.sesli_metin_hazir = True

    if st.session_state.sesli_metin_hazir:
        st.audio(st.session_state.son_ses_bytes, format="audio/mp3")

# ==========================================
# 4. MOD: MÜZİSYEN MODU
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    muzik_sorgu = st.text_input("Şarkıyı tarif et:")
    hedef_dk = st.number_input("Süre (Dakika)", value=2.0)
    
    if st.button("🎸 Müziği Üret") and muzik_sorgu:
        with st.spinner("Besteleniyor..."):
            try:
                # NoModelsMusic modül çağrısı
                import NoModelsMusic
                sarki_verisi = {"notalar": ["C4"] * 16} # Örnek veri
                ses_dosyasi_wav = NoModelsMusic.motoru_calistir(sarki_verisi, hedef_dakika=hedef_dk)
                st.audio(ses_dosyasi_wav, format="audio/wav")
                st.success("🎵 Şarkı Hazır!")
            except Exception as e:
                st.error(f"Hata: {e}")
