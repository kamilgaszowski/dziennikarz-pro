import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Używamy gemini-3-pro-preview - jeśli u Ciebie działa, nie zmieniamy.
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
st.title("🖋️ Dziennikarz Master PRO v11.4")

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

# --- PEŁNE MANIFESTY Z TWOICH PLIKÓW ---
if typ_tekstu == "Wywiad":
    # Wdrożenie instrukcji z wywiad.txt [cite: 1-38]
    manifest = f"""
    TRYB wywiad. Jesteś redaktorem. Twoim zadaniem jest zredagować z materiału wywiad w formie Q/A, ale z porządną redakcją językową wypowiedzi. Nie dodajesz treści, tylko porządkujesz i wygładzasz język[cite: 1, 2]. 
    Traktuj to jako zadanie jednorazowe, bez stanu. Pracuj wyłącznie na materiale źródłowym[cite: 3, 4].
    
    ZAKAZY STYLU: Zakaz metajęzyka (np. 'w tej rozmowie', 'pada przykład', 'wróćmy do'). Pytania mają brzmieć naturalnie[cite: 6, 7]. Unikaj dwukropków i średników. Nie używaj pauz do dopowiedzeń[cite: 8]. Zakaz separatorów typu '---'[cite: 11]. Nie używaj słowa kapłan[cite: 10].
    
    NAGŁÓWKI: Przygotuj 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania). Zakaz powtórzeń słów w obrębie zestawu[cite: 12, 13, 16].
    
    LIDY W WYWIADZIE: Każdy musi zaczynać się od słowa O. Forma: O [czymś], o [czymś] i o [czymś] mówi [kto][cite: 17].
    
    KONSTRUKCJA: Forma Q/A (P: ... O: ...). Liczba bloków: 6-12[cite: 18, 19]. Styl eksploracyjny[cite: 20]. 
    REDAKCJA: Zachowaj styl rozmówcy. Usuń 'ja' w 99% przypadków[cite: 26, 28]. Napraw neologizmy (dodaj sekcję ZAMIANY na końcu)[cite: 30, 32, 33].
    
    CEL DŁUGOŚCI: {target_chars} znaków ±300[cite: 36].
    """
else:
    # Wdrożenie instrukcji z Instrukcja_artykul.txt [cite: 39-107]
    manifest = f"""
    TRYB article. Jesteś redaktorem prasowym. Stwórz artykuł informacyjny[cite: 39]. 
    Pracuj wyłącznie na materiale źródłowym[cite: 41]. 
    
    RDZEŃ: Co najmniej dwie trzecie treści musi pochodzić ze źródła głównego[cite: 48].
    ZAKAZY: Zakaz metajęzyka i komentowania wypowiedzi (np. 'zdradza', 'wyznaje', 'wybrzmiewa')[cite: 50, 52]. Maksymalnie jedno przypisanie wypowiedzi (mówi/dodaje) na akapit[cite: 54].
    TERMINOLOGIA: Nie używaj słowa kapłan. Zastąp go: ksiądz, duchowny, duszpasterz, proboszcz, wikary, prezbiter[cite: 57, 58].
    
    CYTATY: Zapis bez cudzysłowów, w osobnym akapicie, w ramce pauzowej: – Zdanie. Zdanie. Zdanie. Zdanie. –[cite: 71]. Każdy cytat ma min. 4 zdania. Min. 3 zdania kontekstu przed i po[cite: 72].
    
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania). Zakaz powtórzeń słów w zestawie[cite: 77, 78, 82].
    
    STRUKTURA: Relacja z wydarzenia (min. 3 twarde fakty w 1. akapicie) lub tekst problemowy[cite: 91, 93, 96].
    ZAKOŃCZENIE: Domknij tekst konkretem, informacją organizacyjną lub cytatem. Zakaz ogólnych refleksji i metafor[cite: 104, 105].
    
    CEL DŁUGOŚCI: {target_chars} znaków ±300[cite: 84].
    """

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"Przetwarzam..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁ ŹRÓDŁOWY:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API: {e}")
                st.info("Jeśli błąd 404 nadal występuje, spróbuj zamienić model na 'gemini-1.5-flash'.")
    else:
        st.error("Proszę dodać materiały źródłowe!")

# --- WYNIKI I LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    # Licznik z inverse delta (ujemna różnica/niedobór = zielony)
    st.metric(label="Liczba znaków", value=dlugosc, delta=f"{roznica} względem celu", delta_color="inverse")

    st.subheader("Finalny tekst:")
    # st.code zapewnia bezpieczne kopiowanie (ikona w rogu)
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(label="💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt", mime="text/plain")