import streamlit as st
import google.generativeai as genai
import io

# 1. KONFIGURACJA API (Z Twoich Secrets)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-3-pro-preview') 
except Exception as e:
    st.error(f"Błąd API: {e}")

# Obsługa bibliotek (DOCX/PDF)
try:
    from docx import Document
    import PyPDF2
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

st.set_page_config(page_title="Dziennikarz Master PRO", page_icon="🖋️", layout="wide")
st.title("🖋️ Dziennikarz Master PRO v11.7")

# --- POMOCNIKI ---
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
    # Liczymy znaki bez enterów (\n) i powrotów karetki (\r)
    return len(text.replace("\n", "").replace("\r", ""))

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    typ_tekstu = st.radio("Rodzaj publikacji:", ["News (Aktualności)", "Reportaż", "Wywiad"], index=0)
    target_chars = st.slider("Docelowa liczba znaków (netto):", 500, 15000, value=3500, step=500)
    st.markdown("---")
    st.caption("v11.7 - Stabilna wersja z Gemini 3")

# --- WEJŚCIE DANYCH ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    uploaded_files = st.file_uploader("Dodaj pliki źródłowe:", accept_multiple_files=True)
with col_in2:
    pasted_text = st.text_area("Wklej materiały tutaj:", height=150)

# Budowanie bazy źródłowej
all_source = pasted_text
if uploaded_files:
    for f in uploaded_files:
        all_source += f"\n\n--- Materiał z: {f.name} ---\n" + read_file(f)

# --- MANIFESTY (PROMPTY) ---
strict_length = f"DOCELOWA DŁUGOŚĆ: Równe {target_chars} znaków netto (nie licz enterów)."

if typ_tekstu == "Wywiad":
    manifest = f"TRYB wywiad. {strict_length} Redaguj Q/A. Zakaz metajęzyka i słowa 'kapłan'. Nagłówki: 5 zestawów (nadtytuł, tytuł, lid na 'O')."
else:
    manifest = f"TRYB article/news. {strict_length} Redaktor prasowy. Rdzeń: 2/3 treści. Cytaty w ramce pauzowej. Zakaz słowa 'kapłan'."

# --- LOGIKA GENEROWANIA ---
if st.button("🚀 Generuj Materiał"):
    if all_source.strip():
        with st.spinner("AI pracuje..."):
            try:
                full_prompt = f"{manifest}\n\nMATERIAŁ:\n{all_source}"
                response = model.generate_content(full_prompt)
                st.session_state.artykul = response.text
            except Exception as e:
                st.error(f"Błąd podczas generowania: {e}")
    else:
        st.error("Brak materiałów źródłowych!")

# --- WYNIKI (Dostępne zawsze, jeśli tekst istnieje) ---
if "artykul" in st.session_state:
    tekst_wynikowy = st.session_state.artykul
    netto = count_net_chars(tekst_wynikowy)
    roznica = netto - target_chars
    
    st.divider()
    
    # 1. Nagłówek i Licznik
    col_res1, col_res2 = st.columns([1, 2])
    with col_res1:
        st.metric("Liczba znaków (netto)", value=netto, delta=f"{roznica} vs cel", delta_color="inverse")
    
    with col_res2:
        # Szybka korekta - przyciski, które nie psują kopiowania
        c1, c2 = st.columns(2)
        if c1.button("✂️ Skróć tekst (20%)"):
            with st.spinner("Skracam..."):
                res = model.generate_content(f"Skróć to do ok. {int(netto*0.8)} znaków netto:\n\n{tekst_wynikowy}")
                st.session_state.artykul = res.text
                st.rerun()
        if c2.button("➕ Wydłuż tekst (20%)"):
            with st.spinner("Wydłużam..."):
                res = model.generate_content(f"Wydłuż to do ok. {int(netto*1.2)} znaków netto, dodając detale:\n\n{tekst_wynikowy}")
                st.session_state.artykul = res.text
                st.rerun()

    # 2. SEKCJA KOPIOWANIA (Zawsze na wierzchu)
    st.subheader("Tekst gotowy do skopiowania:")
    # st.code zapewnia przycisk kopiowania, który jest integralną częścią ramki
    st.code(tekst_wynikowy, language="markdown", wrap_lines=True)
    
    st.info("💡 Przycisk kopiowania znajduje się w prawym górnym rogu powyższej czarnej ramki.")
    
    # 3. Pobieranie
    st.download_button(
        label="💾 Pobierz jako plik .txt", 
        data=tekst_wynikowy, 
        file_name=f"{typ_tekstu.lower()}_master.txt",
        mime="text/plain"
    )