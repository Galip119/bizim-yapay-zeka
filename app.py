import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import re
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# Sayfa ayarları
st.set_page_config(page_title="Eymen-GPT Pro", layout="centered")

# --- GÜVENLİK VE SERVİSLER ---
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])
tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])

# --- SESSION STATE HAZIRLIK ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "cevap_hazir" not in st.session_state: st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state: st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state: st.session_state.son_dusunce = ""

# --- SIDEBAR (MODEL SEÇİMİ VE BİLGİ) ---
st.sidebar.title("🤖 Eymen-GPT Kontrol")
secilen_model = st.sidebar.selectbox(
    "Modeli Seç:",
    ("mistralai/Mixtral-8x7B-Instruct-v0.1", "gpt-4o-mini")
)
st.sidebar.markdown("---")
st.sidebar.info("💡 **İpucu:** Seçili modelin kotası dolarsa sistem otomatik olarak 'gpt-4o-mini'ye geçiş yapar.")

# --- ANA ARAYÜZ ---
st.title("Eymen-GPT Pro 🚀")

metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

col1, col2 = st.columns([4, 1])
with col1:
    sorgu = st.text_input("Soru sor:", key=metin_anahtari, label_visibility="collapsed", placeholder="Mesajınız...")
with col2:
    yuklenen_dosya = st.file_uploader("Dosya", key=dosya_anahtari, label_visibility="collapsed")

# --- DOSYA İŞLEME FONKSİYONU ---
def dosyayi_oku(dosya):
    try:
        if dosya.name.endswith(".pdf"):
            return "\n".join([sayfa.extract_text() for sayfa in PdfReader(dosya).pages if sayfa.extract_text()])
        elif dosya.name.endswith(".txt"):
            return dosya.read().decode("utf-8")
        return "Desteklenmeyen dosya tipi."
    except: return "Dosya okuma hatası."

dosya_icerigi = dosyayi_oku(yuklenen_dosya) if yuklenen_dosya else ""

# --- GÖNDER BUTONU VE AKILLI YÖNLENDİRİCİ ---
if st.button("Gönder"):
    with st.spinner("Düşünülüyor..."):
        try:
            kullanici_prompt = f"Soru: {sorgu}\nDosya İçeriği: {dosya_icerigi}"
            
            # İstek Gönderme (Akıllı Geçişli)
            try:
                response = client.chat.completions.create(
                    model=secilen_model,
                    messages=[{"role": "user", "content": kullanici_prompt}]
                )
            except:
                st.warning("⚠️ Seçili model limiti doldu! Otomatik olarak 'gpt-4o-mini'ye geçiliyor...")
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": kullanici_prompt}]
                )

            ham_cevap = response.choices[0].message.content
            
            # Düşünceyi ayır
            match = re.search(r'<dusunce>(.*?)</dusunce>', ham_cevap, re.DOTALL)
            st.session_state.son_dusunce = match.group(1).strip() if match else "Düşünme adımı bulunamadı."
            st.session_state.son_cevap = re.sub(r'<dusunce>.*?</dusunce>', '', ham_cevap, flags=re.DOTALL).strip()
            st.session_state.cevap_hazir = True
            
            # Sıfırlama
            st.session_state.form_num += 1
            st.rerun()
            
        except Exception as e:
            st.error(f"Hata: {e}")

# --- SONUÇLARI GÖSTER ---
if st.session_state.cevap_hazir:
    with st.expander("🧠 Düşünme Adımları"):
        st.write(st.session_state.son_dusunce)
    st.markdown(st.session_state.son_cevap)
