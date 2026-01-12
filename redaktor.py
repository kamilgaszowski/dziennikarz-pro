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

# 2. BIBLIOTEKI
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_LIBS = True
except ImportError:
    HAS_WEB_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")

# --- FUNKCJE POMOCNICZE ---

def load_manifest_from_file(filename, target_chars):
    """
    Wczytuje treść manifestu z pliku txt i podstawia liczbę znaków.
    """
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                # Bezpieczne podstawienie liczby znaków w miejsce {target_chars}
                return content.replace("{target_chars}", str(target_chars))
        except Exception as e:
            return f"BŁĄD ODCZYTU PLIKU MANIFESTU {filename}: {e}"
    else:
        return f"BRAK PLIKU MANIFESTU: {filename}. Wgraj go do folderu aplikacji."

def extract_urls(text):
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

def fetch_url_content(url):
    if not HAS_WEB_LIBS: return ""
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

def count_body_chars_only(text):
    if not text: return 0
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) <= 3: return len("".join(lines))
    body_lines = lines[3:] 
    return len("".join(body_lines))

# --- HISTORIA ---
HISTORY_FILE = "historia_redaktora.json"

def extract_title_from_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:10]:
        if line.lower().startswith("tytuł:") or line.lower().startswith("tytuł"):
            return line.split(":", 1)[-1].strip().replace("*", "")
    if len(lines) >= 2: return lines[1].replace("#", "").replace("*", "").strip()
    return "Bez tytułu"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "title" not in item:
                        item["title"] = extract_title_from_text(item["content"])
                    if "chars" not in item: # Migracja
                        item["chars"] = count_body_chars_only(item["content"])
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
        "chars": count_body_chars_only(text),
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

st.title("🖋️ Dziennikarz Master PRO v15.0")

if not HAS_WEB_LIBS:
    st.warning("⚠️ Brak bibliotek requests/bs4. Linki nie będą działać.")

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (TREŚĆ):", 500, 15000, value=3500, step=500)
    target_words = int(target_chars / 7)
    st.caption(f"AI celuje w ok. {target_words} słów treści właściwej.")
    
    # --- STATUS I KOREKTA ---
    st.divider()
    st.markdown("### 📊 Status i Korekta")
    
    current_text = st.session_state.get("artykul", "")
    
    if current_text:
        netto_body = count_body_chars_only(current_text)
        roznica = netto_body - target_chars
        delta_color = "normal" if abs(roznica) < 300 else "inverse"
        
        st.metric("Treść (bez nagłówków)", value=netto_body, delta=f"{roznica} vs cel", delta_color=delta_color)
        btn_disabled = False
    else:
        st.metric("Treść (bez nagłówków)", value=0, delta="oczekiwanie")
        btn_disabled = True
        
    c1, c2 = st.columns(2)
    
    if c1.button("Skróć", disabled=btn_disabled, use_container_width=True):
        with st.spinner("Skracam..."):
            prompt_short = f"ZADANIE: Skróć TREŚĆ WŁAŚCIWĄ do ok. {target_chars} znaków. Zachowaj nagłówki. PRIORYTET: Usuń mniej ważne wątki. ZAKAZ: Słowa 'kapłan'.\n\nTekst:\n{current_text}"
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

# --- PRZETWARZANIE ---
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

# --- ŁADOWANIE MANIFESTÓW Z PLIKÓW ---
# Teraz kod ładuje treść z plików, które wgrałeś obok
if typ_tekstu == "Wywiad":
    manifest = load_manifest_from_file("manifest_wywiad.txt", target_chars)
else:
    manifest = load_manifest_from_file("manifest_news.txt", target_chars)

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    content_payload = [manifest]
    
    # Dodajemy kontekst (notatki/linki)
    if context_data:
        content_payload.append(f"DODATKOWY KONTEKST (Linki/Notatki):\n{context_data}")
        
    # Dodajemy główny materiał (pliki)
    if source_content: 
        content_payload.append(f"GŁÓWNY MATERIAŁ ŹRÓDŁOWY:\n{source_content}")
    
    # Dodajemy audio
    if uploaded_audio:
        with st.spinner("Przesyłam audio do Gemini 3..."):
            with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
            audio_file = genai.upload_file(path="temp.mp3")
            while audio_file.state.name == "PROCESSING": 
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            content_payload.append(audio_file)

    # Strażnik Długości (Word Proxy)
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
                st.error("Brak materiału źródłowego (pliki lub audio).")
            else:
                response = model.generate_content(content_payload)
                st.session_state.artykul = response.text
                add_to_history(response.text, typ_tekstu)
                st.rerun()
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")