import streamlit as st
import io

# Obsługa bibliotek (DOCX/PDF)
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v10.8")

if not HAS_LIBS:
    st.warning("⚠️ Brak bibliotek do czytania DOCX/PDF. Zainstaluj python-docx i pypdf2.")

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

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col_in2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał: {f.name} ---\n" + read_file(f)

# --- MANIFESTY (TWOJE INSTRUKCJE) ---
if typ_tekstu == "Wywiad":
    # Na podstawie wywiad.txt 
    prompt = f"""TRYB wywiad. Jesteś redaktorem. Zredaguj wywiad Q/A. 
    ZASADY: Wyłącznie materiał źródłowy. [cite: 4] Zakaz metajęzyka (np. 'w tej rozmowie'). [cite: 6]
    Nagłówki: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid zaczynający się od 'O'). [cite: 12, 16, 17]
    Konstrukcja: P: ... O: ... (6-12 bloków). [cite: 18, 19]
    Redakcja: Usuń 'ja' w 99%, napraw neologizmy. [cite: 28, 30]
    CEL: {target_chars} znaków (±300). [cite: 37]"""
else:
    # Na podstawie Instrukcja_artykul.txt 
    prompt = f"""TRYB article. Jesteś redaktorem prasowym. [cite: 39]
    ZASADY: Rdzeń z głównego materiału (2/3 treści). [cite: 43, 47] Zakaz słowa 'kapłan' (używaj: ksiądz, duchowny, duszpasterz). [cite: 57, 58]
    Cytaty: W ramce pauzowej (– Zdanie. –), min. 4 zdania. [cite: 71, 72]
    Nagłówki: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid). [cite: 77, 83]
    Pierwszy akapit: Relacja faktów (min. 3 informacje). [cite: 93, 97]
    CEL: {target_chars} znaków (±300). [cite: 85]"""

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner("Przetwarzam zgodnie z manifestem..."):
            # TUTAJ MUSISZ PODPIĄĆ SWOJE API, np:
            # response = model.generate_content(prompt + "\n\nMATERIAŁ:\n" + all_source)
            # st.session_state.artykul = response.text
            
            # Tymczasowo, żebyś widział, że kod działa:
            st.session_state.artykul = f"WYNIK DLA: {typ_tekstu}\n\n[API GOTOWE - TUTAJ POJAWI SIĘ TEKST]"
    else:
        st.error("Brak materiałów źródłowych!")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    st.metric(label="Liczba znaków", value=dlugosc, delta=f"{roznica} różnicy", delta_color="inverse")

    st.subheader("Finalny tekst:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(label="💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt", mime="text/plain")