import streamlit as st
import google.generativeai as genai

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO v3.0", layout="wide")

# --- MANIFESTY (Zoptymalizowane pod Gemini 3 / 2.5) ---
MANIFEST_NEWS = """
Jesteś doświadczonym dziennikarzem depeszowym. TWOIM ZADANIEM NIE JEST STRESZCZENIE, LECZ NAPISANIE NEWSA.
1. TYTUŁ: Chwytliwy, informacyjny, w czasie teraźniejszym.
2. LEAD: Pierwszy akapit (pogrubiony) musi zawierać 5W: Kto, co, gdzie, kiedy, dlaczego.
3. STRUKTURA: Napisz artykuł w formie odwróconej piramidy. Najważniejsze fakty na górze, detale niżej.
4. STYL: Usuń wszystkie "AI-izmy" (kluczowy, istotny, warto zauważyć). Pisz krótko, twardo, konkretnie.
5. ZAKAZ: Nie pisz "W tekście mowa o...", po prostu napisz newsa tak, jakbyś go publikował na portalu.
"""

MANIFEST_WYWIAD = """
Jesteś redaktorem prowadzącym w dużym tygodniku. TWOIM ZADANIEM JEST STWORZENIE GOTOWEGO WYWIADU (Q&A).
1. WSTĘP: Napisz 3-zdaniowy wstęp (tzw. blurb) o rozmówcy i temacie.
2. FORMAT: Pytania redakcji oznacz jako **Pytanie:**, odpowiedzi jako **Odpowiedź:**.
3. REDAKCJA: Bezwzględnie usuń powtórzenia, "ee", "yy", wtrącenia typu "no wie pan" oraz dygresje, które nic nie wnoszą.
4. DYNAMIKA: Jeśli rozmówca mówi zbyt długo, podziel jego wypowiedź dodatkowym pytaniem redakcyjnym.
5. STYL: Zachowaj energię rozmowy, ale spraw, by brzmiała inteligentnie i płynnie.
"""

# --- INTERFEJS ---
st.title("🖋️ Dziennikarz Master PRO (High-End Edition)")

with st.expander("🔑 Ustawienia API i Modelu", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        api_key = st.text_input("Wklej Google API Key:", type="password")
    with col2:
        # Tu wpisałem nazwy, które powinny działać na Twoim koncie płatnym
        model_name = st.selectbox("Wybierz silnik:", [
            "gemini-3-pro-preview", 
            "gemini-2.5-pro", 
            "gemini-1.5-pro-latest"
        ])

if api_key:
    genai.configure(api_key=api_key)
    
    tab1, tab2 = st.tabs(["📝 Redakcja Materiału", "📜 Instrukcje Systemowe"])
    
    with tab1:
        tryb = st.radio("Wybierz format docelowy:", ["News", "Wywiad"], horizontal=True)
        uploaded_file = st.file_uploader("Wgraj nagranie audio lub tekst:", type=["mp3", "wav", "m4a", "txt"])
        
        if st.button("🚀 GENERUJ MATERIAŁ"):
            if uploaded_file:
                with st.spinner(f"Uruchamiam silnik {model_name}..."):
                    try:
                        prompt_system = MANIFEST_NEWS if tryb == "News" else MANIFEST_WYWIAD
                        model = genai.GenerativeModel(model_name=model_name, system_instruction=prompt_system)
                        
                        if uploaded_file.type.startswith('audio'):
                            # Dla Gemini 3 ważne jest, by dodać precyzyjne polecenie obróbki
                            content = [
                                {"mime_type": uploaded_file.type, "data": uploaded_file.read()},
                                f"Na podstawie tego nagrania napisz profesjonalny {tryb.lower()}. Nie streszczaj, napisz gotowy tekst dziennikarski."
                            ]
                        else:
                            text_content = uploaded_file.read().decode("utf-8")
                            content = f"Przerób poniższy tekst na {tryb.lower()} zgodnie z instrukcjami systemowymi:\n\n{text_content}"
                        
                        response = model.generate_content(content)
                        st.success("Materiał gotowy!")
                        st.markdown(response.text)
                        st.download_button("Pobierz (.txt)", response.text, file_name="tekst_zredagowany.txt")
                        
                    except Exception as e:
                        st.error(f"Błąd: {e}")
            else:
                st.warning("Najpierw wgraj plik.")