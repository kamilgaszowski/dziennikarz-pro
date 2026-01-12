import streamlit as st
import google.generativeai as genai

# 1. KONFIGURACJA API (Z Twoich Secrets)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Trzymamy się nazwy gemini-3 zgodnie z Twoim wyborem
    model = genai.GenerativeModel('gemini-3') 
except Exception as e:
    st.error(f"Problem z konfiguracją modelu: {e}")

# Obsługa bibliotek (DOCX/PDF) - stabilne ładowanie
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.8")

# --- FUNKCJE ---
def count_net_chars(text):
    # Liczymy tylko "mięso" - ignorujemy entery (znaki nowej linii)
    return len(text.replace("\n", "").replace("\r", ""))

def read_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith('.docx') and HAS_LIBS:
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith('.pdf') and HAS_LIBS:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
    except Exception:
        return ""
    return ""

# --- INTERFEJS ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków (netto):", 500, 15000, value=3500, step=500)
    st.divider()
    st.caption("Wersja Stabilna v11.8")

col_in1, col_in2 = st.columns(2)
with col_in1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col_in2:
    pasted_text = st.text_area("Lub wklej materiały tutaj:", height=150)

# Budowanie bazy materiałów
all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał: {f.name} ---\n" + read_file(f)

# --- MANIFESTY ---
strict_length = f"CEL: {target_chars} znaków netto (bez znaków nowej linii)."
if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length} Redaguj Q/A. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów (nadtytuł, tytuł, lid na 'O')."
else:
    manifest = f"TRYB article/news. {strict_length} Redaktor prasowy. Rdzeń: 2/3 treści. Cytaty w ramce pauzowej. Zakaz słowa 'kapłan'."

# --- AKCJA ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner("AI pracuje..."):
            try:
                prompt = f"{manifest}\n\nMATERIAŁ ŹRÓDŁOWY:\n{all_source}"
                response = model.generate_content(prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API: {e}")
    else:
        st.error("Brak materiałów źródłowych!")

# --- SEKCJA WYNIKU (Zawsze widoczna, jeśli tekst istnieje) ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    st.divider()
    
    # 1. Licznik Netto
    st.metric(
        label="Liczba znaków (netto - bez enterów)", 
        value=netto, 
        delta=f"{roznica} vs cel", 
        delta_color="inverse"
    )

    # 2. Narzędzia korekty
    c1, c2 = st.columns(2)
    if c1.button("✂️ Skróć o 20%"):
        with st.spinner("Skracam..."):
            res = model.generate_content(f"Skróć o 20% (cel: {int(netto*0.8)} znaków):\n\n{tekst}")
            st.session_state.artykul = res.text
            st.rerun()
    if c2.button("➕ Wydłuż o 20%"):
        with st.spinner("Wydłużam..."):
            res = model.generate_content(f"Wydłuż o 20% (cel: {int(netto*1.2)} znaków):\n\n{tekst}")
            st.session_state.artykul = res.text
            st.rerun()

    # 3. POLE KOPIOWANIA (Serce tej wersji)
    st.subheader("Tekst do skopiowania:")
    # st.code zapewnia, że ikona kopiowania jest ZAWSZE w rogu czarnej ramki
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button("💾 Pobierz jako .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")