import streamlit as st
import google.generativeai as genai
import time
import io
import json
import os
import re
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

def extract_title_from_text(text):
    """Próbuje wyciągnąć tytuł z tekstu do wyświetlania w historii."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # 1. Szukamy linii zaczynającej się wprost od "Tytuł:"
    for line in lines[:10]:
        if line.lower().startswith("tytuł:") or line.lower().startswith("tytuł"):
            return line.split(":", 1)[-1].strip().replace("*", "")
    # 2. Jeśli nie ma etykiety, zakładamy, że 2. linia to tytuł (bo 1. to nadtytuł)
    if len(lines) >= 2:
        return lines[1].replace("#", "").replace("*", "").strip()
    # 3. Fallback
    if lines:
        return lines[0].replace("#", "").replace("*", "").strip()[:50] + "..."
    return "Bez tytułu"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "title" not in item:
                        item["title"] = extract_title_from_text(item["content"])
                return data
        except: return []
    return []

def save_history_to_disk(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

if "history" not in st.session_state:
    st.session_state.history = load_history_from_disk()

def add_to_history(text, type_label):
    timestamp = datetime.now().strftime("%d-%m %H:%M")
    extracted_title = extract_title_from_text(text)
    entry = {
        "time": timestamp,
        "type": type_label,
        "content": text,
        "chars": len(text.replace("\n", "").replace("\r", "")),
        "title": extracted_title
    }
    st.session_state.history.insert(0, entry)
    save_history_to_disk(st.session_state.history)

# --- CSS ---
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
    .history-item { padding: 10px 0; border-bottom: 1px solid #31333f; }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.9")

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

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (netto):", 500, 15000, value=3500, step=500)
    
    st.divider()
    st.subheader("🗄️ Historia (Trwała)")
    
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            with st.container():
                st.markdown(f"**{item.get('title', 'Bez tytułu')}**")
                st.caption(f"{item['type']} | {item['time']} | {item['chars']} zn.")
                if st.button("📂 Wczytaj", key=f"rest_{i}_{item['time']}"):
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

# --- PEŁNE MANIFESTY (100% ORYGINAŁU) ---

# 1. WYWIAD
manifest_wywiad_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWOIM ZADANIEM JEST STWORZENIE WYWIADU.
DOCELOWA DŁUGOŚĆ TEKSTU: ok. {target_chars} znaków netto (bez spacji/enterów).

PEŁNE WYTYCZNE REDAKCYJNE:

Wywiad
1) Tryb i cel
Redaguję materiał do formy Q/A.
Robię porządną redakcję językową wypowiedzi rozmówcy.
Nie dodaję treści. Porządkuję, wygładzam, układam.

2) Zasada nadrzędna pracy na źródle
Pracuję wyłącznie na materiale źródłowym podanym przez Ciebie.
Nie dopisuję faktów, nazwisk, liczb ani kontekstów spoza transkrypcji.

3) Zakazy stylu w pytaniach i przejściach
Zakaz metajęzyka i „głosu narratora”. Nie używam sformułowań typu: „w rozmowie”, „w tej rozmowie”, „pada przykład”, „tu widać”, „w tym miejscu”, „wróćmy do”, „mówiłaś o…”, jeśli wątek nie padł przed chwilą.
Pytania mają brzmieć jak bezpośredni zwrot prowadzącego do rozmówcy (2. osoba).

4) Anty-kompresja
Nie spłaszczam wypowiedzi do streszczeń.
Zachowuję sceny, przykłady, dopowiedzenia, mikrokontrpytania.
Skracam najpierw: oczywiste powtórzenia, „yyy/eee”, dygresje techniczne.

5) Mniej pytań, większa głębia
„Mniej pytań” oznacza większe pytania + ewentualnie krótkie mikrokontrpytania.
Nie tnę odpowiedzi tylko po to, by było krócej.

6) Spójność pytań
Nie używam odwołań typu „wspominałaś wcześniej”, jeśli dany wątek nie padł w pytaniu bezpośrednio poprzedzającym.
Każde pytanie ma być zrozumiałe „tu i teraz”.
Jeśli przenoszę wątek z innej części rozmowy, formułuję pytanie tak, jakby temat pojawiał się po raz pierwszy.

7) Język rozmówcy w Q/A
Wygładzam język mówiony na pisany, zachowując sens i styl mówiącego.
Usuwam wypełniacze (np. „no”, „jakby”, „w sumie”, „nie?”).
Usuwam oczywiste powtórzenia i dygresje techniczne.
Poprawiam składnię, interpunkcję, dzielę na zdania.
Redukuję nadmiarowe „ja” wszędzie tam, gdzie wystarczy czasownik.
Nie dopisuję nowych treści i nie zmieniam znaczenia.

8) Dodatkowa stała preferencja językowa
Nie używam słowa „kapłan” i jego odmian (używam: ksiądz, duchowny, duszpasterz, proboszcz, wikary).

9) Zestaw nagłówków na start
Na początku zawsze daję: nadtytuł, tytuł, lid.
Automatycznie dodaję też:
- 5 propozycji tytułów (maks. 3 słowa),
- 3 propozycje lidów.
Zakaz powtórzeń słów między nadtytułem, tytułem i lidem, także w innych formach (odmiana, liczba, przypadek).
Lid i pierwszy akapit nie mogą zaczynać się od daty.


Checklista przed wysyłką wywiadu:
[ ] Pracuję wyłącznie na materiale źródłowym, bez dopisywania faktów, nazwisk i kontekstów spoza transkrypcji
[ ] Forma jest Q/A, bez dodatkowego „głosu narratora” między pytaniami i odpowiedziami
[ ] W pytaniach nie ma metajęzyka typu „w rozmowie”, „pada przykład”, „tu widać”, „w tym miejscu”
[ ] Pytania są w 2. osobie i brzmią jak bezpośredni zwrot prowadzącego do rozmówcy
[ ] Nie ma odwołań „mówiłaś/wspominałaś/wróćmy do”, jeśli temat nie padł w maksymalnie 1 Q/A wstecz
[ ] Jeśli temat pochodzi z dalszej części transkrypcji, pytanie wprowadza go od zera, bez presupozycji
[ ] Anty-kompresja: zachowane są sceny, przykłady, dopowiedzenia i mikrokontrpytania, bez spłaszczania do streszczeń
[ ] Skróty dotyczą najpierw oczywistych powtórzeń, dygresji technicznych i „yyy/eee”, a nie treści merytorycznej
[ ] „Mniej pytań” oznacza większe pytania i ewentualnie krótkie mikrokontrpytania, a nie skracanie odpowiedzi
[ ] Redakcja wypowiedzi rozmówcy jest do wersji „do druku” bez zmiany sensu, z poprawą składni i interpunkcji
[ ] Usunięte są wypełniacze i nadmiarowe „ja” wszędzie tam, gdzie wystarcza czasownik
[ ] Zwracam jedną spójną wersję ciągłą.
"""

# 2. NEWS / REPORTAŻ
manifest_news_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWOIM ZADANIEM JEST STWORZENIE ARTYKUŁU / RELACJI.
DOCELOWA DŁUGOŚĆ TEKSTU: ok. {target_chars} znaków netto (bez spacji/enterów).

PEŁNE WYTYCZNE REDAKCYJNE:

Artykuł / News
1) Materiał i fakty
Pracuję wyłącznie na materiale źródłowym dostarczonym przez Ciebie.
Jeśli jest załącznik, wszystkie cytaty i fakty biorę tylko z pliku.
Nie dopisuję faktów, nazwisk, liczb ani kontekstów, których nie ma w materiale.

2) Zestaw nagłówków na start
Na początku zawsze daję: nadtytuł, tytuł, lid.
Automatycznie dodaję też:
- 5 propozycji tytułów (maks. 3 słowa),
- 3 propozycje lidów.
Zakaz powtórzeń słów między nadtytułem, tytułem i lidem, także w innych formach (odmiana, liczba, przypadek).
Lid i pierwszy akapit nie mogą zaczynać się od daty.

3) Struktura tekstu głównego
Tekst ma brzmieć jak relacja prasowa, nie streszczenie.
Zwykle cel: 6–10 akapitów.
Jeśli pojawiają się śródtytuły: nie mogą być na początku (najpierw akapit wejściowy), mają mieć raczej metaforyczny charakter.

4) Styl i zakazy językowe
Styl reporterski, precyzyjny, bez klisz i „gotowych fraz”.
Unikam emfazy i zdań pustych treściowo.
Unikam zdań komentujących cytaty w stylu „te słowa pokazują…”, „w tych zdaniach streszcza się…”.
Nie używam średników (;).
Nie używam dwukropków (:).
W tekście autorskim nie używam myślników (chyba że jako wtrącenie w cytacie).

5) Cytaty – reguły żelazne
Cytaty zapisuję bez cudzysłowów.
Stosuję wyłącznie format z myślnikami/pauzami, np.:
– To jest treść cytatu. To jest dalsza część. – mówi Jan Kowalski.
– To jest kolejny cytat. – dodaje.

6) Redakcja cytatów
Zasada 4 zdań: Każdy cytat ma mieć minimum cztery zdania, żeby w pełni oddać myśl.
Zasada kontekstu: Przed każdym cytatem muszą być min. 3 zdania wprowadzające, a po każdym cytacie min. 3 zdania rozwinięcia/komentarza (nie streszczenia!).
Gęstość: Celuję w jeden solidny blok cytatu na jeden akapit tekstu.

7) Zakazy językowe cd.
Nie używam słowa „kapłan” i jego odmian (zastąp: duchowny, ksiądz, duszpasterz).

Checklista przed wysyłką artykułu:
[ ] Pracuję tylko na materiale źródłowym, bez dopisywania faktów spoza pliku
[ ] Na początku są nadtytuł, tytuł, lid oraz 5 propozycji tytułów i 3 propozycje lidów
[ ] Nadtytuł, tytuł i lid nie powtarzają żadnych słów między sobą
[ ] Lid i pierwszy akapit nie zaczynają się od daty
[ ] Tekst ma formę relacji prasowej i trzyma ustaloną strukturę akapitów
[ ] W tekście nie ma średników ani dwukropków
[ ] W tekście własnym nie ma zdań z myślnikami, wyjątek dotyczy wyłącznie formatu cytowania
[ ] Cytaty są bez cudzysłowów i są redagowane do języka pisanego
[ ] Każdy cytat ma minimum cztery zdania
[ ] Przed każdym cytatem są minimum trzy zdania kontekstu
[ ] Po każdym cytacie są minimum trzy zdania rozwinięcia
[ ] Nie ma słowa „kapłan”
"""

if typ_tekstu == "Wywiad":
    manifest = manifest_wywiad_full
else:
    manifest = manifest_news_full

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
    
    # 1. Narzędzia
    c1, c2, c3 = st.columns([1, 1, 2])
    
    if c1.button("✂️ Skróć 20%"):
        with st.spinner("Skracam..."):
            prompt_short = f"Skróć o 20% (cel: {int(netto*0.8)}), ale zachowaj checklistę:\n\n{tekst}"
            res = model.generate_content(prompt_short)
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("➕ Wydłuż 20%"):
        with st.spinner("Wydłużam..."):
            prompt_long = f"Wydłuż o 20% (cel: {int(netto*1.2)}), ale zachowaj checklistę:\n\n{tekst}"
            res = model.generate_content(prompt_long)
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Długi)")
            st.rerun()
            
    with c3:
         st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")

    # 2. OKNO WYNIKU
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    # 3. Pobieranie
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")