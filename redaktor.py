import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API (Pobiera klucz z Twoich 'Secrets')
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Zmiana na 'gemini-1.5-flash' dla lepszej stabilności (naprawia błąd 404)
    model = genai.GenerativeModel('gemini-1.5-flash')
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
st.title("🖋️ Dziennikarz Master PRO v11.1")

# Ostrzeżenie o brakujących bibliotekach (z Twojego screena)
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

# --- PANEL BOCZNY (USTAWIENIA) ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    # Zmieniono 'Publicystyka' na 'Wywiad' zgodnie z wytycznymi
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
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

# --- ŁADOWANIE MANIFESTÓW Z TWOICH PLIKÓW ---
if typ_tekstu == "Wywiad":
    manifest = f"""
    TRYB wywiad[cite: 1]. Zadanie jednorazowe, pracuj wyłącznie na materiale źródłowym[cite: 3, 4]. 
    Nie dopisuj treści, tylko porządkuj i wygładzasz język[cite: 2]. Pokaż tylko gotowy wynik[cite: 5].
    ZAKAZY: Metajęzyk (np. 'w tej rozmowie'), dwukropki, średniki, separatory[cite: 6, 8, 11].
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania zaczynający się od 'O')[cite: 12, 16, 17].
    KONSTRUKCJA: Q/A (P: ... O: ...) 6-12 bloków[cite: 18, 19]. Styl eksploracyjny[cite: 20].
    REDAKCJA: Usuń 'ja' w 99%, napraw neologizmy (dodaj sekcję ZAMIANY na końcu jeśli były)[cite: 29, 32, 33].
    CEL DŁUGOŚCI: {target_chars} znaków ±300[cite: 37].
    """
else:
    manifest = f"""
    TRYB article[cite: 39]. Zadanie jednorazowe na materiale użytkownika[cite: 40, 41]. 
    Co najmniej 2/3 treści musi pochodzić ze źródła głównego[cite: 47, 48].
    ZAKAZY: Metajęzyk, komentowanie wypowiedzi (np. 'zdradza', 'wyznaje')[cite: 51, 52, 53].
    TERMINOLOGIA: Nie używaj słowa 'kapłan'. Zastąp: ksiądz, duchowny, duszpasterz[cite: 58, 59].
    CYTATY: Ramka pauzowa (– Zdanie. –), min. 4 zdania cytatu, min. 3 zdania kontekstu przed i po[cite: 72, 73, 74].
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid)[cite: 78, 83].
    STRUKTURA: Relacja (3 twarde fakty w 1 akapicie) lub tekst problemowy[cite: 93, 97, 99].
    ZAKOŃCZENIE: Konkret organizacyjny lub cytat, brak ogólnych refleksji[cite: 105, 106].
    CEL DŁUGOŚCI: {target_chars} znaków ±300[cite: 85].
    """

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"Generuję {typ_tekstu}..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁY:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API Gemini: {e}")
    else:
        st.error("Proszę dodać materiały źródłowe!")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    # Naprawiony licznik: różnica ujemna będzie zielona (zapas)
    st.metric(label="Liczba znaków", value=dlugosc, delta=f"{roznica} względem celu", delta_color="inverse")

    st.subheader("Finalny tekst:")
    # st.code automatycznie dodaje przycisk 'Copy' w rogu
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(label="💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt", mime="text/plain")