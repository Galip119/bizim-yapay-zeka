import streamlit as st

# 1. Sidebar'a Model Seçim Menüsü ve Bilgi Paneli Ekleme
st.sidebar.title("🤖 Eymen-GPT Kontrol")

# Model seçenekleri
secilen_model = st.sidebar.selectbox(
    "Modeli Seç:",
    ("mistralai/Mixtral-8x7B-Instruct-v0.1", "gpt-4o-mini")
)

# Hakkını gösteren küçük bir bilgilendirme
st.sidebar.markdown("---")
st.sidebar.info("💡 **İpucu:** Eğer Mistral kotan dolarsa (günde 50 hak), otomatik olarak gpt-4o-mini'ye geçiş yapılır.")

# 2. Ana API İstek Fonksiyonu (Akıllı Geçişli)
def get_ai_response(messages, model):
    try:
        # Önce seçilen modelle dene
        return client.chat.completions.create(
            model=model,
            messages=messages
        )
    except Exception as e:
        # Hata alınırsa (quota aşımı vb.) yedek modele geç
        st.warning("⚠️ Seçili model limiti doldu! Otomatik olarak 'gpt-4o-mini'ye geçiliyor...")
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

# 3. Sohbet Arayüzü Kullanımı
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mesaj gönderildiğinde çalışacak kısım
if prompt := st.chat_input("Mesajını yaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        # API'den cevap alırken bizim akıllı fonksiyonu kullan
        response = get_ai_response(st.session_state.messages, secilen_model)
        full_response = response.choices[0].message.content
        st.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
