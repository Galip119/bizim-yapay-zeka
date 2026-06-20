import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
import json
import urllib.parse
import os
from gtts import gTTS
import numpy as np
import scipy.io.wavfile as wav
import io
import re

from pypdf import PdfReader
from docx import Document
import openpyxl
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

st.set_page_config(layout="centered", page_title="Eymen-GPT Gelişmiş")

# --- OTURUM HAFIZASI ---
if "form_num" not in st.session_state: st.session_state.form_num = 0
if "mesaj_gecmisi" not in st.session_state: st.session_state.mesaj_gecmisi = []
if "cevap_hazir" not in st.session_state: st.session_state.cevap_hazir = False
if "son_cevap" not in st.session_state: st.session_state.son_cevap = ""
if "son_dusunce" not in st.session_state: st.session_state.son_dusunce = ""
if "resim_hazir" not in st.session_state: st.session_state.resim_hazir = False
if "son_resim_url" not in st.session_state: st.session_state.son_resim_url = ""

metin_anahtari = f"sorgu_{st.session_state.form_num}"
dosya_anahtari = f"dosya_{st.session_state.form_num}"

github_token = st.secrets["GITHUB_TOKEN"]
tavily_key = st.secrets["TAVILY_API_KEY"]

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=github_token)
tavily = TavilyClient(api_key=tavily_key)

MODELS = {
    "Mistral-8x7B": "Mistral-8x7B",
    "GPT-4o Mini": "gpt-4o-mini",
    "Llama-3.1-70B": "meta-llama-3.1-70b-instruct",
    "Cohere Command R": "cohere-command-r",
    "GPT-4o": "gpt-4o"
}

st.sidebar.title("⚙️ Ayarlar")

uygulama_modu = st.sidebar.radio("Mod Seçimi:", ["Sohbet & Analiz 💬", "Ressam Modu 🎨", "Sesli Yanıt Modu 🗣️", "Müzisyen Modu 🎵"])

st.sidebar.markdown("---")
st.sidebar.write("Kotası biten modelden otomatik olarak diğerine geçilir.")
secilen_model_adi = st.sidebar.selectbox("Bir Model Seçin:", list(MODELS.keys()))
secilen_model_id = MODELS[secilen_model_adi]

if st.sidebar.button("🧹 Sohbet Geçmişini Temizle"):
    st.session_state.mesaj_gecmisi = []
    st.rerun()

st.title("Eymen-GPT 🚀")

# ==========================================
# 1. MOD: SOHBET VE ANALİZ
# ==========================================
if uygulama_modu == "Sohbet & Analiz 💬":
    for mesaj in st.session_state.mesaj_gecmisi:
        with st.chat_message(mesaj["role"]):
            st.markdown(mesaj["content"])

    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        sorgu = st.chat_input("Bana bir şeyler sor...", key=metin_anahtari)
    with col2:
        yuklenen_dosya = st.file_uploader("Dosya Analizi", type=["txt", "pdf", "docx", "xlsx", "py", "html", "htm", "json", "xml", "png", "jpg", "jpeg"], label_visibility="collapsed", key=dosya_anahtari)

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

    if sorgu or dosya_icerigi:
        if sorgu:
            st.session_state.mesaj_gecmisi.append({"role": "user", "content": sorgu})
            with st.chat_message("user"):
                st.markdown(sorgu)

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

                api_mesajlari = [{"role": "system", "content": sistem_mesaji}]
                for msg in st.session_state.mesaj_gecmisi[:-1]:
                    api_mesajlari.append(msg)
                api_mesajlari.append({"role": "user", "content": kullanici_mesaji})

                yedek_modeller = [secilen_model_id] + [m for m in MODELS.values() if m != secilen_model_id]
                basarili_oldu = False
                
                for aktif_model in yedek_modeller:
                    try:
                        response = client.chat.completions.create(
                            messages=api_mesajlari,
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

                    st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": temiz_cevap})
                    
                    with st.chat_message("assistant"):
                        if dusunce_blogu:
                            with st.expander("🧠 Eymen-GPT'nin Düşünme Adımlarını Göster"): 
                                st.write(dusunce_blogu)
                        st.markdown(temiz_cevap)

            except Exception as e: st.error(f"Bir hata oluştu: {e}")

# ==========================================
# 2. MOD: RESSAM MODU
# ==========================================
elif uygulama_modu == "Ressam Modu 🎨":
    st.markdown("### 🎨 Hayal Gücünü Ekrana Yansıt")
    
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
# 3. MOD: SESLİ YANIT MODU
# ==========================================
elif uygulama_modu == "Sesli Yanıt Modu 🗣️":
    st.markdown("### 🗣️ Eymen-GPT Sesli Asistan")
    st.write("Yazdığın her şeyi gerçekçi bir sesle sana okuyabilirim.")
    
    sesli_sorgu = st.text_input("Ne duymak istersin?", placeholder="Örn: Bana yıldızları anlat", key=f"sesli_input_{st.session_state.form_num}")
    oku_butonu = st.button("🎙️ Seslendir")

    if oku_butonu and sesli_sorgu:
        with st.spinner("Sesi kasede kaydediyorum..."):
            try:
                tts = gTTS(text=sesli_sorgu, lang='tr')
                dosya_yolu = "eymen_ses.mp3"
                tts.save(dosya_yolu)
                
                with open(dosya_yolu, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mp3')
                
                st.success("İşte sesin hazır! 🎧")
            except Exception as e:
                st.error(f"Seslendirme hatası: {e}")

# ==========================================
# 4. MOD: 10 KANALLI DEV MÜZİK MOTORU 🎵
# ==========================================
elif uygulama_modu == "Müzisyen Modu 🎵":
    st.markdown("### 🎵 Eymen-GPT 10 Kanallı Dev Stüdyo")
    st.write("Sınırsız ses aralığı (C1'den B7'ye), 10 farklı enstrüman ve çökmeyen optimize sistem!")
    
    muzik_sorgu = st.text_input("Şarkının tarzı ve hissi nedir?", placeholder="Örn: Epik bir film müziği, kopmalık EDM veya karanlık trap rap...", key=f"dev_muzik_{st.session_state.form_num}")
    uret_butonu = st.button("🎧 Orkestrayı Başlat")

    if uret_butonu and muzik_sorgu:
        with st.spinner("Eymen-GPT devasa stüdyoyu kuruyor... (Lütfen bekleyin)"):
            try:
                notalar_listesi = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                notalar_sozlugu = {"-": 0.0}
                for oktav in range(1, 8):
                    for i, nota in enumerate(notalar_listesi):
                        n = (oktav - 4) * 12 + (i - 9) 
                        notalar_sozlugu[f"{nota}{oktav}"] = 440.0 * (2.0 ** (n / 12.0))

                sistem_mesaji = """Sen çılgın bir müzik dehasısın. Kullanıcının verdiği hisse göre tam 16 adımlık bir müzik iskeleti oluştur.
                SADECE GEÇERLİ JSON FORMATINDA YAZ. Başka hiçbir kelime veya kod bloğu kullanma.
                {
                    "tempo": 120,
                    "kick": ["K","-","K","-","K","-","K","-","K","-","K","-","K","-","K","-"],
                    "snare": ["-","-","S","-","-","-","S","-","-","-","S","-","-","-","S","-"],
                    "hihat": ["H","H","H","H","H","H","H","H","H","H","H","H","H","H","H","H"],
                    "perc": ["-","C","-","-","-","-","-","-","-","C","-","-","-","-","-","-"],
                    "sub_bas": ["C2","-","C2","-","C2","-","C2","-","C2","-","C2","-","C2","-","C2","-"],
                    "slap_bas": ["-","G2","-","-","-","G2","-","-","-","G2","-","-","-","G2","-","-"],
                    "akor_pad": ["C4","-","-","-","C4","-","-","-","C4","-","-","-","C4","-","-","-"],
                    "arp_synth": ["C5","E5","G5","C6","C5","E5","G5","C6","C5","E5","G5","C6","C5","E5","G5","C6"],
                    "lead_melodi": ["E5","-","-","D5","C5","-","-","B4","A4","-","-","G4","F4","-","-","E4"],
                    "armoni": ["G5","-","-","F#5","E5","-","-","D5","C5","-","-","B4","A4","-","-","G4"]
                }
                Tüm diziler KESİNLİKLE 16 elemanlı olmalı. Notalar C1-B7 arasıdır. Davullar için K, S, H, C, - kullan.
                """
                
                response = client.chat.completions.create(
                    model=secilen_model_id,
                    messages=[{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": muzik_sorgu}],
                    temperature=0.6
                )
                
                json_str = response.choices[0].message.content.strip()
                
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    
                sarki_verisi = json.loads(json_str)
                
                sample_rate = 44100
                adim_suresi = (60.0 / sarki_verisi.get("tempo", 120)) / 4.0
                samples_per_step = int(sample_rate * adim_suresi)
                t = np.linspace(0, adim_suresi, samples_per_step, endpoint=False)
                
                def uret_kick(): return np.sin(2 * np.pi * np.linspace(120, 30, samples_per_step) * t) * np.exp(-15 * t) * 1.5
                def uret_snare(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-25 * t) * 0.8
                def uret_hihat(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-60 * t) * 0.3
                def uret_perc(): return np.random.uniform(-1, 1, samples_per_step) * np.exp(-5 * t) * 0.5
                
                def uret_sub_bas(f): return np.sin(2 * np.pi * f * t) * 1.0 if f > 0 else np.zeros(samples_per_step)
                def uret_slap_bas(f): return (2 * (t * f - np.floor(t * f + 0.5))) * np.exp(-8 * t) * 0.6 if f > 0 else np.zeros(samples_per_step)
                def uret_akor_pad(f): return 0.3 * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * (f*1.5) * t)) * np.exp(-0.5 * t) if f > 0 else np.zeros(samples_per_step)
                def uret_arp_synth(f): return 0.4 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-10 * t) if f > 0 else np.zeros(samples_per_step)
                def uret_lead_melodi(f):
                    if f == 0: return np.zeros(samples_per_step)
                    vibrato = np.sin(2 * np.pi * 5 * t) * 3 
                    return 0.5 * np.sin(2 * np.pi * (f + vibrato) * t) * np.exp(-2 * t)
                def uret_armoni(f): return 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-3 * t) if f > 0 else np.zeros(samples_per_step)

                ana_ses = np.array([])
                tekrar_sayisi = 8 
                
                def guvenli_liste(isim):
                    liste = sarki_verisi.get(isim, ["-"]*16)
                    if len(liste) < 16: liste += ["-"] * (16 - len(liste))
                    return liste

                kanallar = {
                    "kick": guvenli_liste("kick"), "snare": guvenli_liste("snare"), "hihat": guvenli_liste("hihat"),
                    "perc": guvenli_liste("perc"), "sub_bas": guvenli_liste("sub_bas"), "slap_bas": guvenli_liste("slap_bas"),
                    "akor_pad": guvenli_liste("akor_pad"), "arp_synth": guvenli_liste("arp_synth"),
                    "lead_melodi": guvenli_liste("lead_melodi"), "armoni": guvenli_liste("armoni")
                }
                
                for loop_idx in range(tekrar_sayisi):
                    for i in range(16):
                        katman = np.zeros(samples_per_step)
                        
                        cal_davul = True if loop_idx >= 1 and loop_idx < (tekrar_sayisi - 1) else False 
                        cal_lead = True if loop_idx >= 2 and loop_idx < (tekrar_sayisi - 1) else False 
                        
                        if cal_davul:
                            if kanallar["kick"][i] == "K": katman += uret_kick()
                            if kanallar["snare"][i] == "S": katman += uret_snare()
                            if kanallar["hihat"][i] == "H": katman += uret_hihat()
                            if kanallar["perc"][i] == "C": katman += uret_perc()
                            katman += uret_slap_bas(notalar_sozlugu.get(kanallar["slap_bas"][i], 0.0))
                        
                        katman += uret_sub_bas(notalar_sozlugu.get(kanallar["sub_bas"][i], 0.0))
                        katman += uret_akor_pad(notalar_sozlugu.get(kanallar["akor_pad"][i], 0.0))
                        katman += uret_arp_synth(notalar_sozlugu.get(kanallar["arp_synth"][i], 0.0))
                        
                        if cal_lead:
                            katman += uret_lead_melodi(notalar_sozlugu.get(kanallar["lead_melodi"][i], 0.0))
                            katman += uret_armoni(notalar_sozlugu.get(kanallar["armoni"][i], 0.0))
                        
                        ana_ses = np.concatenate((ana_ses, katman))
                
                max_val = np.max(np.abs(ana_ses))
                if max_val > 0:
                    ana_ses = np.int16(ana_ses / max_val * 32767)
                else:
                    ana_ses = np.int16(ana_ses)
                
                byte_io = io.BytesIO()
                wav.write(byte_io, sample_rate, ana_ses)
                
                st.audio(byte_io.getvalue(), format='audio/wav')
                st.success(f"🎵 {tekrar_sayisi*16} Adımlık Şarkın Hazır! (Tempo: {sarki_verisi.get('tempo', 120)} BPM)")
                
                with st.expander("🛠️ Devasa Orkestra Kayıt Kodlarını İncele"):
                    st.json(sarki_verisi)
                    
            except json.JSONDecodeError:
                st.error("Yapay zeka notaları yazarken harf hatası yaptı. Lütfen butona tekrar basarak yeniden oluşturmasını iste.")
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")
