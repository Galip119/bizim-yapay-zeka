import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# Sayfa ayarları
st.set_page_config(layout="centered", page_title="Galip-GPT Gelişmiş")

# --- SESSION STATE INITIALIZATION ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "cevap_hazir" not in st.session_state: st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state: st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state: st.session_state.son_dusunce = ""
if "soru_sayaci" not in st.session_state: st.session_state.soru_sayaci = 0

# --- MODEL AYARLARI ---
MODELS = {
    "Mistral Large 2": "mistralai/mistral-large-2",
    "GPT-4o Mini": "gpt-4o-mini",
    "Phi-3 Medium": "microsoft/phi-3-medium-128k-instruct",
    "Llama-3-70B": "meta-llama/llama-3-70b-instruct"
}

st.title("Galip-GPT 🚀")

# Sidebar'da model seçimi
selected_model_name = st.sidebar.selectbox("Model Seçin:", list(MODELS.keys()))
selected_model_id = MODELS[selected_model_name]

# Kota Yönetimi
KOTA_LIMITI = 5
if st.session_state.soru_sayaci >= KOTA_LIMITI:
    st.sidebar.error(f"⚠️ {selected_model_name} için kota doldu! Lütfen başka bir model seçin.")
else:
    st.sidebar.success(f"Kalan hak: {KOTA_LIMITI - st.session_state.soru_sayaci}")

# Servis Başlatma
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])
tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])

# --- ARAYÜZ ---
col1, col2 = st.columns([4, 1])
with col1:
    sorgu = st.text_input("Mesajınızı yazın...", key=f"sorgu_{st.session_state.form_num}")
with col2:
    yuklenen_dosya = st.file_uploader("Dosya", key=f"dosya_{st.session_state.form_num}")

gonder_butonu = st.button("Gönder")

if gonder_butonu and (sorgu or yuklenen_dosya):
    if st.session_state.soru_sayaci >= KOTA_LIMITI:
        st.error("Kota doldu! Lütfen model değiştirin veya sayfayı yenileyin.")
    else:
        with st.spinner(f"{selected_model_name} çalışıyor..."):
            # (Dosya okuma kısımları aynıdır, kısalık için burada özet geçildi)
            # ... [Dosya okuma mantığınızı buraya aynen ekleyebilirsiniz] ...
            
            try:
                # API İstek Gönderimi
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Adım adım düşünerek cevapla."},
                        {"role": "user", "content": sorgu}
                    ],
                    model=selected_model_id,
                    temperature=0.6
                )
                
                st.session_state.son_cevap = response.choices[0].message.content
                st.session_state.soru_sayaci += 1
                st.session_state.cevap_hazir = True
                st.session_state.form_num += 1
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

# Cevap gösterme
if st.session_state.cevap_hazir:
    st.markdown("---")
    st.write(st.session_state.son_cevap)

