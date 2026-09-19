import os
import io
import time
import streamlit as st
from pypdf import PdfReader
from google import genai

from courses import COURSES
from references import COURSE_REFERENCES


# =========================================================
# KONFIGURASI
# =========================================================

MODEL_NAME = "gemini-3.6-flash"
MAX_PDF_SIZE_MB = 50
MAX_EXTRACTED_TEXT = 90000

st.set_page_config(
    page_title="Tuton AI",
    page_icon="🎓",
    layout="centered",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9fc;
    }

    .hero {
        padding: 28px 24px;
        border-radius: 18px;
        margin-bottom: 22px;
        background: linear-gradient(135deg, #0d6efd, #4f8cff);
        color: white;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }

    .hero h1 {
        margin: 0;
        font-size: 34px;
        font-weight: 700;
    }

    .hero p {
        margin: 8px 0 0 0;
        font-size: 15px;
        opacity: 0.95;
    }

    .info-box {
        padding: 13px 16px;
        border-radius: 12px;
        background: #eef5ff;
        border-left: 4px solid #0d6efd;
        margin: 10px 0 18px 0;
    }

    .small-note {
        font-size: 13px;
        color: #666;
    }

    div[data-testid="stForm"] {
        background: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
        <h1>🎓 Tuton AI</h1>
        <p>Asisten penyusunan jawaban diskusi Tuton mahasiswa</p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="info-box">
        <b>💡 Tips:</b> Upload modul jika tersedia agar jawaban lebih sesuai
        dengan materi mata kuliah. Modul tidak wajib diupload.
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER API KEY
# =========================================================

def get_api_key():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass

    return os.getenv("GOOGLE_API_KEY")


# =========================================================
# GEMINI CLIENT
# =========================================================

def get_client():
    api_key = get_api_key()

    if not api_key:
        st.error(
            "GOOGLE_API_KEY belum ditemukan. "
            "Tambahkan GOOGLE_API_KEY pada Streamlit Secrets."
        )
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Gagal membuat koneksi Gemini: {e}")
        return None


# =========================================================
# REFERENSI MATA KULIAH
# =========================================================

def get_course_references(kode_mk):
    references = COURSE_REFERENCES.get(kode_mk, [])

    if not references:
        return ""

    lines = []

    for i, item in enumerate(references, start=1):
        if isinstance(item, dict):
            ref = item.get("referensi", "")
        else:
            ref = str(item)

        if ref.strip():
            lines.append(f"{i}. {ref.strip()}")

    return "\n".join(lines)


# =========================================================
# INFORMASI COURSE
# =========================================================

def get_course_info(kode_mk):
    course = COURSES.get(kode_mk, {})

    if isinstance(course, dict):
        return {
            "nama": course.get("nama", ""),
            "sks": course.get("sks", ""),
            "prodi": course.get("prodi", ""),
        }

    return {
        "nama": str(course),
        "sks": "",
        "prodi": "",
    }


# =========================================================
# EKSTRAK TEKS PDF
# =========================================================

def extract_pdf_text(uploaded_file):
    """
    Mencoba membaca text layer dari PDF.

    Fungsi ini BUKAN OCR.
    Tujuannya hanya untuk mengetahui apakah PDF mempunyai
    teks yang bisa diekstrak.

    PDF scan/gambar akan tetap diproses langsung oleh Gemini.
    """

    try:
        uploaded_file.seek(0)

        reader = PdfReader(io.BytesIO(uploaded_file.read()))

        pages = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""

            if text.strip():
                pages.append(
                    f"[Halaman {i + 1}]\n{text.strip()}"
                )

        return "\n\n".join(pages)

    except Exception:
        return ""

    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


# =========================================================
# INSPEKSI PDF
# =========================================================

def inspect_uploaded_pdfs(uploaded_files):
    results = []

    for uploaded_file in uploaded_files:
        try:
            size_mb = uploaded_file.size / (1024 * 1024)

            if size_mb > MAX_PDF_SIZE_MB:
                results.append(
                    {
                        "name": uploaded_file.name,
                        "size_mb": size_mb,
                        "status": "terlalu_besar",
                        "text": "",
                    }
                )
                continue

            text = extract_pdf_text(uploaded_file)

            if len(text.strip()) > 100:
                status = "text"
            else:
                status = "scan"

            results.append(
                {
                    "name": uploaded_file.name,
                    "size_mb": size_mb,
                    "status": status,
                    "text": text,
                }
            )

        except Exception as e:
            results.append(
                {
                    "name": uploaded_file.name,
                    "size_mb": 0,
                    "status": "error",
                    "text": "",
                    "error": str(e),
                }
            )

    return results


# =========================================================
# UPLOAD PDF KE GEMINI
# =========================================================

def upload_pdfs_to_gemini(client, uploaded_files):
    """
    Upload PDF ke Gemini Files API.

    Ini memungkinkan Gemini membaca:
    - PDF biasa
    - PDF dengan text layer
    - PDF hasil scan/gambar
    """

    gemini_files = []

    for uploaded_file in uploaded_files:

        if uploaded_file.size > MAX_PDF_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f"File '{uploaded_file.name}' lebih dari "
                f"{MAX_PDF_SIZE_MB} MB."
            )

        try:
            uploaded_file.seek(0)

            gemini_file = client.files.upload(
                file=uploaded_file,
                config={
                    "mime_type": "application/pdf"
                }
            )

            # Beberapa file dapat membutuhkan waktu untuk diproses.
            # Kita cek statusnya jika tersedia.
            gemini_file = wait_for_file_active(
                client,
                gemini_file
            )

            gemini_files.append(gemini_file)

        except Exception as e:
            raise RuntimeError(
                f"Gagal mengupload '{uploaded_file.name}': {e}"
            )

    return gemini_files


# =========================================================
# MENUNGGU FILE AKTIF
# =========================================================

def wait_for_file_active(client, gemini_file, timeout=120):
    """
    Menunggu file Gemini sampai siap digunakan.
    """

    start_time = time.time()

    while True:

        state = getattr(gemini_file, "state", None)

        if not state:
            return gemini_file

        state_name = getattr(state, "name", str(state))

        if state_name == "ACTIVE":
            return gemini_file

        if state_name not in ("PROCESSING", "STATE_UNSPECIFIED"):
            raise RuntimeError(
                f"Status file '{getattr(gemini_file, 'name', '')}': "
                f"{state_name}"
            )

        if time.time() - start_time > timeout:
            raise TimeoutError(
                "PDF terlalu lama diproses oleh Gemini."
            )

        time.sleep(2)

        gemini_file = client.files.get(
            name=gemini_file.name
        )


# =========================================================
# FORMAT INFO MODUL
# =========================================================

def build_module_info(inspections):
    if not inspections:
        return "Tidak ada modul PDF yang diupload."

    lines = []

    for item in inspections:

        if item["status"] == "text":
            lines.append(
                f"- {item['name']}: PDF memiliki text layer."
            )

        elif item["status"] == "scan":
            lines.append(
                f"- {item['name']}: kemungkinan PDF scan/gambar. "
                f"Gunakan kemampuan pembacaan dokumen visual Gemini."
            )

        elif item["status"] == "terlalu_besar":
            lines.append(
                f"- {item['name']}: dilewati karena melebihi batas ukuran."
            )

        else:
            lines.append(
                f"- {item['name']}: tidak dapat diperiksa secara lokal."
            )

    return "\n".join(lines)


# =========================================================
# STYLE INSTRUCTIONS
# =========================================================

def get_style_instruction(style):
    if style == "Natural seperti mahasiswa":
        return """
Tulis seperti mahasiswa S1 yang sudah membaca materi lalu
menjelaskan kembali dengan bahasa sendiri.

Gunakan bahasa Indonesia yang natural dan wajar untuk forum Tuton.

Hindari:
- bahasa jurnal yang terlalu kaku;
- kalimat yang terlalu sempurna;
- paragraf yang semuanya memiliki pola sama;
- terlalu banyak istilah akademik;
- pembukaan yang terlalu formal;
- pengulangan kesimpulan;
- penggunaan kata transisi yang sama berulang-ulang.

Variasikan panjang kalimat secara wajar.
Gunakan "menurut saya", "bagi saya", atau "dari pemahaman saya"
jika memang sesuai konteks, tetapi jangan dipaksakan.

Jawaban harus tetap akademis dan sopan.
"""

    if style == "Akademik":
        return """
Gunakan bahasa akademik yang jelas, sistematis, dan sopan,
tetapi tetap cocok untuk jawaban diskusi mahasiswa S1.
Hindari bahasa jurnal yang terlalu berat.
"""

    return """
Gunakan bahasa yang sederhana, langsung, dan padat.
Fokus pada inti pertanyaan tanpa mengurangi ketepatan konsep.
"""


# =========================================================
# LENGTH INSTRUCTION
# =========================================================

def get_length_instruction(length):
    if length == "Pendek":
        return """
Panjang jawaban sekitar 180–250 kata.
Prioritaskan inti pembahasan dan jangan memperpanjang penjelasan.
"""

    if length == "Panjang":
        return """
Panjang jawaban sekitar 450–650 kata.
Berikan pembahasan yang cukup mendalam dengan contoh jika relevan.
"""

    return """
Panjang jawaban sekitar 280–400 kata.
"""


# =========================================================
# PROMPT UTAMA V2
# =========================================================

def build_prompt(
    nama,
    prodi,
    upbjj,
    kode_mk,
    mata_kuliah,
    sks,
    pertanyaan,
    style,
    length,
    module_info,
    module_text,
    static_references,
):
    style_instruction = get_style_instruction(style)
    length_instruction = get_length_instruction(length)

    if module_text:
        module_text = module_text[:MAX_EXTRACTED_TEXT]

        extracted_context = f"""
Berikut sebagian teks yang berhasil diekstrak dari PDF:

--- MULAI TEKS PDF ---
{module_text}
--- AKHIR TEKS PDF ---
"""
    else:
        extracted_context = """
Tidak ada text layer yang berhasil diekstrak dari PDF.
Jika PDF terlampir berupa scan/gambar, baca langsung isi halaman
PDF melalui input dokumen yang diberikan.
"""

    if static_references:
        reference_context = f"""
Daftar referensi mata kuliah yang tersedia:

{static_references}
"""
    else:
        reference_context = """
Belum ada referensi statis yang tersedia untuk mata kuliah ini.
Jangan membuat referensi fiktif.
"""

    return f"""
Kamu adalah asisten akademik untuk membantu mahasiswa Universitas Terbuka
menyusun draft jawaban diskusi Tuton.

DATA MAHASISWA
Nama: {nama}
Program Studi: {prodi}
UPBJJ: {upbjj}

DATA MATA KULIAH
Kode: {kode_mk}
Mata Kuliah: {mata_kuliah}
SKS: {sks}

PERTANYAAN DISKUSI
{pertanyaan}

INFORMASI MODUL
{module_info}

{extracted_context}

{reference_context}

==================================================
TUGAS UTAMA
==================================================

Susun jawaban diskusi yang benar-benar menjawab pertanyaan.

Prioritas sumber:
1. Modul PDF yang diberikan.
2. Referensi mata kuliah yang tersedia.
3. Pengetahuan umum yang relevan apabila materi tidak cukup.

Jika PDF diberikan:
- baca isi PDF dengan teliti;
- cari bagian yang paling relevan dengan pertanyaan;
- jika PDF merupakan scan/gambar, baca isi halaman secara visual;
- jangan mengatakan bahwa PDF tidak bisa dibaca hanya karena text layer
  tidak tersedia;
- jangan mencampurkan materi dari mata kuliah lain.

Jika pertanyaan meminta pendapat:
- berikan analisis berdasarkan materi;
- gunakan sudut pandang mahasiswa secara wajar;
- jangan mengarang pengalaman pribadi mahasiswa.

Jika pertanyaan meminta contoh:
- gunakan contoh yang sederhana dan relevan;
- jangan membuat data statistik atau fakta khusus yang tidak memiliki dasar.

==================================================
NATURAL STUDENT WRITING ENGINE
==================================================

Tujuan utama adalah menghasilkan jawaban yang natural, spesifik terhadap
pertanyaan, dan sesuai konteks mahasiswa.

{style_instruction}

{length_instruction}

Jangan menulis dengan pola artikel AI yang terlalu umum.

Hindari secara berlebihan frasa seperti:
- "Dalam era digital yang semakin berkembang..."
- "Tidak dapat dipungkiri bahwa..."
- "Pada akhirnya..."
- "Dengan demikian..."
- "Oleh karena itu..."
- "Hal ini menunjukkan bahwa..."
- "Selain itu..." berulang kali.

Bukan berarti kata-kata tersebut dilarang, tetapi jangan digunakan
secara otomatis atau berulang.

Jangan membuat:
- judul yang tidak diperlukan;
- daftar poin jika soal lebih cocok dijawab dalam paragraf;
- kesimpulan yang hanya mengulang isi jawaban;
- pembukaan seperti artikel ilmiah;
- kalimat yang terdengar seperti definisi buku jika dapat dijelaskan
  dengan bahasa mahasiswa.

Tulisan harus terasa seperti mahasiswa yang memahami materi lalu
menjelaskannya kembali dengan bahasanya sendiri.

Jangan sengaja membuat kesalahan ejaan atau tata bahasa.
Natural bukan berarti dibuat buruk.

==================================================
AKURASI AKADEMIK
==================================================

- Jangan mengarang fakta.
- Jangan mengarang nomor modul.
- Jangan mengarang halaman.
- Jangan mengarang nama penulis.
- Jangan mengarang judul buku atau jurnal.
- Jangan membuat DOI palsu.
- Jangan mengklaim suatu informasi berasal dari modul jika tidak ada
  dasar yang jelas.
- Jika lokasi halaman tidak dapat dipastikan, jangan membuat nomor halaman.
- Jika referensi tidak tersedia atau tidak dapat dipastikan, jangan
  mengada-adakannya.

==================================================
STRUKTUR OUTPUT
==================================================

Tampilkan hanya:

JAWABAN TUTON

[isi jawaban]

REFERENSI

1. [referensi yang benar-benar digunakan]

Gunakan referensi yang memang tersedia atau dapat dipastikan.
Tidak perlu memasukkan banyak referensi hanya agar terlihat akademis.

Jangan menambahkan komentar tentang proses AI.
Jangan menjelaskan bahwa kamu sedang mengikuti prompt.
"""


# =========================================================
# PARSE JAWABAN
# =========================================================

def split_answer_and_references(text):
    if not text:
        return "", ""

    cleaned = text.strip()

    # Bersihkan beberapa kemungkinan heading
    cleaned = cleaned.replace("**JAWABAN TUTON**", "JAWABAN TUTON")
    cleaned = cleaned.replace("**REFERENSI**", "REFERENSI")

    if "REFERENSI" in cleaned:
        answer_part, references_part = cleaned.split(
            "REFERENSI",
            1
        )

        answer_part = answer_part.replace(
            "JAWABAN TUTON",
            "",
            1
        ).strip()

        references_part = references_part.strip()

        return answer_part, references_part

    cleaned = cleaned.replace(
        "JAWABAN TUTON",
        "",
        1
    ).strip()

    return cleaned, ""


# =========================================================
# PROMPT PENYEMPURNAAN NATURAL
# =========================================================

def build_natural_prompt(answer):
    return f"""
Teks berikut adalah draft jawaban diskusi mahasiswa:

--- DRAFT ---
{answer}
--- AKHIR DRAFT ---

Tugas kamu adalah membuat versi yang lebih natural dan nyaman dibaca
seperti tulisan mahasiswa S1.

Pertahankan:
- makna;
- fakta;
- konsep;
- contoh;
- pendapat;
- panjang yang kurang lebih sama.

Jangan menambahkan fakta baru.

Perbaiki jika ada:
- kalimat terlalu kaku;
- pola kalimat terlalu seragam;
- transisi terlalu banyak;
- pengulangan;
- bahasa yang terlalu seperti artikel ilmiah.

Jangan sengaja membuat kesalahan tata bahasa atau ejaan.
Jangan membuat tulisan menjadi terlalu santai.

Hasil harus tetap sopan dan cocok diposting pada forum Tuton.

Tampilkan hanya versi hasil perbaikannya.
"""


# =========================================================
# GENERATE JAWABAN
# =========================================================

def generate_answer(
    client,
    prompt,
    gemini_files=None,
):
    contents = [prompt]

    if gemini_files:
        # File diletakkan setelah prompt agar konteks instruksi tetap jelas.
        for gemini_file in gemini_files:
            contents.append(gemini_file)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
    )

    if not response or not getattr(response, "text", None):
        raise RuntimeError(
            "Gemini tidak mengembalikan jawaban."
        )

    return response.text.strip()


# =========================================================
# FORM INPUT
# =========================================================

with st.form("tuton_form"):

    st.subheader("📝 Data Mahasiswa")

    col1, col2 = st.columns(2)

    with col1:
        nama = st.text_input(
            "Nama lengkap",
            placeholder="Contoh: Ashad Bayu Saputra"
        )

    with col2:
        prodi = st.text_input(
            "Program Studi",
            value="S1 Sistem Informasi"
        )

    upbjj = st.text_input(
        "UPBJJ",
        placeholder="Contoh: Palangkaraya"
    )

    st.subheader("📚 Mata Kuliah")

    course_options = list(COURSES.keys())

    if not course_options:
        st.error("COURSES belum berisi data mata kuliah.")
        st.stop()

    kode_mk = st.selectbox(
        "Kode Mata Kuliah",
        options=course_options
    )

    selected_course = get_course_info(kode_mk)

    mata_kuliah = selected_course["nama"]
    sks = selected_course["sks"]

    st.info(
        f"**Mata Kuliah:** {mata_kuliah}  \n"
        f"**SKS:** {sks}"
    )

    pertanyaan = st.text_area(
        "Soal diskusi",
        height=180,
        placeholder="Tempelkan soal diskusi Tuton di sini..."
    )

    st.subheader("📄 Modul")

    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        accept_multiple_files=True,
        help=(
            "Opsional. Bisa berupa PDF biasa maupun PDF hasil scan. "
            "Maksimal 50 MB per file."
        ),
    )

    if modul:
        st.caption(
            f"{len(modul)} file PDF dipilih."
        )

    st.subheader("✍️ Gaya Jawaban")

    style = st.selectbox(
        "Gaya penulisan",
        [
            "Natural seperti mahasiswa",
            "Akademik",
            "Ringkas dan padat",
        ],
        index=0,
    )

    length = st.selectbox(
        "Panjang jawaban",
        [
            "Pendek",
            "Sedang",
            "Panjang",
        ],
        index=1,
    )

    submitted = st.form_submit_button(
        "🚀 Buat Jawaban Tuton",
        use_container_width=True,
    )


# =========================================================
# PROSES GENERATE
# =========================================================

if submitted:

    if not nama.strip():
        st.warning("Silakan isi nama lengkap.")
        st.stop()

    if not pertanyaan.strip():
        st.warning("Silakan masukkan soal diskusi.")
        st.stop()

    client = get_client()

    if not client:
        st.stop()

    try:

        # -------------------------------------------------
        # INSPEKSI PDF
        # -------------------------------------------------

        inspections = []

        if modul:
            with st.spinner("🔎 Memeriksa modul PDF..."):
                inspections = inspect_uploaded_pdfs(modul)

            invalid_files = [
                x["name"]
                for x in inspections
                if x["status"] == "terlalu_besar"
            ]

            if invalid_files:
                st.error(
                    "File berikut melebihi batas 50 MB:\n\n"
                    + "\n".join(
                        f"- {name}"
                        for name in invalid_files
                    )
                )
                st.stop()

            with st.expander(
                "📄 Status modul yang diupload",
                expanded=False
            ):
                for item in inspections:

                    if item["status"] == "text":
                        st.success(
                            f"✅ {item['name']} — text layer terdeteksi"
                        )

                    elif item["status"] == "scan":
                        st.info(
                            f"🖼️ {item['name']} — kemungkinan PDF scan, "
                            f"akan dibaca langsung oleh Gemini"
                        )

                    else:
                        st.warning(
                            f"⚠️ {item['name']}"
                        )

        # -------------------------------------------------
        # UPLOAD KE GEMINI
        # -------------------------------------------------

        gemini_files = []

        if modul:

            with st.spinner(
                "📤 Mengirim modul ke Gemini..."
            ):
                gemini_files = upload_pdfs_to_gemini(
                    client,
                    modul
                )

        # -------------------------------------------------
        # GABUNG TEKS PDF YANG BISA DIEKSTRAK
        # -------------------------------------------------

        all_module_text = []

        for item in inspections:
            if item.get("text"):
                all_module_text.append(
                    f"===== {item['name']} =====\n"
                    f"{item['text']}"
                )

        module_text = "\n\n".join(
            all_module_text
        )

        module_info = build_module_info(
            inspections
        )

        static_references = get_course_references(
            kode_mk
        )

        # -------------------------------------------------
        # BUILD PROMPT
        # -------------------------------------------------

        prompt = build_prompt(
            nama=nama.strip(),
            prodi=prodi.strip(),
            upbjj=upbjj.strip(),
            kode_mk=kode_mk,
            mata_kuliah=mata_kuliah,
            sks=sks,
            pertanyaan=pertanyaan.strip(),
            style=style,
            length=length,
            module_info=module_info,
            module_text=module_text,
            static_references=static_references,
        )

        # -------------------------------------------------
        # GENERATE
        # -------------------------------------------------

        with st.spinner(
            "🧠 Menganalisis soal dan menyusun jawaban..."
        ):
            raw_answer = generate_answer(
                client,
                prompt,
                gemini_files
            )

        answer, references = split_answer_and_references(
            raw_answer
        )

        if not answer:
            answer = raw_answer

        # Simpan hasil
        st.session_state["answer"] = answer
        st.session_state["references"] = references
        st.session_state["kode_mk"] = kode_mk
        st.session_state["mata_kuliah"] = mata_kuliah

        # Reset hasil natural lama
        st.session_state["natural_answer"] = ""

        st.success(
            "✅ Jawaban berhasil dibuat."
        )

    except Exception as e:

        st.error(
            "❌ Terjadi kesalahan saat membuat jawaban."
        )

        st.code(
            str(e),
            language="text"
        )


# =========================================================
# HASIL JAWABAN
# =========================================================

if st.session_state.get("answer"):

    st.divider()

    st.subheader("💬 Jawaban Tuton")

    st.text_area(
        "Hasil jawaban",
        value=st.session_state["answer"],
        height=430,
        key="answer_display",
    )

    # -----------------------------------------------------
    # REFERENSI
    # -----------------------------------------------------

    references = st.session_state.get(
        "references",
        ""
    )

    if references:

        with st.expander(
            "📚 Referensi",
            expanded=True
        ):
            st.text(references)

    # -----------------------------------------------------
    # NATURAL VERSION
    # -----------------------------------------------------

    st.divider()

    st.subheader("✨ Penyempurnaan Gaya")

    st.caption(
        "Jawaban pertama sudah dibuat dengan gaya natural. "
        "Gunakan tombol ini hanya jika ingin bahasa sedikit lebih santai."
    )

    if st.button(
        "🔄 Buat Lebih Santai",
        use_container_width=True
    ):

        client = get_client()

        if client:

            try:

                with st.spinner(
                    "✍️ Menyesuaikan gaya tulisan..."
                ):

                    natural_prompt = build_natural_prompt(
                        st.session_state["answer"]
                    )

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=natural_prompt,
                    )

                    natural_answer = (
                        response.text.strip()
                        if response and response.text
                        else ""
                    )

                    if natural_answer:
                        st.session_state[
                            "natural_answer"
                        ] = natural_answer

            except Exception as e:

                st.error(
                    f"Gagal membuat versi lebih santai: {e}"
                )

    if st.session_state.get("natural_answer"):

        st.text_area(
            "Versi lebih santai",
            value=st.session_state["natural_answer"],
            height=430,
            key="natural_answer_display",
        )

        st.caption(
            "Silakan baca dan sesuaikan kembali dengan pemahaman "
            "serta gaya tulisan Anda sebelum diposting."
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🎓 Tuton AI — Gunakan sebagai alat bantu belajar dan penyusunan draft. "
    "Periksa kembali isi, fakta, dan referensi sebelum digunakan."
)
