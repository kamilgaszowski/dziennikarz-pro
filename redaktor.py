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
    """
    Próbuje inteligentnie wyciągnąć tytuł z tekstu.
    Zakładamy strukturę: Nadtytuł -> Tytuł -> Lid.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 1. Szukamy linii zaczynającej się wprost od "Tytuł:"
    for line in lines[:10]:
        if line.lower().startswith("tytuł:") or line.lower().startswith("tytuł"):
            return line.split(":", 1)[-1].strip().replace("*", "")
            
    # 2. Jeśli nie ma etykiety, zakładamy, że 2. linia to tytuł (bo 1. to nadtytuł)
    if len(lines) >= 2:
        clean_title = lines[1].replace("#", "").replace("*", "").strip()
        return clean_title
    
    # 3. Fallback - pierwsza linia
    if lines:
        return lines[0].replace("#", "").replace("*", "").strip()[:50] + "..."
        
    return "Bez tytułu"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migracja dla starych wpisów bez tytułu
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
    # Automatyczne wyciąganie tytułu
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

# --- CSS: FIXED SCROLL & STICKY HEADER ---
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
    
    /* Stylizacja listy historii */
    .history-item {
        padding: 10px 0;
        border-bottom: 1px solid #31333f;
    }
</style>
""", unsafe_allow_html=True)

st.title("🖋️ Dziennikarz Master PRO v13.8")

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
            # Kontener dla jednego wpisu
            with st.container():
                # Tytuł (Pogrubiony)
                st.markdown(f"**{item.get('title', 'Bez tytułu')}**")
                
                # Meta dane w jednej linii (Typ | Data) - mała czcionka
                st.caption(f"{item['type']} | {item['time']} | {item['chars']} zn.")
                
                # Przycisk wczytania
                btn_key = f"rest_{i}_{item['time']}"
                if st.button("📂 Wczytaj", key=btn_key):
                    st.session_state.artykul = item['content']
                    st.rerun()
                
                st.markdown("---") # Separator
        
        if st.button("🗑️ Usuń wszystko"):
            st.session_state.history = []
            save_history_to_disk([])
            st.rerun()
    else:
        st.caption("Historia jest pusta.")

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

# --- PEŁNE MANIFESTY (v13.7 Base) ---

# WYWIAD
manifest_wywiad_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWOIM ZADANIEM JEST STWORZENIE WYWIADU.
DOCELOWA DŁUGOŚĆ: ok. {target_chars} znaków netto.

WYTYCZNE:
1. Forma Q/A. Porządna redakcja językowa wypowiedzi.
2. Pracuj TYLKO na materiale źródłowym.
3. ZAKAZ METAJĘZYKA (np. "w tej rozmowie"). Pytania w 2. osobie.
4. ANTY-KOMPRESJA: Zachowuj sceny, przykłady. Nie streszczaj.
5. ZAKAZ: "mówiłaś wcześniej" (chyba że w pytaniu obok).
6. Redakcja: Język mówiony -> pisany. Usuń "yyy", powtórzenia.
7. ZAKAZ słowa "kapłan".
8. NAGŁÓWKI: Nadtytuł -> Tytuł -> Lid.
"""

# NEWS
manifest_news_full = f"""
JESTEŚ REDAKTOREM MASTER PRO. TWÓRZ NEWS / REPORTAŻ.
DOCELOWA DŁUGOŚĆ: ok. {target_chars} znaków netto.

WYTYCZNE:
1. Pracuj TYLKO na materiale źródłowym.
2. NAGŁÓWKI: Nadtytuł, Tytuł, Lid + (5 tytułów i 3 lidy extra).
   Zakaz powtórzeń słów w nagłówkach. Lid nie od daty.
3. STYL: Reporterski, bez "te słowa pokazują".
4. CYTATY: BEZ CUDZYSŁOWÓW. Format pauzowy (– ... –).
   Min. 4 zdania w cytacie.
   Min. 3 zdania kontekstu przed i po.
5. ZAKAZ słowa "kapłan".
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
            prompt_short = f"Skróć o 20% (cel: {int(netto*0.8)}), ZAKAZ słowa 'kapłan':\n\n{tekst}"
            res = model.generate_content(prompt_short)
            st.session_state.artykul = res.text
            add_to_history(res.text, f"{typ_tekstu} (Skrót)")
            st.rerun()
            
    if c2.button("➕ Wydłuż 20%"):
        with st.spinner("Wydłużam..."):
            prompt_long = f"Wydłuż o 20% (cel: {int(netto*1.2)}), ZAKAZ cudzysłowów:\n\n{tekst}"
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