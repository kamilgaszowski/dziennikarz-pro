Rozumiem. Wprowadzamy zmiany UX (User Experience) oraz logikę liczenia znaków "netto" (bez nagłówków).

Oto wersja **v14.4**.

### Co zmieniono?

1. **Stały Panel Boczny:** Sekcja "Status i Korekta" jest teraz widoczna **zawsze**. Jeśli nie ma jeszcze artykułu, licznik pokazuje "0", a przyciski są **nieaktywne (szare)**.
2. **Czyste Przyciski:** Usunąłem ikony (nożyczki, plusy). Są teraz proste: "Skróć" i "Wydłuż".
3. **Inteligentne Liczenie (Body Only):** Dodałem funkcję, która analizuje tekst. Zakładamy, że zgodnie z Twoim manifestem pierwsze 3 bloki tekstu to *Nadtytuł*, *Tytuł* i *Lid*. Funkcja pomija je i liczy znaki dopiero od 4. bloku (właściwej treści).
4. **Kontekst:** Pasek boczny reaguje dynamicznie na to, co dzieje się w aplikacji.

Oto kompletny kod:

```python
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

# 2. BIBLIOTEKI PLIKÓW
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

# 3. BIBLIOTEKI WEB (Obsługa błędów, jeśli ich nie ma)
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_LIBS = True
except ImportError:
    HAS_WEB_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

# --- FUNKCJE POMOCNICZE ---

def extract_urls(text):
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

def fetch_url_content(url):
    if not HAS_WEB_LIBS:
        return ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:8000]
    except: return ""

# NOWA FUNKCJA LICZĄCA ZNAKI (BEZ NAGŁÓWKÓW)
def count_body_chars_only(text):
    """
    Liczy znaki pomijając nagłówki (Nadtytuł, Tytuł, Lid).
    Zakłada, że pierwsze 3 niepuste linie/bloki to nagłówki.
    """
    if not text: return 0
    
    # Dzielimy na linie i usuwamy puste
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Jeśli tekst jest bardzo krótki (np. błąd generowania), licz wszystko
    if len(lines) <= 3:
        return len("".join(lines))
    
    # Pomijamy pierwsze 3 elementy (zakładamy: Nadtytuł, Tytuł, Lid)
    body_lines = lines[3:] 
    
    # Łączymy resztę i liczymy
    return len("".join(body_lines))

# --- HISTORIA ---
HISTORY_FILE = "historia_redaktora.json"

def extract_title_from_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:10]:
        if line.lower().startswith("tytuł:") or line.lower().startswith("tytuł"):
            return line.split(":", 1)[-1].strip().replace("*", "")
    if len(lines) >= 2:
        return lines[1].replace("#", "").replace("*", "").strip()
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
    entry = {
        "time": timestamp,
        "type": type_label,
        "content": text,
        "chars": count_body_chars_only(text), # Używamy nowego licznika też w historii
        "title": extract_title_from_text(text)
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
    div[data-testid="stCodeBlock"]::-webkit-scrollbar { width: 12px; }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-track { background: #0e1117; }
    div[data-testid="stCodeBlock"]::-webkit-scrollbar-thumb { background-color: #262730; border-radius: 10px; border: 2px solid #0e1117; }
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v14.4")

if not HAS_WEB_LIBS:
    st.warning("⚠️ Brak bibliotek requests/bs4. Linki nie będą działać (dodaj je do requirements.txt).")

# --- PANEL BOCZNY (ZMIANY UI) ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (TREŚĆ):", 500, 15000, value=3500, step=500)
    target_words = int(target_chars / 7)
    st.caption(f"AI celuje w ok. {target_words} słów treści właściwej.")
    
    # --- SEKCJA STATUSU (ZAWSZE WIDOCZNA) ---
    st.divider()
    st.markdown("### 📊 Status i Korekta")
    
    # Pobieramy aktualny tekst (jeśli jest)
    current_text = st.session_state.get("artykul", "")
    
    if current_text:
        # Obliczamy tylko treść (bez nagłówków)
        netto_body = count_body_chars_only(current_text)
        roznica = netto_body - target_chars
        delta_color = "normal" if abs(roznica) < 300 else "inverse"
        
        st.metric("Treść (bez nagłówków)", value=netto_body, delta=f"{roznica} vs cel", delta_color=delta_color)
        btn_disabled = False
    else:
        st.metric("Treść (bez nagłówków)", value=0, delta="oczekiwanie")
        btn_disabled = True # Przyciski nieaktywne
        
    # Przyciski (bez ikonek, zawsze widoczne, ale mogą być nieaktywne)
    c1, c2 = st.columns(2)
    
    if c1.button("Skróć", disabled=btn_disabled, use_container_width=True):
        with st.spinner("Skracam..."):
            prompt_short = f"ZADANIE: Skróć TREŚĆ WŁAŚCIWĄ do ok. {target_chars} znaków. Zachowaj nagłówki bez zmian. PRIORYTET: Usuń mniej ważne wątki. ZAKAZ: Słowa 'kapłan'.\n\nTekst:\n{current_text}"
            res = model.generate_content(prompt_short)
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("Wydłuż", disabled=btn_disabled, use_container_width=True):
        with st.spinner("Rozwijam..."):
            prompt_long = f"Wydłuż TREŚĆ WŁAŚCIWĄ do ok. {target_chars} znaków, dodając detale. Zachowaj nagłówki. ZAKAZ cudzysłowów.\n\n{current_text}"
            res = model.generate_content(prompt_long)
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Długi)")
            st.rerun()

    # --- HISTORIA ---
    st.divider()
    st.subheader("🗄️ Historia")
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            with st.container():
                st.markdown(f"**{item.get('title', 'Bez tytułu')}**")
                # Tutaj też używamy już policzonej wartości chars (body only) jeśli była zapisana nową metodą
                chars_display = item.get('chars', 0)
                st.caption(f"{item['type']} | {item['time']} | {chars_display} zn.")
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

col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    uploaded_audio = st.file_uploader("🎤 Audio (MP3/WAV):", type=['mp3', 'wav', 'm4a'])
with col_b:
    uploaded_files = st.file_uploader("📄 Pliki (PDF/DOCX):", accept_multiple_files=True)
with col_c:
    pasted_text = st.text_area("✍️ Notatki i Linki:", height=100)

# --- PRZETWARZANIE NOTATEK I PLIKÓW ---
context_data = ""
if pasted_text:
    urls = extract_urls(pasted_text)
    if urls:
        st.info(f"🔎 Analizuję {len(urls)} linków...")
        context_data += "--- TREŚĆ Z LINKÓW ---\n"
        for url in urls:
            content = fetch_url_content(url)
            context_data += f"ŹRÓDŁO: {url}\n{content}\n\n"
    context_data += f"--- NOTATKI UŻYTKOWNIKA ---\n{pasted_text}\n"

source_content = ""
if uploaded_files:
    for f in uploaded_files:
        source_content += f"\n\n--- PLIK: {f.name} ---\n" + read_text_file(f)

# --- MANIFESTY ---
manifest_wywiad_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWOIM ZADANIEM JEST STWORZENIE WYWIADU.
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
4) Anty-kompresja (UWAGA: ZALEŻNA OD LIMITU ZNAKÓW - PATRZ PRIORYTET DŁUGOŚCI)
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
[ ] Pracuję wyłącznie na materiale źródłowym
[ ] Forma Q/A
[ ] Brak metajęzyka
[ ] Pytania w 2. osobie
[ ] Anty-kompresja (chyba że limit znaków wymusza cięcia)
[ ] Redakcja do języka pisanego
[ ] Brak słowa "kapłan"
[ ] Sekcja "KOTWICE I PEREŁKI" na końcu
"""

manifest_news_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWOIM ZADANIEM JEST STWORZENIE ARTYKUŁU / RELACJI.
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
[ ] Materiał tylko ze źródła
[ ] Nagłówki + propozycje
[ ] Styl reporterski
[ ] Brak średników i dwukropków
[ ] Cytaty bez cudzysłowów (pauzy)
[ ] Cytaty min. 4 zdania
[ ] Kontekst min. 3 zdania
[ ] Brak słowa "kapłan"
"""

if typ_tekstu == "Wywiad":
    manifest = manifest_wywiad_full
else:
    manifest = manifest_news_full

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content_payload = [manifest]
    if context_data:
        content_payload.append(f"DODATKOWY KONTEKST (Linki/Notatki):\n{context_data}")
    if source_content: 
        content_payload.append(f"GŁÓWNY MATERIAŁ ŹRÓDŁOWY:\n{source_content}")
    
    if uploaded_audio:
        with st.spinner("Przesyłam audio do Gemini 3..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": 
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            content_payload.append(audio_file)

    length_enforcer = f"""
    *** INSTRUKCJA PRIORYTETOWA (KONTROLA DŁUGOŚCI) ***
    Użytkownik wymaga tekstu o objętości ok. {target_chars} znaków netto (licząc BEZ nagłówków).
    DLA CIEBIE OZNACZA TO: Napisz samą treść właściwą na około {target_words} SŁÓW.
    Jeśli materiału jest za dużo -> PO PROSTU ODETNIJ mniej ważne wątki.
    """
    content_payload.append(length_enforcer)

    with st.spinner("Generowanie tekstu..."):
        try:
            if not source_content and not uploaded_audio:
                st.error("Brak materiału źródłowego!")
            else:
                response = model.generate_content(content_payload)
                st.session_state.artykul = response.text
                add_to_history(response.text, typ_tekstu)
                st.rerun()
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI: GŁÓWNE OKNO ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")

```