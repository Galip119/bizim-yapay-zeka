import streamlit as st
from openai import OpenAI
import re

# Sayfa ayarları
st.set_page_config(page_title="Eymen-GPT Pro", layout="centered")

# --- GÜVENLİK ---
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])

# --- SIDEBAR (MODEL SEÇİMİ) ---
st.sidebar.title("🤖 Eymen-GPT Kontrol")
secilen_model = st.sidebar.selectbox(
    "Modeli Seç:",
    ("mistralai/Mixtral-8x7B-Instruct-v0.1", "gpt-4o-mini", "dall-e-3")
)

# --- ANA ARAYÜZ ---
st.title("Eymen-GPT Pro 🚀")

if "messages" not in st.session_state: st.session_state.messages = []

# Mesaj gönderildiğinde çalışacak kısım
if prompt := st.chat_input("Mesajını yaz veya resim için detay ver..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("İşleniyor..."):
            try:
                # 1. GÖRSEL ÜRETİM (DALL-E 3)
                if secilen_model == "dall-e-3":
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    image_url = response.data[0].url
                    st.image(image_url, caption="DALL-E 3 ile oluşturuldu")
                    st.session_state.messages.append({"role": "assistant", "content": f"![Görsel]({image_url})"})

                # 2. METİN ÜRETİMİ (MISTRAL VEYA GPT)
                else:
                    response = client.chat.completions.create(
                        model=secilen_model,
                        messages=st.session_state.messages
                    )
                    cevap = response.choices[0].message.content
                    st.markdown(cevap)
                    st.session_state.messages.append({"role": "assistant", "content": cevap})

            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")
                if "429" in str(e):
                    st.warning("Limit doldu! Lütfen başka bir model seç veya yarını bekle.")


