import streamlit as st
import google.generativeai as genai
import time
import io
from datetime import datetime # Do oznaczania czasu w historii

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

# --- INICJALIZACJA HISTORII ---
if "history" not in st.session_state:
    st.session_state.history = []

# --- CSS: MAGICZNY ATRYBUT FIXED/STICKY ---
st.markdown("""
<style>
    /* Namierzamy kontener kodu Streamlit */
    div[data-testid="stCodeBlock"] {
        max-height: 75vh !important; 
        overflow-y: auto !important;
        border: 1px solid #41444e;
        border-radius: 8px;
        background-color: #0e1117;
    }

    /* Pasek przewijania */
    div[data-testid="stCodeBlock"]::-webkit-scrollbar {
        width: 12px;
    }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-track {
        background: #0e1117;
    }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-thumb {
        background-color: #262730;
        border-radius: 10px;
        border: 2px solid #0e1117;
    }
    
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.5")

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

def add_to_history(text, type_label):
    """Dodaje tekst do historii sesji"""
    timestamp = datetime.now().strftime("%H:%M")
    entry = {
        "time": timestamp,
        "type": type_label,
        "content": text,
        "chars": count_net_chars(text)
    }
    # Dodajemy na początek listy (najnowsze na górze)
    st.session_state.history.insert(0, entry)

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    
    # --- SEKCJA HISTORII W PASEKU BOCZNYM ---
    st.divider()
    st.subheader("🗄️ Historia sesji")
    
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            # Przycisk dla każdego wpisu w historii
            label = f"{item['time']} | {item['type']} ({item['chars']} zn.)"
            if st.button(label, key=f"hist_{i}"):
                # Przywracanie tekstu
                st.session_state.artykul = item['content']
                st.rerun()
        
        if st.button("🗑️ Wyczyść historię"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("Brak zapisanych tekstów w tej sesji.")

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
manifest_wywiad = f"""
Jesteś redaktorem Master PRO. Tworzysz WYWIAD w formie Q/A.
ZASADY:
- Docelowa długość: ok. {target_chars} znaków netto.
- ZAKAZ METAJĘZYKA (np. "w tej rozmowie"). Pytania w 2. osobie.
- ANTY-KOMPRESJA: Nie spłaszczaj wypowiedzi. Zachowuj sceny i przykłady.
- REDAKCJA: Wygładzaj język mówiony, usuwaj nadmiarowe "ja".
- STRUKTURA: Q/A. Nagłówki: Nadtytuł, Tytuł, Lid (na "O").
- ZAKAZ słowa "kapłan".
"""

manifest_news = f"""
Jesteś redaktorem Master PRO. Tworzysz ARTYKUŁ / RELACJĘ.
ZASADY:
- Docelowa długość: ok. {target_chars} znaków netto.
- STRUKTURA: Nadtytuł, Tytuł, Lid + propozycje. Lid nie od daty.
- STYL: Reporterski, precyzyjny. Bez "te słowa pokazują".
- CYTATY: Bez cudzysłowów, format pauzowy (– ... –). Min. 4 zdania w cytacie.
- ZAKAZ słowa "kapłan".
"""

if typ_tekstu == "Wywiad":
    manifest = manifest_wywiad
else:
    manifest = manifest_news

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content = [manifest]
    if all_source: content.append(f"TEKST:\n{all_source}")
    
    if uploaded_audio:
        with st.spinner("Przesyłam audio do Gemini 3..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": 
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            content.append(audio_file)

    with st.spinner("Generowanie tekstu..."):
        try:
            response = model.generate_content(content)
            new_text = response.text
            st.session_state.artykul = new_text
            # ZAPIS DO HISTORII
            add_to_history(new_text, typ_tekstu)
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Narzędzia edycji
    c1, c2, c3 = st.columns([1, 1, 2])
    
    if c1.button("✂️ Skróć 20%"):
        with st.spinner("Skracam..."):
            res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            # ZAPIS DO HISTORII WERSJI SKRÓCONEJ
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("➕ Wydłuż 20%"):
        with st.spinner("Wydłużam..."):
            res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            # ZAPIS DO HISTORII WERSJI WYDŁUŻONEJ
            add_to_history(res.text, f"{typ_tekstu} (Długi)")
            st.rerun()
            
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    # 2. GŁÓWNE OKNO (Sticky Copy)
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    # 3. Pobieranie
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")