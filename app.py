import streamlit as st
from openai import OpenAI

# 1. AYARLAR
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=st.secrets["GITHUB_TOKEN"])

st.set_page_config(page_title="Eymen-GPT Hibrit")
st.title("Eymen-GPT Pro 🚀")

# 2. MODEL SEÇİMİ
secilen_model = st.sidebar.selectbox(
    "Metin Modeli Seç:",
    ["mistralai/Mixtral-8x7B-Instruct-v0.1", "gpt-4o-mini"]
)

if "messages" not in st.session_state: st.session_state.messages = []

# 3. CHAT MANTIĞI
prompt = st.chat_input("Mesaj yaz veya 'resim: [komut]' de...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # GÖRSEL TESPİTİ (Eğer kullanıcı "resim:" ile başlarsa)
    if prompt.lower().startswith("resim:"):
        resim_komutu = prompt.split("resim:")[1].strip()
        gorsel_url = f"https://image.pollinations.ai/prompt/{resim_komutu.replace(' ', '%20')}"
        
        with st.chat_message("assistant"):
            st.markdown(f"**Görsel Oluşturuldu:** {resim_komutu}")
            st.image(gorsel_url)
            st.session_state.messages.append({"role": "assistant", "content": f"![{resim_komutu}]({gorsel_url})"})
            
    # METİN TESPİTİ (Normal sohbet)
    else:
        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model=secilen_model,
                    messages=st.session_state.messages
                )
                cevap = response.choices[0].message.content
                st.markdown(cevap)
                st.session_state.messages.append({"role": "assistant", "content": cevap})
            except Exception as e:
                st.error(f"Hata: {e}")
