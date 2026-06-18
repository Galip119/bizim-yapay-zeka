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

# --- AYARLAR ---
st.set_page_config(page_title="Eymen-GPT", layout="wide")

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])
tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- YAN PANEL ---
with st.sidebar:
    st.title("⚙️ Ayarlar")
    model_choice = st.selectbox("Model Seçimi", ["gpt-4o", "gpt-4o-mini"])
    temperature = st.slider("Yaratıcılık (Temperature)", 0.0, 1.0, 0.6)
    if st.button("Sohbeti Temizle"):
        st.session_state.messages = []
        st.rerun()

st.title("Eymen-GPT 🚀")

# --- DOSYA İŞLEME FONKSİYONU ---
def dosya_oku(dosya):
    try:
        if dosya.name.endswith((".txt", ".py")): return dosya.read().decode("utf-8")
        elif dosya.name.endswith(".pdf"):
            reader = PdfReader(dosya)
            return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif dosya.name.endswith(".docx"):
            doc = Document(dosya)
            return "\n".join([p.text for p in doc.paragraphs])
        # Diğer formatlar için genişletilebilir...
        return "Desteklenmeyen dosya formatı."
    except Exception as e: return f"Hata: {e}"

# --- SOHBET ARAYÜZÜ ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "dusunce" in message and message["dusunce"]:
            with st.expander("🧠 Düşünme Adımları"):
                st.write(message["dusunce"])
        st.markdown(message["content"])

# --- GİRDİ ALANI ---
col1, col2 = st.columns([5, 1])
with col1:
    prompt = st.chat_input("Bir şeyler yazın...")
with col2:
    yuklenen_dosyalar = st.file_uploader("Dosya Ekle", accept_multiple_files=True, label_visibility="collapsed")

if prompt:
    dosya_icerikleri = ""
    if yuklenen_dosyalar:
        for f in yuklenen_dosyalar:
            dosya_icerikleri += f"\n[Dosya: {f.name}]\n{dosya_oku(f)}\n"

    # Kullanıcı mesajını ekle
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Eymen-GPT düşünüyor..."):
            # Arama ve Bağlam
            context = tavily.search(query=prompt, search_depth="basic")["results"]
            context_text = "\n".join([r["content"] for r in context])
            
            full_prompt = f"Bağlam: {context_text}\n\nDosyalar: {dosya_icerikleri}\n\nSoru: {prompt}"
            
            response_stream = client.chat.completions.create(
                model=model_choice,
                messages=[{"role": "system", "content": "Adımları <dusunce> etiketiyle düşün, sonra cevabı ver."}] + 
                         [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                temperature=temperature,
                stream=True
            )

            placeholder = st.empty()
            full_response = ""
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")

            # Düşünce ayırma
            match = re.search(r'<dusunce>(.*?)</dusunce>', full_response, re.DOTALL)
            dusunce = match.group(1) if match else ""
            temiz_cevap = re.sub(r'<dusunce>.*?</dusunce>', '', full_response, flags=re.DOTALL).strip()

            placeholder.markdown(temiz_cevap)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": temiz_cevap, 
                "dusunce": dusunce
            })
