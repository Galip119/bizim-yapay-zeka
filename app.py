"""
EYMEX NEXUS-CORE V17.0 - TITAN PRIME (AI OS + LATEX ENGINE)
"""

import streamlit as st
import time
import base64
import io
import datetime
import re
from openai import OpenAI
from gtts import gTTS


# ---------------- STATE ----------------
for key, default in {
    "otonom_aktif": False,
    "baslangic_zamani": time.time(),
    "loglar": [],
    "aktif_model": "mistral-8x7b",
    "secilen_model": "mistral-8x7b"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------- APP ----------------
st.set_page_config(
    page_title="Nexus-Core AI OS",
    layout="wide"
)

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=st.secrets.get("GITHUB_TOKEN", "")
)


# ---------------- MODELS ----------------
MODELS = [
    "mistral-8x7b",
    "gpt-4o-mini",
    "gpt-4o",
    "llama-3.3-70b",
    "cohere-command-r"
]


# ---------------- LATEX DETECTOR ----------------
def latex_bul(text):
    patterns = [
        r"\$.*?\$",        # inline math
        r"\\\[.*?\\\]",    # display math
        r"\\begin\{.*?\}"   # latex env
    ]
    return any(re.search(p, text) for p in patterns)


def latex_goster(text):
    """
    LaTeX varsa render eder yoksa normal text basar
    """
    if latex_bul(text):
        st.latex(text)
    else:
        st.write(text)


# ---------------- MODEL ROUTER ----------------
def model_yonlendir(gorsel=False, dosya=False):

    if gorsel or dosya:
        st.session_state.aktif_model = "gpt-4o"
        return "gpt-4o"

    st.session_state.aktif_model = st.session_state.secilen_model
    return st.session_state.secilen_model


# ---------------- LOG ----------------
def log(msg):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.loglar.append(f"[{t}] {msg}")


# ---------------- TTS ----------------
def ses(text):
    try:
        tts = gTTS(text=text[:400], lang="tr")
        buf = io.BytesIO()
        tts.write_to_fp(buf)

        b64 = base64.b64encode(buf.getvalue()).decode()

        st.components.v1.html(
            f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{b64}">
            </audio>
            """,
            height=0
        )
    except:
        pass


# ---------------- CORE ENGINE ----------------
def nexus(prompt, img=None, file=None):

    img_bytes = img.read() if img else None

    model = model_yonlendir(
        gorsel=(img_bytes is not None),
        dosya=(file is not None)
    )

    system = (
        "Sen Nexus-Core AI'sın. "
        "Matematik içeriklerinde LaTeX üret."
    )

    content = [{"type": "text", "text": prompt}]

    if img_bytes:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
            }
        })

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content}
    ]

    res = client.chat.completions.create(
        model=model,
        messages=messages
    )

    ans = res.choices[0].message.content

    log(f"{model} | {prompt[:30]}")

    return ans


# ---------------- UI ----------------
st.title("🧠 Nexus-Core AI OS Terminal")

st.sidebar.subheader("⚙ Model Paneli")

st.session_state.secilen_model = st.sidebar.selectbox(
    "Model",
    MODELS
)

st.sidebar.info(f"Aktif: {st.session_state.aktif_model}")


# ---------------- INPUTS ----------------
img = st.camera_input("📷 Kamera")
file = st.file_uploader("📄 Dosya", type=["png","jpg","jpeg","pdf","txt"])
prompt = st.text_input("💬 Soru")


# ---------------- RUN ----------------
if st.button("▶ Çalıştır") and prompt:

    with st.spinner("AI işliyor..."):

        result = nexus(prompt, img, file)

        st.subheader("📌 Çıktı")

        latex_goster(result)

        ses(result)


# ---------------- AUTO MODE ----------------
if st.sidebar.button("🚀 Otonom Başlat"):
    st.session_state.otonom_aktif = True

if st.sidebar.button("🛑 Durdur"):
    st.session_state.otonom_aktif = False


if st.session_state.otonom_aktif and img:

    with st.spinner("Otonom analiz..."):

        out = nexus("Bu görüntüyü analiz et", img)

        st.subheader("🤖 Otonom Sonuç")

        latex_goster(out)

        ses(out)

        time.sleep(2)

        st.rerun()


# ---------------- LOG PANEL ----------------
st.divider()
st.subheader("📜 Sistem Logları")

for l in reversed(st.session_state.loglar[-25:]):
    st.code(l)


# ---------------- SIDEBAR STATUS ----------------
st.sidebar.divider()

st.sidebar.metric(
    "Log",
    len(st.session_state.loglar)
)

st.sidebar.metric(
    "Uptime",
    str(int(time.time() - st.session_state.baslangic_zamani)) + " sn"
)
