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
# --- GEMINI ---
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

# --- CSS (HARDCORE CUSTOMIZATION) ---
st.markdown("""
<style>
    /* 1. TYPOGRAFIA */
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
        margin-bottom: 20px;
    }

    /* 2. UPLOADER */
    [data-testid='stFileUploader'] section > div:first-child span { display: none; }
    [data-testid='stFileUploader'] section > div:first-child small { display: none; }
    
    [data-testid='stFileUploader'] section > div:first-child::before {
        content: "Importuj";
        display: block; text-align: center; font-weight: 600; font-size: 16px; color: #e0e0e0; margin-bottom: 5px;
    }
    [data-testid='stFileUploader'] section > div:first-child::after {
        content: "Limit 200MB • TXT, PDF, DOCX, MP3, WAV, M4A";
        display: block; text-align: center; font-size: 11px; color: #666;
    }
    [data-testid='stFileUploader'] section {
        padding: 20px 10px !important;
        background-color: #16181e; border: 1px dashed #444; border-radius: 6px;
    }
    [data-testid='stFileUploader'] section:hover { border-color: #888; background-color: #1c1f26; }
    [data-testid='stFileUploader'] svg { display: none; }

    /* 3. BUTTONS (GLOBAL) */
    div.stButton > button {
        background-color: #2b2d35; color: #ffffff; border: 1px solid #41444e;
        border-radius: 4px; font-size: 14px; padding: 0.5rem 1rem; width: 100%;
    }
    div.stButton > button:hover { background-color: #ffffff; color: #000000; border-color: #ffffff; }

    /* 4. SIDEBAR SPECIFIC (COMPACT HISTORY) */
    /* Zmniejszamy przyciski w sidebarze, żeby historia była gęstsza */
    [data-testid="stSidebar"] div.stButton > button {
        padding: 4px 8px !important; /* Bardzo mały padding */
        font-size: 13px !important;
        height: auto !important;
        min-height: 0px !important;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        line-height: 1.2 !important;
    }
    
    /* Zmniejszenie odstępów między kolumnami w historii */
    [data-testid="stSidebar"] [data-testid="column"] {
        padding: 0px 2px !important;
    }

    /* Ukrycie standardowych marginesów kontenerów w sidebarze */
    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* 5. HISTORIA */
    div[data-testid="stCodeBlock"] { border: 1px solid #333; background-color: #0e1117; }
    .stDeployButton {display:none;}
    div[data-testid="stSidebar"] button { text-align: left; }
</style>
""", unsafe_allow_html=True)

# --- FUNKCJE POMOCNICZE ---
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
st.markdown("<p class='version-text'>v17.7</p>", unsafe_allow_html=True)

if not HAS_WEB_LIBS: st.warning("Brak bibliotek requests/bs4.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Ustawienia")
    model_choice = st.radio("Silnik AI:", ["Gemini 3 Pro", "GPT-5.2 (OpenAI)"])
    if model_choice == "GPT-5.2 (OpenAI)" and not HAS_OPENAI: st.error("Brak klucza OpenAI.")
    
    st.divider()
    typ_tekstu = st.radio("Rodzaj:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    
    # SUWAK I STATUS
    target_chars = st.slider("Cel znaków (treść):", 500, 15000, value=3500, step=500)
    target_words = int(target_chars / 7)
    st.caption(f"Cel: ~{target_words} słów.")

    current_text = st.session_state.get("artykul", "")
    netto = 0
    diff_html = ""
    
    if current_text:
        netto = count_body_chars_only(current_text)
        diff = netto - target_chars
        color = "#66bb6a" if abs(diff) < 300 else "#ef5350"
        sign = "+" if diff > 0 else ""
        diff_html = f'<span style="color: {color}; margin-left: 8px; font-size: 12px;">{sign}{diff}</span>'
    else:
        diff_html = '<span style="color: #666; margin-left: 8px; font-size: 12px;">...</span>'

    st.markdown(f"""
    <div style="background-color: #16181e; border: 1px solid #333; border-radius: 6px; padding: 8px; margin-top: 5px;">
        <p style="margin: 0; font-size: 10px; color: #888; text-transform: uppercase;">Obecna długość (netto)</p>
        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #e0e0e0; font-family: monospace;">
            {netto} {diff_html}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # HISTORIA KOMPAKTOWA
    st.divider()
    st.subheader("Historia")
    if st.session_state.history:
        for i, item in enumerate(st.session_state.history):
            # Używamy CSS-owego ścisku. Layout 5:1
            c1, c2 = st.columns([5, 1])
            with c1:
                # Główny przycisk z tytułem
                if st.button(item.get('title','Bez tytułu'), key=f"l{i}", use_container_width=True):
                    st.session_state.artykul = item['content']
                    st.rerun()
            with c2:
                # Malutki przycisk kosza
                st.button("🗑️", key=f"d{i}", on_click=delete_history_item, args=(i,), help="Usuń")
            
            # Caption bardzo blisko przycisków
            st.markdown(f"""
            <div style="font-size: 10px; color: #666; margin-top: -12px; margin-bottom: 8px; margin-left: 4px;">
                {item.get('type','AI')} | {item['time']} | {item.get('chars',0)}
            </div>
            """, unsafe_allow_html=True)
            
        st.button("Wyczyść wszystko", on_click=clear_all_history)
    else: st.caption("Pusto.")

# --- GŁÓWNY INTERFEJS ---

pasted_text = st.text_area("Notatki / Kontekst:", height=100, placeholder="Wklej notatki lub linki...", label_visibility="visible")

col_left, col_right = st.columns([1, 3]) 

audio_to_proc = None
docs_to_proc = []

with col_left:
    uploaded = st.file_uploader(" ", type=['txt','pdf','docx','mp3','wav','m4a'], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded:
        for f in uploaded:
            if f.name.endswith(('.mp3','.wav','.m4a')): audio_to_proc = f
            else: docs_to_proc.append(f)
        info = []
        if audio_to_proc: info.append(f"Audio: {audio_to_proc.name}")
        if docs_to_proc: info.append(f"Docs: {len(docs_to_proc)}")
        if info: st.caption(" | ".join(info))

    st.markdown("<div style='height: 5px'></div>", unsafe_allow_html=True)
    start_gen = st.button("Generuj", use_container_width=True)

with col_right:
    pass 

# --- LOGIKA GENEROWANIA ---
if start_gen:
    ctx = ""
    if pasted_text:
        urls = extract_urls(pasted_text)
        if urls:
            st.toast(f"Skanuję {len(urls)} linków...")
            ctx += "--- WEB ---\n" + "\n".join([f"{u}\n{fetch_url_content(u)}" for u in urls])
        ctx += f"\n--- INFO ---\n{pasted_text}"
        
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

    with st.spinner("Przetwarzanie..."):
        try:
            if not src and not audio_to_proc:
                st.error("Brak materiałów (pliki)!")
            else:
                if model_choice.startswith("GPT") and audio_to_proc:
                    st.toast("GPT nie obsługuje audio. Przełączam na Gemini.", icon="⚠️")
                
                if model_choice.startswith("GPT") and HAS_OPENAI and not audio_to_proc:
                    full_p = f"{manifest}\n\nKONTEKST:\n{ctx}\n\nMATERIAŁ:\n{src}\n\n{instruction}"
                    res = call_openai_gpt5("Redaktor", full_p)
                    st.session_state.artykul = res
                    add_to_history(res, typ_tekstu, "GPT-5.2")
                    st.rerun()
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
    st.markdown("---")
    st.markdown("### Wynik")
    st.code(st.session_state.artykul, language="markdown", wrap_lines=True)
    st.download_button("Pobierz .txt", data=st.session_state.artykul, file_name=f"{typ_tekstu.lower()}.txt")