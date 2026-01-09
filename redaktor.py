import streamlit as st
import google.generativeai as genai
import re

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO v9.0", layout="wide", page_icon="🖋️")

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

# --- MANIFESTY (ZAAWANSOWANE) ---

MANIFEST_WYWIAD = """
Jesteś elitarnym redaktorem wywiadów (styl Kamila Gąszowskiego). Twój cel: stworzyć tekst, w którym rozmówca lśni, a dziennikarz umiejętnie prowadzi grę.

1. ZASADA "OTWARTEGO ZAMKA" (KLUCZOWE):
   - Zakaz "spojlerowania" w pytaniach. Nie podawaj faktów, które rozmówca ma dopiero wyjawić.
   - ZAMIAST: "Jak wspominasz praktykę w Mokrzeszowie?", ZAPYTAJ: "Doświadczyłeś życia w małej, wiejskiej wspólnocie. Jak to zderzenie z prostą codziennością na Ciebie wpłynęło?".
   - Pytanie ma dawać PRZESTRZEŃ, a nie gotową tezę.

2. REŻYSERIA I DYNAMIKA:
   - Wycinaj "brud" (mhm, tak, właśnie), ale zachowaj potoczność tam, gdzie buduje emocje.
   - Jeśli odpowiedź jest długa, "wejdź w słowo" pytaniem, które wynika z logiki wypowiedzi, by nadać rozmowie tempo.

3. STRUKTURA:
   - METADANE: 3x TYTUŁ (metaforyczny, na cytacie, informacyjny).
   - LEAD: Esencjonalny blurb.
   - ROZMOWA: **Pytanie:** / Odpowiedź:. Śródtytuły (WERSALIKI) co 3-4 pytania.

4. ZAKAZ AI-YZMÓW: Żadnych "kluczowych aspektów", "istotnych kwestii" czy "warto zauważyć".
"""

MANIFEST_NEWS = """
Jesteś osobistym redaktorem Kamila Gąszowskiego. Piszesz newsy z charakterem.
CZĘŚĆ 1: METADANE (3x Nadtytuł WERSALIKAMI, 3x Tytuł, 3x Lead: Sylwetkowy, Newsowy, Opisowy).
CZĘŚĆ 2: ARTYKUŁ. Wybierz najlepszy lead (bold) i napisz mięsisty tekst.
- Zakaz AI-yzmów. Brak danych oznacz jako [BRAK DANYCH].
"""

# --- INTERFEJS ---
st.title("🖋️ Dziennikarz Master PRO v9.0")
st.caption("Tryb: Journalistic Integrity & No-Spoiler Questions")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    api_key = st.text_input("Klucz Google API:", type="password")
    model_selection = st.selectbox("Model:", ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-1.5-pro-latest"])
    
    st.divider()
    dlugosc = st.select_slider(
        "Docelowa objętość (znaki):",
        options=[500, 1000, 2000, 3000, 5000, 10000],
        value=3000
    )

if api_key:
    genai.configure(api_key=api_key)
    
    col_main, col_ctx = st.columns([2, 1])
    
    with col_main:
        st.markdown("### 1. Materiał do obróbki")
        tryb = st.radio("Format docelowy:", ["News / Artykuł", "Wywiad Q&A"], horizontal=True)
        main_file = st.file_uploader("Wgraj plik (audio lub .txt):", type=["mp3", "wav", "m4a", "txt"])
    
    with col_ctx:
        st.markdown("### 2. Kontekst / Notatki")
        context_text = st.text_area("Dodaj tło, linki lub bio:", height=150)
        context_file = st.file_uploader("Plik dodatkowy (PDF/TXT):", type=["pdf", "txt"])

    if st.button("🚀 GENERUJ ZREDAGOWANY TEKST"):
        if main_file:
            with st.spinner("Gemini 3 prowadzi rozmowę..."):
                try:
                    prompt_sys = MANIFEST_NEWS if "News" in tryb else MANIFEST_WYWIAD
                    prompt_sys += f"\nZorientuj się na długość ok. {dlugosc} znaków."
                    
                    model = genai.GenerativeModel(model_name=model_selection, system_instruction=prompt_sys)
                    
                    user_parts = []
                    # Dodaj kontekst
                    if context_text or context_file:
                        ctx = f"KONTEKST (Użyj go, by lepiej rozumieć rozmówcę, ale nie zdradzaj faktów w pytaniach):\n{context_text}\n"
                        if context_file:
                            ctx += context_file.read().decode("utf-8", errors="ignore")
                        user_parts.append(ctx)
                    
                    # Dodaj główne źródło
                    if main_file.type.startswith('audio'):
                        user_parts.append({"mime_type": main_file.type, "data": main_file.read()})
                        user_parts.append(f"Zredaguj to audio jako {tryb}. Pamiętaj: pytania mają otwierać wątki, a nie je zdradzać.")
                    else:
                        user_parts.append(f"MATERIAŁ DO OBRÓBKI:\n{main_file.read().decode('utf-8')}")
                        user_parts.append(f"Zredaguj to jako {tryb}. Stosuj 'Zasadę Otwartego Zamka' w pytaniach.")

                    response = model.generate_content(user_parts)
                    final_text = response.text
                    
                    # Dynamiczna nazwa pliku
                    file_name_clean = get_safe_filename(final_text)
                    
                    st.success("Materiał gotowy!")
                    
                    # Przyciski
                    c1, c2, c3 = st.columns([1, 1, 3])
                    c1.download_button("💾 Pobierz .txt", final_text, file_name=f"{file_name_clean}.txt")
                    c2.copy_button("📋 Kopiuj", final_text)
                    
                    st.divider()
                    st.markdown(final_text)
                    
                except Exception as e:
                    st.error(f"Wystąpił błąd: {e}")
        else:
            st.warning("Wgraj materiał źródłowy.")
else:
    st.info("Wprowadź klucz API, aby odblokować system.")