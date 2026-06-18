import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import xml.etree.ElementTree as ET

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# Başlık
st.title("Eymen-GPT 🚀")

# Yan menüye Gelişmiş Dosya Yükleme Alanı
st.sidebar.header("Dosya Analizi 📂")
yuklenen_dosya = st.sidebar.file_uploader(
    "Bir dosya yükle:", 
    type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"]
)

dosya_icerigi = ""

if yuklenen_dosya is not None:
    dosya_adi = yuklenen_dosya.name.lower()
    
    try:
        # 1. Metin ve Kod Dosyaları (.txt, .py)
        if dosya_adi.endswith((".txt", ".py")):
            dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            
        # 2. PDF Dosyaları
        elif dosya_adi.endswith(".pdf"):
            pdf_okuyucu = PdfReader(yuklenen_dosya)
            pdf_metni = [sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()]
            dosya_icerigi = "\n".join(pdf_metni)
            
        # 3. Word Dosyaları (.docx)
        elif dosya_adi.endswith(".docx"):
            doc = Document(yuklenen_dosya)
            dosya_icerigi = "\n".join([p.text for p in doc.paragraphs])
            
        # 4. Excel Dosyaları (.xlsx)
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

        # 5. HTML Dosyaları (.html, .htm) -> Kodları temizleyip sadece saf yazıyı alır
        elif dosya_adi.endswith((".html", ".htm")):
            ham_html = yuklenen_dosya.read().decode("utf-8")
            soup = BeautifulSoup(ham_html, "html.parser")
            dosya_icerigi = soup.get_text(separator="\n", strip=True)

        # 6. JSON Dosyaları (.json) -> Verileri düzenli bir metne çevirir
        elif dosya_adi.endswith(".json"):
            veri = json.load(yuklenen_dosya)
            dosya_icerigi = json.dumps(veri, indent=2, ensure_ascii=False)

        # 7. XML Dosyaları (.xml)
        elif dosya_adi.endswith(".xml"):
            ham_xml = yuklenen_dosya.read().decode("utf-8")
            dosya_icerigi = ham_xml # Yapay zeka XML yapısını doğrudan okuyabilir

        # 8. Resim Dosyaları (.png, .jpg, .jpeg) -> OCR ile içindeki yazıları okur
        elif dosya_adi.endswith((".png", ".jpg", ".jpeg")):
            st.sidebar.image(yuklenen_dosya, caption="Yüklenen Resim", use_container_width=True)
            try:
                resim = Image.open(yuklenen_dosya)
                dosya_icerigi = pytesseract.image_to_string(resim, lang="tur+eng")
            except Exception as ocr_error:
                st.sidebar.warning("Resim yüklendi fakat sunucuda OCR (Yazı Okuma) kütüphanesi eksik olduğu için yazılar çıkartılamadı.")

        # Başarı Mesajı Kontrolü
        if dosya_icerigi:
            st.sidebar.success(f"✅ {dosya_adi} başarıyla analiz edildi!")
        else:
            st.sidebar.warning("Dosya okundu fakat içi boş veya yazı bulunamadı.")
            
    except Exception as e:
        st.sidebar.error(f"Dosya okunurken hata oluştu: {e}")

# Ana ekrandaki soru girişi
sorgu = st.text_input("Bana bir şeyler sor:")

if st.button("Gönder") and (sorgu or dosya_icerigi):
    with st.spinner("Eymen-GPT düşünüyor ve araştırıyor..."):
        try:
            context = ""
            
            # İnternet araması
            if sorgu:
                search_result = tavily.search(query=sorgu, search_depth="basic")
                context = "\n".join([res["content"] for res in search_result["results"]])
            
            # Yüklenen dosyanın içeriğini hafızaya ekleme
            if dosya_icerigi:
                context += f"\n\n[Kullanıcının Yüklediği Dosya/Kod İçeriği]:\n{dosya_icerigi}"
            
            sistem_mesaji = "Sen çok gelişmiş bir Eymen-GPT yardımcı asistanısın. Sana verilen internet verilerini, kodları (HTML, JSON, XML, Python) veya yüklenen döküman içeriklerini analiz ederek mükemmel cevaplar üretirsin."
            
            kullanici_mesaji = ""
            if context:
                kullanici_mesaji += f"Veriler:\n{context}\n\n"
            if sorgu:
                kullanici_mesaji += f"Soru: {sorgu}"
            else:
                kullanici_mesaji += "Yukarıdaki dosyanın/kodun içeriğini analiz et, ne işe yaradığını açıkla ve bana özetle."

            # İstek gönderiliyor
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sistem_mesaji},
                    {"role": "user", "content": kullanici_mesaji}
                ],
                model="gpt-4o-mini",
                temperature=0.5
            )
            st.write(response.choices[0].message.content)
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
