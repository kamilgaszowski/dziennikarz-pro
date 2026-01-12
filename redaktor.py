import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd konfiguracji API: {e}")

# Obsługa bibliotek do plików
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.6")

# --- FUNKCJE POMOCNICZE ---
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
    except Exception as e:
        st.error(f"Błąd pliku {uploaded_file.name}: {e}")
    return ""

def count_net_chars(text):
    return len(text.replace("\n", "").replace("\r", ""))

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków (netto):", 500, 15000, value=3500, step=500)
    st.info(f"Tryb: {typ_tekstu} | Cel: {target_chars} znaków")

# --- WEJŚCIE DANYCH ---
col1, col2 = st.columns(2)
with col1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col2:
    pasted_text = st.text_area("Wklej materiały tutaj:", height=150)

all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- MANIFESTY ---
strict_length_instruction = f"WAŻNE: Celuj w {target_chars} znaków netto (bez enterów)."

if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length_instruction} Redaguj wywiad Q/A. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów (nadtytuł, tytuł, lid na 'O')."
else:
    manifest = f"TRYB article/news. {strict_length_instruction} Redaktor prasowy. Rdzeń: 2/3 treści. Cytaty w ramce pauzowej. Nagłówki: 5 zestawów. Zakaz słowa 'kapłan'."

# --- GENEROWANIE GŁÓWNE ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner("Piszę tekst..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁ:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd API: {e}")
    else:
        st.error("Brak materiałów źródłowych!")

# --- WYNIKI I KOREKTA ---
if "artykul" in st.session_state:
    tekst = st.session_state.artykul
    netto = count_net_chars(tekst)
    roznica = netto - target_chars
    
    st.divider()
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} względem celu", delta_color="inverse")
    
    with col_m2:
        st.write("### 🛠️ Szybka korekta długości")
        c1, c2, c3 = st.columns(3)
        
        if c1.button("✂️ Skróć o ok. 20%"):
            with st.spinner("Skracam..."):
                new_res = model.generate_content(f"Skróć poniższy tekst o około 20%, zachowując jego strukturę i styl. Celuj w ok. {int(netto*0.8)} znaków netto:\n\n{tekst}")
                st.session_state.artykul = new_res.text
                st.rerun()
                
        if c2.button("➕ Wydłuż o ok. 20%"):
            with st.spinner("Rozszerzam..."):
                new_res = model.generate_content(f"Rozszerz poniższy tekst o około 20% (dodaj detale, opisy lub cytaty ze źródła), zachowując strukturę. Celuj w ok. {int(netto*1.2)} znaków netto:\n\n{tekst}")
                st.session_state.artykul = new_res.text
                st.rerun()

    st.subheader("Gotowy materiał:")
    st.code(tekst, language="markdown", wrap_lines=True)
    
    st.download_button(label="💾 Pobierz .txt", data=tekst, file_name=f"{typ_tekstu.lower()}.txt")