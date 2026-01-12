import streamlit as st
import io

# Obsługa bibliotek do plików (PDF i DOCX)
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

st.title("🖋️ Dziennikarz Master PRO v10.7")

# Powiadomienie o bibliotekach
if not HAS_LIBS:
    st.warning("⚠️ Brak bibliotek do czytania DOCX/PDF. Zainstaluj je komendą: pip install python-docx pypdf2")

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
    
    typ_tekstu = st.radio(
        "Rodzaj publikacji:", 
        ["News (Aktualności)", "Reportaż", "Wywiad"], 
        index=0
    )
    
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: **{typ_tekstu}** | Cel: **{target_chars}** znaków")

# --- WEJŚCIE DANYCH (PLIKI + TEKST) ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col_in2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

# Łączenie materiałów źródłowych
all_source_material = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source_material += f"\n\n--- Materiał z pliku: {f.name} ---\n" + read_file(f)

# --- ŁADOWANIE MANIFESTÓW (Z TWOICH PLIKÓW) ---

if typ_tekstu == "Wywiad":
    # Pełny manifest z wywiad.txt 
    manifest = f"""
    TRYB wywiad. Jesteś redaktorem. Twoim zadaniem jest zredagować z materiału wywiad w formie Q/A, 
    ale z porządną redakcją językową wypowiedzi. Nie dodajesz treści, tylko porządkujesz i wygładzasz język.
    Nie korzystaj z zapisanych wspomnień. Traktuj to jako zadanie jednorazowe.
    Pracuj wyłącznie na materiale źródłowym. Nie dopisuj faktów.
    ZAKAZY STYLU: Zakaz metajęzyka (w tej rozmowie, pada przykład itp.). Pytania naturalne.
    Unikaj dwukropków i średników. Zakaz separatorów ---. Akapity oddzielaj pustą linią.
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania). Zakaz powtórzeń w zestawie.
    LIDY W WYWIADZIE: Każdy musi zaczynać się od słowa O. Forma: O [czymś], o [czymś] mówi [kto].
    KONSTRUKCJA: Forma Q/A (P: ... O: ...). Liczba bloków: 6-12.
    REDAKCJA: Zachowaj styl rozmówcy. Usuń 'ja' w 99%. Napraw neologizmy (dodaj sekcję ZAMIANY na końcu jeśli były).
    DŁUGOŚĆ: TARGET_CHARS = {target_chars} znaków (±300).
    """
else:
    # Pełny manifest z Instrukcja_artykul.txt 
    manifest = f"""
    TRYB article. Jesteś redaktorem prasowym. Stwórz artykuł informacyjny.
    Nie korzystaj z zapisanych wspomnień. Pracuj wyłącznie na materiale źródłowym.
    RDZEŃ: Co najmniej 2/3 treści musi pochodzić ze źródła głównego.
    ZAKAZY: Zakaz metajęzyka i komentowania wypowiedzi. Maksymalnie jedno 'mówi/dodaje' na akapit.
    Zakaz słowa 'kapłan' (używaj: ksiądz, duchowny, duszpasterz, proboszcz).
    CYTATY: W ramce pauzowej (– Zdanie. –), min. 4 zdania. 3 zdania kontekstu przed i po.
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid). Zakaz powtórzeń w zestawie.
    STRUKTURA: Relacja z wydarzenia lub tekst problemowy. Pierwszy akapit: wprowadzenie (3 twarde fakty).
    DŁUGOŚĆ: TARGET_CHARS = {target_chars} znaków (±300).
    Akapity oddzielaj pustą linią. Zakaz list wypunktowanych.
    """

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source_material.strip():
        with st.spinner("Przetwarzam materiały zgodnie z instrukcjami..."):
            
            # --- UWAGA: Tutaj musisz wstawić swoje wywołanie API ---
            # Przykład (jeśli używasz Gemini): 
            # response = model.generate_content(manifest + "\\n\\nMATERIAŁ:\\n" + all_source_material)
            # wygenerowany_tekst = response.text
            
            # Na razie zostawiam symulację, żeby kod się uruchomił:
            wygenerowany_tekst = f"WYNIK DLA: {typ_tekstu}\\n\\n[Tu pojawi się treść wygenerowana przez Twoje API...]"
            
            st.session_state.artykul = wygenerowany_tekst
    else:
        st.error("Proszę najpierw wgraj pliki lub wklej materiały!")

# --- WYNIKI I POPRAWIONY LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    
    # Delta_color="inverse" sprawia, że ujemna różnica (niedobór) jest ZIELONA
    st.metric(
        label="Liczba znaków", 
        value=dlugosc, 
        delta=f"{roznica} względem celu",
        delta_color="inverse"
    )

    st.subheader("Finalny tekst:")
    # st.code automatycznie dodaje przycisk "Copy" i nie wywala błędów
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.caption("☝️ Przycisk kopiowania znajduje się w prawym górnym rogu ramki powyżej.")

    st.download_button(
        label="💾 Pobierz .txt",
        data=tekst,
        file_name=f"{typ_tekstu.lower()}_gotowy.txt",
        mime="text/plain"
    )