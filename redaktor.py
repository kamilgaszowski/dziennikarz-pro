import streamlit as st
import google.generativeai as genai
import time
import io
import json
import os
from datetime import datetime

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

# --- TRWAŁA HISTORIA ---
HISTORY_FILE = "historia_redaktora.json"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_history_to_disk(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

if "history" not in st.session_state:
    st.session_state.history = load_history_from_disk()

# --- CSS: FIXED SCROLL ---
st.markdown("""
<style>
    div[data-testid="stCodeBlock"] {
        max-height: 75vh !important; 
        overflow-y: auto !important;
        border: 1px solid #41444e;
        border-radius: 8px;
        background-color: #0e1117;
    }
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
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.7")

# --- POMOCNIKI ---
def count_net_chars(text):
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

def add_to_history(text, type_label):
    timestamp = datetime.now().strftime("%d-%m %H:%M")
    entry = {
        "time": timestamp,
        "type": type_label,
        "content": text,
        "chars": count_net_chars(text)
    }
    st.session_state.history.insert(0, entry)
    save_history_to_disk(st.session_state.history)

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    
    st.divider()
    st.subheader("🗄️ Historia (Trwała)")
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            btn_key = f"hist_{i}_{item['time']}"
            label = f"{item['time']} | {item['type']} ({item['chars']})"
            if st.button(label, key=btn_key):
                st.session_state.artykul = item['content']
                st.rerun()
        st.markdown("---")
        if st.button("🗑️ Usuń wszystko"):
            st.session_state.history = []
            save_history_to_disk([])
            st.rerun()
    else:
        st.caption("Pusto.")

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

# --- PEŁNE MANIFESTY (WKLEJONE W CAŁOŚCI Z TWOICH PLIKÓW) ---

manifest_wywiad = f"""
TRYB: WYWIAD
CEL DŁUGOŚCI: ok. {target_chars} znaków netto (bez enterów).

1) Tryb i cel
Redaguję materiał do formy Q/A.
Robię porządną redakcję językową wypowiedzi rozmówcy.
Nie dodaję treści. Porządkuję, wygładzam, układam.

2) Zasada nadrzędna pracy na źródle
Pracuję wyłącznie na materiale źródłowym podanym przez Ciebie.
Nie dopisuję faktów, nazwisk, liczb ani kontekstów spoza transkrypcji.

3) Zakazy stylu w pytaniach i przejściach
Zakaz metajęzyka i „głosu narratora”. Nie używam sformułowań typu:
„w rozmowie”, „w tej rozmowie”, „pada przykład”, „tu widać”, „w tym miejscu”, „wróćmy do”, „mówiłaś o…”, jeśli wątek nie padł przed chwilą.
Pytania mają brzmieć jak bezpośredni zwrot prowadzącego do rozmówcy (2. osoba).

4) Anty-kompresja
Nie spłaszczam wypowiedzi do streszczeń.
Zachowuję sceny, przykłady, dopowiedzenia, mikrokontrpytania.
Skracam najpierw: oczywiste powtórzenia, „yyy/eee”, dygresje techniczne.

5) Mniej pytań, większa głębia
„Mniej pytań” oznacza większe pytania + ewentualnie krótkie mikrokontrpytania.
Nie tnę odpowiedzi tylko po to, by było krócej.

6) Spójność pytań
Nie używam odwołań typu „wspominałeś wcześniej”, jeśli temat nie padł w poprzednim pytaniu.
Jeśli temat pochodzi z odległej części transkrypcji, wprowadzam go w pytaniu tak, jakby był nowy.

7) Redakcja wypowiedzi
Zachowuję styl rozmówcy, ale w wersji „do druku”.
Usuwam: „no”, „jakby”, „w sumie”, „nie?”.
Poprawiam składnię, interpunkcję, dzielę tasiemcowe zdania.
Usuwam nadmiarowe „ja” (np. „ja myślę” -> „myślę”), chyba że służy kontrastowi.

8) Stała preferencja językowa
Nie używam słowa „kapłan” i jego odmian.

9) Struktura nagłówków
Zawsze daję zestaw:
- Nadtytuł
- Tytuł (max 3 słowa)
- Lid (1-2 zdania).
LID W WYWIADZIE: Każdy musi zaczynać się od słowa „O”. Forma: O [czymś], o [czymś] mówi [kto].

10) Checklista końcowa
- Czy jest forma Q/A (P: / O:)?
- Czy usunięto metajęzyk?
- Czy neologizmy są poprawione?
- Czy jest sekcja ZAMIANY na końcu (jeśli były neologizmy)?
"""

manifest_news = f"""
TRYB: ARTYKUŁ / NEWS / REPORTAŻ
CEL DŁUGOŚCI: ok. {target_chars} znaków netto (bez enterów).

1) Materiał i fakty
Pracuję wyłącznie na materiale źródłowym.
Nie dopisuję faktów, nazwisk, liczb ani kontekstów spoza materiału.

2) Zestaw nagłówków na start
Zawsze: Nadtytuł, Tytuł, Lid.
Automatycznie dodaję też:
- 5 propozycji tytułów (max 3 słowa).
- 3 propozycje lidów.
ZAKAZ powtórzeń słów między nadtytułem, tytułem i lidem.
Lid i pierwszy akapit NIE mogą zaczynać się od daty.

3) Struktura tekstu głównego
Tekst ma brzmieć jak relacja prasowa, nie streszczenie.
Zwykle 6–10 akapitów.
Śródtytuły (opcjonalnie) – metaforyczne, nie na samym początku.

4) Styl i zakazy językowe
Styl reporterski, precyzyjny. Bez klisz.
Unikam zdań: „te słowa pokazują…”, „w tych zdaniach streszcza się…”.
ZAKAZ: Średników (;) i dwukropków (:).
ZAKAZ: Myślników w tekście własnym (wyjątek: cytaty).
ZAKAZ słowa „kapłan”.

5) Zasady cytowania (BARDZO WAŻNE)
- Cytaty BEZ CUDZYSŁOWÓW.
- Format: – Treść cytatu. Treść cytatu. – atrybucja.
- Długość: Minimum 4 zdania w cytacie.
- Kontekst: Minimum 3 zdania własne przed cytatem i 3 po cytacie.
- Interpunkcja: Kropka na końcu cytatu wewnątrz pauz jest błędem, jeśli następuje atrybucja.
- Przykład poprawny: – To jest zdanie. To drugie zdanie. – mówi rozmówca.

6) Zakończenie
Domknij konkretem, informacją organizacyjną lub cytatem-puentą.
Nie kończ ogólną refleksją, podsumowaniem „znaczenia wydarzenia”.

7) Checklista
- Czy usunięto słowo „kapłan”?
- Czy cytaty są bez cudzysłowów?
- Czy zachowano proporcje cytatów (min. 4 zdania)?
"""

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
            new_text = response.text
            st.session_state.artykul = new_text
            add_to_history(new_text, typ_tekstu)
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("✂️ Skróć 20%"):
        with st.spinner("Skracam..."):
            res = model.generate_content(f"Skróć o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("➕ Wydłuż 20%"):
        with st.spinner("Wydłużam..."):
            res = model.generate_content(f"Wydłuż o 20%:\n\n{tekst}")
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Długi)")
            st.rerun()
            
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")