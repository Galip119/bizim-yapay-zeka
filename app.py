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
st.set_page_config(layout="centered", page_title="Galip-GPT Gelişmiş")

# --- OTURUM HAFIZASI (SESSION STATE) KONTROLLERİ ---
if "form_num" not in st.session_state:
    st.session_state.form_num = 0
if "cevap_hazir" not in st.session_state:
    st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state:
    st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state:
    st.session_state.son_dusunce = ""

metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

# Anahtarları al
github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

# Servisleri başlat
client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# --- MODEL LİSTESİ ---
MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-8B": "meta-llama-3.1-8b-instruct",
    "Phi-3 Medium": "phi-3-medium-128k-instruct",
    "GPT-4o": "gpt-4o"
}

st.sidebar.title("⚙️ Model Ayarları")
st.sidebar.write("Kotası biten modelden otomatik olarak diğerine geçilir.")
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

st.title("Galip-GPT 🚀")

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
            st.info(f"📎 {yuklenen_dosya.name} başarıyla okundu.")
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")

gonder_butonu = st.button("Gönder")

if gonder_butonu and (sorgu or dosya_icerigi):
    with st.spinner("Eymen-GPT düşünüyor..."):
        try:
            arama_metni = ""
            
            # Sadece soru varsa veya soru dosyadan bağımsız bir şeyse arama yap
            if sorgu:
                try:
                    search_result = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([res["content"] for res in search_result["results"]])
                except Exception:
                    st.warning("İnternet araması yapılamadı.")
            
            # --- SİSTEM MESAJI GÜNCELLENDİ (KESİN KURALLAR VE ÖRNEK EKLENDİ) ---
            sistem_mesaji = (
                "Sen çok gelişmiş bir Eymen-GPT asistanısın. "
                "KESİN KURAL: Herhangi bir cevap vermeden önce, kendi iç planlamanı, dosya analizini veya akıl yürütmeni "
                "MUTLAKA <dusunce> ve </dusunce> etiketleri arasına yazmalısın. "
                "Düşünce kısmını bitirdikten sonra, etiketlerin DIŞINA kullanıcıya vereceğin temiz, nihai cevabı yaz.\n\n"
                "Örnek Format:\n"
                "<dusunce>\nKullanıcı bana bir dosya vermiş. İçeriğine bakıyorum... Şunları özetlemeliyim...\n</dusunce>\n"
                "Merhaba! İstediğiniz analizi tamamladım. İşte sonuçlar..."
            )
            
            # --- MESAJ YAPISI GÜNCELLENDİ (KARIŞIKLIĞI ÖNLEMEK İÇİN) ---
            kullanici_mesaji = ""
            
            if arama_metni:
                kullanici_mesaji += f"--- İNTERNET ARAMA SONUÇLARI ---\n{arama_metni}\n\n"
                
            if dosya_icerigi:
                # Çok büyük dosyaların sistemi çökertmesini önlemek için karakter sınırı (API limitleri için)
                guvenli_icerik = dosya_icerigi[:35000] 
                kullanici_mesaji += f"--- YÜKLENEN DOSYA İÇERİĞİ ---\n{guvenli_icerik}\n\n"
            
            if sorgu:
                kullanici_mesaji += f"Kullanıcının Sorusu: {sorgu}"
            else:
                kullanici_mesaji += "Kullanıcının Sorusu: Lütfen yüklediğim bu dosyayı detaylıca analiz et ve özetle."

            # --- OTOMATİK MODEL DEĞİŞTİRME ---
            yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
            basarili_oldu = False
            
            for aktif_model in yedek_modeller:
                try:
                    response = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": sistem_mesaji},
                            {"role": "user", "content": kullanici_mesaji}
                        ],
                        model=aktif_model,
                        temperature=0.6
                    )
                    basarili_oldu = True
                    break 
                except Exception as e:
                    continue
            
            if not basarili_oldu:
                st.error("Tüm modellerin kotası dolmuş veya bir bağlantı hatası var.")
            else:
                ham_cevap = response.choices[0].message.content
                
                # --- DÜŞÜNCE AYIKLAMA GÜNCELLENDİ (Düşünce, thinking gibi varyasyonları da yakalar) ---
                dusunce_blogu = ""
                temiz_cevap = ham_cevap
                
                match = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', ham_cevap, re.DOTALL | re.IGNORECASE)
                if match:
                    dusunce_blogu = match.group(1).strip()
                    temiz_cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', ham_cevap, flags=re.DOTALL | re.IGNORECASE).strip()
                elif "thinking process:" in ham_cevap.lower():
                    parcalar = re.split(r'thinking process:', ham_cevap, flags=re.IGNORECASE)
                    if len(parcalar) > 1:
                        # Eğer alt satırlara kadar iniyorsa kabaca ilk kısmı düşünce sayalım
                        ayirici = parcalar[1].find('\n\n')
                        if ayirici != -1:
                            dusunce_blogu = parcalar[1][:ayirici].strip()
                            temiz_cevap = parcalar[1][ayirici:].strip()
                        else:
                            dusunce_blogu = parcalar[1].strip()
                            temiz_cevap = "Cevap metni ayrılamadı, lütfen düşünce bloğuna bakın."

                st.session_state.son_cevap = temiz_cevap
                st.session_state.son_dusunce = dusunce_blogu
                st.session_state.cevap_hazir = True

                st.session_state.form_num += 1
                st.rerun()
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")

if st.session_state.cevap_hazir:
    if st.session_state.son_dusunce:
        with st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster/Gizle"):
            st.write(st.session_state.son_dusunce)
    
    st.markdown(st.session_state.son_cevap)
