import os
import io
import streamlit as st
from pypdf import PdfReader
from google import genai
from courses import COURSES


# =========================================================
# KONFIGURASI HALAMAN
# =========================================================

st.set_page_config(
    page_title="Tuton AI",
    page_icon="🎓",
    layout="centered",
)


# =========================================================
# TAMPILAN
# =========================================================

st.markdown("""
<style>
.block-container {
    max-width: 900px;
    padding-top: 2rem;
}

.hero {
    background: linear-gradient(135deg, #1756c9, #2876e8);
    padding: 28px;
    border-radius: 16px;
    color: white;
    margin-bottom: 18px;
}

.hero h1 {
    margin: 0 0 8px;
    font-size: 30px;
}

.hero p {
    margin: 0;
    opacity: .92;
}

.small {
    font-size: 12px;
    color: #68758a;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <h1>🎓 Tuton AI</h1>
    <p>
        Asisten penyusunan jawaban diskusi mahasiswa —
        dengan atau tanpa modul PDF.
    </p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# FUNGSI EKSTRAK PDF
# =========================================================

def extract_pdf(uploaded):
    reader = PdfReader(io.BytesIO(uploaded.getvalue()))

    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        if text.strip():
            pages.append(
                f"[Halaman {i + 1}]\n{text}"
            )

    return "\n\n".join(pages)


# =========================================================
# PROMPT AI
# =========================================================

def build_prompt(
    nama,
    prodi,
    upbjj,
    kode_mk,
    mk,
    sks_mk,
    pertanyaan,
    gaya,
    panjang,
    module_text,
):
    if module_text:
        source_note = """
MODUL DIUNGGAH.

Gunakan isi modul yang diberikan sebagai sumber utama.
Pengetahuan umum boleh digunakan sebagai pelengkap.

Jangan mengarang nomor halaman.
Jika menyebut halaman, pastikan halaman tersebut memang
terlihat dari teks modul yang diberikan.
"""
    else:
        source_note = """
MODUL TIDAK DIUNGGAH.

Gunakan konteks mata kuliah dan pengetahuan akademik yang relevan.

Jangan mengklaim bahwa jawaban berasal dari modul UT tertentu.
Jangan mengarang nomor halaman, kutipan, nama penulis,
atau isi modul yang tidak diberikan.
"""

    return f"""
Anda adalah asisten akademik untuk membantu mahasiswa
menyusun jawaban diskusi Tuton Universitas Terbuka.

Tujuan utama:
Membantu mahasiswa memahami pertanyaan dan menghasilkan
jawaban yang relevan, logis, akademis, tetapi tetap natural.

==================================================
DATA MAHASISWA
==================================================

Nama:
{nama or "-"}

Program studi:
{prodi or "S1 Sistem Informasi"}

UPBJJ:
{upbjj or "-"}

Kode mata kuliah:
{kode_mk or "-"}

Mata kuliah:
{mk or "-"}

SKS:
{sks_mk or "-"}


==================================================
PERTANYAAN TUTON
==================================================

{pertanyaan}


==================================================
PREFERENSI JAWABAN
==================================================

Gaya:
{gaya}

Panjang:
{panjang}


==================================================
ATURAN PENULISAN
==================================================

1. Jawab dalam Bahasa Indonesia.

2. Sesuaikan isi jawaban dengan mata kuliah yang dipilih.

3. Jangan menjawab terlalu umum jika konteks mata kuliahnya
   memungkinkan jawaban yang lebih spesifik.

4. Gunakan istilah akademik yang sesuai dengan bidang
   mata kuliah, tetapi jangan membuat bahasa terlalu kaku.

5. Buat jawaban terasa seperti ditulis mahasiswa yang
   memahami materi, bukan seperti artikel AI.

6. Hindari kalimat pembuka yang terlalu generik seperti:
   "Dalam era globalisasi..."
   kecuali memang benar-benar relevan dengan pertanyaan.

7. Jangan mengulang pertanyaan secara berlebihan.

8. Jangan membuat fakta, kutipan, nama penulis, judul buku,
   teori, nomor halaman, atau referensi yang tidak diketahui.

9. Jika modul tersedia, prioritaskan modul tersebut.

10. Jika modul tidak tersedia, gunakan pengetahuan akademik
    yang relevan dengan mata kuliah.

11. Jawaban harus menjadi bahan yang masih dapat diedit
    mahasiswa sebelum dikumpulkan.

12. Jangan mengatakan bahwa AI telah menggantikan pekerjaan
    akademik mahasiswa.

13. Sertakan bagian:
    "Inti jawaban"

14. Sertakan bagian:
    "Kesimpulan"

15. Jika pertanyaan membutuhkan contoh, berikan contoh
    yang relevan dan mudah dipahami.

16. Jangan membuat jawaban terlalu panjang jika pertanyaannya
    sebenarnya dapat dijawab secara sederhana.

17. Utamakan ketepatan isi dibanding penggunaan kata-kata
    yang rumit.

{source_note}


==================================================
ISI MODUL
==================================================

{module_text[:90000] if module_text else "(tidak ada modul)"}
"""


# =========================================================
# FORM INPUT
# =========================================================

with st.form("student_form"):

    st.subheader("👤 Data Mahasiswa")

    c1, c2 = st.columns(2)

    with c1:
        nama = st.text_input(
            "Nama lengkap"
        )

        prodi = st.text_input(
            "Program studi",
            value="S1 Sistem Informasi"
        )

    with c2:
        upbjj = st.text_input(
            "UPBJJ"
        )

        # ---------------------------------------------
        # PILIH MATA KULIAH
        # ---------------------------------------------

        course_options = [""] + list(COURSES.keys())

        kode_mk = st.selectbox(
            "Mata kuliah",
            course_options,
            format_func=lambda kode: (
                "Pilih mata kuliah..."
                if kode == ""
                else (
                    f"{kode} — "
                    f"{COURSES[kode]['nama']} "
                    f"({COURSES[kode]['sks']} SKS)"
                )
            ),
        )

    # ---------------------------------------------
    # INFORMASI MATA KULIAH
    # ---------------------------------------------

    if kode_mk:
        mata_kuliah = COURSES[kode_mk]["nama"]
        sks_mk = COURSES[kode_mk]["sks"]

        st.caption(
            f"📚 {kode_mk} — {mata_kuliah} "
            f"• {sks_mk} SKS"
        )

    else:
        mata_kuliah = ""
        sks_mk = ""

    # ---------------------------------------------
    # PERTANYAAN
    # ---------------------------------------------

    st.subheader("📝 Pertanyaan / Topik Diskusi")

    pertanyaan = st.text_area(
        "Masukkan pertanyaan Tuton",
        height=180,
        placeholder=(
            "Contoh: Jelaskan bagaimana "
            "penerapan konsep tersebut dalam kehidupan sehari-hari..."
        ),
    )

    # ---------------------------------------------
    # MODUL
    # ---------------------------------------------

    st.subheader("📚 Modul (opsional)")

    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        help=(
            "Tidak wajib. Tanpa modul, aplikasi tetap "
            "dapat membuat jawaban berdasarkan konteks mata kuliah."
        ),
    )

    # ---------------------------------------------
    # GAYA
    # ---------------------------------------------

    st.subheader("⚙️ Gaya Jawaban")

    gaya = st.selectbox(
        "Pilih gaya",
        [
            "Natural seperti mahasiswa",
            "Akademik",
            "Ringkas dan padat",
        ],
    )

    panjang = st.select_slider(
        "Panjang jawaban",
        options=[
            "Pendek",
            "Sedang",
            "Panjang",
        ],
        value="Sedang",
    )

    submitted = st.form_submit_button(
        "✨ Buat Jawaban Diskusi",
        use_container_width=True,
    )


# =========================================================
# PROSES GENERATE
# =========================================================

if submitted:

    if not nama.strip():
        st.error("Nama lengkap belum diisi.")
        st.stop()

    if not kode_mk:
        st.error("Mata kuliah belum dipilih.")
        st.stop()

    if not pertanyaan.strip():
        st.error("Pertanyaan Tuton belum diisi.")
        st.stop()

    # ---------------------------------------------
    # AMBIL API KEY
    # ---------------------------------------------

    api_key = st.secrets.get(
        "GOOGLE_API_KEY",
        os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        st.warning(
            "Aplikasi sudah siap, tetapi API AI belum "
            "dikonfigurasi."
        )

        st.info(
            "Tambahkan GOOGLE_API_KEY pada Secrets "
            "Streamlit untuk mengaktifkan generator AI."
        )

        st.stop()

    # ---------------------------------------------
    # BACA MODUL
    # ---------------------------------------------

    module_text = ""

    if modul:
        try:
            module_text = extract_pdf(modul)
        except Exception as e:
            st.error(
                f"Modul PDF tidak dapat dibaca: {e}"
            )
            st.stop()

    # ---------------------------------------------
    # GENERATE AI
    # ---------------------------------------------

    with st.spinner(
        "🧠 Menganalisis pertanyaan dan menyusun jawaban..."
    ):

        try:

            client = genai.Client(
                api_key=api_key
            )

            response = client.interactions.create(
                model="gemini-3.6-flash",
                input=build_prompt(
                    nama,
                    prodi,
                    upbjj,
                    kode_mk,
                    mata_kuliah,
                    sks_mk,
                    pertanyaan,
                    gaya,
                    panjang,
                    module_text,
                ),
            )

            answer = response.output_text

            # -----------------------------------------
            # HASIL
            # -----------------------------------------

            st.success(
                "✅ Jawaban berhasil dibuat."
            )

            if modul:
                st.info(
                    "🟢 Modul digunakan sebagai sumber utama."
                )
            else:
                st.warning(
                    "🟡 Modul tidak diunggah. "
                    "Jawaban dibuat berdasarkan konteks "
                    "mata kuliah dan pengetahuan akademik."
                )

            st.markdown(
                "### 📄 Hasil Jawaban"
            )

            st.text_area(
                "Silakan edit sebelum dikumpulkan",
                answer,
                height=520,
            )

        except Exception as e:

            st.error(
                f"Terjadi kesalahan saat memproses: {e}"
            )
