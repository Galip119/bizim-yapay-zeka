import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import xml.etree.ElementTree as ET
import re

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# Sayfa genişlik ayarını yapalım (Modern durması için)
st.set_page_config(layout="centered")

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# Başlık
st.title("Eymen-GPT 🚀")

# --- YAN YANA METİN VE DOSYA GİRİŞ ALANI ---
# Ekranı yan yana 2 sütuna bölüyoruz: %80 metin alanı, %20 dosya yükleme
col1, col2 = st.columns([4, 1])

with col1:
    sorgu = st.text_input("Bana bir şeyler sor veya dosya analiz et:", placeholder="Mesajınızı yazın...", label_visibility="collapsed")

with col2:
    yuklenen_dosya = st.file_uploader("Dosya", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"], label_visibility="collapsed")

# Dosya içeriğini tutacak değişken
dosya_icerigi = ""
dosya_adi = ""

# Dosya yükleme kontrolü ve okuma işlemleri
if yuklenen_dosya is not None:
    dosya_adi = yuklenen_dosya.name.lower()
    try:
        if dosya_adi.endswith((".txt", ".py")):
            dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
        elif dosya_adi.endswith(".pdf"):
            pdf_okuyucu = PdfReader(yuklenen_dosya)
            pdf_metni = [sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()]
            dosya_icerigi = "\n".join(pdf_metni)
        elif dosya_adi.endswith(".docx"):
            doc = Document(yuklenen_dosya)
            dosya_icerigi = "\n".join([p.text for p in doc.paragraphs])
        elif dosya_adi.endswith(".xlsx"):
            wb = openpyxl.load_workbook(yuklenen_dosya, data_only=True)
            excel_metni = []
            for sayfa in wb.sheetnames:
                ws = wb[sayfa]
                excel_metni.append(f"--- Sayfa: {sayfa} ---")
                for satir in ws.iter_rows(values_only=True):
                    satir_filtreli = [str(hucre) for hucre in satir if hucre is not None]
                    if satir_filtreli:
                        excel_metni.append(" | ".join(satir_filtreli))
            dosya_icerigi = "\n".join(excel_metni)
        elif dosya_adi.endswith((".html", ".htm")):
            ham_html = yuklenen_dosya.read().decode("utf-8")
            soup = BeautifulSoup(ham_html, "html.parser")
            dosya_icerigi = soup.get_text(separator="\n", strip=True)
        elif dosya_adi.endswith(".json"):
            veri = json.load(yuklenen_dosya)
            dosya_icerigi = json.dumps(veri, indent=2, ensure_ascii=False)
        elif dosya_adi.endswith(".xml"):
            dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
        elif dosya_adi.endswith((".png", ".jpg", ".jpeg")):
            st.image(yuklenen_dosya, caption="Yüklenen Resim", width=200)
            try:
                resim = Image.open(yuklenen_dosya)
                dosya_icerigi = pytesseract.image_to_string(resim, lang="tur+eng")
            except:
                st.warning("OCR sistemi sunucuda tam kurulu olmadığı için resimdeki yazılar okunamadı.")

        if dosya_icerigi:
            st.info(f"📎 {yuklenen_dosya.name} yüklendi.")
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")

# Gönder butonu
gonder_butonu = st.button("Gönder")

if gonder_butonu and (sorgu or dosya_icerigi):
    with st.spinner("Eymen-GPT düşünüyor ve araştırıyor..."):
        try:
            context = ""
            
            # İnternet araması
            if sorgu:
                search_result = tavily.search(query=sorgu, search_depth="basic")
                context = "\n".join([res["content"] for res in search_result["results"]])
            
            # Dosya içeriğini bağlama ekleme
            if dosya_icerigi:
                context += f"\n\n[Kullanıcının Yüklediği Dosya/Kod İçeriği]:\n{dosya_icerigi}"
            
            # Mistral'e düşünmesini ama bunu özel etiketler içine almasını söylüyoruz
            sistem_mesaji = (
                "Sen çok gelişmiş bir Eymen-GPT yardımcı asistanısın. "
                "Sana verilen internet verilerini veya yüklenen dosya içeriklerini analiz ederek mükemmel cevaplar üretirsin. "
                "KURAL: Akıl yürütme, analiz ve düşünme adımlarını cevabın EN BAŞINDA <dusunce> ve </dusunce> etiketlerinin arasına yaz. "
                "Bu etiketlerin dışına ise SADECE kullanıcıya vereceğin temiz, net ve düzenli nihai cevabı yaz."
            )
            
            kullanici_mesaji = ""
            if context:
                kullanici_mesaji += f"Veriler:\n{context}\n\n"
            if sorgu:
                kullanici_mesaji += f"Soru: {sorgu}"
            else:
                kullanici_mesaji += "Yukarıdaki dosyanın/kodun içeriğini analiz et, ne işe yaradığını açıkla ve bana özetle."

            # Yapay zekaya istek gönderiliyor
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sistem_mesaji},
                    {"role": "user", "content": kullanici_mesaji}
                ],
                model="gpt-4o-mini", # Buraya Mistral model ismini de yazabilirsin
                temperature=0.6
            )
            
            ham_cevap = response.choices[0].message.content
            
            # --- DÜŞÜNME ADIMLARINI AYIRMA MANTIĞI ---
            dusunce_blogu = ""
            temiz_cevap = ham_cevap
            
            # Regex ile <dusunce>...</dusunce> arasını ayıklıyoruz
            match = re.search(r'<dusunce>(.*?)</dusunce>', ham_cevap, re.DOTALL)
            if match:
                dusunce_blogu = match.group(1).strip()
                temiz_cevap = re.sub(r'<dusunce>.*?</dusunce>', '', ham_cevap, flags=re.DOTALL).strip()
            
            # Eğer model etiketi unuttuysa ama klasik "Thinking:" falan yazdıysa yedek kontrol
            elif "thinking process:" in ham_cevap.lower():
                parcalar = re.split(r'thinking process:', ham_cevap, flags=re.IGNORECASE)
                dusunce_blogu = parcalar[0].strip()
                temiz_cevap = parcalar[1].strip()

            # 1. Düşünme adımları varsa bunu açılır kapanır bir kutuda gösteriyoruz
            if dusunce_blogu:
                with st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster/Gizle"):
                    st.write(dusunce_blogu)
            
            # 2. Esas temiz cevabı ana ekrana basıyoruz
            st.markdown(temiz_cevap)
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
