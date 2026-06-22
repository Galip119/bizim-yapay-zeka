import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import re
import urllib.parse
import io
import os
import subprocess
import tempfile
from gtts import gTTS

# Dosya okuma kütüphaneleri
from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

st.set_page_config(
    layout="wide",
    page_title="Eymen-GPT Ultimate",
    initial_sidebar_state="expanded"
)

# =========================
# OTURUM HAFIZASI
# =========================

if "form_num" not in st.session_state:
    st.session_state.form_num = 0

if "mesaj_gecmisi" not in st.session_state:
    st.session_state.mesaj_gecmisi = []

if "dosya_bellegi" not in st.session_state:
    st.session_state.dosya_bellegi = ""

if "resim_hazir" not in st.session_state:
    st.session_state.resim_hazir = False

if "son_resim_url" not in st.session_state:
    st.session_state.son_resim_url = ""

if "sesli_metin_hazir" not in st.session_state:
    st.session_state.sesli_metin_hazir = False

if "son_ses_bytes" not in st.session_state:
    st.session_state.son_ses_bytes = None


# =========================
# API ANAHTARLARI
# =========================

try:
    github_token = st.secrets["GITHUB_TOKEN"]
    tavily_key = st.secrets["TAVILY_API_KEY"]

except:
    st.error("❌ API anahtarları bulunamadı!")
    st.stop()


client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token
)

tavily = TavilyClient(api_key=tavily_key)


# =========================
# MODELLER
# =========================

MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}


# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Sistem Ayarları")

uygulama_modu = st.sidebar.radio(
    "Mod Seçimi:",
    [
        "Sohbet & Analiz 💬",
        "Ressam Modu 🎨",
        "Sesli Yanıt 🗣️",
        "Müzisyen Modu 🎵"
    ]
)

st.sidebar.markdown("---")

secilen_model_adi = st.sidebar.selectbox(
    "Bir Model Seçin:",
    list(MODELS.keys())
)

secilen_model_id = MODELS[secilen_model_adi]


if st.sidebar.button(
    "🧹 Sistemi Temizle",
    use_container_width=True
):
    st.session_state.mesaj_gecmisi = []
    st.session_state.dosya_bellegi = ""
    st.session_state.resim_hazir = False
    st.session_state.sesli_metin_hazir = False
    st.rerun()


st.title("Eymen-GPT Ultimate 🚀")


# ==================================================
# 1. MOD: SOHBET VE ANALİZ
# ==================================================

if uygulama_modu == "Sohbet & Analiz 💬":

    yuklenen_dosya = st.file_uploader(
        "Dosya Yükle",
        type=[
            "txt",
            "pdf",
            "docx",
            "xlsx",
            "py",
            "html",
            "htm",
            "json",
            "xml",
            "png",
            "jpg",
            "jpeg"
        ]
    )

    if yuklenen_dosya is not None:

        dosya_adi = yuklenen_dosya.name.lower()
        icerik = ""

        with st.spinner("Dosya işleniyor..."):
            try:

                if dosya_adi.endswith(
                    (".txt", ".py", ".xml")
                ):
                    icerik = (
                        yuklenen_dosya
                        .read()
                        .decode("utf-8")
                    )

                elif dosya_adi.endswith(".pdf"):

                    pdf = PdfReader(
                        yuklenen_dosya
                    )

                    icerik = "\n".join(
                        [
                            sayfa.extract_text()
                            for sayfa in pdf.pages
                            if sayfa.extract_text()
                        ]
                    )

                elif dosya_adi.endswith(".docx"):
                    doc = Document(yuklenen_dosya)
                    icerik = "\n".join(
                        [p.text for p in doc.paragraphs]
                    )

                elif dosya_adi.endswith(".xlsx"):

                    wb = openpyxl.load_workbook(
                        yuklenen_dosya,
                        data_only=True
                    )

                    satirlar = []

                    for sayfa in wb.sheetnames:
                        ws = wb[sayfa]

                        satirlar.append(
                            f"--- Sayfa: {sayfa} ---"
                        )

                        for satir in ws.iter_rows(values_only=True):

                            hucreler = [
                                str(hucre)
                                for hucre in satir
                                if hucre is not None
                            ]

                            if hucreler:
                                satirlar.append(
                                    " | ".join(hucreler)
                                )

                    icerik = "\n".join(satirlar)


                elif dosya_adi.endswith(
                    (".html", ".htm")
                ):
                    soup = BeautifulSoup(
                        yuklenen_dosya.read().decode("utf-8"),
                        "html.parser"
                    )

                    icerik = soup.get_text(
                        separator="\n",
                        strip=True
                    )


                elif dosya_adi.endswith(".json"):

                    icerik = json.dumps(
                        json.load(yuklenen_dosya),
                        indent=2,
                        ensure_ascii=False
                    )


                elif dosya_adi.endswith(
                    (".png", ".jpg", ".jpeg")
                ):

                    st.image(
                        yuklenen_dosya,
                        width=300
                    )

                    try:
                        icerik = pytesseract.image_to_string(
                            Image.open(yuklenen_dosya),
                            lang="tur+eng"
                        )
                    except:
                        st.warning(
                            "OCR okunamadı."
                        )


                if icerik:
                    st.session_state.dosya_bellegi = icerik

                    st.success(
                        f"📎 {yuklenen_dosya.name} hafızaya alındı!"
                    )


            except Exception as e:
                st.error(f"Hata: {e}")

    else:
        st.session_state.dosya_bellegi = ""


    for mesaj in st.session_state.mesaj_gecmisi:

        with st.chat_message(
            mesaj["role"]
        ):
            st.markdown(
                mesaj["content"]
            )


    if sorgu := st.chat_input(
        "Sorunu yaz..."
    ):

        st.session_state.mesaj_gecmisi.append(
            {
                "role": "user",
                "content": sorgu
            }
        )

        with st.chat_message("user"):
            st.markdown(sorgu)

        with st.spinner("Düşünüyor..."):

            try:
                arama_metni = ""

                try:
                    sonuc = tavily.search(
                        query=sorgu,
                        search_depth="basic"
                    )

                    arama_metni = "\n".join(
                        [
                            r["content"]
                            for r in sonuc["results"]
                        ]
                    )

                except:
                    pass

# ==========================================
# 3. MOD: SESLİ YANIT
# ==========================================
elif uygulama_modu == "Sesli Yanıt 🗣️":
    sesli_sorgu = st.text_area(
        "Seslendirilecek metni girin:",
        height=150
    )

    if st.button("🎙️ Sese Çevir", use_container_width=True) and sesli_sorgu:
        with st.spinner("Ses oluşturuluyor..."):
            try:
                tts = gTTS(
                    text=sesli_sorgu,
                    lang="tr",
                    slow=False
                )

                ses_bellek = io.BytesIO()
                tts.write_to_fp(ses_bellek)
                ses_bellek.seek(0)

                st.session_state.son_ses_bytes = ses_bellek.getvalue()
                st.session_state.sesli_metin_hazir = True

            except Exception as e:
                st.error(f"Hata: {e}")

    if st.session_state.sesli_metin_hazir:
        st.audio(
            st.session_state.son_ses_bytes,
            format="audio/mp3"
        )

        st.download_button(
            label="💾 MP3 Olarak İndir",
            data=st.session_state.son_ses_bytes,
            file_name="eymen_ses.mp3",
            mime="audio/mp3",
            use_container_width=True
        )


# ==========================================
# 4. MOD: MÜZİSYEN MODU
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":

    st.markdown("### 🎵 NoModelsMusic Dev Stüdyo")

    col_m1, col_m2 = st.columns([3, 1])

    with col_m1:
        muzik_sorgu = st.text_input(
            "Şarkıyı tarif et:",
            placeholder="Örn: 80s synthwave, hareketli, elektronik..."
        )

    with col_m2:
        hedef_dk = st.number_input(
            "Süre (Dakika)",
            min_value=0.5,
            max_value=10.0,
            value=2.0,
            step=0.5
        )

    if st.button(
        "🎸 Müziği Üret",
        use_container_width=True
    ) and muzik_sorgu:

        with st.spinner(
            f"{hedef_dk} dakikalık müzik besteleniyor..."
        ):
            try:
                sistem_mesaji = """
Sen profesyonel bir müzik yapımcısısın.
Kullanıcının tarifine göre NoModelsMusic için
16 adımlık geçerli JSON üret.

Sadece JSON yaz.
Tüm diziler 16 elemanlı olmalıdır.
Notalar C1 ile B7 arasında olmalıdır.
"""
                basarili = False

                for model_id in [secilen_model_id] + [
                    m for m in MODELS.values()
                    if m != secilen_model_id
                ]:
                    try:
                        response = client.chat.completions.create(
                            messages=[
                                {
                                    "role": "system",
                                    "content": sistem_mesaji
                                },
                                {
                                    "role": "user",
                                    "content": muzik_sorgu
                                }
                            ],
                            model=model_id,
                            temperature=0.7
                        )

                        basarili = True
                        break

                    except:
                        continue


                if basarili:

                    json_str = response.choices[0].message.content.strip()

                    m = re.search(
                        r"\{.*\}",
                        json_str,
                        re.DOTALL
                    )

                    if m:
                        json_str = m.group(0)

                    sarki_verisi = json.loads(json_str)

                    import NoModelsMusic


                    # WAV üret
                    ses_dosyasi_wav = NoModelsMusic.motoru_calistir(
                        sarki_verisi,
                        hedef_dakika=hedef_dk
                    )


                    # Varsayılan WAV
                    ses_verisi = ses_dosyasi_wav
                    ses_format = "audio/wav"
                    dosya_adi = "Eymen_Sarki.wav"


                    # FFmpeg varsa MP3'e çevir
                    try:
                        process = subprocess.run(
                            [
                                "ffmpeg",
                                "-i",
                                "pipe:0",
                                "-f",
                                "mp3",
                                "-b:a",
                                "192k",
                                "pipe:1"
                            ],
                            input=ses_dosyasi_wav,
                            capture_output=True,
                            check=True
                        )

                        ses_verisi = process.stdout
                        ses_format = "audio/mp3"
                        dosya_adi = "Eymen_Sarki.mp3"


                    except Exception:
                        st.warning(
                            "⚠️ MP3 dönüştürülemedi. WAV olarak veriliyor."
                        )


                    st.audio(
                        ses_verisi,
                        format=ses_format
                    )

                    st.success("🎵 Şarkı Hazır!")


                    st.download_button(
                        label=f"💾 {dosya_adi} indir",
                        data=ses_verisi,
                        file_name=dosya_adi,
                        mime=ses_format,
                        use_container_width=True
                    )


                    with st.expander("🛠️ Kanallar (JSON)"):
                        st.json(sarki_verisi)

                else:
                    st.error("❌ Model bağlantısı kurulamadı.")

            except Exception as e:
                st.error(f"Hata: {e}")
