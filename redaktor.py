import streamlit as st
import io

# Obsługa bibliotek zewnętrznych
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

st.title("🖋️ Dziennikarz Master PRO v10.3")

if not HAS_LIBS:
    st.warning("⚠️ Do obsługi PDF/DOCX potrzebne są biblioteki. Zainstaluj je komendą: pip install python-docx pypdf2")

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

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Publicystyka"], index=1)
    
    # Rozszerzony limit do 15 000 znaków
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("Dodaj pliki (PDF, DOCX, TXT):", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

# Łączenie materiałów
all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner("Piszę artykuł..."):
            # Symulacja wyniku (tutaj Twoje API)
            st.session_state.artykul = f"WYNIK DLA: {typ_tekstu}\n\n[Tu pojawi się Twój tekst na ok. {target_chars} znaków...]"
    else:
        st.error("Brak materiałów źródłowych!")

# --- WYNIKI (BEZ BŁĘDU COPY_BUTTON) ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    
    st.divider()
    
    # Statystyki
    c1, c2 = st.columns([1, 2])
    c1.metric("Liczba znaków", f"{dlugosc}", delta=f"{dlugosc - target_chars} różnicy")

    # Finalny tekst z wbudowanym kopiowaniem (st.code)
    st.subheader("Finalny tekst:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.caption("☝️ Przycisk 'Copy' znajdziesz w prawym górnym rogu powyższej ramki.")

    # Przycisk pobierania .txt (Działa poprawnie)
    st.download_button(
        label="💾 Pobierz jako .txt",
        data=tekst,
        file_name="artykul.txt",
        mime="text/plain"
    )