import streamlit as st
from groq import Groq
from duckduckgo_search import DDGS

# API bağlantısı
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

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
        prompt = f"Aşağıdaki internet arama sonuçlarını kullanarak kullanıcıya cevap ver. Eğer sonuçlar alakasızsa veya boşsa, kendi bilgilerinle cevapla.\n\nArama Sonuçları:\n{kaynak_metin}\nSoru: {sorgu}"
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sen yardımcı bir asistansın. Sana sağlanan güncel internet verilerini kullanarak mantıklı ve doğru cevaplar üretirsin."},
                {"role": "user", "content": prompt}
            ],
            model="mixtral-8x7b-32768",
            temperature=0.5,
        )
        cevap = chat_completion.choices[0].message.content
        
        # 3. Cevabı ekrana yazdır
        st.write(cevap)
        
        # 4. Hangi sitelere baktığını da alt tarafta göster
        with st.expander("Kullanılan İnternet Kaynakları"):
            st.write(kaynak_metin)
