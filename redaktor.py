
import streamlit as st
import google.generativeai as genai
import re

# --- KONFIGURACJA ---
st.set_page_config(page_title="Dziennikarz Master PRO v11.0", layout="wide", page_icon="🖋️")
# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️")

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
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🖋️ Dziennikarz Master PRO v11.0")
st.title("🖋️ Dziennikarz Master PRO v10.1")

# --- BOCZNY PANEL ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    if not api_key:
        api_key = st.text_input("Klucz Google API:", type="password")
    else:
        st.success("Klucz załadowany z ustawień serwera ✅")
    # Wybór rodzaju tekstu (Dodano Reportaż)
    typ_tekstu = st.radio(
        "Rodzaj publikacji:",
        ["News (Aktualności)", "Reportaż", "Publicystyka"],
        index=0
    )
    
    model_selection = st.selectbox("Model:", ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-1.5-pro-latest"])
    # Cel znakowy
    target_chars = st.slider("Docelowa liczba znaków:", 1000, 5000, value=3500, step=100)
    
    st.divider()
    st.markdown("### 📏 Objętość materiału")
    
    # Użycie session_state do synchronizacji
    if 'target_chars' not in st.session_state:
        st.session_state.target_chars = 3000
    st.markdown("---")
    st.info(f"Wybrany tryb: **{typ_tekstu}**\n\nLimit: **{target_chars}** znaków.")

    def update_slider():
        st.session_state.target_chars = st.session_state.input_val
    def update_input():
        st.session_state.input_val = st.session_state.target_chars
# --- WEJŚCIE DANYCH ---
source_material = st.text_area("Wklej materiały źródłowe lub konspekt:", height=300, 
                               placeholder="Tutaj wklej notatki, wypowiedzi lub surowy tekst...")

    target = st.number_input("Docelowa liczba znaków:", 500, 15000, step=100, key="input_val", on_change=update_slider)
    st.slider("Suwak:", 500, 15000, step=100, key="target_chars", on_change=update_input)
# --- LOGIKA PROMPTU (MANIFEST) ---
# Tutaj definiujemy, jak AI ma pisać
instrukcja_stylu = f"""
Jesteś doświadczonym redaktorem. Napisz tekst w stylu 'Instytutu Gość Media'.
RODZAJ TEKSTU: {typ_tekstu}
LIMIT: Maksymalnie {target_chars} znaków ze spacjami. To jest limit NIEPRZEKRACZALNY.

if api_key:
    genai.configure(api_key=api_key)
    
    col_main, col_ctx = st.columns([2, 1])
STRUKTURA OBOWIĄZKOWA:
1. Nadtytuł (krótki, nad tytułem głównym).
2. Tytuł (mocny, przyciągający).
3. Lid (streszczenie, na końcu dodaj: (Instytut Gość Media)).
4. Sekcja 'Propozycje tytułów' (lista 5 propozycji).
5. Sekcja 'Propozycje lidów' (lista 3-5 propozycji, każdy zakończony: (Instytut Gość Media)).
6. Treść główna:
   - Używaj pauz do cytatów: — Tekst cytatu —
   - Styl ma być rzeczowy, ale ciepły (blisko ludzi).
   - Jeśli to News: trzymaj się faktów.
   - Jeśli to Reportaż: pozwól na więcej opisu i emocji, ale zachowaj strukturę powyżej.
"""

if st.button("🚀 Generuj Materiał"):
    if source_material:
        with st.spinner("Przetwarzam materiały i formatuję tekst..."):
            # MIEJSCE NA TWOJE WYWOŁANIE API (np. OpenAI lub Gemini)
            # Przykład:
            # response = client.generate(prompt=instrukcja_stylu + source_material)
            # wygenerowany_tekst = response.text
            
            # SYMULACJA (do testu wyglądu):
            wygenerowany_tekst = f"Nadtytuł\nPrzykładowy nadtytuł\n\nTytuł\n{typ_tekstu}: Nowe wydarzenie\n\nLid\nTo jest wygenerowany lid zgodnie z Twoim wzorem. (Instytut Gość Media)\n\n..."
            
            st.session_state.artykul = wygenerowany_tekst
    else:
        st.error("Wklej najpierw materiały źródłowe!")

# --- WYŚWIETLANIE WYNIKÓW ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    dlugosc = len(tekst)
    
    with col_main:
        st.markdown("### 1. Materiał Główny")
        tryb = st.radio("Tryb:", ["News / Artykuł", "Wywiad Q&A"], horizontal=True)
        main_file = st.file_uploader("Audio lub Tekst (.txt):", type=["mp3", "wav", "m4a", "txt"])
    st.divider()
    
    with col_ctx:
        st.markdown("### 2. Tło (Kontekst)")
        context_text = st.text_area("Notatki / Linki:", height=150)
        context_file = st.file_uploader("Plik dodatkowy:", type=["pdf", "txt"])
    # Licznik i statystyki
    col1, col2 = st.columns(2)
    with col1:
        # Zmienia kolor w zależności od limitu
        if dlugosc > target_chars:
            st.metric("Liczba znaków", f"{dlugosc}", delta=f"{dlugosc - target_chars} za dużo", delta_color="inverse")
        else:
            st.metric("Liczba znaków", f"{dlugosc}", delta=f"{target_chars - dlugosc} zapasu")

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
    with col2:
        st.write("") # Odstęp
        if dlugosc > target_chars:
            st.warning("⚠️ Tekst przekracza założony limit znaków!")

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
    # Sekcja kopiowania
    st.subheader("Finalny tekst (gotowy do skopiowania):")
    st.code(tekst, language="text", wrap_lines=True)
    
    st.caption("💡 Kliknij przycisk 'Copy' w prawym górnym rogu ramki powyżej.")

    # Opcja "Tnij tekst" - jeśli wyjdzie za długi
    if dlugosc > target_chars + 200:
        if st.button("✂️ Skróć tekst o 20% (zachowaj styl)"):
            st.info("Tutaj można dodać funkcję 'Refine', która wyśle tekst z powrotem do AI z prośbą o skróty.")