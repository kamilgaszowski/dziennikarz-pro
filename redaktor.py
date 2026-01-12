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

# --- CSS: KONTENER "CHAT-LIKE" ---
# Stylizacja ramki z przyklejonym nagłówkiem
st.markdown("""
<style>
    .editor-container {
        background-color: #0e1117;
        border: 1px solid #31333f;
        border-radius: 8px;
        margin-top: 10px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        position: relative;
    }
    
    .editor-header {
        background-color: #262730;
        padding: 10px 15px;
        border-bottom: 1px solid #31333f;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: sticky; /* PRZYKLEJENIE DO GÓRY */
        top: 0;
        z-index: 10;
    }

    .editor-title {
        color: #bdc6d5;
        font-family: sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .copy-btn-integrated {
        background-color: transparent;
        color: #fafafa;
        border: 1px solid #41444e;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .copy-btn-integrated:hover {
        background-color: #31333f;
        border-color: #fafafa;
    }

    .editor-content {
        padding: 20px;
        color: #fafafa;
        font-family: 'Source Code Pro', monospace;
        font-size: 0.95rem;
        line-height: 1.6;
        white-space: pre-wrap; /* Zawijanie wierszy */
        max-height: 75vh; /* Ramka ma max 75% wysokości ekranu */
        overflow-y: auto; /* Własny scroll wewnątrz ramki */
    }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v12.4")

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
    st.caption("v12.4 | Gemini 3 Pro")

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

# --- MANIFESTY (PROMPTY) ---
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

# --- WYNIKI: TYLKO JEDEN WIDOK ---
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

    # 2. KONTENER HTML (To jest ten właściwy element)
    safe_text = json.dumps(tekst) 
    
    st.markdown(f"""
        <div class="editor-container">
            <div class="editor-header">
                <div class="editor-title">
                    Gotowy Artykuł
                </div>
                <button class="copy-btn-integrated" onclick="copyToClipboard()">
                    📋 Kopiuj
                </button>
            </div>
            <div class="editor-content">{tekst}</div>
        </div>

        <script>
        function copyToClipboard() {{
            const text = {safe_text};
            navigator.clipboard.writeText(text).then(() => {{
                const btn = document.querySelector('.copy-btn-integrated');
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Skopiowano!';
                setTimeout(() => {{
                    btn.innerHTML = originalText;
                }}, 2000);
            }});
        }}
        </script>
    """, unsafe_allow_html=True)
    
    # 3. Pobieranie pliku (bez wyświetlania tekstu ponownie!)
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")