import streamlit as st
from openai import OpenAI
from duckduckgo_search import DDGS

# GitHub şifreni gizli ayarlardan çekiyoruz
token = st.secrets["GITHUB_TOKEN"]

# GitHub'ın yapay zeka sunucusuna bağlanıyoruz (Evrensel OpenAI kütüphanesi ile)
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=token,
)

st.title("Bizim Yapay Zeka Arayüzü 🚀")

sorgu = st.text_input("Bana bir şeyler sor (İnternetten araştırıp cevaplayacağım):")

if st.button("Gönder") and sorgu:
    with st.spinner("İnternette araştırılıyor ve cevap hazırlanıyor..."):
        
        # 1. DuckDuckGo ile arama yap
        kaynak_metin = ""
        try:
            with DDGS() as ddgs:
                sonuclar = list(ddgs.text(sorgu, max_results=3))
                for sonuc in sonuclar:
                    kaynak_metin += f"Başlık: {sonuc['title']}\nİçerik: {sonuc['body']}\n\n"
        except Exception:
            kaynak_metin = "Arama yapılamadı veya internet bağlantı sorunu oluştu."

        # 2. Arama sonuçlarını modele gönder
        prompt = f"Aşağıdaki internet arama sonuçlarını kullanarak kullanıcıya cevap ver. Eğer sonuçlar alakasızsa kendi bilgilerinle cevapla.\n\nArama Sonuçları:\n{kaynak_metin}\nSoru: {sorgu}"
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sen yardımcı bir asistansın. Sana sağlanan verileri kullanarak cevap üretirsin."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini", # Hata veren model yerine en stabil olanı yazdık
            temperature=0.5,
        )
        cevap = response.choices[0].message.content
        
        # 3. Cevabı ekrana yazdır
        st.write(cevap)
        
        # 4. Kaynakları göster
        with st.expander("Kullanılan İnternet Kaynakları"):
            st.write(kaynak_metin)
