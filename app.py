import streamlit as st
from openai import OpenAI
from tavily import TavilyClient

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat (GitHub Models üzerinden Mistral veya OpenAI formatı)
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# Başlığı senin istediğin gibi Eymen-GPT yaptık!
st.title("Eymen-GPT 🚀")

# Yan menüye (Sidebar) Dosya Yükleme Alanı ekledik
st.sidebar.header("Dosya Analizi 📂")
yuklenen_dosya = st.sidebar.file_uploader("Bir metin veya kod dosyası yükle (.txt, .py, .md):", type=["txt", "py", "md"])

# Ana ekrandaki soru girişi
sorgu = st.text_input("Bana bir şeyler sor:")

dosya_icerigi = ""
if yuklenen_dosya is not None:
    # Dosyanın içindeki yazıyı okuyoruz
    dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
    st.sidebar.success("Dosya başarıyla yüklendi ve okundu!")

if st.button("Gönder") and (sorgu or dosya_icerigi):
    with st.spinner("Eymen-GPT düşünüyor ve araştırıyor..."):
        try:
            context = ""
            
            # Eğer kullanıcı bir soru sorduysa ve internette aramak istiyorsa
            if sorgu:
                search_result = tavily.search(query=sorgu, search_depth="basic")
                context = "\n".join([res["content"] for res in search_result["results"]])
            
            # Eğer bir dosya yüklendiyse, onu da yapay zekanın hafızasına (context) ekliyoruz
            if dosya_icerigi:
                context += f"\n\nKullanıcının Yüklediği Dosya İçeriği:\n{dosya_icerigi}"
            
            # Sistem talimatı
            sistem_mesaji = "Sen yardımcı bir asistansın. Sana verilen internet verilerini veya yüklenen dosya içeriklerini kullanarak doğru cevaplar üretirsin."
            
            # Kullanıcı mesajını hazırlayalım
            kullanici_mesaji = ""
            if context:
                kullanici_mesaji += f"Veriler:\n{context}\n\n"
            if sorgu:
                kullanici_mesaji += f"Soru: {sorgu}"
            else:
                kullanici_mesaji += "Yukarıdaki dosyayı analiz et ve bana özetle."

            # İstek gönderiliyor (Model kısmını Mistral-8x7B olarak güncelleyebilirsin)
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sistem_mesaji},
                    {"role": "user", "content": kullanici_mesaji}
                ],
                model="gpt-4o-mini", # Buraya istersen "Mistral-8x7B-Instruct-v0.1" (veya tam kütüphane adını) yazabilirsin
                temperature=0.5
            )
            st.write(response.choices[0].message.content)
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
