import streamlit as st
from openai import OpenAI

# Ayarlar
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])

st.title("Eymen-GPT Pro 🎨")

# Model seçimi
model = st.sidebar.selectbox("Model:", ["gpt-4o-mini", "mistralai/Mistral-Large-2"])

if "messages" not in st.session_state: st.session_state.messages = []

prompt = st.chat_input("Bir şey sor veya 'resim: [ne istediğin]' yaz...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Görsel isteği kontrolü
    if prompt.lower().startswith("resim:"):
        resim_konusu = prompt.split("resim:")[1].strip()
        # DALL-E yerine Stable Diffusion (ücretsiz ve sınırsız API) kullanımı
        gorsel_url = f"https://image.pollinations.ai/prompt/{resim_konusu.replace(' ', '%20')}"
        
        st.chat_message("assistant").image(gorsel_url, caption=f"'{resim_konusu}' için görsel")
        st.session_state.messages.append({"role": "assistant", "content": gorsel_url})
    
    else:
        # Metin cevapları
        with st.chat_message("assistant"):
            response = client.chat.completions.create(model=model, messages=st.session_state.messages)
            cevap = response.choices[0].message.content
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})

