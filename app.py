import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
import subprocess
import datetime
import logging
import time
from gtts import gTTS

# --- DOSYA OKUMA KÜTÜPHANELERİ ---
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

# =====================================================================
# 🛠️ GİZLİ KÜTÜPHANEMİZİ İÇERİ AKTARIYORUZ
# =====================================================================
from nomodelsmusic.engine import ColossusEngine 

# =====================================================================
# 1. SİSTEM LOG (KAYIT) ALTYAPISI
# =====================================================================
# Log dosyasını yapılandırıyoruz. Tüm işlemler eymen_system.log dosyasına yazılacak.
LOG_FILE = "eymen_system.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_kaydet(mesaj, seviye="info"):
    """Özel log kaydetme fonksiyonu"""
    if seviye == "info":
        logging.info(mesaj)
    elif seviye == "error":
        logging.error(mesaj)
    elif seviye == "warning":
        logging.warning(mesaj)

# Uygulama başlatıldığında log al
if "baslangic_loglandi" not in st.session_state:
    log_kaydet("🚀 Eymen-GPT Ultimate Studio Başlatıldı.")
    st.session_state.baslangic_loglandi = True

# =====================================================================
# SAYFA YAPILANDIRMASI
# =====================================================================
st.set_page_config(
    layout="wide", 
    page_title="Eymen-GPT Ultimate Studio", 
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# =====================================================================
# OTURUM HAFIZASI (SESSION STATE)
# =====================================================================
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "dosya_bellegi" not in st.session_state: st.session_state.dosya_bellegi = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""
if "sesli_metin_hazir" not in st.session_state: st.session_state.sesli_metin_hazir = False
if "son_ses_bytes" not in st.session_state: st.session_state.son_ses_bytes = None
if "sistem_baslatildi" not in st.session_state: st.session_state.sistem_baslatildi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =====================================================================
# YAN MENÜ: TEMA VE AYARLAR
# =====================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=80)
    st.title("⚙️ Sistem Kontrolü")
    st.caption(f"Aktif Oturum: {st.session_state.sistem_baslatildi}")
    
    st.markdown("---")
    
    # 2. TEMA SEÇİM MOTORU
    secilen_tema = st.selectbox(
        "🎨 Arayüz Teması:", 
        ["Varsayılan (Dark/Light)", "Matrix (Terminal)", "Neon Cyberpunk", "Gece Mavisi"]
    )
    
    log_kaydet(f"Tema değiştirildi: {secilen_tema}")

    st.markdown("---")
    uygulama_modu = st.radio(
        "Ana Modu Seçin:", 
        ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Sesli Yanıt 🗣️", "Müzisyen Modu 🎵"],
        index=0
    )

    st.markdown("---")
    st.subheader("🤖 AI Ayarları")
    MODELS = {
        "Mistral-8x7B": "Mistral-8x7B",
        "GPT-4o Mini": "gpt-4o-mini",
        "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
        "Cohere Command R": "cohere-command-r",
        "GPT-4o": "gpt-4o"
    }
    secilen_model_adi = st.selectbox("Aktif Model:", list(MODELS.keys()))
    secilen_model_id = MODELS[secilen_model_adi]
    sicaklik_degeri = st.slider("Yaratıcılık Seviyesi", 0.0, 1.0, 0.7, 0.1)

    st.markdown("---")
    if st.button("🧹 Sistemi Temizle", use_container_width=True):
        log_kaydet("Kullanıcı sistemi ve hafızayı temizledi.")
        st.session_state.mesaj_gecmisi = []
        st.session_state.dosya_bellegi = ""
        st.session_state.resim_hazir = False
        st.session_state.sesli_metin_hazir = False
        st.rerun()
        
    if len(st.session_state.mesaj_gecmisi) > 0:
        gecmis_json = json.dumps(st.session_state.mesaj_gecmisi, ensure_ascii=False, indent=4)
        st.download_button("💾 Geçmişi İndir", gecmis_json, f"Log_{datetime.datetime.now().strftime('%H%M%S')}.json", "application/json", use_container_width=True)

    # CANLI LOG İZLEYİCİ (YENİ)
    st.markdown("---")
    with st.expander("📜 Sistem Logları (Admin)"):
        if st.button("🔄 Logları Yenile"):
            pass # Rerun tetikler
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                satirlar = f.readlines()
                # Sadece son 15 logu göster
                son_loglar = "".join(satirlar[-15:])
                st.code(son_loglar, language="bash")
        except FileNotFoundError:
            st.info("Henüz log kaydı yok.")

# =====================================================================
# TEMA UYGULAYICI (DİNAMİK CSS)
# =====================================================================
css_kodu = ""
if secilen_tema == "Matrix (Terminal)":
    css_kodu = """
    <style>
    .stApp { background-color: #0d0d0d; color: #00FF41; font-family: 'Courier New', Courier, monospace; }
    h1, h2, h3 { color: #00FF41 !important; }
    .stTextInput>div>div>input { background-color: #000; color: #00FF41; border: 1px solid #00FF41; }
    .stButton>button { background-color: #000; color: #00FF41; border: 1px solid #00FF41; }
    .stButton>button:hover { background-color: #00FF41; color: #000; }
    </style>
    """
elif secilen_tema == "Neon Cyberpunk":
    css_kodu = """
    <style>
    .stApp { background-color: #0b0f19; color: #0ff; }
    h1, h2, h3 { color: #f0f !important; text-shadow: 0 0 5px #f0f; }
    .stButton>button { background-color: transparent; color: #0ff; border: 2px solid #0ff; box-shadow: 0 0 10px #0ff; }
    .stButton>button:hover { background-color: #0ff; color: #000; box-shadow: 0 0 20px #0ff; }
    </style>
    """
elif secilen_tema == "Gece Mavisi":
    css_kodu = """
    <style>
    .stApp { background-color: #1a2639; color: #e0e6ed; }
    h1, h2, h3 { color: #4DA8DA !important; }
    .stButton>button { background-color: #4DA8DA; color: white; border: none; border-radius: 8px; }
    .stButton>button:hover { background-color: #12232E; border: 1px solid #4DA8DA; }
    </style>
    """

if css_kodu:
    st.markdown(css_kodu, unsafe_allow_html=True)

# Ortak Başlık Tasarımı
st.markdown('<div style="font-size: 2.5rem; text-align: center; font-weight: bold; margin-bottom: 5px;">Eymen-GPT Ultimate Studio 🚀</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 1.1rem; text-align: center; margin-bottom: 30px; opacity: 0.7;">Yapay Zeka Destekli Gelişmiş Üretim Platformu</div>', unsafe_allow_html=True)

# =====================================================================
# API BAĞLANTILARI
# =====================================================================
try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except KeyError:
    log_kaydet("Kritik Hata: API Anahtarları bulunamadı!", "error")
    st.error("❌ API anahtarları bulunamadı! Lütfen '.streamlit/secrets.toml' dosyanı kontrol et.")
    st.stop()

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

# =====================================================================
# MOD 1: SOHBET VE ANALİZ
# =====================================================================
if uygulama_modu == "Sohbet & Analiz 💬":
    
    st.markdown("### 📎 Döküman Analiz Merkezi")
    yuklenen_dosya = st.file_uploader("Okunmasını istediğin dosyayı yükle (Kod, PDF, Excel, Görsel vb.):", type=["txt", "pdf", "docx", "xlsx", "py", "html", "json", "png", "jpg"])

    if yuklenen_dosya is not None:
        dosya_adi = yuklenen_dosya.name.lower()
        icerik = ""
        baslangic_zamani = time.time()
        log_kaydet(f"Dosya yükleme başlatıldı: {yuklenen_dosya.name}")
        
        with st.spinner("Dosya işleniyor..."):
            try:
                if dosya_adi.endswith((".txt", ".py")): icerik = yuklenen_dosya.read().decode("utf-8")
                elif dosya_adi.endswith(".pdf"):
                    pdf = PdfReader(yuklenen_dosya)
                    icerik = "\n".join([sayfa.extract_text() for sayfa in pdf.pages if sayfa.extract_text()])
                elif dosya_adi.endswith(".docx"):
                    doc = Document(yuklenen_dosya)
                    icerik = "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
                elif dosya_adi.endswith(".xlsx"):
                    wb = openpyxl.load_workbook(yuklenen_dosya, data_only=True)
                    satirlar = [f"Sayfa: {sayfa} \n" + " | ".join([str(h) for h in satir if h]) for sayfa in wb.sheetnames for satir in wb[sayfa].iter_rows(values_only=True)]
                    icerik = "\n".join(satirlar)
                elif dosya_adi.endswith(".json"):
                    icerik = json.dumps(json.load(yuklenen_dosya), indent=2, ensure_ascii=False)
                elif dosya_adi.endswith((".png", ".jpg")):
                    st.image(yuklenen_dosya, width=300)
                    icerik = pytesseract.image_to_string(Image.open(yuklenen_dosya), lang="tur+eng")
                
                if icerik:
                    st.session_state.dosya_bellegi = icerik
                    gecen_sure = round(time.time() - baslangic_zamani, 2)
                    log_kaydet(f"Dosya başarıyla okundu: {yuklenen_dosya.name} ({len(icerik)} karakter, {gecen_sure} sn)")
                    st.success(f"✅ {yuklenen_dosya.name} hafızaya alındı! ({gecen_sure} saniye sürdü)")
            except Exception as e: 
                log_kaydet(f"Dosya okuma hatası ({yuklenen_dosya.name}): {e}", "error")
                st.error(f"Hata: {e}")

    st.markdown("---")
    
    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]): st.markdown(mesaj["content"])

    if sorgu := st.chat_input("Yapay zekaya soru sor..."):
        st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
        log_kaydet(f"Kullanıcı sorgusu: {sorgu[:50]}...")
        with st.chat_message("user"): st.markdown(sorgu)

        with st.spinner(f"Düşünüyor... ({secilen_model_adi})"):
            try:
                arama_metni = ""
                try:
                    res = tavily.search(query=sorgu, search_depth="basic")
                    arama_metni = "\n".join([r["content"] for r in res["results"]])
                    log_kaydet("İnternet araması (Tavily) başarıyla yapıldı.")
                except: pass
                
                sistem_mesaji = "Sen Eymen-GPT'sin. Akıl yürütmeni <dusunce> etiketi içine yaz, sonra cevabı net ver."
                k_msg = f"Soru: {sorgu}\n"
                if arama_metni: k_msg += f"İNTERNET: {arama_metni}\n"
                if st.session_state.dosya_bellegi: k_msg += f"DOSYA: {st.session_state.dosya_bellegi[:30000]}\n"

                msgs = [{"role": "system", "content": sistem_mesaji}] + st.session_state.mesaj_gecmisi[:-1] + [{"role": "user", "content": k_msg}]

                basarili = False
                for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                    try:
                        ai_baslangic = time.time()
                        response = client.chat.completions.create(messages=msgs, model=model_id, temperature=sicaklik_degeri)
                        basarili = True
                        log_kaydet(f"AI Yanıtı alındı. Model: {model_id}, Süre: {round(time.time()-ai_baslangic, 2)}sn")
                        break
                    except: continue

                if basarili:
                    cevap = response.choices[0].message.content
                    d_blog = ""
                    m = re.search(r'<(?:dusunce|düşünce|thinking)>(.*?)</(?:dusunce|düşünce|thinking)>', cevap, re.DOTALL | re.IGNORECASE)
                    if m:
                        d_blog = m.group(1).strip()
                        cevap = re.sub(r'<(?:dusunce|düşünce|thinking)>.*?</(?:dusunce|düşünce|thinking)>', '', cevap, flags=re.DOTALL | re.IGNORECASE).strip()

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": cevap})
                    with st.chat_message("assistant"):
                        if d_blog:
                            with st.expander("🧠 AI Düşünce Süreci"): st.write(d_blog)
                        st.markdown(cevap)
                else: 
                    log_kaydet("Tüm modeller çöktü/yanıt vermedi.", "error")
                    st.error("Modeller yanıt veremedi.")
            except Exception as e: 
                log_kaydet(f"Sohbet hatası: {e}", "error")
                st.error(f"Hata: {e}")

# =====================================================================
# MOD 2: RESSAM MODU
# =====================================================================
elif uygulama_modu == "Ressam Modu 🎨":
    st.markdown("### 🎨 AI Görsel Stüdyosu")
    resim_sorgu = st.text_input("Neyin resmini çizmek istersin?")
    
    if st.button("🖌️ Üret", use_container_width=True) and resim_sorgu:
        with st.spinner("Çiziliyor..."):
            log_kaydet(f"Görsel üretimi tetiklendi: {resim_sorgu}")
            st.session_state.son_resim_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(resim_sorgu)}?width=1024&height=1024&nologo=true"
            st.session_state.resim_hazir = True
            
    if st.session_state.resim_hazir:
        st.image(st.session_state.son_resim_url, use_container_width=True)

# =====================================================================
# MOD 3: SESLİ YANIT
# =====================================================================
elif uygulama_modu == "Sesli Yanıt 🗣️":
    st.markdown("### 🗣️ Metinden Sese (TTS)")
    sesli_sorgu = st.text_area("Metni girin:", height=150)
    hiz = st.checkbox("Yavaş Oku")
    
    if st.button("🎙️ Sese Çevir", use_container_width=True) and sesli_sorgu:
        log_kaydet("TTS işlemi başlatıldı.")
        with st.spinner("Sentezleniyor..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr', slow=hiz)
                ses_bellek = io.BytesIO()
                tts.write_to_fp(ses_bellek)
                ses_bellek.seek(0)
                st.session_state.son_ses_bytes = ses_bellek.getvalue()
                st.session_state.sesli_metin_hazir = True
                log_kaydet("TTS işlemi başarılı.")
            except Exception as e: 
                log_kaydet(f"TTS hatası: {e}", "error")
                st.error(f"Hata: {e}")
            
    if st.session_state.sesli_metin_hazir:
        st.audio(st.session_state.son_ses_bytes, format='audio/mp3')
        st.download_button("💾 İndir", st.session_state.son_ses_bytes, "ses.mp3", "audio/mp3", use_container_width=True)

# =====================================================================
# MOD 4: MÜZİSYEN MODU (GİZLİ KÜTÜPHANELİ)
# =====================================================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 DSP Müzik Stüdyosu (NoModelsMusic Core)")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: muzik_sorgu = st.text_input("Şarkı Tarifi:", placeholder="120 bpm synthwave...")
    with col2: hedef_dk = st.number_input("Süre (Dk)", 0.5, 10.0, 1.0, 0.5)
    with col3: fxler = st.multiselect("FX", ["compressor", "reverb", "chorus"], ["compressor"])

    if st.button("🎸 Üret (Render)", use_container_width=True) and muzik_sorgu:
        log_kaydet(f"Müzik üretimi başlatıldı. Tarz: {muzik_sorgu[:30]}..., Süre: {hedef_dk}dk")
        with st.spinner("Beste yapılıyor ve motor sentezliyor..."):
            try:
                s_msg = f'Sen müzisyen AI. Geçerli JSON iskeleti kur. {{"tempo":120,"global_fx":{json.dumps(fxler)},"kick_808":["K","-","K","-"]}} Sadece JSON.'
                
                basarili = False
                for model_id in [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]:
                    try:
                        resp = client.chat.completions.create(messages=[{"role":"system","content":s_msg},{"role":"user","content":muzik_sorgu}], model=model_id)
                        basarili = True
                        break
                    except: continue

                if basarili:
                    json_str = re.search(r'\{.*\}', resp.choices[0].message.content.strip(), re.DOTALL).group(0)
                    sarki_verisi = json.loads(json_str)
                    
                    st.info("Beste tamam! DSP Motoru dalgaları sentezliyor (Render ediliyor)...")
                    render_start = time.time()
                    
                    # 🚀 GİZLİ KÜTÜPHANE ÇAĞRISI
                    motor = ColossusEngine()
                    wav_ses = motor.render(sarki_verisi, hedef_dk)
                    
                    render_sure = round(time.time() - render_start, 2)
                    log_kaydet(f"Müzik render edildi. Süre: {render_sure} saniye.")
                    
                    try:
                        proc = subprocess.run(['ffmpeg','-i','pipe:0','-f','mp3','-b:a','192k','pipe:1'], input=wav_ses, capture_output=True, check=True)
                        st.audio(proc.stdout, format='audio/mp3')
                        st.download_button("💾 İndir (.MP3)", proc.stdout, "Muzik.mp3", "audio/mp3", use_container_width=True)
                        log_kaydet("FFMPEG MP3 dönüşümü başarılı.")
                    except:
                        st.warning("MP3 motoru (FFMPEG) bulunamadı. Orijinal WAV veriliyor.")
                        st.audio(wav_ses, format='audio/wav')
                        st.download_button("💾 İndir (.WAV)", wav_ses, "Muzik.wav", "audio/wav", use_container_width=True)
                        
                    with st.expander("🛠️ Yazılan Notalar (JSON)"): st.json(sarki_verisi)
                else: 
                    log_kaydet("Müzik besteleme AI hatası", "error")
                    st.error("Bağlantı koptu.")
            except Exception as e: 
                log_kaydet(f"Sentez hatası: {e}", "error")
                st.error(f"Kritik hata: {e}")
