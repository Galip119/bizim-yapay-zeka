import streamlit as st
from openai import OpenAI
from duckduckgo_search import DDGS

token = st.secrets["GITHUB_TOKEN"]

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=token,
)

st.title("Bizim Yapay Zeka Arayüzü 🚀")

sorgu = st.text_input("Bana bir şeyler sor (İnternetten araştırıp cevaplayacağım):")

if st.button("Gönder") and sorgu:
    with st.spinner("İnternette araştırılıyor ve cevap hazırlanıyor..."):
        
        kaynak_metin = ""
        try:
            # DuckDuckGo'yu farklı bir altyapıyla (html) bağlanmaya zorluyoruz
            with DDGS() as ddgs:
                sonuclar = list(ddgs.text(sorgu, backend="html", max_results=3))
                for sonuc in sonuclar:
                    kaynak_metin += f"Başlık: {sonuc['title']}\nİçerik: {sonuc['body']}\n\n"
        except Exception as e:
            # Eğer DuckDuckGo yine engellerse, hatayı açıkça kaydediyoruz
            kaynak_metin = f"DuckDuckGo Bağlantı Engeli (Rate Limit/IP Ban): {e}\n\nLütfen aramayı daha sonra tekrar deneyin veya farklı bir arama motoru entegre edin."

        prompt = f"Aşağıdaki internet arama sonuçlarını kullanarak kullanıcıya cevap ver. Eğer sonuçlar alakasızsa veya bir hata mesajı varsa kendi mevcut bilgilerinle cevapla.\n\nArama Sonuçları:\n{kaynak_metin}\nSoru: {sorgu}"
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sen yardımcı bir asistansın. Sana sağlanan verileri kullanarak cevap üretirsin."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini",
            temperature=0.5,
        )
        cevap = response.choices[0].message.content
        
        st.write(cevap)
        
        with st.expander("Kullanılan İnternet Kaynakları (veya Hata Kaydı)"):
            st.write(kaynak_metin)
