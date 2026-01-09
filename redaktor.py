import streamlit as st
import google.generativeai as genai

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO", layout="wide", page_icon="🖋️")

# CSS dla lepszego wyglądu (opcjonalnie)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
    </style>
 """, unsafe_allow_html=True)

# --- MANIFESTY (Ostateczne wersje) ---
MANIFEST_NEWS = """
Jesteś surowym redaktorem agencji prasowej (standard Reuters/PAP). 
TWOJE ZADANIA:
1. LEAD: Pierwszy akapit (max 25 słów) musi zawierać: Kto, co, gdzie, kiedy. Najważniejsza informacja na start.
2. STRUKTURA: Odwrócona piramida. Akapity 2-3 zdaniowe.
3. FILTR ANTY-AI: Bezwzględnie usuń: "kluczowy", "istotny", "unikalny", "fascynujący", "warto zauważyć", "w dzisiejszych czasach".
4. STYL: Używaj strony czynnej. Zamiast "zostało przeprowadzone", pisz "przeprowadzono".
"""

MANIFEST_WYWIAD = """
Jesteś redaktorem wywiadów prasowych.
TWOJE ZADANIA:
1. NUT GRAF: Napisz wstęp wyjaśniający kontekst rozmowy.
2. FORMAT: Pytania pogrubione (np. **Pytanie:**), odpowiedzi czyste.
3. REDAKCJA: Usuń wypełniacze (yhy, mhm, no właśnie, wie pan). Skracaj dygresje, zostawiając samo mięso.
4. CHARAKTER: Zachowaj specyficzny język rozmówcy. Jeśli mówi potocznie – zostaw to. Nie poprawiaj go na styl encyklopedyczny.
5. FILTR ANTY-AI: Usuń zwroty typu: "to świetne pytanie", "cieszę się, że o to pytasz".
"""

# --- INTERFEJS ---
st.title("🖋️ Dziennikarz Master PRO")
st.subheader("Twoje studio transkrypcji i redakcji")

with st.expander("🔑 Ustawienia API i Modelu", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        api_key = st.text_input("Wklej Google API Key:", type="password")
    with col2:
    model_name = st.selectbox("Wybierz silnik:", ["gemini-1.5-flash", "gemini-1.5-pro-latest"])
if api_key:
    genai.configure(api_key=api_key)
    
    tab1, tab2 = st.tabs(["📝 Przetwarzanie", "📜 Twoje Manifesty"])
    
    with tab2:
        st.info("Oto instrukcje, którymi kieruje się AI:")
        st.text_area("Manifest News:", MANIFEST_NEWS, height=150, disabled=True)
        st.text_area("Manifest Wywiad:", MANIFEST_WYWIAD, height=150, disabled=True)

    with tab1:
        tryb = st.radio("Wybierz format docelowy:", ["News", "Wywiad"], horizontal=True)
        
        uploaded_file = st.file_uploader("Wgraj nagranie (audio) lub plik tekstowy:", type=["mp3", "wav", "m4a", "txt"])
        
        if st.button("🚀 GENERUJ MATERIAŁ"):
            if uploaded_file is not None:
                with st.spinner("Gemini analizuje materiał..."):
                    try:
                        # Wybór instrukcji
                        current_prompt = MANIFEST_NEWS if tryb == "News" else MANIFEST_WYWIAD
                        
                        model = genai.GenerativeModel(
                            model_name=model_name,
                            system_instruction=current_prompt
                        )
                        
                        # Obsługa audio vs tekst
                        if uploaded_file.type.startswith('audio'):
                            response = model.generate_content([
                                {"mime_type": uploaded_file.type, "data": uploaded_file.read()},
                                "Przeprowadź transkrypcję i zredaguj zgodnie z instrukcją."
                            ])
                        else:
                            text_content = uploaded_file.read().decode("utf-8")
                            response = model.generate_content(text_content)
                        
                        st.success("Gotowe!")
                        st.markdown("---")
                        st.markdown(response.text)
                        st.download_button("Pobierz tekst (.txt)", response.text, file_name=f"{tryb}_zredagowany.txt")
                        
                    except Exception as e:
                        st.error(f"Błąd przetwarzania: {e}")
            else:
                st.warning("Najpierw wgraj plik.")
else:
    st.warning("Wprowadź swój klucz API w sekcji powyżej, aby odblokować narzędzie.")