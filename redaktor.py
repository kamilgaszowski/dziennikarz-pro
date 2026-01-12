import streamlit as st
import google.generativeai as genai
import time
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Do długich nagrań model 'gemini-1.5-pro' lub 'gemini-3-pro-preview' jest bezkonkurencyjny
    model = genai.GenerativeModel('gemini-1.5-pro') 
except Exception as e:
    st.error(f"Błąd konfiguracji: {e}")

# Obsługa bibliotek (DOCX/PDF)
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.9 (Audio Ready)")

# --- POMOCNIKI ---
def count_net_chars(text):
    return len(text.replace("\n", "").replace("\r", ""))

def read_text_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS:
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except: return ""
    return ""

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków (netto):", 500, 15000, value=3500, step=500)
    st.divider()
    st.caption("v11.9 - Obsługa długich nagrań")

# --- WEJŚCIE DANYCH (AUDIO + TEKST + PLIKI) ---
st.subheader("1. Materiały źródłowe")
col_a, col_b, col_c = st.columns([1, 1, 1])

with col_a:
    uploaded_audio = st.file_uploader("🎤 Wgraj nagranie (MP3, WAV, M4A):", type=['mp3', 'wav', 'm4a'])
    if uploaded_audio:
        st.success("Nagranie gotowe do analizy")

with col_b:
    uploaded_files = st.file_uploader("📄 Dodaj dokumenty (PDF, DOCX):", accept_multiple_files=True)

with col_c:
    pasted_text = st.text_area("✍️ Wklej notatki:", height=100)

# --- MANIFESTY ---
strict_length = f"DOCELOWA DŁUGOŚĆ: Równe {target_chars} znaków netto (nie licz enterów)."
if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length} Redaguj Q/A na podstawie nagrania/tekstu. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów (nadtytuł, tytuł, lid na 'O')."
else:
    manifest = f"TRYB article/news. {strict_length} Redaktor prasowy. Rdzeń: 2/3 treści. Cytaty w ramce pauzowej. Zakaz słowa 'kapłan'."

# --- GENEROWANIE ---
if st.button("🚀 Generuj Materiał"):
    # Zbieranie materiałów
    content_to_send = [manifest]
    
    text_sources = pasted_text
    if uploaded_files:
        for f in uploaded_files:
            text_sources += f"\n\n--- Materiał z: {f.name} ---\n" + read_text_file(f)
    
    if text_sources:
        content_to_send.append(f"TEKST ŹRÓDŁOWY:\n{text_sources}")

    if uploaded_audio:
        with st.spinner("Przesyłam nagranie do AI (może to zająć chwilę przy długich plikach)..."):
            # Zapisujemy audio do tymczasowego pliku
            with open("temp_audio.mp3", "wb") as f:
                f.write(uploaded_audio.getbuffer())
            
            # Przesyłamy do Google File API
            audio_file = genai.upload_file(path="temp_audio.mp3")
            
            # Czekamy aż plik zostanie przetworzony
            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            content_to_send.append(audio_file)
            content_to_send.append("Odsłuchaj nagranie i wykorzystaj je jako główne źródło do artykułu.")

    if len(content_to_send) > 1:
        with st.spinner("AI analizuje materiały i pisze..."):
            try:
                response = model.generate_content(content_to_send)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API: {e}")
    else:
        st.error("Brak materiałów (audio lub tekst)!")

# --- SEKCJA WYNIKU (Zawsze widoczna) ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    st.divider()
    
    col_res1, col_res2 = st.columns([1, 2])
    with col_res1:
        st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")
    
    with col_res2:
        c1, c2 = st.columns(2)
        if c1.button("✂️ Skróć tekst (20%)"):
            with st.spinner("Skracam..."):
                res = model.generate_content(f"Skróć to do ok. {int(netto*0.8)} znaków netto:\n\n{tekst}")
                st.session_state.artykul = res.text
                st.rerun()
        if c2.button("➕ Wydłuż tekst (20%)"):
            with st.spinner("Wydłużam..."):
                res = model.generate_content(f"Wydłuż to do ok. {int(netto*1.2)} znaków netto:\n\n{tekst}")
                st.session_state.artykul = res.text
                st.rerun()

    st.subheader("Tekst gotowy do skopiowania:")
    st.code(tekst, language="markdown", wrap_lines=True)
    st.download_button("💾 Pobierz jako .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")