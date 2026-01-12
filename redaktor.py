import streamlit as st
import google.generativeai as genai
import time
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd API: {e}")

# Biblioteki plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

# --- CSS: PRZYKLEJONY PASEK NARZĘDZI ---
st.markdown("""
    <style>
    .sticky-container {
        position: -webkit-sticky;
        position: sticky;
        top: 2.8rem;
        z-index: 1000;
        background-color: #0e1117;
        padding: 10px;
        border-bottom: 2px solid #31333f;
        margin-bottom: 20px;
    }
    .copy-btn {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v12.1")

# --- POMOCNIKI ---
def count_net_chars(text):
    return len(text.replace("\n", "").replace("\r", ""))

def read_text_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS:
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except: return ""
    return ""

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    st.divider()
    st.caption("v12.1 | Sticky Copy Mode")

# --- WEJŚCIE DANYCH ---
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    uploaded_audio = st.file_uploader("🎤 Nagranie audio:", type=['mp3', 'wav', 'm4a'])
with col_b:
    uploaded_files = st.file_uploader("📄 Pliki (PDF/DOCX):", accept_multiple_files=True)
with col_c:
    pasted_text = st.text_area("✍️ Notatki:", height=100)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- {f.name} ---\n" + read_text_file(f)

# --- MANIFESTY ---
strict_length = f"CEL: {target_chars} znaków netto (bez enterów)."
if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length} Redaguj Q/A. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów."
else:
    manifest = f"TRYB article/news. {strict_length} Redaktor prasowy. Rdzeń: 2/3 treści. Cytaty w ramce pauzowej. Zakaz słowa 'kapłan'."

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content = [manifest]
    if all_source: content.append(f"TEKST:\n{all_source}")
    if uploaded_audio:
        with st.spinner("AI słucha nagrania..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": time.sleep(2); audio_file = genai.get_file(audio_file.name)
            content.append(audio_file)

    with st.spinner("Generowanie..."):
        try:
            response = model.generate_content(content)
            st.session_state.artykul = response.text
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI Z PRZYPIĘTYM PASKIEM ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # --- PRZYPIĘTY PASEK (HTML + JS) ---
    # Ten element będzie zawsze widoczny na górze podczas przewijania
    escaped_text = tekst.replace("'", "\\'").replace("\n", "\\n")
    st.markdown(f"""
        <div class="sticky-container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="color: white; font-size: 1.1rem;">
                    <b>Licznik Netto: {netto}</b> | Cel: {target_chars} ({roznica})
                </div>
                <button class="copy-btn" onclick="copyToClipboard()">📋 KOPIUJ ARTYKUŁ</button>
            </div>
        </div>
        <script>
        function copyToClipboard() {{
            const text = `{escaped_text}`;
            navigator.clipboard.writeText(text).then(() => {{
                alert('Skopiowano artykuł do schowka!');
            }});
        }}
        </script>
    """, unsafe_allow_html=True)

    # Przyciski korekty pod paskiem
    c1, c2 = st.columns(2)
    if c1.button("✂️ Skróć o 20%"):
        res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()
    if c2.button("➕ Wydłuż o 20%"):
        res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()

    st.subheader("Treść materiału:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")