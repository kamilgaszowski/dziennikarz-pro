import streamlit as st

# --- NAGŁÓWEK ---
st.title("🖋️ Dziennikarz Master PRO v10.0")

# --- BOCZNY PANEL (Ustawienia) ---
with st.sidebar:
    st.header("Ustawienia tekstu")
    # Zmieniamy klucz na 'target_chars_input', żeby nie gryzł się z session_state
    limit_znakow = st.slider("Docelowa liczba znaków", 500, 5000, value=3500, step=100)
    
    st.info(f"Cel: ok. {limit_znakow} znaków")

# --- GŁÓWNA CZĘŚĆ ---
# Zakładamy, że tutaj masz swoje pole tekstowe na temat/źródła
temat = st.text_area("Wpisz temat lub wklej materiały źródłowe:", height=200)

if st.button("Generuj artykuł"):
    with st.spinner("Piszę... Proszę czekać."):
        # TUTAJ TWOJA LOGIKA GENEROWANIA (OpenAI / Inne API)
        # Pamiętaj, aby w promptcie dodać: "STRICT LIMIT: Maximum {limit_znakow} characters"
        
        # Przykład wywołania (uproszczony):
        # wygenerowany_tekst = call_my_api(temat, limit_znakow)
        
        # Na potrzeby przykładu przyjmijmy, że mamy już tekst:
        wygenerowany_tekst = "Tutaj pojawi się Twój wygenerowany tekst..." 
        
        # Zapisujemy w session_state, żeby nie zniknęło po odświeżeniu
        st.session_state.final_text = wygenerowany_tekst

# --- SEKCJA WYNIKOWA (TUTAJ SĄ POPRAWKI) ---
if "final_text" in st.session_state:
    tekst = st.session_state.final_text
    aktualna_liczba_znaków = len(tekst)
    
    st.divider()
    
    # 1. Licznik znaków w formie czytelnych kolumn
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktualna liczba znaków", aktualna_liczba_znaków)
    col2.metric("Limit", limit_znakow)
    
    roznica = aktualna_liczba_znaków - limit_znakow
    if roznica > 0:
        col3.warning(f"Nadmiar: +{roznica}")
    else:
        col3.success(f"Zapas: {abs(roznica)}")

    # 2. Wyświetlanie tekstu z opcją kopiowania (Opcja 1)
    st.subheader("Gotowy materiał:")
    st.code(tekst, language="text", wrap_lines=True)
    
    st.caption("☝️ Kliknij ikonę w prawym górnym rogu ramki, aby skopiować.")

    # 3. Opcja skracania (Dodatek)
    if roznica > 500:
        st.error("⚠️ Tekst jest znacznie za długi. Czy chcesz go streścić?")
        if st.button("Skróć tekst automatycznie"):
            # Tutaj możesz dodać logikę poprawki (tzw. "refining")
            pass