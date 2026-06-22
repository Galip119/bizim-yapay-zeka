import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import xml.etree.ElementTree as ET
import re
import urllib.parse
import requests

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# Sayfa genişlik ayarı
st.set_page_config(layout="centered", page_title="Eymen-GPT Gelişmiş")

# --- OTURUM HAFIZASI (SESSION STATE) KONTROLLERİ ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "cevap_hazir" not in st.session_state: st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state: st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state: st.session_state.son_dusunce = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
# 🎵 Ses için yeni hafıza değişkenleri:
if "ses_hazir" not in st.session_state: st.session_state.ses_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None

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
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

# --- SOL MENÜ VE MOD SEÇİMİ ---
st.sidebar.title("⚙️ Ayarlar")

uygulama_modu = st.sidebar.radio("Mod Seçimi:", ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Müzisyen Modu 🎵"])

st.sidebar.markdown("---")
st.sidebar.write("Kotası biten modelden otomatik olarak diğerine geçilir.")
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

st.title("Eymen-GPT 🚀")

# ==========================================
# 1. MOD: SOHBET VE ANALİZ
# ==========================================
if uygulama_modu == "Sohbet & Analiz 💬":
    col1, col2 = st.columns([4, 1])

    with col1:
        sorgu = st.text_input("Bana bir şeyler sor veya dosya analiz et:", placeholder="Mesajınızı yazın...", label_visibility="collapsed", key=metin_anahtari)

    with col2:
        yuklenen_dosya = st.file_uploader("Dosya", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"], label_visibility="collapsed", key=dosya_anahtari)

    dosya_icerigi = ""

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        try:
            if dosya_adi.endswith((".txt", ".py")): dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            elif dosya_adi.endswith(".pdf"):
                pdf_okuyucu = PdfReader(yuklenen_dosya)
                dosya_icerigi = "\n".join([sayfa.extract_text() for sayfa in pdf_okuyucu.pages if sayfa.extract_text()])
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
                        if satir_filtreli: excel_metni.append(" | ".join(satir_filtreli))
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
            
            if dosya_icerigi: st.info(f"📎 {yuklenen_dosya.name} başarıyla okundu.")
        except Exception as e: st.error(f"Dosya okunurken hata oluştu: {e}")

    gonder_butonu = st.button("Gönder")

    if gonder_butonu and (sorgu or dosya_icerigi):
        with st.spinner("Eymen-GPT düşünüyor..."):
            try:
                arama_metni = ""
                if sorgu:
                    try:
                        search_result = tavily.search(query=sorgu, search_depth="basic")
                        arama_metni = "\n".join([res["content"] for res in search_result["results"]])
                    except: st.warning("İnternet araması yapılamadı.")
                
                sistem_mesaji = "Sen çok gelişmiş bir Eymen-GPT asistanısın. Herhangi bir cevap vermeden önce, akıl yürütmeni MUTLAKA <dusunce> ve </dusunce> etiketleri arasına yaz. Düşünce kısmını bitirdikten sonra DIŞINA nihai cevabı yaz."
                kullanici_mesaji = ""
                
                if arama_metni: kullanici_mesaji += f"--- İNTERNET ARAMASI ---\n{arama_metni}\n\n"
                if dosya_icerigi: kullanici_mesaji += f"--- DOSYA İÇERİĞİ ---\n{dosya_icerigi[:35000]}\n\n"
                if sorgu: kullanici_mesaji += f"Soru: {sorgu}"
                else: kullanici_mesaji += "Soru: Lütfen yüklediğim bu dosyayı detaylıca analiz et ve özetle."

                yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
                basarili_oldu = False
                
                for aktif_model in yedek_modeller:
                    try:
                        response = client.chat.completions.create(
                            messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": kullanici_mesaji}],
                            model=aktif_model, temperature=0.6
                        )
                        basarili_oldu = True
                        break 
                    except: continue
                
                if not basarili_oldu: st.error("Tüm modellerin kotası dolmuş veya bir bağlantı hatası var.")
                else:
                    ham_cevap = response.choices[0].message.content
                    dusunce_blogu, temiz_cevap = "", ham_cevap
                    
                    match = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', ham_cevap, re.DOTALL | re.IGNORECASE)
                    if match:
                        dusunce_blogu = match.group(1).strip()
                        temiz_cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', ham_cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.son_cevap = temiz_cevap
                    st.session_state.son_dusunce = dusunce_blogu
                    st.session_state.cevap_hazir = True
                    st.session_state.form_num += 1
                    st.rerun()
            except Exception as e: st.error(f"Bir hata oluştu: {e}")

    if st.session_state.cevap_hazir:
        if st.session_state.son_dusunce:
            with st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster"): st.write(st.session_state.son_dusunce)
        st.markdown(st.session_state.son_cevap)

# ==========================================
# 2. MOD: RESSAM MODU
# ==========================================
elif uygulama_modu == "Ressam Modu 🎨":
    st.markdown("### 🎨 Hayal Gücünü Ekrana Yansıt")
    st.write("İstediğin resmi detaylıca tarif et. Ne kadar çok detay verirsen, o kadar iyi sonuç alırsın!")
    
    resim_sorgu = st.text_input("Neyin resmini çizmek istersin?", placeholder="Örn: Yağmurlu bir gecede yürüyen fütüristik kedi", key=f"resim_input_{st.session_state.form_num}")
    cizdir_butonu = st.button("🖼️ Resmi Oluştur")
    
    if cizdir_butonu and resim_sorgu:
        with st.spinner("Tuval hazırlanıyor, boyalar karıştırılıyor..."):
            guvenli_sorgu = urllib.parse.quote(resim_sorgu)
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{guvenli_sorgu}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
            st.session_state.form_num += 1
            st.rerun()
            
    if st.session_state.resim_hazir and st.session_state.son_resim_url:
        st.image(st.session_state.son_resim_url, caption="İşte oluşturulan resim!", use_container_width=True)

# ==========================================
# 3. MOD: MÜZİSYEN MODU (GÜNCELLENDİ 🎵)
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 Yapay Zeka Müzik Stüdyosu")
    st.write("İstediğin ritmi veya melodiyi İngilizce veya Türkçe tarif et.")
    
    muzik_sorgu = st.text_input("Nasıl bir müzik istiyorsun?", placeholder="Örn: 80s synthwave fast beat", key=f"muzik_input_{st.session_state.form_num}")
    cal_butonu = st.button("🎸 Müziği Üret")

    if cal_butonu and muzik_sorgu:
        with st.spinner("Müzik besteleniyor... (Bu işlem 30-40 saniye sürebilir, heyecanla bekliyoruz!)"):
            try:
                API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
                
                # Hugging Face Token kontrolü yapıyoruz
                if "HUGGINGFACE_TOKEN" in st.secrets:
                    headers = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_TOKEN']}"}
                else:
                    headers = {} # Token yoksa kısıtlı erişim dener
                    
                payload = {"inputs": muzik_sorgu}
                response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

                if response.status_code == 200:
                    # Başarılıysa ses byte'larını hafızaya alıp sayfayı tetikliyoruz
                    st.session_state.son_ses_bytes = response.content
                    st.session_state.ses_hazir = True
                    st.session_state.form_num += 1
                    st.rerun()
                elif response.status_code == 503:
                    st.warning("⏳ Yapay zeka uykudan uyanıyor! Model şu an yükleniyor. Lütfen yaklaşık 20 saniye bekleyip butona TEKRAR bas.")
                else:
                    st.error(f"Hata Kodu {response.status_code}: Sunucu şu an meşgul veya token hatalı. Lütfen detayları kontrol et.")
            
            except requests.exceptions.ConnectionError:
                st.error("Bağlantı Hatası: Streamlit ana sunucuya bağlanamadı. Lütfen sağ alttaki 'Manage App' kısmından uygulamayı 'Reboot' et veya sayfayı yenile.")
            except Exception as e:
                st.error(f"Beklenmeyen bir hata: {e}")

    # Hafızada müzik varsa ekranda sabit tut ve oynat
    if st.session_state.ses_hazir and st.session_state.son_ses_bytes:
        st.audio(st.session_state.son_ses_bytes, format='audio/wav')
        st.success("Müzik hazır! 🎧")

