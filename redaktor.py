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

st.title("🖋️ Dziennikarz Master PRO v10.5")

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
    st.header("⚙️ Ustawienia Redakcyjne")
    
    typ_tekstu = st.radio(
        "Rodzaj publikacji:", 
        ["News (Aktualności)", "Reportaż", "Wywiad"], 
        index=0
    )
    
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    
    st.markdown("---")
    st.info(f"Wybrany tryb: **{typ_tekstu}**\n\nLimit: **{target_chars}** znaków.")

# --- WEJŚCIE DANYCH (PLIKI + TEKST) ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    uploaded_files = st.file_uploader("1. Dodaj pliki źródłowe:", accept_multiple_files=True)
with col_in2:
    pasted_text = st.text_area("2. Lub wklej notatki/wywiady:", height=150)

# Łączenie materiałów źródłowych
all_source_material = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source_material += f"\n\n--- Materiał z pliku: {f.name} ---\n" + read_file(f)

# --- MANIFEST STYLU (PROMPT) ---
# To jest serce aplikacji, które instruuje AI jak ma pisać.
manifest = f"""
Jesteś doświadczonym redaktorem pracującym dla 'Instytutu Gość Media'. 
Twoim zadaniem jest opracowanie materiału na podstawie dostarczonych źródeł.

WYTYCZNE STYLU:
1. RODZAJ: {typ_tekstu}.
2. DŁUGOŚĆ: Celuj w około {target_chars} znaków ze spacjami.
3. STRUKTURA OBOWIĄZKOWA:
   - Nadtytuł (krótki, nad tytułem).
   - Tytuł (przyciągający uwagę, w stylu Gościa).
   - Lid (streszczenie, na końcu dodaj: (Instytut Gość Media)).
   - Propozycje tytułów (lista 5 różnych opcji).
   - Propozycje lidów (lista 3-5 opcji, każda zakończona: (Instytut Gość Media)).
   - Treść główna.

4. ZASADY FORMALNE:
   - Cytaty: Zawsze używaj pauz: — Tekst cytatu —
   - Styl: Rzeczowy, blisko ludzi, unikaj sztuczności.
   - Jeśli WYWIAD: Skup się na dynamicznym dialogu i ciekawych puentach.
   - Jeśli REPORTAŻ: Buduj obrazowe sceny, ale zachowaj strukturę (Nadtytuł/Lid).
"""

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source_material.strip():
        with st.spinner("Tworzę materiał zgodnie z Manifestem..."):
            # TUTAJ TWOJA LOGIKA API (np. OpenAI lub Gemini)
            # Przykład: 
            # response = wywolaj_api(manifest, all_source_material)
            # st.session_state.artykul = response
            
            # Placeholder dla testu (usuń to po podpięciu API):
            st.session_state.artykul = f"NADTYTUŁ\nUroczystość w diecezji\n\nTYTUŁ\nSwoje miejsce\n\nLID\nW wałbrzyskiej wspólnocie Sobięcina Paweł Kulesza przyjął święcenia... (Instytut Gość Media)\n\nTREŚĆ\n— Myślę, że najlepszym słowem będzie powiedzieć, że po prostu czuję się w końcu we właściwym miejscu — mówi bohater..."
    else:
        st.error("Wgraj pliki lub wklej materiały źródłowe!")

# --- WYNIKI I POPRAWIONY LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    
    # LICZNIK: Delta na czerwono tylko gdy przekroczymy limit
    # delta_color="inverse" sprawia, że dodatnia liczba (nadmiar) jest czerwona.
    st.metric(
        label="Aktualna liczba znaków", 
        value=dlugosc, 
        delta=f"{roznica} względem celu",
        delta_color="inverse"
    )

    st.subheader("Gotowy tekst (Manifest Gość Media):")
    # To okno ma wbudowany przycisk "Copy" w prawym górnym rogu!
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.caption("☝️ Kopiuj przyciskiem w rogu ramki powyżej.")

    # Pobieranie pliku
    st.download_button(
        label="💾 Pobierz jako .txt",
        data=tekst,
        file_name="artykul_gotowy.txt",
        mime="text/plain"
    )