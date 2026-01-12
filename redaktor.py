@ -1,16 +1,120 @@
import streamlit as st
import google.generativeai as genai
import re

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO v11.0", layout="wide", page_icon="🖋️")

def get_safe_filename(text):
    try:
        lines = text.split('\n')
        title = "zredagowany_tekst"
        for line in lines:
            if any(x in line.upper() for x in ["TYTUŁ", "TYTUL"]):
                title = line.split(':')[-1].strip()
                break
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
        return re.sub(r'[-\s]+', '_', clean_title)[:50]
    except:
        return "zredagowany_material"

# --- MANIFESTY ---
MANIFEST_WYWIAD = """
Jesteś elitarnym redaktorem wywiadów (styl Kamila Gąszowskiego).
1. ZASADA "OTWARTEGO ZAMKA": Pytania mają dawać PRZESTRZEŃ. Nie podawaj faktów, które rozmówca ma dopiero wyjawić.
2. REŻYSERIA: Wycinaj brud, kondensuj odpowiedzi, wstawiaj pytania dopytujące w długie bloki tekstu.
3. STRUKTURA: 3x TYTUŁ, LEAD (blurb), ROZMOWA (Pytanie: / Odpowiedź:), ŚRÓDTYTUŁY (WERSALIKI).
"""

MANIFEST_NEWS = """
Jesteś osobistym redaktorem Kamila Gąszowskiego. Piszesz newsy z charakterem.
CZĘŚĆ 1: METADANE (3x Nadtytuł WERSALIKAMI, 3x Tytuł, 3x Lead: Sylwetkowy, Newsowy, Opisowy).
CZĘŚĆ 2: ARTYKUŁ z pogrubionym leadem i ŚRÓDTYTUŁAMI (WERSALIKI).
- Całkowity zakaz AI-yzmów. Brak danych = [BRAK DANYCH].
"""

# --- LOGIKA KLUCZA API ---
# Najpierw sprawdź, czy klucz jest w Secrets (dla wersji online)
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🖋️ Dziennikarz Master PRO v11.0")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    # Jeśli klucza nie ma w sekretach, pokaż pole do wpisania
    if not api_key:
        api_key = st.text_input("Klucz Google API:", type="password")
        st.warning("Dodaj klucz w Secrets, aby nie wpisywać go za każdym razem.")
    else:
        st.success("Klucz API załadowany automatycznie (Secrets) ✅")
        st.success("Klucz załadowany z ustawień serwera ✅")
    
    model_selection = st.selectbox("Model:", ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-1.5-pro-latest"])
    # ... reszta kodu (suwak itd.)
    
    st.divider()
    st.markdown("### 📏 Objętość materiału")
    
    # Użycie session_state do synchronizacji
    if 'target_chars' not in st.session_state:
        st.session_state.target_chars = 3000

    def update_slider():
        st.session_state.target_chars = st.session_state.input_val
    def update_input():
        st.session_state.input_val = st.session_state.target_chars

    target = st.number_input("Docelowa liczba znaków:", 500, 15000, step=100, key="input_val", on_change=update_slider)
    st.slider("Suwak:", 500, 15000, step=100, key="target_chars", on_change=update_input)

if api_key:
    genai.configure(api_key=api_key)
    
    col_main, col_ctx = st.columns([2, 1])
    
    with col_main:
        st.markdown("### 1. Materiał Główny")
        tryb = st.radio("Tryb:", ["News / Artykuł", "Wywiad Q&A"], horizontal=True)
        main_file = st.file_uploader("Audio lub Tekst (.txt):", type=["mp3", "wav", "m4a", "txt"])
    
    with col_ctx:
        st.markdown("### 2. Tło (Kontekst)")
        context_text = st.text_area("Notatki / Linki:", height=150)
        context_file = st.file_uploader("Plik dodatkowy:", type=["pdf", "txt"])

    if st.button("🚀 URUCHOM REDAKCJĘ"):
        if main_file:
            with st.spinner("Przetwarzanie..."):
                try:
                    target_val = st.session_state.target_chars
                    prompt_sys = MANIFEST_NEWS if "News" in tryb else MANIFEST_WYWIAD
                    prompt_sys += f"\nWYMÓG OBJĘTOŚCI: ok. {target_val} znaków (+/- 10%)."
                    
                    model = genai.GenerativeModel(model_name=model_selection, system_instruction=prompt_sys)
                    
                    user_parts = []
                    if context_text or context_file:
                        ctx = f"KONTEKST:\n{context_text}\n"
                        if context_file: ctx += context_file.read().decode("utf-8", errors="ignore")
                        user_parts.append(ctx)
                    
                    if main_file.type.startswith('audio'):
                        user_parts.append({"mime_type": main_file.type, "data": main_file.read()})
                        user_parts.append(f"Zredaguj jako {tryb}. Cel: {target_val} znaków.")
                    else:
                        user_parts.append(f"MATERIAŁ:\n{main_file.read().decode('utf-8')}")
                        user_parts.append(f"Zredaguj jako {tryb}. Cel: {target_val} znaków.")

                    response = model.generate_content(user_parts)
                    final_text = response.text
                    file_name_clean = get_safe_filename(final_text)
                    
                    st.success("Gotowe!")
                    c1, c2, c3 = st.columns([1, 1, 3])
                    c1.download_button("💾 Pobierz .txt", final_text, file_name=f"{file_name_clean}.txt")
                    c2.copy_button("📋 Kopiuj", final_text)
                    st.divider()
                    st.markdown(final_text)
                    
                except Exception as e:
                    st.error(f"Błąd: {e}")
        else:
            st.warning("Wgraj plik.")
else:
    st.info("Dodaj klucz API w ustawieniach (Secrets) lub wpisz go w panelu bocznym.")