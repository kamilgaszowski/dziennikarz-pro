import streamlit as st
import google.generativeai as genai
import openai
import time
import io
import json
import os
import re
from datetime import datetime

# 1. KONFIGURACJA API
# --- GEMINI (Wersja 3 Pro) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd API Google: {e}")

# --- OPENAI ---
try:
    openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    HAS_OPENAI = True
except Exception as e:
    HAS_OPENAI = False

# 2. BIBLIOTEKI PLIKÓW
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

# 3. BIBLIOTEKI WEB
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_LIBS = True
except ImportError:
    HAS_WEB_LIBS = False

# --- UI CONFIG ---
st.set_page_config(page_title="Redaktor", layout="wide")

# --- CSS (MODERN MINIMALIST STYLE) ---
st.markdown("""
<style>
    /* 1. TYPOGRAFIA NAGŁÓWKA */
    h1 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 200 !important;
        letter-spacing: -1px;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        color: #e0e0e0;
    }
    .version-text {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: #666;
        margin-top: -10px;
        margin-bottom: 30px;
    }

    /* 2. STYLIZACJA FILE UPLOADER (MNIEJSZY) */
    [data-testid='stFileUploader'] section {
        padding: 15px !important; /* Mniejszy padding wewnątrz */
        min-height: 0px !important;
        background-color: #1a1c24; /* Ciemne tło */
        border: 1px dashed #41444e;
    }
    [data-testid='stFileUploader'] section:hover {
        border-color: #777;
    }
    /* Ukrycie niektórych domyślnych tekstów uploadera, żeby był czystszy */
    [data-testid='stFileUploader'] .st-emotion-cache-1ae8axi {
        font-size: 14px;
    }

    /* 3. STYLIZACJA PRZYCISKU GENERUJ (BEZ CZERWIENI) */
    /* Nadpisujemy domyślny styl przycisku */
    div.stButton > button {
        background-color: #2b2d35; /* Ciemnoszary, neutralny */
        color: #ffffff;
        border: 1px solid #41444e;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        padding: 0.4rem 1.2rem;
        transition: all 0.2s ease-in-out;
        box-shadow: none !important;
    }
    
    div.stButton > button:hover {
        background-color: #ffffff; /* Biały po najechaniu - wysoki kontrast */
        color: #000000;
        border-color: #ffffff;
        transform: translateY(-1px);
    }
    
    div.stButton > button:active {
        transform: translateY(1px);
    }

    /* 4. HISTORIA I TEXTAREA */
    div[data-testid="stCodeBlock"] {
        border: 1px solid #333;
        background-color: #0e1117;
    }
    
    /* Ukrycie przycisku deploy */
    .stDeployButton {display:none;}
    
    /* Sidebar buttons alignment */
    div[data-testid="stSidebar"] button { text-align: left; }
</style>
""", unsafe_allow_html=True)

# --- FUNKCJE POMOCNICZE ---
# (Tutaj bez zmian w logice, tylko kod)

def call_openai_gpt5(system_prompt, user_content):
    if not HAS_OPENAI: return "BŁĄD: Brak klucza OPENAI."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e: return f"Błąd OpenAI: {str(e)}"

def load_manifest_from_file(filename, target_chars):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read().replace("{target_chars}", str(target_chars))
        except Exception as e: return f"BŁĄD PLIKU: {e}"
    else: return f"BRAK PLIKU: {filename}"

def extract_urls(text):
    return re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)

def fetch_url_content(url):
    if not HAS_WEB_LIBS: return ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for s in soup(["script", "style", "nav", "footer"]): s.decompose()
        lines = [line.strip() for line in soup.get_text(separator='\n').splitlines() if line.strip()]
        return "\n".join(lines)[:8000]
    except: return ""

def count_body_chars_only(text):
    if not text: return 0
    clean_text = text.replace("\r", "")
    for sep in ["### ARTYKUŁ", "### WYWIAD", "### TREŚĆ"]:
        if sep in clean_text:
            parts = clean_text.split(sep, 1)
            if len(parts) > 1: return len(parts[1].replace("\n", ""))
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    if len(lines) > 10: return int(len(clean_text.replace("\n", "")) * 0.8)
    return len(clean_text.replace("\n", ""))

def read_text_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'): return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS: return "\n".join([p.text for p in Document(uploaded_file).paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS: return "\n".join([p.extract_text() for p in PyPDF2.PdfReader(uploaded_file).pages])
    except: return ""
    return ""

# --- HISTORIA ---
HISTORY_FILE = "historia_redaktora.json"

def extract_title_from_text(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines[:15]:
        if l.lower().startswith("tytuł"): return l.split(":", 1)[-1].strip().replace("*", "")
    if len(lines) >= 2: return lines[1].replace("#", "").replace("*", "").strip()
    return "Bez tytułu"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "chars" not in item: item["chars"] = count_body_chars_only(item["content"])
                return data
        except: return []
    return []

def save_history_to_disk(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history_list, f, ensure_ascii=False, indent=4)

if "history" not in st.session_state: st.session_state.history = load_history_from_disk()

def add_to_history(text, type_label, model_name="AI"):
    timestamp = datetime.now().strftime("%d-%m %H:%M")
    st.session_state.history.insert(0, {
        "time": timestamp, "type": f"{type_label} ({model_name})", "content": text,
        "chars": count_body_chars_only(text), "title": extract_title_from_text(text)
    })
    save_history_to_disk(st.session_state.history)

def delete_history_item(index):
    if 0 <= index < len(st.session_state.history):
        st.session_state.history.pop(index)
        save_history_to_disk(st.session_state.history)

def clear_all_history():
    st.session_state.history = []
    save_history_to_disk([])

# --- UI: NAGŁÓWEK ---
st.markdown("<h1>Redaktor</h1>", unsafe_allow_html=True)
st.markdown("<p class='version-text'>v17.2</p>", unsafe_allow_html=True)

if not HAS_WEB_LIBS: st.warning("Brak bibliotek requests/bs4.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Ustawienia")
    model_choice = st.radio("Silnik AI:", ["Gemini 3 Pro", "GPT-5.2 (OpenAI)"])
    if model_choice == "GPT-5.2 (OpenAI)" and not HAS_OPENAI: st.error("Brak klucza OpenAI.")
    
    st.divider()
    typ_tekstu = st.radio("Rodzaj:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (treść):", 500, 15000, value=3500, step=500)
    target_words = int(target_chars / 7)
    st.caption(f"Cel: ~{target_words} słów.")
    
    st.divider()
    st.markdown("### Status")
    current_text = st.session_state.get("artykul", "")
    
    if current_text:
        netto = count_body_chars_only(current_text)
        diff = netto - target_chars
        st.metric("Treść (netto)", value=netto, delta=f"{diff} vs cel", delta_color="inverse")
        btn_dis = False
    else:
        st.metric("Treść (netto)", value=0, delta="...")
        btn_dis = True
        
    c1, c2 = st.columns(2)
    if c1.button("Skróć", disabled=btn_dis, use_container_width=True):
        with st.spinner("Skracam..."):
            prompt = f"ZADANIE: Skróć TREŚĆ WŁAŚCIWĄ (pod ###) do {target_chars} znaków. Zachowaj strukturę. Usuń mniej ważne. ZAKAZ 'kapłan'.\n\n{current_text}"
            res = call_openai_gpt5("Redaktor", prompt) if model_choice.startswith("GPT") and HAS_OPENAI else gemini_model.generate_content(prompt).text
            st.session_state.artykul = res
            add_to_history(res, f"{typ_tekstu} (Skrót)", model_choice)
            st.rerun()
    if c2.button("Wydłuż", disabled=btn_dis, use_container_width=True):
        with st.spinner("Wydłużam..."):
            prompt = f"ZADANIE: Wydłuż TREŚĆ WŁAŚCIWĄ (pod ###) do {target_chars} znaków. ZAKAZ cudzysłowów.\n\n{current_text}"
            res = call_openai_gpt5("Redaktor", prompt) if model_choice.startswith("GPT") and HAS_OPENAI else gemini_model.generate_content(prompt).text
            st.session_state.artykul = res
            add_to_history(res, f"{typ_tekstu} (Długi)", model_choice)
            st.rerun()

    st.divider()
    st.subheader("Historia")
    if st.session_state.history:
        for i, item in enumerate(st.session_state.history):
            cl, cd = st.columns([4, 1])
            with cl: 
                if st.button(item.get('title','Bez tytułu'), key=f"l{i}", use_container_width=True):
                    st.session_state.artykul = item['content']
                    st.rerun()
            with cd: 
                st.button("X", key=f"d{i}", on_click=delete_history_item, args=(i,))
            st.caption(f"{item.get('type','AI')} | {item['time']} | {item.get('chars',0)} zn.")
            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)
        st.button("Wyczyść wszystko", on_click=clear_all_history)
    else: st.caption("Pusto.")

# --- GŁÓWNY INTERFEJS (MINIMALIST) ---

# Układ: 2 kolumny na input, ale inputy w jednej linii wizualnej
col_input, col_meta = st.columns([3, 2])

audio_to_proc = None
docs_to_proc = []

with col_input:
    # Uploader (Teraz mniejszy dzięki CSS)
    uploaded = st.file_uploader("Materiały (Audio, Dokumenty):", type=['txt','pdf','docx','mp3','wav','m4a'], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            if f.name.endswith(('.mp3','.wav','.m4a')): audio_to_proc = f
            else: docs_to_proc.append(f)
        
        # Wyświetlamy małe podsumowanie co wgrano
        info = []
        if audio_to_proc: info.append(f"Audio: {audio_to_proc.name}")
        if docs_to_proc: info.append(f"Docs: {len(docs_to_proc)}")
        if info: st.caption(" | ".join(info))

with col_meta:
    # Notatki
    notes = st.text_area("Kontekst / Linki:", height=100, placeholder="Wklej linki lub dodatkowe uwagi...")
    
    # PRZYCISK GENERUJ - TERAZ PO PRAWEJ STRONIE, MNIEJSZY
    # Używamy kolumn wewnątrz kolumny, żeby wyrównać go do prawej
    _, btn_col = st.columns([1, 1])
    with btn_col:
        start_gen = st.button("Generuj materiał", use_container_width=True)

# --- LOGIKA GENEROWANIA ---
if start_gen:
    
    # 1. Przygotowanie danych
    ctx = ""
    if notes:
        urls = extract_urls(notes)
        if urls:
            with col_meta: st.info(f"Skanuję {len(urls)} linków...")
            ctx += "--- WEB ---\n" + "\n".join([f"{u}\n{fetch_url_content(u)}" for u in urls])
        ctx += f"\n--- INFO ---\n{notes}"
        
    src = ""
    if docs_to_proc:
        src = "\n".join([f"\n--- {f.name} ---\n{read_text_file(f)}" for f in docs_to_proc])

    manifest_file = "manifest_wywiad.txt" if typ_tekstu == "Wywiad" else "manifest_news.txt"
    manifest = load_manifest_from_file(manifest_file, target_chars)
    
    instruction = f"""
    *** INSTRUKCJA PRIORYTETOWA ***
    1. Wstaw separator: ### {("WYWIAD" if typ_tekstu == "Wywiad" else "ARTYKUŁ")} po nagłówkach.
    2. Treść pod separatorem ma mieć ok. {target_words} słów.
    """

    # 2. Wykonanie
    with st.spinner("Przetwarzanie..."):
        try:
            if not src and not audio_to_proc:
                st.error("Brak materiałów.")
            else:
                # GPT
                if model_choice.startswith("GPT") and HAS_OPENAI and not audio_to_proc:
                    full_p = f"{manifest}\n\nKONTEKST:\n{ctx}\n\nMATERIAŁ:\n{src}\n\n{instruction}"
                    res = call_openai_gpt5("Redaktor", full_p)
                    st.session_state.artykul = res
                    add_to_history(res, typ_tekstu, "GPT-5.2")
                    st.rerun()
                # GEMINI
                else:
                    payload = [manifest]
                    if ctx: payload.append(f"KONTEKST:\n{ctx}")
                    if src: payload.append(f"MATERIAŁ:\n{src}")
                    payload.append(instruction)
                    
                    if audio_to_proc:
                        with open("temp.mp3", "wb") as f: f.write(audio_to_proc.getbuffer())
                        af = genai.upload_file("temp.mp3")
                        while af.state.name == "PROCESSING": time.sleep(1); af = genai.get_file(af.name)
                        payload.append(af)
                        
                    res = gemini_model.generate_content(payload).text
                    st.session_state.artykul = res
                    model_tag = "Gemini 3" if not (model_choice.startswith("GPT") and audio_to_proc) else "Gemini (Audio)"
                    add_to_history(res, typ_tekstu, model_tag)
                    st.rerun()
        except Exception as e: st.error(f"Błąd: {e}")

# --- WYNIK ---
if "artykul" in st.session_state:
    st.markdown("---") # Subtelna linia oddzielająca
    st.markdown("### Wynik")
    st.code(st.session_state.artykul, language="markdown", wrap_lines=True)
    
    # Przycisk pobierania - też minimalistyczny (bez use_container_width)
    st.download_button("Pobierz .txt", data=st.session_state.artykul, file_name=f"{typ_tekstu.lower()}.txt")