import streamlit as st
from groq import Groq

# Güvenlik için API anahtarını gizli ayarlardan çekeceğiz
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

# Sitenin başlığı
st.title("Bizim Yapay Zeka Arayüzü 🚀")

# Kullanıcıdan soru aldığımız kutu
sorgu = st.text_input("Bana bir şeyler sor:")

# Gönder butonuna basıldığında çalışacak kısım
if st.button("Gönder") and sorgu:
    with st.spinner("Cevap hazırlanıyor..."):
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sen yardımcı bir asistansın."},
                {"role": "user", "content": sorgu}
            ],
            model="mixtral-8x7b-32768",
            temperature=0.5,
        )
        cevap = chat_completion.choices[0].message.content
        
        # Cevabı ekrana yazdır
        st.write(cevap)