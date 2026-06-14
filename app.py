import streamlit as st
from openai import OpenAI
from tavily import TavilyClient

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

st.title("Bizim Yapay Zeka Arayüzü 🚀")
sorgu = st.text_input("Bana bir şeyler sor (İnterneti tarayıp cevaplayacağım):")

if st.button("Gönder") and sorgu:
    with st.spinner("İnternette araştırılıyor..."):
        try:
            # Tavily ile arama yap
            search_result = tavily.search(query=sorgu, search_depth="basic")
            context = "\n".join([res["content"] for res in search_result["results"]])
            
            # OpenAI formatında GitHub modeline gönder
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Sen yardımcı bir asistansın. Sana verilen internet verilerini kullanarak cevap üretirsin."},
                    {"role": "user", "content": f"İnternet verisi: {context}\n\nSoru: {sorgu}"}
                ],
                model="gpt-4o-mini",
                temperature=0.5
            )
            st.write(response.choices[0].message.content)
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
