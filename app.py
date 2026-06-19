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

# Sayfa genişlik ayarı
st.set_page_config(layout="centered")

# --- OTURUM HAFIZASI (SESSION STATE) KONTROLLERİ ---
# Form elemanlarını sıfırlamak için benzersiz anahtarlar (key) üretiyoruz
if "form_num" not in st.session_state:
    st.session_state.form_num = 0
if "cevap_hazir" not in st.session_state:
    st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state:
    st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state:
    st.session_state.son_dusunce = ""

# Anahtarları dinamik yapmak için form numarasını kullanıyoruz
metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# Başlık
st.title("Galip-GPT 🚀")

# --- YAN YANA METİN VE DOSYA GİRİŞ ALANI ---
col1, col2 = st.columns([4, 1])

with col1:
    sorgu = st.text_input(
        "Bana bir şeyler sor veya dosya analiz et:", 
        placeholder="Mesajınızı yazın...", 
        label_visibility="collapsed",
        key=metin_anahtari
    )

with col2:
    yuklenen_dosya = st.file_uploader(
        "Dosya", 
        type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"], 
        label_visibility="collapsed",
        key=dosya_anahtari
    )

dosya_icerigi = ""
dosya_adi = ""

# Dosya okuma işlemleri
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
                st.warning("OCR sistemi tam çalışmadığı için yazı okunamadı.")

        if dosya_icerigi:
            st.info(f"📎 {yuklenen_dosya.name} yüklendi.")
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")

# Gönder butonu
gonder_butonu = st.button("Gönder")

if gonder_butonu and (sorgu or dosya_icerigi):
    with st.spinner("Eymen-GPT düşünüyor..."):
        try:
            context = ""
            
            # İnternet araması
            if sorgu:
                search_result = tavily.search(query=sorgu, search_depth="basic")
                context = "\n".join([res["content"] for res in search_result["results"]])
            
            # Dosya bağlama ekleme
            if dosya_icerigi:
                context += f"\n\n[Kullanıcının Yüklediği Dosya/Kod İçeriği]:\n{dosya_icerigi}"
            
            sistem_mesaji = (
                "Sen çok gelişmiş bir Eymen-GPT yardımcı asistanısın. "
                "KURAL: Akıl yürütme, analiz ve düşünme adımlarını cevabın EN BAŞINDA <dusunce> ve </dusunce> etiketlerinin arasına yaz. "
                "Bu etiketlerin dışına ise SADECE nihai cevabı yaz."
            )
            
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
                temperature=0.6
            )
            
            ham_cevap = response.choices[0].message.content
            
            # Düşünme adımlarını ayırma
            dusunce_blogu = ""
            temiz_cevap = ham_cevap
            
            match = re.search(r'<dusunce>(.*?)</dusunce>', ham_cevap, re.DOTALL)
            if match:
                dusunce_blogu = match.group(1).strip()
                temiz_cevap = re.sub(r'<dusunce>.*?</dusunce>', '', ham_cevap, flags=re.DOTALL).strip()
            elif "thinking process:" in ham_cevap.lower():
                parcalar = re.split(r'thinking process:', ham_cevap, flags=re.IGNORECASE)
                dusunce_blogu = parcalar[0].strip()
                temiz_cevap = parcalar[1].strip()

            # Cevapları ekranda kalıcı kılmak için session_state'e kaydediyoruz
            st.session_state.son_cevap = temiz_cevap
            st.session_state.son_dusunce = dusunce_blogu
            st.session_state.cevap_hazir = True

            # --- SİHRİN GERÇEKLEŞTİĞİ YER (OTOMATİK TEMİZLEME) ---
            # Form numarasını artırarak input alanlarını anında sıfırlıyoruz
            st.session_state.form_num += 1
            st.rerun() # Sayfayı anında yeni boş inputlarla yeniliyoruz
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")

# Eğer kaydedilmiş bir cevap varsa, temizlenen sayfada bunları gösteriyoruz
if st.session_state.cevap_hazir:
    if st.session_state.son_dusunce:
        with st.expand_tracker if hasattr(st, "expand_tracker") else st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster/Gizle"):
            st.write(st.session_state.son_dusunce)
    
    st.markdown(st.session_state.son_cevap)
