import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API (Pobiera klucz z Twoich 'Secrets')
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro') # Używamy najmocniejszego modelu
except Exception as e:
    st.error("Błąd konfiguracji API. Sprawdź czy 'GOOGLE_API_KEY' jest w Secrets!")

# Obsługa bibliotek do plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.0")

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
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków:", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

# Łączenie tekstów
all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- MANIFESTY (TWOJE PROMTPY) ---
if typ_tekstu == "Wywiad":
    manifest = f"""
    TRYB wywiad. Jesteś redaktorem. Twoim zadaniem jest zredagować z materiału wywiad w formie Q/A, ale z porządną redakcją językową wypowiedzi rozmówcy. Nie dodajesz treści, tylko porządkujesz i wygładzasz język. Nie korzystaj z zapisanych wspomnień. Traktuj to jako zadanie jednorazowe. 
    Pracuj wyłącznie na materiale źródłowym. Nie dopisuj faktów. 
    ZAKAZY STYLU: Zakaz metajęzyka (w tej rozmowie, pada przykład itp.). Pytania naturalne, wygładzone. Unikaj dwukropków i średników. Zakaz separatorów ---. Akapity oddzielaj wyłącznie pustą linią. 
    NAGŁÓWKI: Przygotuj 5 zestawów (nadtytuł, tytuł max 3 słowa, lid 1-2 zdania). Zakaz powtórzeń w zestawie. 
    LIDY W WYWIADZIE: Każdy musi zaczynać się od słowa O. Forma: O [czymś], o [czymś] mówi [kto]. 
    KONSTRUKCJA: Forma Q/A (P: ... O: ...). Liczba bloków: min 6, maks 12. 
    REDAKCJA: Zachowaj styl rozmówcy, ale bez błędów. Usuń 'ja' w 99%. 
    DŁUGOŚĆ: Celuj w {target_chars} znaków (±300).
    """
else:
    manifest = f"""
    TRYB article. Jesteś redaktorem prasowym. Twoim zadaniem jest stworzyć na podstawie materiałów artykuł informacyjny. 
    Nie korzystaj z zapisanych wspomnień. Pracuj wyłącznie na materiale źródłowym. 
    RDZEŃ: Co najmniej dwie trzecie treści musi pochodzić ze źródła głównego. 
    ZAKAZY: Zakaz metajęzyka i komentowania wypowiedzi. Maksymalnie jedno 'mówi/dodaje' na akapit. Zakaz słowa 'kapłan' (używaj: ksiądz, duchowny, duszpasterz, proboszcz). 
    CYTATY: Każdy cytat w ramce pauzowej (– Zdanie. –), minimum 4 zdania cytatu. 3 zdania kontekstu przed i po. 
    NAGŁÓWKI: 5 zestawów (nadtytuł, tytuł max 3 słowa, lid). Zakaz powtórzeń w zestawie. 
    STRUKTURA: Relacja z wydarzenia lub tekst problemowy. Pierwszy akapit: wprowadzenie (minimum 3 twarde fakty). 
    DŁUGOŚĆ: Celuj w {target_chars} znaków (±300). Akapity oddzielaj pustą linią. Zakaz list wypunktowanych.
    """

# --- GENEROWANIE (REALNE API) ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner(f"AI pracuje nad {typ_tekstu}..."):
            try:
                # Wywołanie modelu Gemini z Manifestem i Materiałem
                full_prompt = f"{manifest}\n\nMATERIAŁY ŹRÓDŁOWE:\n{all_source}"
                response = model.generate_content(full_prompt)
                
                # Zapisujemy wynik w sesji
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API Gemini: {e}")
    else:
        st.error("Wgraj pliki lub wklej materiały!")

# --- WYNIKI I POPRAWIONY LICZNIK ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    roznica = dlugosc - target_chars
    
    st.divider()
    
    # Licznik: delta_color="inverse" sprawia, że niedobór (minus) jest ZIELONY
    st.metric(
        label="Liczba znaków", 
        value=dlugosc, 
        delta=f"{roznica} względem celu",
        delta_color="inverse"
    )

    st.subheader("Finalny tekst:")
    # st.code ma wbudowany przycisk "Copy" w rogu - to rozwiązuje błąd copy_button
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(
        label="💾 Pobierz .txt", 
        data=tekst, 
        file_name=f"{typ_tekstu.lower()}.txt", 
        mime="text/plain"
    )