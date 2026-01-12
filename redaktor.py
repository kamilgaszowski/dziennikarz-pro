import streamlit as st
import google.generativeai as genai
import time
import io
import html

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

# --- CSS: STYLIZACJA (Bezpieczna) ---
st.markdown("""
<style>
    /* Kontener edytora */
    .editor-wrapper {
        border: 1px solid #31333f;
        border-radius: 8px;
        background-color: #0e1117;
        margin-top: 15px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        position: relative;
    }

    /* Przyklejony nagłówek */
    .editor-header {
        background-color: #262730;
        padding: 8px 15px;
        display: flex;
        justify-content: flex-end; /* Ikona po prawej */
        align-items: center;
        border-bottom: 1px solid #31333f;
        position: sticky;
        top: 0;
        z-index: 100;
        height: 45px;
    }

    /* Przycisk kopiowania */
    .copy-btn {
        background: transparent;
        border: 1px solid #41444e;
        color: #e0e0e0;
        cursor: pointer;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }

    .copy-btn:hover {
        background-color: #31333f;
        border-color: #fafafa;
        color: #fff;
    }

    /* Pole tekstowe (wygląda jak tekst, działa jak input) */
    .editor-textarea {
        background-color: #0e1117;
        color: #fafafa;
        border: none;
        width: 100%;
        padding: 20px;
        font-family: 'Source Code Pro', monospace;
        font-size: 15px;
        line-height: 1.6;
        resize: none;
        outline: none;
        min-height: 500px;
        height: 70vh; /* Wysokość okna */
        white-space: pre-wrap;
    }
    
    .editor-textarea::-webkit-scrollbar {
        width: 10px;
        background: #0e1117;
    }
    .editor-textarea::-webkit-scrollbar-thumb {
        background: #31333f;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v12.6")

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
    st.caption("v12.6 | Safe Mode")

# --- WEJŚCIE DANYCH ---
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    uploaded_audio = st.file_uploader("🎤 Audio (MP3/WAV):", type=['mp3', 'wav', 'm4a'])
with col_b:
    uploaded_files = st.file_uploader("📄 Pliki (PDF/DOCX):", accept_multiple_files=True)
with col_c:
    pasted_text = st.text_area("✍️ Notatki:", height=100)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- {f.name} ---\n" + read_text_file(f)

# [cite_start]--- MANIFESTY [cite: 1-38, 39-107] ---
strict_length = f"CEL: {target_chars} znaków netto (bez enterów)."
if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length} Redaguj Q/A. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów (nadtytuł, tytuł, lid na 'O')."
else:
    manifest = f"TRYB article/news. {strict_length} Redaktor prasowy. Rdzeń: 2/3 treści ze źródła. Cytaty w ramce pauzowej. Zakaz słowa 'kapłan'."

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content = [manifest]
    if all_source: content.append(f"TEKST:\n{all_source}")
    if uploaded_audio:
        with st.spinner("Przesyłam audio do Gemini 3..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": time.sleep(2); audio_file = genai.get_file(audio_file.name)
            content.append(audio_file)

    with st.spinner("Generowanie tekstu..."):
        try:
            response = model.generate_content(content)
            st.session_state.artykul = response.text
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI: BEZPIECZNE RENDEROWANIE ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Przyciski korekty i licznik
    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("✂️ Skróć 20%"):
        res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()
    if c2.button("➕ Wydłuż 20%"):
        res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    # 2. KOMPONENT HTML (Budowany bezpieczną metodą .replace)
    # To zapobiega błędom "Wysypało się coś"
    
    escaped_text = html.escape(tekst) # Zabezpieczenie treści
    
    # Szablon HTML (JavaScript i CSS są tutaj bezpieczne)
    html_template = """
    <div class="editor-wrapper">
        <div class="editor-header">
            <button class="copy-btn" onclick="safeCopy()">
                📋 Kopiuj tekst
            </button>
        </div>
        <textarea id="main-textarea" class="editor-textarea" readonly>__CONTENT__</textarea>
    </div>

    <script>
    function safeCopy() {
        const textarea = document.getElementById("main-textarea");
        textarea.select();
        try {
            document.execCommand("copy");
            const btn = document.querySelector(".copy-btn");
            btn.innerHTML = "✅ Skopiowano!";
            setTimeout(() => { btn.innerHTML = "📋 Kopiuj tekst"; }, 2000);
        } catch (err) {
            console.error("Błąd kopiowania", err);
        }
        window.getSelection().removeAllRanges();
    }
    </script>
    """
    
    # Wstawienie treści w bezpieczny sposób
    final_html = html_template.replace("__CONTENT__", escaped_text)
    
    st.markdown(final_html, unsafe_allow_html=True)
    
    # Przycisk pobierania
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")