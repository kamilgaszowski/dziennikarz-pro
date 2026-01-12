import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd konfiguracji API: {e}")

# Obsługa bibliotek do plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.5")

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

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków (bez enterów):", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- MANIFESTY Z POPRAWIONĄ INSTRUKCJĄ DŁUGOŚCI ---
strict_length_instruction = f"""
WAŻNE: Docelowa długość tekstu to równe {target_chars} znaków. 
Limit ten nie obejmuje znaków nowej linii (enterów). 
Jeśli materiału źródłowego jest mało, rozwiń wątki zgodnie ze stylem. 
Jeśli jest za dużo, skracaj bez litości, zachowując esencję. 
Bądź precyzyjny – AI często pisze za długo, Ty napisz dokładnie tyle, ile wskazano.
"""

if typ_tekstu == "Wywiad":
    manifest = f"""
    TRYB wywiad. {strict_length_instruction}
    Jesteś redaktorem. Zredaguj wywiad Q/A. Pracuj wyłącznie na materiale źródłowym.
    ZAKAZY: Metajęzyk, dwukropki, średniki, separatory, słowo 'kapłan'.
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania zaczynający się od 'O').
    KONSTRUKCJA: Forma Q/A (P: ... O: ...). Liczba bloków: 6-12.
    REDAKCJA: Usuń 'ja' w 99%. Napraw neologizmy (sekcja ZAMIANY na końcu).
    """
else:
    manifest = f"""
    TRYB article/news. {strict_length_instruction}
    Jesteś redaktorem prasowym. Rdzeń: 2/3 treści ze źródła głównego.
    ZAKAZY: Metajęzyk, słowo 'kapłan' (używaj: ksiądz, duszpasterz, proboszcz).
    CYTATY: Ramka pauzowa: – Zdanie. Zdanie. Zdanie. Zdanie. – (min. 4 zdania).
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid).
    STRUKTURA: Relacja (3 twarde fakty w 1. akapicie) lub tekst problemowy.
    ZAKOŃCZENIE: Konkret lub cytat. Brak ogólnych refleksji.
    """

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"Generowanie tekstu..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁ ŹRÓDŁOWY:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API: {e}")
    else:
        st.error("Proszę dodać materiały źródłowe!")

# --- WYNIKI I NOWY LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    
    # NOWA LOGIKA: Liczymy znaki ignorując entery (\n)
    dlugosc_bez_enterow = len(tekst.replace("\n", ""))
    roznica = dlugosc_bez_enterow - target_chars
    
    st.divider()
    
    # Licznik pokazuje teraz wartość netto (bez enterów)
    st.metric(
        label="Liczba znaków (netto - bez enterów)", 
        value=dlugosc_bez_enterow, 
        delta=f"{roznica} względem celu", 
        delta_color="inverse"
    )

    st.subheader("Finalny tekst:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(label="💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt", mime="text/plain")