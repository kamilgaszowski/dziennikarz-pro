import streamlit as st
import google.generativeai as genai
import time
import io
import base64

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

# --- CSS: WYGLĄD CHAT-GPT STYLE ---
st.markdown("""
<style>
    /* Główny kontener - ciemna ramka */
    .chat-container {
        border: 1px solid #444;
        border-radius: 8px;
        background-color: #0e1117;
        margin-top: 20px;
        overflow: hidden; /* Ważne dla zaokrągleń */
        display: flex;
        flex-direction: column;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    /* Przyklejony nagłówek (Sticky Header) */
    .chat-header {
        background-color: #343541; /* Kolor nagłówka ChatGPT */
        padding: 10px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #444;
        position: sticky; /* TO PRZYKLEJA PASEK */
        top: 0;
        z-index: 100;
    }

    .header-title {
        color: #d1d5db;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Przycisk Kopiuj */
    .copy-btn {
        background-color: transparent;
        color: #d1d5db;
        border: 1px solid #565869;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .copy-btn:hover {
        background-color: #40414f;
        color: white;
        border-color: #acacbe;
    }

    /* Treść artykułu */
    .chat-content {
        padding: 20px;
        color: #ececf1;
        font-size: 1rem;
        line-height: 1.6;
        white-space: pre-wrap; /* Zachowuje akapity */
        max-height: 70vh; /* Maksymalna wysokość okna */
        overflow-y: auto; /* Własny pasek przewijania */
    }
    
    /* Scrollbar */
    .chat-content::-webkit-scrollbar {
        width: 8px;
    }
    .chat-content::-webkit-scrollbar-thumb {
        background: #565869;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.0")

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
    st.caption("v13.0 | Base64 Safe Copy")

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

# --- WYNIKI: BEZPIECZNE OKNO Z KOPIOWANIEM ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Górne menu korekty
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

    # 2. PRZYGOTOWANIE TREŚCI (BASE64) - TO NAPRAWIA "KRZAKI"
    # Zamieniamy tekst na kod, którego przeglądarka nie pomyli z HTML
    b64_text = base64.b64encode(tekst.encode('utf-8')).decode('utf-8')
    
    # SVG Ikonka kopiowania
    icon_svg = """<svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>"""

    # 3. RENDEROWANIE HTML
    html_code = f"""
    <div class="chat-container">
        <div class="chat-header">
            <div class="header-title">
                <span>📄</span> Gotowy Materiał
            </div>
            <button class="copy-btn" onclick="copyBase64()">
                {icon_svg} Kopiuj tekst
            </button>
        </div>
        <div class="chat-content" id="content-display">{tekst}</div>
    </div>

    <script>
    function copyBase64() {{
        // Odbieramy bezpieczny kod Base64 i zamieniamy z powrotem na tekst
        const b64 = "{b64_text}";
        
        try {{
            // Dekodowanie UTF-8 (dla polskich znaków)
            const binaryString = window.atob(b64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {{
                bytes[i] = binaryString.charCodeAt(i);
            }}
            const decoder = new TextDecoder('utf-8');
            const decodedText = decoder.decode(bytes);

            // Kopiowanie do schowka
            navigator.clipboard.writeText(decodedText).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.innerHTML = '✅ Skopiowano!';
                btn.style.borderColor = '#19c37d';
                btn.style.color = '#19c37d';
                
                setTimeout(() => {{
                    btn.innerHTML = '{icon_svg} Kopiuj tekst';
                    btn.style.borderColor = '#565869';
                    btn.style.color = '#d1d5db';
                }}, 2000);
            }});
        }} catch (err) {{
            console.error('Błąd kopiowania:', err);
            alert('Błąd kopiowania. Spróbuj ręcznie.');
        }}
    }}
    </script>
    """
    
    st.markdown(html_code, unsafe_allow_html=True)
    
    # Przycisk pobierania pod spodem
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")