import os
import io
import streamlit as st
from pypdf import PdfReader
from google import genai

st.set_page_config(
    page_title="Tuton AI",
    page_icon="🎓",
    layout="centered",
)

st.markdown("""
<style>
.block-container {max-width: 900px; padding-top: 2rem;}
.hero {background: linear-gradient(135deg,#1756c9,#2876e8); padding: 28px;
       border-radius: 16px; color:white; margin-bottom: 18px;}
.hero h1 {margin:0 0 8px; font-size: 30px;}
.hero p {margin:0; opacity:.92;}
.card {border:1px solid #e4e8ef; border-radius:14px; padding:18px; margin:12px 0;}
.small {font-size: 12px; color:#68758a;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🎓 Tuton AI</h1>
<p>Asisten penyusunan jawaban diskusi mahasiswa — dengan atau tanpa modul PDF.</p>
</div>
""", unsafe_allow_html=True)

with st.form("student_form"):
    st.subheader("👤 Data Mahasiswa")
    c1, c2 = st.columns(2)
    with c1:
        nama = st.text_input("Nama lengkap")
        prodi = st.text_input("Program studi")
    with c2:
        upbjj = st.text_input("UPBJJ")
        mata_kuliah = st.text_input("Mata kuliah")

    st.subheader("📝 Pertanyaan / Topik Diskusi")
    pertanyaan = st.text_area(
        "Masukkan pertanyaan Tuton",
        height=180,
        placeholder="Contoh: Jelaskan bagaimana ...",
    )

    st.subheader("📚 Modul (opsional)")
    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        help="Tidak wajib. Tanpa modul, aplikasi tetap dapat membuat jawaban.",
    )

    st.subheader("⚙️ Gaya Jawaban")
    gaya = st.selectbox(
        "Pilih gaya",
        ["Natural seperti mahasiswa", "Akademik", "Ringkas dan padat"],
    )
    panjang = st.select_slider(
        "Panjang jawaban",
        options=["Pendek", "Sedang", "Panjang"],
        value="Sedang",
    )

    submitted = st.form_submit_button("✨ Buat Jawaban Diskusi", use_container_width=True)

def extract_pdf(uploaded):
    reader = PdfReader(io.BytesIO(uploaded.getvalue()))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Halaman {i+1}]\n{text}")
    return "\n\n".join(pages)

def build_prompt(nama, prodi, mk, pertanyaan, gaya, panjang, module_text):
    source_note = (
        "MODUL DIUNGGAH. Gunakan isi modul sebagai sumber utama. "
        "Jangan mengarang nomor halaman; hanya sebutkan halaman yang benar-benar tersedia."
        if module_text else
        "MODUL TIDAK DIUNGGAH. Tetap jawab berdasarkan pengetahuan yang relevan. "
        "Jangan mengklaim atau mengutip modul UT seolah-olah modul tersedia."
    )
    return f"""
Anda adalah asisten akademik untuk membantu mahasiswa menyusun jawaban diskusi Tuton.
Tujuan utama: membantu mahasiswa menghasilkan jawaban yang memahami pertanyaan, bukan sekadar
menyalin sumber.

Data:
Nama: {nama or '-'}
Program studi: {prodi or '-'}
Mata kuliah: {mk or '-'}

Pertanyaan:
{pertanyaan}

Gaya: {gaya}
Panjang: {panjang}

Aturan:
- Jawab dalam Bahasa Indonesia.
- Berikan struktur yang jelas dan natural.
- Hindari kalimat yang terasa seperti template AI.
- Jangan membuat fakta, kutipan, nama penulis, judul buku, atau nomor halaman yang tidak diketahui.
- Jika modul tersedia, prioritaskan modul dan gunakan pengetahuan umum hanya sebagai pelengkap.
- Jika modul tidak tersedia, katakan secara jujur bahwa jawaban tidak berbasis modul yang diunggah.
- Jawaban harus merupakan bahan yang masih dapat diedit mahasiswa, bukan klaim bahwa AI menggantikan pekerjaan akademik mahasiswa.
- Sertakan bagian "Inti jawaban" dan "Kesimpulan".
- Bila sumber modul tersedia dan relevan, sebutkan halaman hanya jika halaman tersebut jelas dari teks.

{source_note}

Isi modul:
{module_text[:90000] if module_text else "(tidak ada modul)"}
"""

if submitted:
    if not pertanyaan.strip():
        st.error("Pertanyaan Tuton belum diisi.")
        st.stop()

    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

    if not api_key:
        st.warning(
            "Aplikasi sudah siap, tetapi API AI belum dikonfigurasi. "
            "Tambahkan GOOGLE_API_KEY pada Secrets Streamlit untuk mengaktifkan generator AI."
        )
        st.info("Setelah API key dipasang, tombol ini akan menghasilkan jawaban otomatis.")
        st.stop()

    with st.spinner("Menganalisis pertanyaan dan menyusun jawaban..."):
        try:
            module_text = extract_pdf(modul) if modul else ""

            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=build_prompt(
                    nama, prodi, mata_kuliah, pertanyaan, gaya, panjang, module_text
                ),
            )

            answer = response.text

            st.success("Jawaban berhasil dibuat.")

            if modul:
                st.info("🟢 Modul digunakan sebagai sumber utama.")
            else:
                st.warning("🟡 Modul tidak diunggah. Jawaban dibuat tanpa sumber modul.")

            st.markdown("### 📄 Hasil Jawaban")
            st.text_area(
                "Silakan edit sebelum dikumpulkan",
                answer,
                height=520,
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses: {e}")
