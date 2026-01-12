import streamlit as st
import google.generativeai as genai
import time
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd API: {e}")

# Biblioteki plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

# --- CSS: MAGICZNY ATRYBUT FIXED/STICKY (Z Twojego pliku) ---
st.markdown("""
<style>
    /* Namierzamy kontener kodu Streamlit */
    div[data-testid="stCodeBlock"] {
        /* Ustawiamy maksymalną wysokość na 75% ekranu */
        max-height: 75vh !important; 
        
        /* Dodajemy scrollbar wewnątrz tego okna */
        overflow-y: auto !important;
        
        /* Estetyka ramki */
        border: 1px solid #41444e;
        border-radius: 8px;
        background-color: #0e1117;
    }

    /* Opcjonalnie: Stylizacja paska przewijania */
    div[data-testid="stCodeBlock"]::-webkit-scrollbar {
        width: 12px;
    }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-track {
        background: #0e1117;
    }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-thumb {
        background-color: #262730;
        border-radius: 10px;
        border: 2px solid #0e1117;
    }
    
    /* Ukrycie zbędnych przycisków Streamlit, zostaje tylko Copy */
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.4")

# --- POMOCNIKI ---
def count_net_chars(text):
    # Liczymy znaki bez enterów
    return len(text.replace("\n", "").replace("\r", ""))

def read_text_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS:
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except: return ""
    return ""

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    st.divider()
    st.caption("v13.4 | Pełne Manifesty")

# --- WEJŚCIE DANYCH ---
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    uploaded_audio = st.file_uploader("🎤 Audio (MP3/WAV):", type=['mp3', 'wav', 'm4a'])
with col_b:
    uploaded_files = st.file_uploader("📄 Pliki (PDF/DOCX):", accept_multiple_files=True)
with col_c:
    pasted_text = st.text_area("✍️ Notatki:", height=100)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- {f.name} ---\n" + read_text_file(f)

# --- SZCZEGÓŁOWE MANIFESTY (Z TWOICH PLIKÓW) ---

# 1. INSTRUKCJA DLA WYWIADU
manifest_wywiad = f"""
Jesteś redaktorem Master PRO. Tworzysz WYWIAD w formie Q/A.
Twoim zadaniem jest redagować materiał źródłowy, nie dodając treści spoza niego, ale dbając o najwyższą jakość językową.

PARAMETRY TECHNICZNE:
- Docelowa długość: ok. {target_chars} znaków netto (bez spacji/enterów).
- Jeśli materiału jest dużo, selekcjonuj najważniejsze wątki.
- Jeśli materiału jest mało, zachowaj każdy szczegół.

ZASADY REDAKCJI (MANIFEST):
1. ZAKAZ METAJĘZYKA: Nie używaj sformułowań typu "w tej rozmowie", "pada przykład", "wróćmy do", "mówiłaś o...". Pytania mają brzmieć jak bezpośredni zwrot (2. osoba).
2. ANTY-KOMPRESJA: Nie spłaszczaj wypowiedzi do streszczeń. Zachowuj sceny, przykłady, dopowiedzenia. Skracaj tylko powtórzenia i dygresje techniczne.
3. PYTANIA: Mniej pytań, ale głębsze. Nie tnij odpowiedzi tylko po to, by było krócej.
4. REDAKCJA JĘZYKA: Wygładzaj język mówiony do wersji "do druku". Usuwaj nadmiarowe "ja" tam, gdzie wystarczy czasownik. Poprawiaj składnię.
5. STRUKTURA: Q/A. Pytania pogrubione.
6. FORMATOWANIE:
   - NAGŁÓWKI: Przygotuj zestaw: Nadtytuł, Tytuł (max 3 słowa), Lid (1-2 zdania). Lid musi zaczynać się od słowa "O".
   - KOTWICE I PEREŁKI: Na samym końcu wylistuj najmocniejsze cytaty ("perełki").

ZAKAZY:
- Nie dopisuj faktów, nazwisk ani liczb spoza źródła.
- Nie używaj słowa "kapłan" (zastąp: ksiądz, duchowny, duszpasterz).

Twoim celem jest tekst gotowy do druku.
"""

# 2. INSTRUKCJA DLA NEWS / REPORTAŻ / ARTYKUŁ
manifest_news = f"""
Jesteś redaktorem prasowym Master PRO. Tworzysz ARTYKUŁ / RELACJĘ (News lub Reportaż).
Pracujesz wyłącznie na materiale źródłowym.

PARAMETRY TECHNICZNE:
- Docelowa długość: ok. {target_chars} znaków netto.

STRUKTURA I NAGŁÓWKI:
- Na początku: Nadtytuł, Tytuł (max 3 słowa), Lid.
- Automatycznie dodaj też 5 propozycji alternatywnych tytułów i 3 propozycji lidów.
- ZAKAZ powtórzeń słów między nadtytułem, tytułem i lidem.
- Lid i pierwszy akapit NIE mogą zaczynać się od daty.

STYL:
- Styl reporterski, precyzyjny. Bez klisz i zdań pustych treściowo.
- ZAKAZ: "te słowa pokazują", "w tych zdaniach streszcza się".
- ZAKAZ: Średników (;) i dwukropków (:).
- ZAKAZ: Myślników w tekście własnym (chyba że w cytacie).

CYTATY - REGUŁY ŻELAZNE:
1. FORMAT: Cytaty zapisuj BEZ CUDZYSŁOWÓW. Używaj formatu z pauzami.
   Wzór: – Treść cytatu. Treść cytatu. – atrybucja (mówi/dodaje).
2. DŁUGOŚĆ: Każdy cytat musi mieć MINIMUM 4 zdania.
3. KONTEKST: Przed każdym cytatem MINIMUM 3 zdania wprowadzające. Po każdym cytacie MINIMUM 3 zdania rozwinięcia.
4. GĘSTOŚĆ: Celuj w jeden cytat na akapit.
5. INTERPUNKCJA: Cytat kończy się bez kropki wewnątrz pauz. Kropka dopiero po atrybucji.
   Przykład: – To jest ważne zdanie. To kolejne. – zaznacza rozmówca.

SŁOWNICTWO:
- ABSOLUTNY ZAKAZ słowa "kapłan" i jego odmian.

ZAKOŃCZENIE:
- Domknij konkretem lub cytatem. Bez ogólnych refleksji.
"""

# Wybór odpowiedniego manifestu
if typ_tekstu == "Wywiad":
    manifest = manifest_wywiad
else:
    manifest = manifest_news


# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content = [manifest]
    if all_source: content.append(f"TEKST:\n{all_source}")
    
    if uploaded_audio:
        with st.spinner("Przesyłam audio do Gemini 3..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": 
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            content.append(audio_file)

    with st.spinner("Generowanie tekstu..."):
        try:
            response = model.generate_content(content)
            st.session_state.artykul = response.text
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI: JEDNO OKNO Z PRZYKLEJONYM PASKIEM ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    # 1. Pasek narzędzi
    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("✂️ Skróć 20%"):
        res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()
    if c2.button("➕ Wydłuż 20%"):
        res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
        st.session_state.artykul = res.text
        st.rerun()
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    # 2. GŁÓWNE OKNO (Standardowe st.code + CSS Fix)
    st.subheader("Gotowy Artykuł:")
    # Dzięki CSS wyżej, to okno będzie miało stałą wysokość i wewnętrzny scroll.
    # Przycisk kopiowania (ikona w rogu) pozostanie w miejscu.
    st.code(tekst, language="markdown", wrap_lines=True)
    
    # 3. Pobieranie
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")