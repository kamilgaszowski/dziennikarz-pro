import streamlit as st
import google.generativeai as genai

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennikarz Master PRO v5.0", layout="wide", page_icon="🖋️")

# --- ZAAWANSOWANE MANIFESTY (STYL GĄSZOWSKI) ---

MANIFEST_WYWIAD = """
Jesteś elitarnym redaktorem wywiadów prasowych (styl Kamila Gąszowskiego). 
Twoim zadaniem jest przekształcenie surowego materiału w gotowy, płynny wywiad (Q&A).

1. FILOZOFIA: "REŻYSERIA ROZMOWY"
   - Surowa transkrypcja to tylko materiał. Stwórz płynną rozmowę.
   - Usuń potakiwania ("tak", "oczywiście", "mhm"). Zostaw samo gęste.
   - Skracaj zawiłe pytania dziennikarza do jednego, celnego zdania.

2. ŁĄCZENIE I DZIELENIE
   - Łączenie: Jeśli dziennikarz zadaje kilka pytań pomocniczych, zbij je w jedno konkretne.
   - Dzielenie: Jeśli odpowiedź jest zbyt długa, wstaw logiczny śródtytuł lub rozbij ją pytaniem dopytującym (nawet jeśli nie padło, ale wynika z kontekstu).

3. STRUKTURA (OBOWIĄZKOWA):
   - LEAD: Wywiad musi mieć wstęp (blurb) – kim jest rozmówca i jaki jest cel rozmowy.
   - ŚRÓDTYTUŁY: Co 3-4 pytania wstaw śródtytuł (WERSALIKI).
   - FORMATOWANIE: **Pytanie:** (pogrubione), Odpowiedź: (tekst zwykły).
"""

MANIFEST_NEWS = """
Jesteś osobistym redaktorem dziennikarza Kamila Gąszowskiego. 
Twoim zadaniem jest pisanie gotowych do publikacji tekstów na podstawie materiałów i KONTEKSTU.

### STRUKTURA WYJŚCIOWA (OBOWIĄZKOWA):

CZĘŚĆ 1: METADANE
- NADTYTUŁY (3 warianty): Krótkie, informacyjne, WERSALIKI.
- TYTUŁY (3 warianty): 2-6 słów, chwytliwe lub oparte na mocnym cytacie.
- LEADY (3 warianty): 
  * Wariant A: Sylwetkowy (o bohaterze).
  * Wariant B: Newsowy (5W: kto, co, gdzie, kiedy, dlaczego).
  * Wariant C: Opisowy (obrazowy/reportażowy).

CZĘŚĆ 2: GOTOWY ARTYKUŁ
- Zredagowany tekst. Wybierz najlepszy lead i wstaw go na początek (pogrubiony).
- ŚRÓDTYTUŁY (WERSALIKI) co ok. 3 akapity.
- Pamiętaj o "mięsistych cytatach" i braku "AI-yzmów" (kluczowy, istotny, unikalny).
- Jeśli brakuje danych (daty, nazwiska) – napisz w nawiasie [BRAK DANYCH].

ZAKAZ HALUCYNACJI: Opieraj się na materiale źródłowym i dostarczonym kontekście.
"""

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🖋️ Dziennikarz Master PRO")
st.subheader("System redakcyjny v5.0 (Edycja Gąszowski)")

# Sidebar z ustawieniami
with st.sidebar:
    st.header("⚙️ Konfiguracja")
    api_key = st.text_input("Klucz Google API:", type="password")
    model_selection = st.selectbox("Wybierz silnik:", [
        "gemini-3-pro-preview", 
        "gemini-2.5-pro", 
        "gemini-1.5-pro-latest"
    ])
    st.divider()
    st.markdown("### Jak używać?")
    st.write("1. Wybierz format.")
    st.write("2. Wgraj główne audio/tekst.")
    st.write("3. (Opcjonalnie) Dodaj kontekst.")
    st.write("4. Kliknij Redaguj.")

if api_key:
    genai.configure(api_key=api_key)
    
    # Główne okno
    col_main, col_ctx = st.columns([2, 1])
    
    with col_main:
        st.markdown("### 1. Materiał Źródłowy")
        tryb = st.radio("Format docelowy:", ["News / Artykuł", "Wywiad Q&A"], horizontal=True)
        main_file = st.file_uploader("Wgraj główne nagranie (audio) lub tekst (txt):", type=["mp3", "wav", "m4a", "txt"])
    
    with col_ctx:
        st.markdown("### 2. Kontekst (Opcjonalnie)")
        context_text = st.text_area("Linki, notatki, bio rozmówcy:", placeholder="Wklej tutaj dodatkowe informacje lub treść linków...")
        context_file = st.file_uploader("Dodatkowy plik z tłem (PDF/TXT):", type=["pdf", "txt"])

    if st.button("🚀 REDAGUJ ZGODNIE Z MANIFESTEM"):
        if main_file:
            with st.spinner("Trwa proces reżyserii i redakcji..."):
                try:
                    # Wybór Manifestu
                    system_prompt = MANIFEST_NEWS if "News" in tryb else MANIFEST_WYWIAD
                    model = genai.GenerativeModel(model_name=model_selection, system_instruction=system_prompt)
                    
                    # Przygotowanie wsadu
                    user_parts = []
                    
                    # 1. Dodaj kontekst (jeśli istnieje)
                    if context_text or context_file:
                        ctx_info = f"--- KONTEKST I TŁO ---\n{context_text}\n"
                        if context_file:
                            if context_file.type == "text/plain":
                                ctx_info += context_file.read().decode("utf-8")
                            else:
                                ctx_info += "[Wgrano plik pomocniczy PDF/Inny]" # Uproszczenie dla PDF
                        user_parts.append(ctx_info)
                    
                    # 2. Dodaj główny materiał
                    if main_file.type.startswith('audio'):
                        user_parts.append({"mime_type": main_file.type, "data": main_file.read()})
                        user_parts.append(f"Zredaguj to nagranie audio jako {tryb}. Wykorzystaj powyższy kontekst, jeśli został podany.")
                    else:
                        main_text = main_file.read().decode("utf-8")
                        user_parts.append(f"--- MATERIAŁ GŁÓWNY ---\n{main_text}")
                        user_parts.append(f"Zredaguj powyższy materiał jako {tryb}. Wykorzystaj kontekst do uzupełnienia luk.")

                    # Generowanie
                    response = model.generate_content(user_parts)
                    
                    st.success("Materiał przygotowany!")
                    st.divider()
                    st.markdown(response.text)
                    st.download_button("Pobierz gotowy tekst (.txt)", response.text, file_name=f"{tryb}_Gaszowski.txt")
                    
                except Exception as e:
                    st.error(f"Błąd silnika: {e}")
        else:
            st.warning("Musisz wgrać przynajmniej plik główny.")
else:
    st.info("Wprowadź swój klucz API w panelu bocznym, aby zacząć pracę.")