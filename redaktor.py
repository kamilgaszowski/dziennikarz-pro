import streamlit as st
import google.generativeai as genai
import time
import io
import json
import os
from datetime import datetime

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

# --- TRWAŁA HISTORIA (Nowość v13.6) ---
HISTORY_FILE = "historia_redaktora.json"

def load_history_from_disk():
    """Ładuje historię z pliku JSON przy starcie."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history_to_disk(history_list):
    """Zapisuje całą historię do pliku JSON."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

# Inicjalizacja stanu (ładujemy z dysku, jeśli session_state jest pusty)
if "history" not in st.session_state:
    st.session_state.history = load_history_from_disk()

# --- CSS: FIXED SCROLL (To co działało w v13.2) ---
st.markdown("""
<style>
    div[data-testid="stCodeBlock"] {
        max-height: 75vh !important; 
        overflow-y: auto !important;
        border: 1px solid #41444e;
        border-radius: 8px;
        background-color: #0e1117;
    }
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

st.title("🖋️ Dziennikarz Master PRO v13.6")

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
    """Dodaje wpis do RAM i na Dysk."""
    timestamp = datetime.now().strftime("%d-%m %H:%M") # Dodano datę
    entry = {
        "time": timestamp,
        "type": type_label,
        "content": text,
        "chars": count_net_chars(text)
    }
    # 1. Dodaj do sesji (RAM)
    st.session_state.history.insert(0, entry)
    # 2. Zapisz na dysk (TRWAŁOŚĆ)
    save_history_to_disk(st.session_state.history)

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    
    # --- HISTORIA (TRWAŁA) ---
    st.divider()
    st.subheader("🗄️ Historia (Trwała)")
    
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            # Unikalny klucz przycisku
            btn_key = f"hist_{i}_{item['time']}"
            label = f"{item['time']} | {item['type']} ({item['chars']})"
            
            if st.button(label, key=btn_key):
                st.session_state.artykul = item['content']
                st.rerun()
        
        st.markdown("---")
        if st.button("🗑️ Usuń wszystko (trwale)"):
            st.session_state.history = []
            save_history_to_disk([]) # Czyścimy plik
            st.rerun()
    else:
        st.caption("Historia jest pusta.")

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

# --- MANIFESTY (PEŁNE Z TWOICH PLIKÓW) ---
manifest_wywiad = f"""
Jesteś redaktorem Master PRO. Tworzysz WYWIAD w formie Q/A.
ZASADY (Baza + Twoje Manifesty):
- Cel: ok. {target_chars} znaków netto.
- ZAKAZ METAJĘZYKA (np. "w tej rozmowie", "pada przykład", "wróćmy do"). Pytania jako bezpośredni zwrot (2. osoba).
- ANTY-KOMPRESJA: Zachowuj sceny, przykłady, dopowiedzenia. Nie spłaszczaj do streszczeń.
- REDAKCJA: Język mówiony -> pisany (bez zmiany sensu). Usuń "yyy", powtórzenia i nadmiarowe "ja".
- STRUKTURA: Q/A. Nagłówki: Nadtytuł, Tytuł (max 3 słowa), Lid (na "O").
- KOTWICE: Na końcu wylistuj "perełki" (najmocniejsze cytaty).
- ZAKAZ słowa "kapłan" (używaj: ksiądz, duchowny etc.).
"""

manifest_news = f"""
Jesteś redaktorem Master PRO. Tworzysz NEWS / REPORTAŻ.
ZASADY (Baza + Twoje Manifesty):
- Cel: ok. {target_chars} znaków netto.
- STRUKTURA: Nadtytuł, Tytuł, Lid.
- BONUS: Dodaj 5 propozycji tytułów i 3 propozycji lidów.
- ZAKAZ: Powtórzeń słów w nagłówkach. Lid i 1. akapit nie od daty.
- STYL: Reporterski, precyzyjny. Bez "te słowa pokazują".
- CYTATY: Bez cudzysłowów, w ramce pauzowej (– ... –). Min. 4 zdania w cytacie.
- KONTEKST: Min. 3 zdania przed i po cytacie.
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
            # ZAPIS TRWAŁY
            add_to_history(new_text, typ_tekstu)
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Narzędzia
    c1, c2, c3 = st.columns([1, 1, 2])
    
    if c1.button("✂️ Skróć 20%"):
        with st.spinner("Skracam..."):
            res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("➕ Wydłuż 20%"):
        with st.spinner("Wydłużam..."):
            res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Długi)")
            st.rerun()
            
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    # 2. OKNO WYNIKU
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    # 3. Pobieranie
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")