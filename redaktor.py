# --- LOGIKA KLUCZA API ---
# Najpierw sprawdź, czy klucz jest w Secrets (dla wersji online)
api_key = st.secrets.get("GOOGLE_API_KEY")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    # Jeśli klucza nie ma w sekretach, pokaż pole do wpisania
    if not api_key:
        api_key = st.text_input("Klucz Google API:", type="password")
        st.warning("Dodaj klucz w Secrets, aby nie wpisywać go za każdym razem.")
    else:
        st.success("Klucz API załadowany automatycznie (Secrets) ✅")
    
    model_selection = st.selectbox("Model:", ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-1.5-pro-latest"])
    # ... reszta kodu (suwak itd.)