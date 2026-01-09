import streamlit as st
import io

# Jeśli używasz plików docx/pdf, upewnij się, że masz zainstalowane biblioteki:
# pip install python-docx pypdf2
try:
    from docx import Document
    import PyPDF2
except ImportError:
    st.warning("⚠️ Brak bibliotek do czytania DOCX/PDF. Zainstaluj python-docx i pypdf2.")

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

st.title("🖋️ Dziennikarz Master PRO v10.2")

# --- FUNKCJE POMOCNICZE DO PLIKÓW ---
def read_file(uploaded_file):
    if uploaded_file.name.endswith('.txt'):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith('.docx'):
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif uploaded_file.name.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in pdf_reader.pages])
    return ""

# --- BOCZNY PANEL ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    typ_tekstu = st.radio(
        "Rodzaj publikacji:",
        ["News (Aktualności)", "Reportaż", "Publicystyka"],
        index=1 # Domyślnie ustawiony na Reportaż
    )
    
    # Zwiększony limit do 15k
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    
    st.markdown("---")
    st.info(f"Wybrany tryb: **{typ_tekstu}**\n\nLimit: **{target_chars}** znaków.")

# --- WEJŚCIE DANYCH (PLIKI + TEKST) ---
col_in1, col_in2 = st.columns(2)

with col_in1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe (PDF, DOCX, TXT):", 
                                     accept_multiple_files=True)

with col_in2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

# Łączenie źródeł
all_source_material = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source_material += f"\n\n--- Treść z pliku {f.name} ---\n" + read_file(f)

# --- PROMPT (MANIFEST) ---
instrukcja_stylu = f"""
Jesteś doświadczonym redaktorem. Napisz tekst w stylu 'Instytutu Gość Media'.
RODZAJ TEKSTU: {typ_tekstu}
DOCELOWA DŁUGOŚĆ: ok. {target_chars} znaków ze spacjami.

STRUKTURA OBOWIĄZKOWA:
1. Nadtytuł
2. Tytuł
3. Lid (na końcu dodaj: (Instytut Gość Media))
4. Sekcja 'Propozycje tytułów' (lista 5 sztuk)
5. Sekcja 'Propozycje lidów' (lista 3-5 sztuk, każdy z (Instytut Gość Media))
6. Treść główna (Cytaty w formie: — tekst —)
"""

if st.button("🚀 Generuj Materiał"):
    if all_source_material.strip():
        with st.spinner("Przetwarzam materiały..."):
            # Tutaj Twoja logika API (np. Gemini/GPT)
            # Na potrzeby testu:
            st.session_state.artykul = f"WYNIK DLA: {typ_tekstu}\n\n[Tu pojawi się wygenerowany artykuł na ok. {target_chars} znaków...]"
    else:
        st.error("Proszę dodać plik lub wkleić tekst źródłowy!")

# --- WYNIKI I LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    
    st.divider()
    
    col_stat1, col_stat2 = st.columns([1, 2])
    with col_stat1:
        st.metric("Liczba znaków", f"{dlugosc}", delta=f"{dlugosc - target_chars} różnicy")
    
    st.subheader("Finalny tekst:")
    st.code(tekst, language="text", wrap_lines=True)
    st.caption("💡 Użyj przycisku 'Copy' w rogu ramki.")