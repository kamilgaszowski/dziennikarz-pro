import streamlit as st
import google.generativeai as genai
import re

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO v10.0", layout="wide", page_icon="🖋️")

def get_safe_filename(text):
    """Generuje nazwę pliku na podstawie tytułu zaproponowanego przez AI."""
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
1. ZASADA "OTWARTEGO ZAMKA": Pytania mają dawać PRZESTRZEŃ. Nie podawaj w pytaniu faktów, które rozmówca ma dopiero wyjawić. 
   - ZAMIAST: "Wiem, że byłeś w Wałbrzychu...", ZAPYTAJ: "Zostałeś posłany do pracy w dużym mieście. Jak to zderzenie z miejską parafią zmieniło Twoje postrzeganie posługi?".
2. REŻYSERIA: Wycinaj brud, kondensuj odpowiedzi, wstawiaj pytania dopytujące w długie bloki tekstu.
3. STRUKTURA: 3x TYTUŁ, LEAD (blurb), ROZMOWA (Pytanie: / Odpowiedź:), ŚRÓDTYTUŁY (WERSALIKI).
"""

MANIFEST_NEWS = """
Jesteś osobistym redaktorem Kamila Gąszowskiego. Piszesz newsy z charakterem.
CZĘŚĆ 1: METADANE (3x Nadtytuł WERSALIKAMI, 3x Tytuł, 3x Lead: Sylwetkowy, Newsowy, Opisowy).
CZĘŚĆ 2: ARTYKUŁ z pogrubionym leadem i ŚRÓDTYTUŁAMI (WERSALIKI).
- Całkowity zakaz AI-yzmów. Brak danych = [BRAK DANYCH].
"""

# --- INTERFEJS ---
st.title("🖋️ Dziennikarz Master PRO v10.0")

# Inicjalizacja stanu dla synchronizacji suwaka i pola liczbowego
if 'target_chars' not in st.session_state:
    st.session_state.target_chars = 3000

with st.sidebar:
    st.header("⚙️ Ustawienia")
    api_key = st.text_input("Klucz Google API:", type="password")
    model_selection = st.selectbox("Model:", ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-1.5-pro-latest"])
    
    st.divider()
    st.markdown("### 📏 Objętość materiału")
    
    # Synchronizacja suwaka i inputu
    chars_input = st.number_input("Docelowa liczba znaków:", min_value=500, max_value=15000, step=100, key="target_chars")
    chars_slider = st.slider("Przesuń, by zmienić:", min_value=500, max_value=15000, step=100, key="target_chars_slider", value=st.session_state.target_chars)
    
    # Aktualizacja session_state, by oba pola były spójne
    st.session_state.target_chars = chars_slider
    
    st.caption("AI zachowa margines błędu ok. 10% (tolerancja redakcyjna).")

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

    if st.button("🚀 GENERUJ ZREDAGOWANY MATERIAŁ"):
        if main_file:
            with st.spinner("Model Gemini 3 pracuje nad tekstem..."):
                try:
                    target = st.session_state.target_chars
                    prompt_sys = MANIFEST_NEWS if "News" in tryb else MANIFEST_WYWIAD
                    prompt_sys += f"\nWYMÓG OBJĘTOŚCI: Przygotuj materiał o długości ok. {target} znaków (tolerancja +/- 10%)."
                    
                    model = genai.GenerativeModel(model_name=model_selection, system_instruction=prompt_sys)
                    
                    user_parts = []
                    if context_text or context_file:
                        ctx = f"KONTEKST (tło dla redaktora):\n{context_text}\n"
                        if context_file:
                            ctx += context_file.read().decode("utf-8", errors="ignore")
                        user_parts.append(ctx)
                    
                    if main_file.type.startswith('audio'):
                        user_parts.append({"mime_type": main_file.type, "data": main_file.read()})
                        user_parts.append(f"Zredaguj jako {tryb}. Celuj w {target} znaków. Pamiętaj o zasadzie 'Otwartego Zamka' w wywiadzie.")
                    else:
                        user_parts.append(f"MATERIAŁ DO REDAKCJI:\n{main_file.read().decode('utf-8')}")
                        user_parts.append(f"Zredaguj jako {tryb}. Celuj w {target} znaków. Nie spojleruj faktów w pytaniach.")

                    response = model.generate_content(user_parts)
                    final_text = response.text
                    
                    file_name_clean = get_safe_filename(final_text)
                    
                    st.success("Redakcja zakończona!")
                    
                    # Akcje
                    c1, c2, c3 = st.columns([1, 1, 3])
                    c1.download_button("💾 Pobierz .txt", final_text, file_name=f"{file_name_clean}.txt")
                    c2.copy_button("📋 Kopiuj", final_text)
                    
                    st.divider()
                    st.markdown(final_text)
                    
                except Exception as e:
                    st.error(f"Błąd: {e}")
        else:
            st.warning("Najpierw wgraj plik źródłowy.")
else:
    st.info("Podaj klucz API w panelu bocznym.")