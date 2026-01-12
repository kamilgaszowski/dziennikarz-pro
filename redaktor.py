import streamlit as st
import google.generativeai as genai
import time
import io
import json

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

# --- CSS: WYGLĄD IDEALNIE JAK W STREAMLIT ---
st.markdown("""
<style>
    /* Kontener główny - ramka */
    .st-code-container {
        border: 1px solid #31333f;
        border-radius: 8px;
        background-color: #0e1117;
        margin-top: 10px;
        overflow: hidden;
        position: relative;
        display: flex;
        flex-direction: column;
        max-height: 75vh; /* Maksymalna wysokość okna */
    }

    /* Nagłówek przyklejony (Sticky) */
    .st-code-header {
        background-color: #262730;
        padding: 8px 12px;
        display: flex;
        justify-content: flex-end; /* Ikona po prawej */
        align-items: center;
        border-bottom: 1px solid #31333f;
        position: sticky;
        top: 0;
        z-index: 10;
        height: 40px;
    }

    /* Przycisk z ikoną */
    .copy-button-icon {
        background: transparent;
        border: none;
        cursor: pointer;
        color: #fafafa;
        opacity: 0.7;
        padding: 4px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        transition: opacity 0.2s, background-color 0.2s;
    }

    .copy-button-icon:hover {
        opacity: 1;
        background-color: #31333f;
    }

    /* Pole tekstowe udające zwykły tekst */
    .st-code-content {
        background-color: #0e1117;
        color: #fafafa;
        border: none;
        width: 100%;
        padding: 15px;
        font-family: 'Source Code Pro', monospace;
        font-size: 14px;
        line-height: 1.5;
        resize: none; /* Blokada zmiany rozmiaru myszką */
        outline: none;
        overflow-y: auto; /* Scroll wewnątrz */
        min-height: 400px;
        height: 100%;
        white-space: pre-wrap;
    }
    
    /* Ukrycie scrollbara dla estetyki (opcjonalne) */
    .st-code-content::-webkit-scrollbar {
        width: 8px;
        background: #0e1117;
    }
    .st-code-content::-webkit-scrollbar-thumb {
        background: #31333f;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v12.5")

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
    st.caption("v12.5 | Native Look & Fix")

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

# --- MANIFESTY ---
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

# --- WYNIKI: JEDNO OKNO Z DZIAŁAJĄCYM KOPIOWANIEM ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Przyciski korekty i licznik (poza ramką)
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

    # 2. KOMPONENT ARTYKUŁU (HTML + JS + SVG)
    # SVG ikonki kopiowania (dwie karteczki)
    copy_icon_svg = """
    <svg viewBox="0 0 24 24" aria-hidden="true" height="16" width="16" fill="currentColor">
        <path d="M7 6V3a3 3 0 0 1 3-3h7a3 3 0 0 1 3 3v7a1 1 0 0 1-1 1h-2v3a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3zM9 2a1 1 0 0 0-1 1v3h8a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H10zM6 8v9a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V8H8a1 1 0 0 0-1 1zm9-5h2a1 1 0 0 1 1 1v7h-2V3z"></path>
    </svg>
    """
    
    # Bezpieczne kodowanie tekstu
    safe_text = json.dumps(tekst) 
    
    # Renderowanie HTML
    st.markdown(f"""
        <div class="st-code-container">
            <div class="st-code-header">
                <button class="copy-button-icon" onclick="copyNative()" title="Kopiuj do schowka">
                    {copy_icon_svg}
                </button>
            </div>
            <textarea id="article-content" class="st-code-content" readonly>{tekst}</textarea>
        </div>

        <script>
        function copyNative() {{
            const textArea = document.getElementById('article-content');
            textArea.select();
            textArea.setSelectionRange(0, 99999); /* Dla urządzeń mobilnych */
            
            try {{
                document.execCommand('copy');
                const btn = document.querySelector('.copy-button-icon');
                const originalColor = btn.style.color;
                btn.style.color = '#4caf50'; // Zielony kolor sukcesu
                setTimeout(() => {{ btn.style.color = ''; }}, 1000);
            }} catch (err) {{
                console.error('Błąd kopiowania', err);
            }}
            
            // Odznacz tekst po skopiowaniu
            window.getSelection().removeAllRanges();
        }}
        </script>
    """, unsafe_allow_html=True)
    
    # Przycisk pobierania na samym dole
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")