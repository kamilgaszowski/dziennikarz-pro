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

# --- CSS: TUTAJ JEST TWOJE "FIXED/STICKY" ---
st.markdown("""
<style>
    /* Główna ramka (kontener) */
    .custom-container {
        border: 1px solid #41444e;
        border-radius: 8px;
        background-color: #0e1117;
        margin-top: 15px;
        overflow: hidden; 
        display: flex;
        flex-direction: column;
        position: relative;
    }

    /* --- O TO CHODZIŁO: PRZYKLEJONY NAGŁÓWEK --- */
    .sticky-header {
        background-color: #262730;
        padding: 10px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #41444e;
        
        /* ATRYBUT, KTÓREGO BRAKOWAŁO: */
        position: sticky; 
        top: 0;
        z-index: 100; /* Zawsze na wierzchu */
    }
    /* ------------------------------------------ */

    .header-title {
        color: #fafafa;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Przycisk kopiowania */
    .copy-btn {
        background: transparent;
        border: 1px solid #565869;
        color: #d1d5db;
        cursor: pointer;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .copy-btn:hover {
        background-color: #40414f;
        border-color: #fafafa;
        color: #fff;
    }

    /* Treść artykułu (to ona się przewija) */
    .scrollable-content {
        padding: 20px;
        color: #fafafa;
        font-family: 'Source Code Pro', monospace;
        font-size: 0.95rem;
        line-height: 1.6;
        white-space: pre-wrap; 
        max-height: 70vh;    /* Ramka ma max 70% ekranu */
        overflow-y: auto;    /* Wewnątrz pojawia się suwak */
    }
    
    /* Wygląd paska przewijania */
    .scrollable-content::-webkit-scrollbar { width: 10px; }
    .scrollable-content::-webkit-scrollbar-track { background: #0e1117; }
    .scrollable-content::-webkit-scrollbar-thumb { background: #31333f; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.3")

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
    st.caption("v13.3 | Sticky + Base64")

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

# --- WYNIKI: JEDNO OKNO (HTML + STICKY CSS) ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Górne menu (Licznik i przyciski edycji)
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

    # 2. PRZYGOTOWANIE TREŚCI (BASE64) 
    # To zapobiega błędom "matrixa" na ekranie
    b64_text = base64.b64encode(tekst.encode('utf-8')).decode('utf-8')
    
    # Ikona (dwie karteczki)
    icon_svg = """<svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="14" width="14" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>"""

    # 3. RENDEROWANIE OKNA (HTML)
    # Zwróć uwagę na klasę 'sticky-header' użytą poniżej
    html_code = f"""
    <div class="custom-container">
        <div class="sticky-header">
            <div class="header-title">Gotowy Artykuł</div>
            <button class="copy-btn" onclick="copySafe()">
                {icon_svg} Kopiuj
            </button>
        </div>
        <div class="scrollable-content">{tekst}</div>
    </div>

    <script>
    function copySafe() {{
        const b64 = "{b64_text}";
        try {{
            const bin = window.atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const txt = new TextDecoder('utf-8').decode(bytes);
            
            navigator.clipboard.writeText(txt).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.innerHTML = '✅ Skopiowano!';
                btn.style.color = '#4caf50';
                btn.style.borderColor = '#4caf50';
                setTimeout(() => {{ 
                    btn.innerHTML = '{icon_svg} Kopiuj'; 
                    btn.style.color = '#d1d5db';
                    btn.style.borderColor = '#565869';
                }}, 2000);
            }});
        }} catch (e) {{ console.error(e); }}
    }}
    </script>
    """
    st.markdown(html_code, unsafe_allow_html=True)
    
    # 4. Pobieranie pliku
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")