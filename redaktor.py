import streamlit as st

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️")

st.title("🖋️ Dziennikarz Master PRO v10.1")

# --- BOCZNY PANEL ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    # Wybór rodzaju tekstu (Dodano Reportaż)
    typ_tekstu = st.radio(
        "Rodzaj publikacji:",
        ["News (Aktualności)", "Reportaż", "Publicystyka"],
        index=0
    )
    
    # Cel znakowy
    target_chars = st.slider("Docelowa liczba znaków:", 1000, 5000, value=3500, step=100)
    
    st.markdown("---")
    st.info(f"Wybrany tryb: **{typ_tekstu}**\n\nLimit: **{target_chars}** znaków.")

# --- WEJŚCIE DANYCH ---
source_material = st.text_area("Wklej materiały źródłowe lub konspekt:", height=300, 
                               placeholder="Tutaj wklej notatki, wypowiedzi lub surowy tekst...")

# --- LOGIKA PROMPTU (MANIFEST) ---
# Tutaj definiujemy, jak AI ma pisać
instrukcja_stylu = f"""
Jesteś doświadczonym redaktorem. Napisz tekst w stylu 'Instytutu Gość Media'.
RODZAJ TEKSTU: {typ_tekstu}
LIMIT: Maksymalnie {target_chars} znaków ze spacjami. To jest limit NIEPRZEKRACZALNY.

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
    
    st.divider()
    
    # Licznik i statystyki
    col1, col2 = st.columns(2)
    with col1:
        # Zmienia kolor w zależności od limitu
        if dlugosc > target_chars:
            st.metric("Liczba znaków", f"{dlugosc}", delta=f"{dlugosc - target_chars} za dużo", delta_color="inverse")
        else:
            st.metric("Liczba znaków", f"{dlugosc}", delta=f"{target_chars - dlugosc} zapasu")

    with col2:
        st.write("") # Odstęp
        if dlugosc > target_chars:
            st.warning("⚠️ Tekst przekracza założony limit znaków!")

    # Sekcja kopiowania
    st.subheader("Finalny tekst (gotowy do skopiowania):")
    st.code(tekst, language="text", wrap_lines=True)
    
    st.caption("💡 Kliknij przycisk 'Copy' w prawym górnym rogu ramki powyżej.")

    # Opcja "Tnij tekst" - jeśli wyjdzie za długi
    if dlugosc > target_chars + 200:
        if st.button("✂️ Skróć tekst o 20% (zachowaj styl)"):
            st.info("Tutaj można dodać funkcję 'Refine', która wyśle tekst z powrotem do AI z prośbą o skróty.")