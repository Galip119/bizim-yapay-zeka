import streamlit as st
from openai import OpenAI
from googlesearch import search

token = st.secrets["GITHUB_TOKEN"]

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=token,
)

st.title("Bizim Yapay Zeka Arayüzü 🚀")

sorgu = st.text_input("Bana bir şeyler sor:")

if st.button("Gönder") and sorgu:
    with st.spinner("Google üzerinden araştırılıyor..."):
        kaynak_metin = ""
        try:
            # Google'da arama yap
            results = search(sorgu, num_results=3)
            for url in results:
                kaynak_metin += f"Kaynak: {url}\n"
        except Exception:
            kaynak_metin = "Arama yapılamadı."

        # Modeli çağır
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sen yardımcı bir asistansın. İnternet sonuçlarını kullanarak cevap ver."},
                {"role": "user", "content": f"Arama sonuçları: {kaynak_metin}\nSoru: {sorgu}"}
            ],
            model="gpt-4o-mini",
            temperature=0.5,
        )
        st.write(response.choices[0].message.content)
