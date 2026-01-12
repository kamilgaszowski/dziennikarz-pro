import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Zmieniono model na gemini-3 zgodnie z Twoją prośbą
    model = genai.GenerativeModel('gemini-3') 
except Exception as e:
    st.error(f"Błąd konfiguracji API: {e}")

# Obsługa bibliotek do plików (PDF i DOCX)
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.2")

if not HAS_LIBS:
    st.warning("⚠️ Brak bibliotek do czytania DOCX/PDF. Zainstaluj: pip install python-docx pypdf2")

# --- FUNKCJA CZYTANIA PLIKÓW ---
def read_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS:
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except Exception as e:
        st.error(f"Błąd czytania pliku {uploaded_file.name}: {e}")
    return ""

# --- PANEL BOCZNY (USTAWIENIA) ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("Wklej materiały pomocnicze:", height=150)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- MANIFESTY (TWOJE INSTRUKCJE) ---
if typ_tekstu == "Wywiad":
    manifest = f"""
    TRYB wywiad. Zadanie jednorazowe, pracuj wyłącznie na materiale źródłowym. 
    Nie dopisuj treści, tylko porządkuj i wygładzasz język. Pokaż tylko gotowy wynik.
    ZAKAZY: Metajęzyk (np. 'w tej rozmowie'), dwukropki, średniki, separatory.
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania zaczynający się od 'O').
    KONSTRUKCJA: Q/A (P: ... O: ...) 6-12 bloków. 
    REDAKCJA: Usuń 'ja' w 99%, napraw neologizmy.
    CEL: {target_chars} znaków (±300).
    """
else:
    manifest = f"""
    TRYB article. Zadanie jednorazowe na materiale użytkownika. 
    Co najmniej 2/3 treści musi pochodzić ze źródła głównego.
    ZAKAZY: Metajęzyk, komentowanie wypowiedzi (np. 'zdradza', 'wyznaje').
    TERMINOLOGIA: Nie używaj słowa 'kapłan'. Zastąp: ksiądz, duchowny, duszpasterz.
    CYTATY: Ramka pauzowa (– Zdanie. –), min. 4 zdania cytatu.
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid).
    STRUKTURA: Relacja (3 twarde fakty w 1 akapicie).
    CEL: {target_chars} znaków (±300).
    """

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"Gemini 3 generuje {typ_tekstu}..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁY:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API Gemini 3: {e}. Sprawdź, czy nazwa modelu jest poprawna dla Twojego regionu.")
    else:
        st.error("Proszę dodać materiały źródłowe!")