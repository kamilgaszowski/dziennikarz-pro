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

# --- OPENAI (Wersja 5.2) ---
try:
    openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    HAS_OPENAI = True
except Exception as e:
    HAS_OPENAI = False
    # Cicha obsługa błędu przy braku klucza
    pass

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

# --- UI: KONFIGURACJA STRONY (BEZ IKONY) ---
st.set_page_config(page_title="Redaktor", layout="wide")

# --- FUNKCJE POMOCNICZE ---

def call_openai_gpt5(system_prompt, user_content):
    if not HAS_OPENAI:
        return "BŁĄD: Brak klucza OPENAI_API_KEY w secrets."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Błąd OpenAI (GPT-5.2): {str(e)}"

def load_manifest_from_file(filename, target_chars):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
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
    clean_text = text.replace("\r", "")
    separators = ["### ARTYKUŁ", "### WYWIAD", "### TREŚĆ"]
    for sep in separators:
        if sep in clean_text:
            parts = clean_text.split(sep, 1)
            if len(parts) > 1:
                content_part = parts[1]
                return len(content_part.replace("\n", ""))
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    if len(lines) > 10:
        return int(len(clean_text.replace("\n", "")) * 0.8)
    return len(clean_text.replace("\n", ""))

# --- HISTORIA ---
HISTORY_FILE = "historia_redaktora.json"

def extract_title_from_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:15]:
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
                    if "chars" not in item:
                        item["chars"] = count_body_chars_only(item["content"])
                return data
        except: return []
    return []

def save_history_to_disk(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

if "history" not in st.session_state:
    st.session_state.history = load_history_from_disk()

def add_to_history(text, type_label, model_name="AI"):
    timestamp = datetime.now().strftime("%d-%m %H:%M")
    entry = {
        "time": timestamp,
        "type": f"{type_label} ({model_name})",
        "content": text,
        "chars": count_body_chars_only(text),
        "title": extract_title_from_text(text)
    }
    st.session_state.history.insert(0, entry)
    save_history_to_disk(st.session_state.history)

def delete_history_item(index):
    if 0 <= index < len(st.session_state.history):
        st.session_state.history.pop(index)
        save_history_to_disk(st.session_state.history)

def clear_all_history():
    st.session_state.history = []
    save_history_to_disk([])

# --- UI: CZYSTY NAGŁÓWEK ---
st.markdown("""
<style>
    /* Stylizacja głównego nagłówka */
    h1 {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    /* Stylizacja wersji pod nagłówkiem */
    .version-text {
        font-size: 14px;
        color: #666;
        margin-top: -15px;
        margin-bottom: 20px;
        font-family: monospace;
    }
    
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
    div[data-testid="stSidebar"] button { text-align: left; }
</style>
""", unsafe_allow_html=True)

# NOWY TYTUŁ - BEZ IKONY, CZYSTY TEKST
st.markdown("<h1>Redaktor</h1>", unsafe_allow_html=True)
st.markdown("<p class='version-text'>v16.2</p>", unsafe_allow_html=True)

if not HAS_WEB_LIBS:
    st.warning("⚠️ Brak bibliotek requests/bs4. Linki nie będą działać.")

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    model_choice = st.radio("Silnik AI:", ["Gemini 3 Pro", "GPT-5.2 (OpenAI)"])
    if model_choice == "GPT-5.2 (OpenAI)" and not HAS_OPENAI:
        st.error("Brak klucza OpenAI w secrets!")
    
    st.divider()
    typ_tekstu = st.radio("Rodzaj:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Cel znaków (TREŚĆ):", 500, 15000, value=3500, step=500)
    target_words = int(target_chars / 7)
    st.caption(f"Cel: ~{target_words} słów treści.")
    
    # --- STATUS I KOREKTA ---
    st.divider()
    st.markdown("### 📊 Status")
    
    current_text = st.session_state.get("artykul", "")
    
    if current_text:
        netto_body = count_body_chars_only(current_text)
        roznica = netto_body - target_chars
        delta_color = "normal" if abs(roznica) < 300 else "inverse"
        st.metric("Treść (netto)", value=netto_body, delta=f"{roznica} vs cel", delta_color=delta_color)
        btn_disabled = False
    else:
        st.metric("Treść (netto)", value=0, delta="oczekiwanie")
        btn_disabled = True
        
    c1, c2 = st.columns(2)
    
    if c1.button("Skróć", disabled=btn_disabled, use_container_width=True):
        with st.spinner(f"Skracam ({model_choice})..."):
            prompt_short = f"ZADANIE: Skróć TREŚĆ WŁAŚCIWĄ (tę pod nagłówkiem ###) do ok. {target_chars} znaków. Zachowaj strukturę. PRIORYTET: Usuń mniej ważne wątki. ZAKAZ: Słowa 'kapłan'.\n\nTekst:\n{current_text}"
            
            if model_choice == "GPT-5.2 (OpenAI)" and HAS_OPENAI:
                res_text = call_openai_gpt5(system_prompt="Jesteś redaktorem.", user_content=prompt_short)
            else:
                res = gemini_model.generate_content(prompt_short)
                res_text = res.text
                
            st.session_state.artykul = res_text
            add_to_history(res_text, f"{typ_tekstu} (Skrót)", model_name=model_choice)
            st.rerun()
            
    if c2.button("Wydłuż", disabled=btn_disabled, use_container_width=True):
        with st.spinner(f"Rozwijam ({model_choice})..."):
            prompt_long = f"Wydłuż TREŚĆ WŁAŚCIWĄ (tę pod nagłówkiem ###) do ok. {target_chars} znaków. Zachowaj separator. ZAKAZ cudzysłowów.\n\n{current_text}"
            
            if model_choice == "GPT-5.2 (OpenAI)" and HAS_OPENAI:
                res_text = call_openai_gpt5(system_prompt="Jesteś redaktorem.", user_content=prompt_long)
            else:
                res = gemini_model.generate_content(prompt_long)
                res_text = res.text
                
            st.session_state.artykul = res_text
            add_to_history(res_text, f"{typ_tekstu} (Długi)", model_name=model_choice)
            st.rerun()

    # --- HISTORIA ---
    st.divider()
    st.subheader("🗄️ Historia")
    
    if len(st.session_state.history) > 0:
        for i, item in enumerate(st.session_state.history):
            col_load, col_del = st.columns([4, 1])
            with col_load:
                title_label = item.get('title', 'Bez tytułu')
                if st.button(title_label, key=f"load_{i}_{item['time']}", use_container_width=True):
                    st.session_state.artykul = item['content']
                    st.rerun()
            with col_del:
                st.button("❌", key=f"del_{i}_{item['time']}", on_click=delete_history_item, args=(i,))
            
            chars_display = item.get('chars', 0)
            type_display = item.get('type', 'AI')
            st.caption(f"{type_display} | {item['time']} | {chars_display} zn.")
            st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

        st.button("🗑️ Usuń WSZYSTKO", type="primary", on_click=clear_all_history)
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
    if uploaded_audio and model_choice == "GPT-5.2 (OpenAI)":
        st.warning("⚠️ GPT-5.2 (API) nie obsługuje audio w tym trybie. Przełączam na Gemini 3.")
        
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

# --- ŁADOWANIE MANIFESTÓW ---
if typ_tekstu == "Wywiad":
    manifest = load_manifest_from_file("manifest_wywiad.txt", target_chars)
else:
    manifest = load_manifest_from_file("manifest_news.txt", target_chars)

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    
    length_enforcer = f"""
    *** INSTRUKCJA PRIORYTETOWA ***
    1. Koniecznie wstaw separator: ### {("WYWIAD" if typ_tekstu == "Wywiad" else "ARTYKUŁ")} po sekcji propozycji.
    2. Tekst WŁAŚCIWY (pod separatorem) ma mieć ok. {target_words} słów.
    Jeśli masz za dużo materiału -> USUŃ mniej ważne wątki.
    """
    
    # SCENARIUSZ A: GPT-5.2
    if model_choice == "GPT-5.2 (OpenAI)" and HAS_OPENAI and not uploaded_audio:
        with st.spinner("Generowanie (GPT-5.2)..."):
            full_user_content = ""
            if context_data: full_user_content += f"DODATKOWY KONTEKST:\n{context_data}\n\n"
            if source_content: full_user_content += f"GŁÓWNY MATERIAŁ:\n{source_content}\n\n"
            full_user_content += length_enforcer

            if not source_content:
                st.error("Brak materiału źródłowego!")
            else:
                res_text = call_openai_gpt5(system_prompt=manifest, user_content=full_user_content)
                st.session_state.artykul = res_text
                add_to_history(res_text, typ_tekstu, model_name="GPT-5.2")
                st.rerun()

    # SCENARIUSZ B: GEMINI 3 PRO
    else:
        content_payload = [manifest]
        if context_data: content_payload.append(f"DODATKOWY KONTEKST:\n{context_data}")
        if source_content: content_payload.append(f"GŁÓWNY MATERIAŁ:\n{source_content}")
        content_payload.append(length_enforcer)
        
        if uploaded_audio:
            with st.spinner("Przesyłam audio do Gemini 3..."):
                with open("temp.mp3", "wb") as f: f.write(uploaded_audio.getbuffer())
                audio_file = genai.upload_file(path="temp.mp3")
                while audio_file.state.name == "PROCESSING": 
                    time.sleep(2)
                    audio_file = genai.get_file(audio_file.name)
                content_payload.append(audio_file)

        with st.spinner(f"Generowanie (Gemini 3)..."):
            try:
                if not source_content and not uploaded_audio:
                    st.error("Brak materiału źródłowego!")
                else:
                    response = gemini_model.generate_content(content_payload)
                    st.session_state.artykul = response.text
                    final_model = "Gemini 3" if model_choice == "Gemini 3 Pro" else "Gemini 3 (Audio)"
                    add_to_history(response.text, typ_tekstu, model_name=final_model)
                    st.rerun()
            except Exception as e: st.error(f"Błąd Gemini: {e}")

# --- WYNIKI ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    st.subheader("Gotowy Artykuł:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz plik .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")