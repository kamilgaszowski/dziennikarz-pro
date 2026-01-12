import streamlit as st
import io

# Obsługa bibliotek do plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

st.title("🖋️ Dziennikarz Master PRO v10.6")

if not HAS_LIBS:
    st.warning("⚠️ Brak bibliotek DOCX/PDF. Zainstaluj: pip install python-docx pypdf2")

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
        st.error(f"Błąd pliku {uploaded_file.name}: {e}")
    return ""

# --- PANEL BOCZNY (USTAWIENIA) ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    typ_tekstu = st.radio(
        "Rodzaj publikacji:", 
        ["News (Aktualności)", "Reportaż", "Wywiad"], 
        index=0
    )
    
    # Rozszerzony limit do 15 000 znaków
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("1. Dodaj pliki źródłowe:", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("2. Lub wklej materiały tutaj:", height=150)

# Łączenie materiałów
all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- DYNAMICZNE MANIFESTY (TWOJE PROMPTY) ---

if typ_tekstu == "Wywiad":
    # Manifest na podstawie pliku wywiad.txt
    current_manifest = f"""
    TRYB wywiad. Jesteś redaktorem. Twoim zadaniem jest zredagować z materiału wywiad w formie Q/A. [cite: 1]
    Nie dodajesz treści, tylko porządkujesz i wygładzasz język. [cite: 2]
    
    ZASADY:
    - Pracuj wyłącznie na materiale źródłowym. [cite: 4]
    - Zakaz metajęzyka i komentowania przebiegu rozmowy. [cite: 6, 7]
    - Akapity oddzielaj wyłącznie pustą linią. [cite: 11]
    - Przygotuj 5 zestawów nagłówków (nadtytuł, tytuł, lid). [cite: 12]
    - Lidy w wywiadzie: zaczynają się od słowa 'O', forma: O [czymś], o [czymś] mówi [kto]. [cite: 18]
    - Forma Q/A: P: ... O: ... (Minimum 6, maksimum 12 bloków). [cite: 19]
    - Usuń zbędne 'ja' w 99% przypadków. [cite: 28]
    - DŁUGOŚĆ: Celuj w {target_chars} znaków (±300). [cite: 37]
    """
else:
    # Manifest na podstawie pliku Instrukcja_artykul.txt (dla News i Reportaż)
    current_manifest = f"""
    TRYB article. Jesteś redaktorem prasowym. Stwórz artykuł informacyjny. [cite: 39]
    
    ZASADY:
    - Pracuj wyłącznie na materiale źródłowym. [cite: 41]
    - Rdzeń tekstu: Co najmniej dwie trzecie treści musi pochodzić ze źródła głównego. [cite: 48]
    - Zakaz metajęzyka i klisz. [cite: 51, 57]
    - Terminologia: Zakaz używania słowa 'kapłan'. Używaj: ksiądz, duchowny, duszpasterz. [cite: 58, 59]
    - Cytaty: W ramce pauzowej (– Zdanie. –), minimum 4 zdania. [cite: 72]
    - Nagłówki: 5 zestawów (nadtytuł, tytuł do 3 słów, lid). [cite: 78, 83]
    - DŁUGOŚĆ: Celuj w {target_chars} znaków (±300). [cite: 85]
    """

# --- PRZYCISK GENEROWANIA ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"Generuję {typ_tekstu}..."):
            # Tutaj Twoje wywołanie API (np. model.generate_content(current_manifest + all_source))
            # Poniżej placeholder:
            st.session_state.artykul = f"WYNIK DLA: {typ_tekstu}\n\n[Tu pojawi się treść wygenerowana zgodnie z manifestem...]"
    else:
        st.error("Wgraj pliki lub wklej materiały!")

# --- WYNIKI I POPRAWIONY LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    
    # Delta color "inverse" sprawia, że ujemna różnica (niedomiar) jest zielona
    st.metric(
        label="Liczba znaków", 
        value=dlugosc, 
        delta=f"{roznica} względem celu",
        delta_color="inverse"
    )

    st.subheader("Finalny tekst:")
    # st.code NIE WYWALA BŁĘDÓW i ma wbudowany przycisk kopiowania
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(
        label="💾 Pobierz .txt",
        data=tekst,
        file_name=f"{typ_tekstu.lower()}.txt",
        mime="text/plain"
    )