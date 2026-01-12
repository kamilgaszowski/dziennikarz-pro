import streamlit as st
import google.generativeai as genai

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO", layout="wide", page_icon="🖋️")
st.set_page_config(page_title="Dziennikarz Master PRO v3.0", layout="wide")

# CSS dla lepszego wyglądu (opcjonalnie)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
    </style>
 """, unsafe_allow_html=True)

# --- MANIFESTY (Ostateczne wersje) ---
# --- MANIFESTY (Zoptymalizowane pod Gemini 3 / 2.5) ---
MANIFEST_NEWS = """
Jesteś surowym redaktorem agencji prasowej (standard Reuters/PAP). 
TWOJE ZADANIA:
1. LEAD: Pierwszy akapit (max 25 słów) musi zawierać: Kto, co, gdzie, kiedy. Najważniejsza informacja na start.
2. STRUKTURA: Odwrócona piramida. Akapity 2-3 zdaniowe.
3. FILTR ANTY-AI: Bezwzględnie usuń: "kluczowy", "istotny", "unikalny", "fascynujący", "warto zauważyć", "w dzisiejszych czasach".
4. STYL: Używaj strony czynnej. Zamiast "zostało przeprowadzone", pisz "przeprowadzono".
Jesteś doświadczonym dziennikarzem depeszowym. TWOIM ZADANIEM NIE JEST STRESZCZENIE, LECZ NAPISANIE NEWSA.
1. TYTUŁ: Chwytliwy, informacyjny, w czasie teraźniejszym.
2. LEAD: Pierwszy akapit (pogrubiony) musi zawierać 5W: Kto, co, gdzie, kiedy, dlaczego.
3. STRUKTURA: Napisz artykuł w formie odwróconej piramidy. Najważniejsze fakty na górze, detale niżej.
4. STYL: Usuń wszystkie "AI-izmy" (kluczowy, istotny, warto zauważyć). Pisz krótko, twardo, konkretnie.
5. ZAKAZ: Nie pisz "W tekście mowa o...", po prostu napisz newsa tak, jakbyś go publikował na portalu.
"""

MANIFEST_WYWIAD = """
Jesteś redaktorem wywiadów prasowych.
TWOJE ZADANIA:
1. NUT GRAF: Napisz wstęp wyjaśniający kontekst rozmowy.
2. FORMAT: Pytania pogrubione (np. **Pytanie:**), odpowiedzi czyste.
3. REDAKCJA: Usuń wypełniacze (yhy, mhm, no właśnie, wie pan). Skracaj dygresje, zostawiając samo mięso.
4. CHARAKTER: Zachowaj specyficzny język rozmówcy. Jeśli mówi potocznie – zostaw to. Nie poprawiaj go na styl encyklopedyczny.
5. FILTR ANTY-AI: Usuń zwroty typu: "to świetne pytanie", "cieszę się, że o to pytasz".
Jesteś redaktorem prowadzącym w dużym tygodniku. TWOIM ZADANIEM JEST STWORZENIE GOTOWEGO WYWIADU (Q&A).
1. WSTĘP: Napisz 3-zdaniowy wstęp (tzw. blurb) o rozmówcy i temacie.
2. FORMAT: Pytania redakcji oznacz jako **Pytanie:**, odpowiedzi jako **Odpowiedź:**.
3. REDAKCJA: Bezwzględnie usuń powtórzenia, "ee", "yy", wtrącenia typu "no wie pan" oraz dygresje, które nic nie wnoszą.
4. DYNAMIKA: Jeśli rozmówca mówi zbyt długo, podziel jego wypowiedź dodatkowym pytaniem redakcyjnym.
5. STYL: Zachowaj energię rozmowy, ale spraw, by brzmiała inteligentnie i płynnie.
"""

# --- INTERFEJS ---
st.title("🖋️ Dziennikarz Master PRO")
st.subheader("Twoje studio transkrypcji i redakcji")
st.title("🖋️ Dziennikarz Master PRO (High-End Edition)")

with st.expander("🔑 Ustawienia API i Modelu", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        api_key = st.text_input("Wklej Google API Key:", type="password")
    with col2:
        model_name = st.selectbox("Wybierz silnik:", ["gemini-2.5-flash", "gemini-2.5-pro-latest"])
        # Tu wpisałem nazwy, które powinny działać na Twoim koncie płatnym
        model_name = st.selectbox("Wybierz silnik:", [
            "gemini-3-pro-preview", 
            "gemini-2.5-pro", 
            "gemini-1.5-pro-latest"
        ])

if api_key:
    genai.configure(api_key=api_key)
    
    tab1, tab2 = st.tabs(["📝 Przetwarzanie", "📜 Twoje Manifesty"])
    tab1, tab2 = st.tabs(["📝 Redakcja Materiału", "📜 Instrukcje Systemowe"])
    
    with tab2:
        st.info("Oto instrukcje, którymi kieruje się AI:")
        st.text_area("Manifest News:", MANIFEST_NEWS, height=150, disabled=True)
        st.text_area("Manifest Wywiad:", MANIFEST_WYWIAD, height=150, disabled=True)

    with tab1:
        tryb = st.radio("Wybierz format docelowy:", ["News", "Wywiad"], horizontal=True)
        
        uploaded_file = st.file_uploader("Wgraj nagranie (audio) lub plik tekstowy:", type=["mp3", "wav", "m4a", "txt"])
        uploaded_file = st.file_uploader("Wgraj nagranie audio lub tekst:", type=["mp3", "wav", "m4a", "txt"])
        
        if st.button("🚀 GENERUJ MATERIAŁ"):
            if uploaded_file is not None:
                with st.spinner("Gemini analizuje materiał..."):
            if uploaded_file:
                with st.spinner(f"Uruchamiam silnik {model_name}..."):
                    try:
                        # Wybór instrukcji
                        current_prompt = MANIFEST_NEWS if tryb == "News" else MANIFEST_WYWIAD
                        
                        model = genai.GenerativeModel(
                            model_name=model_name,
                            system_instruction=current_prompt
                        )
                        prompt_system = MANIFEST_NEWS if tryb == "News" else MANIFEST_WYWIAD
                        model = genai.GenerativeModel(model_name=model_name, system_instruction=prompt_system)
                        
                        # Obsługa audio vs tekst
                        if uploaded_file.type.startswith('audio'):
                            response = model.generate_content([
                            # Dla Gemini 3 ważne jest, by dodać precyzyjne polecenie obróbki
                            content = [
                                {"mime_type": uploaded_file.type, "data": uploaded_file.read()},
                                "Przeprowadź transkrypcję i zredaguj zgodnie z instrukcją."
                            ])
                                f"Na podstawie tego nagrania napisz profesjonalny {tryb.lower()}. Nie streszczaj, napisz gotowy tekst dziennikarski."
                            ]
                        else:
                            text_content = uploaded_file.read().decode("utf-8")
                            response = model.generate_content(text_content)
                            content = f"Przerób poniższy tekst na {tryb.lower()} zgodnie z instrukcjami systemowymi:\n\n{text_content}"
                        
                        st.success("Gotowe!")
                        st.markdown("---")
                        response = model.generate_content(content)
                        st.success("Materiał gotowy!")
                        st.markdown(response.text)
                        st.download_button("Pobierz tekst (.txt)", response.text, file_name=f"{tryb}_zredagowany.txt")
                        st.download_button("Pobierz (.txt)", response.text, file_name="tekst_zredagowany.txt")
                        
                    except Exception as e:
                        st.error(f"Błąd przetwarzania: {e}")
                        st.error(f"Błąd: {e}")
            else:
                st.warning("Najpierw wgraj plik.")
else:
    st.warning("Wprowadź swój klucz API w sekcji powyżej, aby odblokować narzędzie.")
                st.warning("Najpierw wgraj plik.")