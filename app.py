import os
import io
import streamlit as st
from pypdf import PdfReader
from google import genai
from courses import COURSES
from references import COURSE_REFERENCES


# =========================================================
# KONFIGURASI HALAMAN
# =========================================================

st.set_page_config(
    page_title="Tuton AI",
    page_icon="🎓",
    layout="centered",
)


# =========================================================
# TAMPILAN UTAMA (CSS & HERO)
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
# FUNGSI BANTUAN (HELPER FUNCTIONS)
# =========================================================

def extract_pdf(uploaded):
    """Ekstrak teks dari file PDF per halaman."""
    reader = PdfReader(io.BytesIO(uploaded.getvalue()))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Halaman {i + 1}]\n{text}")
    return "\n\n".join(pages)


def get_course_references(kode_mk):
    """Mengambil referensi statis bawaan berdasarkan kode mata kuliah."""
    references = COURSE_REFERENCES.get(kode_mk, [])
    if not references:
        return ""
    lines = [f"{i}. {item['referensi']}" for i, item in enumerate(references, start=1)]
    return "\n".join(lines)


def split_answer_and_references(text):
    """Memisahkan bagian JAWABAN TUTON dan REFERENSI."""
    marker = "REFERENSI"
    if marker in text:
        parts = text.split(marker, 1)
        answer_part = parts[0].replace("JAWABAN TUTON", "", 1).strip()
        references_part = parts[1].strip()
        return answer_part, references_part
    return text.strip(), ""


# =========================================================
# PROMPT BUILDERS
# =========================================================

def build_prompt(
    nama, prodi, upbjj, kode_mk, mata_kuliah, sks_mk,
    pertanyaan, gaya, panjang, module_text
):
    """Menyusun prompt utama untuk pembuat jawaban Tuton."""
    if module_text:
        sumber = """
MODUL TERSEDIA.
Gunakan modul PDF yang diberikan sebagai sumber utama jawaban.
Pahami isi modul terlebih dahulu sebelum menyusun jawaban.
Jika terdapat konsep/istilah relevan di modul, prioritaskan materi tersebut.
Modul yang diberikan pengguna juga harus menjadi sumber utama dalam bagian REFERENSI.
"""
    else:
        sumber = """
MODUL TIDAK TERSEDIA.
Jawaban tetap harus dibuat berdasarkan konteks mata kuliah yang dipilih dan pengetahuan akademik yang relevan.
Gunakan sumber akademik yang relevan untuk membantu menyusun jawaban dan referensi.
Jangan mengklaim jawaban berasal dari modul tertentu jika modul tidak tersedia.
"""

    if gaya == "Natural seperti mahasiswa":
        gaya_instruksi = """
GAYA UTAMA: PENDAPAT PRIBADI MAHASISWA
Tulis seperti mahasiswa S1 yang menyampaikan pemahamannya sendiri dalam forum Tuton.
Gunakan sudut pandang pribadi secara alami (misal: "Menurut pemahaman saya...", "Bagi saya...").
Bahasanya harus natural, sopan, cukup akademis tapi tidak kaku, serta tidak bertele-tele.
"""
    elif gaya == "Akademik":
        gaya_instruksi = """
GAYA: AKADEMIK
Gunakan bahasa akademik yang jelas, sistematis, objektif, dan sesuai tingkat mahasiswa perguruan tinggi.
"""
    else:
        gaya_instruksi = """
GAYA: RINGKAS DAN PADAT
Jawab langsung pada inti pertanyaan dengan bahasa sederhana namun tetap akademis.
"""

    if panjang == "Pendek":
        panjang_instruksi = "Target jawaban sekitar 3–5 paragraf. Utamakan inti jawaban."
    elif panjang == "Panjang":
        panjang_instruksi = "Buat jawaban cukup lengkap dan mendalam. Jelaskan konsep, alasan, dan contoh jika diperlukan."
    else:
        panjang_instruksi = "Buat jawaban dengan panjang sedang dan cukup lengkap."

    return f"""
Anda adalah asisten akademik yang membantu mahasiswa Universitas Terbuka menyusun jawaban untuk forum Tutorial Online (Tuton).

DATA MAHASISWA:
- Nama: {nama or "-"}
- Program Studi: {prodi or "S1 Sistem Informasi"}
- UPBJJ: {upbjj or "-"}
- Mata Kuliah: {kode_mk} - {mata_kuliah} ({sks_mk} SKS)

PERTANYAAN TUTON:
{pertanyaan}

FOKUS MATA KULIAH:
Jawaban WAJIB berfokus pada {kode_mk} - {mata_kuliah}.

SUMBER MATERI:
{sumber}

ISI MODUL:
{module_text[:90000] if module_text else "(tidak ada modul)"}

PETUNJUK PENULISAN:
{gaya_instruksi}
{panjang_instruksi}

FORMAT OUTPUT:
Keluarkan dalam PLAIN TEXT tanpa tanda Markdown (*, **, #).
Gunakan format persis berikut:

JAWABAN TUTON

[isi jawaban]

REFERENSI

1. [Daftar referensi yang valid]
"""


def build_paraphrase_prompt(jawaban, kode_mk, mata_kuliah):
    """Menyusun prompt untuk pembuat versi natural (parafrase)."""
    return f"""
Anda adalah editor bahasa untuk jawaban forum Tuton mahasiswa Universitas Terbuka.
MATA KULIAH: {kode_mk} - {mata_kuliah}

TUGAS:
Edit dan parafrase jawaban berikut agar terasa lebih natural dan luwes seperti tulisan mahasiswa.
Jangan mengubah makna utama, fakta, argumen, maupun contoh yang sudah ada.

FORMAT OUTPUT:
Keluarkan hanya hasil editan jawaban (PLAIN TEXT tanpa Markdown).

JAWABAN ASLI:
{jawaban}
"""


# =========================================================
# FORM INPUT MAHASISWA
# =========================================================

with st.form("student_form"):
    st.subheader("👤 Data Mahasiswa")
    c1, c2 = st.columns(2)

    with c1:
        nama = st.text_input("Nama lengkap")
        prodi = st.text_input("Program studi", value="S1 Sistem Informasi")

    with c2:
        upbjj = st.text_input("UPBJJ")
        course_options = [""] + list(COURSES.keys())
        kode_mk = st.selectbox(
            "Mata kuliah",
            course_options,
            format_func=lambda kode: (
                "Pilih mata kuliah..."
                if kode == ""
                else f"{kode} — {COURSES[kode]['nama']} ({COURSES[kode]['sks']} SKS)"
            ),
        )

    if kode_mk:
        mata_kuliah = COURSES[kode_mk]["nama"]
        sks_mk = COURSES[kode_mk]["sks"]
        st.caption(f"📚 {kode_mk} — {mata_kuliah} • {sks_mk} SKS")
    else:
        mata_kuliah = ""
        sks_mk = ""

    st.subheader("📝 Pertanyaan / Topik Diskusi")
    pertanyaan = st.text_area(
        "Masukkan pertanyaan Tuton",
        height=160,
        placeholder="Contoh: Jelaskan bagaimana penerapan konsep tersebut dalam kehidupan sehari-hari...",
    )

    st.subheader("📚 Modul (Opsional)")
    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        help="Opsional. Jika kosong, AI akan menjawab berdasarkan pengetahuan mata kuliah.",
    )

    st.subheader("⚙️ Pengaturan Jawaban")
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


# =========================================================
# PROSES PEMBUATAN JAWABAN (AI GENERATION)
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

    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
    if not api_key:
        st.warning("API Key belum dikonfigurasi pada Streamlit Secrets / Environment Variable.")
        st.stop()

    module_text = ""
    if modul:
        try:
            module_text = extract_pdf(modul)
        except Exception as e:
            st.error(f"Modul PDF tidak dapat dibaca: {e}")
            st.stop()

    with st.spinner("🧠 Menganalisis pertanyaan dan menyusun jawaban..."):
        try:
            client = genai.Client(api_key=api_key)
            prompt = build_prompt(
                nama, prodi, upbjj, kode_mk, mata_kuliah, sks_mk,
                pertanyaan, gaya, panjang, module_text
            )

            # Menggunakan API genai resmi (Gemini 2.5)
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

            st.session_state["answer"] = response.text
            st.session_state["kode_mk"] = kode_mk
            st.session_state["mata_kuliah"] = mata_kuliah
            st.session_state["natural_answer"] = ""

            st.success("✅ Jawaban berhasil dibuat.")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses: {e}")


# =========================================================
# MENAMPILKAN HASIL & PARAFRASE
# =========================================================

if st.session_state.get("answer"):
    st.markdown("---")
    st.markdown("### 📄 Hasil Jawaban")

    st.text_area(
        "Silakan salin atau edit sebelum dikumpulkan",
        st.session_state["answer"],
        height=450,
    )

    st.markdown("### ✨ Buat Jawaban Lebih Natural")
    st.caption("Ubah gaya bahasa agar lebih luwes tanpa mengubah isi materi.")

    if st.button("✨ Buat Lebih Natural", use_container_width=True):
        api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
        if not api_key:
            st.error("GOOGLE_API_KEY belum dikonfigurasi.")
            st.stop()

        original_answer = st.session_state["answer"]
        jawaban_utama, referensi = split_answer_and_references(original_answer)

        with st.spinner("✍️ Sedang membuat versi yang lebih natural..."):
            try:
                client = genai.Client(api_key=api_key)
                para_prompt = build_paraphrase_prompt(
                    jawaban_utama,
                    st.session_state["kode_mk"],
                    st.session_state["mata_kuliah"],
                )

                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=para_prompt,
                )

                natural_body = response.text.strip()
                if referensi:
                    natural_answer = f"JAWABAN TUTON\n\n{natural_body}\n\nREFERENSI\n\n{referensi}"
                else:
                    natural_answer = f"JAWABAN TUTON\n\n{natural_body}"

                st.session_state["natural_answer"] = natural_answer

            except Exception as e:
                st.error(f"Gagal membuat versi natural: {e}")

    if st.session_state.get("natural_answer"):
        st.markdown("### 📝 Versi Lebih Natural")
        st.text_area(
            "Hasil parafrase — silakan edit jika diperlukan",
            st.session_state["natural_answer"],
            height=450,
        )
