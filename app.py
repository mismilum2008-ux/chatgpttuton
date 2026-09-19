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
# CSS / TAMPILAN
# =========================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f7f9fc;
    }

    .hero {
        padding: 30px 24px;
        border-radius: 20px;
        margin-bottom: 22px;
        background: linear-gradient(135deg, #0d6efd, #4f8cff);
        color: white;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }

    .hero h1 {
        margin: 0;
        font-size: 36px;
        font-weight: 700;
    }

    .hero p {
        margin: 8px 0 0 0;
        font-size: 15px;
        opacity: 0.95;
    }

    .info-box {
        padding: 14px 16px;
        border-radius: 12px;
        background: #eef5ff;
        border-left: 4px solid #0d6efd;
        margin-bottom: 18px;
    }

    .stTextArea textarea {
        line-height: 1.6;
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
        <b>💡 Tips:</b>
        Upload modul jika tersedia agar jawaban lebih sesuai dengan
        materi mata kuliah. Modul bersifat opsional.
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "answer" not in st.session_state:
    st.session_state.answer = ""

if "references" not in st.session_state:
    st.session_state.references = ""

if "natural_answer" not in st.session_state:
    st.session_state.natural_answer = ""


# =========================================================
# API KEY
# =========================================================

def get_api_key():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass

    return os.getenv("GOOGLE_API_KEY")


def get_client():
    api_key = get_api_key()

    if not api_key:
        st.error(
            "GOOGLE_API_KEY belum ditemukan. "
            "Silakan masukkan API key pada Streamlit Secrets."
        )
        return None

    try:
        return genai.Client(api_key=api_key)

    except Exception as e:
        st.error(f"Gagal menghubungkan ke Gemini: {e}")
        return None


# =========================================================
# DATA MATA KULIAH
# =========================================================

def get_course_references(kode_mk):
    """
    Mengambil referensi khusus berdasarkan kode mata kuliah.
    """

    references = COURSE_REFERENCES.get(kode_mk, [])

    if not references:
        return ""

    result = []

    for i, item in enumerate(references, start=1):

        if isinstance(item, dict):
            ref = item.get("referensi", "")
        else:
            ref = str(item)

        if ref.strip():
            result.append(
                f"{i}. {ref.strip()}"
            )

    return "\n".join(result)


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_pdf_text(uploaded_file):
    """
    Mencoba membaca text layer dari PDF.

    Ini bukan OCR.
    Fungsinya untuk mengetahui apakah PDF mempunyai
    teks yang dapat diekstrak.

    Jika PDF berupa scan/gambar, file tetap akan dikirim
    langsung ke Gemini untuk dibaca secara visual.
    """

    try:
        uploaded_file.seek(0)

        pdf_bytes = uploaded_file.read()

        reader = PdfReader(
            io.BytesIO(pdf_bytes)
        )

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

def inspect_pdfs(uploaded_files):

    results = []

    for uploaded_file in uploaded_files:

        size_mb = uploaded_file.size / (
            1024 * 1024
        )

        if size_mb > MAX_PDF_SIZE_MB:

            results.append({
                "name": uploaded_file.name,
                "status": "too_large",
                "text": "",
                "size_mb": size_mb,
            })

            continue

        text = extract_pdf_text(
            uploaded_file
        )

        if len(text.strip()) >= 100:

            status = "text"

        else:

            status = "scan"

        results.append({
            "name": uploaded_file.name,
            "status": status,
            "text": text,
            "size_mb": size_mb,
        })

    return results


# =========================================================
# UPLOAD PDF KE GEMINI
# =========================================================

def wait_for_file_active(
    client,
    gemini_file,
    timeout=120
):
    """
    Menunggu file selesai diproses Gemini.
    """

    start_time = time.time()

    while True:

        state = getattr(
            gemini_file,
            "state",
            None
        )

        if not state:
            return gemini_file

        state_name = getattr(
            state,
            "name",
            str(state)
        )

        if state_name == "ACTIVE":
            return gemini_file

        if state_name not in (
            "PROCESSING",
            "STATE_UNSPECIFIED"
        ):
            raise RuntimeError(
                f"Status file Gemini: {state_name}"
            )

        if (
            time.time() - start_time
            > timeout
        ):
            raise TimeoutError(
                "PDF terlalu lama diproses oleh Gemini."
            )

        time.sleep(2)

        gemini_file = client.files.get(
            name=gemini_file.name
        )


def upload_pdfs_to_gemini(
    client,
    uploaded_files
):

    gemini_files = []

    for uploaded_file in uploaded_files:

        if uploaded_file.size > (
            MAX_PDF_SIZE_MB * 1024 * 1024
        ):
            raise ValueError(
                f"File '{uploaded_file.name}' "
                f"melebihi {MAX_PDF_SIZE_MB} MB."
            )

        uploaded_file.seek(0)

        try:

            gemini_file = client.files.upload(
                file=uploaded_file,
                config={
                    "mime_type": "application/pdf"
                }
            )

            gemini_file = wait_for_file_active(
                client,
                gemini_file
            )

            gemini_files.append(
                gemini_file
            )

        except Exception as e:

            raise RuntimeError(
                f"Gagal memproses "
                f"'{uploaded_file.name}': {e}"
            )

    return gemini_files


# =========================================================
# INFO MODUL
# =========================================================

def build_module_info(inspections):

    if not inspections:

        return (
            "Tidak ada modul PDF yang diupload."
        )

    result = []

    for item in inspections:

        if item["status"] == "text":

            result.append(
                f"- {item['name']}: "
                "text layer berhasil dibaca."
            )

        elif item["status"] == "scan":

            result.append(
                f"- {item['name']}: "
                "kemungkinan PDF scan/gambar. "
                "Baca langsung menggunakan kemampuan "
                "pemahaman dokumen visual."
            )

        elif item["status"] == "too_large":

            result.append(
                f"- {item['name']}: "
                "melebihi batas ukuran dan tidak digunakan."
            )

    return "\n".join(result)


# =========================================================
# GAYA PENULISAN
# =========================================================

def get_style_instruction(style):

    if style == "Natural seperti mahasiswa":

        return """
Tulis seperti mahasiswa S1 yang sudah membaca materi,
memahami pertanyaan, kemudian menjelaskan kembali
dengan bahasanya sendiri.

Gunakan bahasa Indonesia yang natural dan wajar untuk
forum diskusi Tuton.

Jangan membuat tulisan terasa seperti artikel jurnal.

Variasikan panjang kalimat secara alami.

Jangan menggunakan pola pembukaan dan penutup yang
terlalu kaku.

Gunakan "menurut saya", "bagi saya", atau
"dari pemahaman saya" jika memang sesuai konteks,
tetapi jangan dipaksakan.

Hindari penggunaan kata penghubung yang sama berulang-ulang,
seperti:
- selain itu
- oleh karena itu
- dengan demikian
- hal ini menunjukkan
- tidak dapat dipungkiri

Kata-kata tersebut boleh digunakan jika memang diperlukan,
tetapi jangan digunakan secara otomatis.

Natural bukan berarti membuat kesalahan tata bahasa.
Tetap gunakan bahasa yang baik dan sopan.
"""

    elif style == "Akademik":

        return """
Gunakan bahasa akademik yang jelas, sistematis,
dan sopan untuk mahasiswa S1.

Tetap hindari bahasa yang terlalu kaku seperti artikel jurnal.
"""

    else:

        return """
Gunakan bahasa yang sederhana, langsung, dan padat.

Fokus pada inti pertanyaan dan jangan memperpanjang
jawaban dengan penjelasan yang tidak diperlukan.
"""


# =========================================================
# PANJANG JAWABAN
# =========================================================

def get_length_instruction(length):

    if length == "Pendek":

        return """
Target sekitar 180–250 kata.
"""

    elif length == "Panjang":

        return """
Target sekitar 450–650 kata.
"""

    else:

        return """
Target sekitar 280–400 kata.
"""


# =========================================================
# PROMPT UTAMA
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

    style_instruction = get_style_instruction(
        style
    )

    length_instruction = get_length_instruction(
        length
    )

    if module_text:

        module_context = f"""
TEKS MODUL YANG BERHASIL DIEKSTRAK:

--- MULAI MODUL ---
{module_text[:MAX_EXTRACTED_TEXT]}
--- SELESAI MODUL ---
"""

    else:

        module_context = """
Tidak ada teks modul yang berhasil diekstrak.

Jika PDF yang diberikan berupa scan/gambar,
gunakan file PDF yang terlampir sebagai sumber utama
dan baca isi halaman secara visual.
"""

    if static_references:

        reference_context = f"""
REFERENSI MATA KULIAH YANG TERSEDIA:

{static_references}
"""

    else:

        reference_context = """
Tidak tersedia referensi statis untuk mata kuliah ini.
Jangan mengarang referensi.
"""

    prompt = f"""
Kamu adalah asisten akademik untuk membantu mahasiswa
Universitas Terbuka menyusun draft jawaban diskusi Tuton.

==================================================
IDENTITAS MAHASISWA
==================================================

Nama:
{nama}

Program Studi:
{prodi}

UPBJJ:
{upbjj}


==================================================
MATA KULIAH
==================================================

Kode:
{kode_mk}

Nama:
{mata_kuliah}

SKS:
{sks}


==================================================
SOAL DISKUSI
==================================================

{pertanyaan}


==================================================
INFORMASI MODUL
==================================================

{module_info}

{module_context}

{reference_context}


==================================================
CARA MENJAWAB
==================================================

Pertama, pahami terlebih dahulu apa yang sebenarnya
diminta oleh soal.

Jangan menjawab secara umum jika pertanyaan meminta
hal yang spesifik.

Gunakan materi mata kuliah yang sesuai.

Jika modul tersedia, prioritaskan modul tersebut.

Jika terdapat beberapa PDF, cari bagian yang paling
relevan dan jangan mencampurkan materi dari mata kuliah
lain.

Jika PDF merupakan scan atau gambar, baca langsung
halaman PDF tersebut.

Jika soal meminta pendapat, berikan pendapat berdasarkan
pemahaman terhadap materi.

Jangan mengarang pengalaman pribadi mahasiswa.

Jika soal meminta contoh, gunakan contoh yang masuk akal
dan relevan dengan pembahasan.

==================================================
GAYA PENULISAN
==================================================

{style_instruction}

{length_instruction}


==================================================
NATURAL STUDENT WRITING
==================================================

Jawaban harus terasa seperti mahasiswa yang sudah membaca
materi kemudian menjelaskan kembali menggunakan bahasanya
sendiri.

Jangan membuat semua paragraf memiliki struktur yang sama.

Jangan membuat setiap kalimat terlalu panjang.

Jangan terlalu banyak menggunakan istilah akademik jika
bahasa sederhana sudah cukup.

Jangan membuat pembukaan seperti:

"Di era perkembangan teknologi yang semakin pesat..."

kecuali memang relevan dengan soal.

Jangan menggunakan:

"Sebagai mahasiswa, kita harus..."

jika tidak diperlukan.

Jangan mengulang pertanyaan dalam bentuk paragraf.

Jangan membuat kesimpulan yang hanya mengulang semua
isi jawaban.

Jangan membuat tulisan sengaja salah ejaan atau tata bahasa.

==================================================
AKURASI
==================================================

Jangan mengarang:

- fakta
- angka
- statistik
- nama tokoh
- nama buku
- jurnal
- DOI
- nomor modul
- nomor halaman
- kutipan
- referensi

Jika nomor halaman tidak dapat dipastikan dari dokumen,
jangan mencantumkannya.

Jika referensi tidak tersedia atau tidak dapat dipastikan,
jangan membuatnya sendiri.

==================================================
OUTPUT
==================================================

Gunakan format:

JAWABAN TUTON

[Jawaban]

REFERENSI

[Referensi yang benar-benar digunakan]

Tidak perlu menjelaskan proses berpikir.

Tidak perlu menjelaskan bahwa kamu adalah AI.

Tidak perlu menambahkan catatan kepada mahasiswa.

Jawaban harus langsung berupa draft yang dapat dibaca
dan diperiksa oleh mahasiswa sebelum diposting.
"""

    return prompt


# =========================================================
# GENERATE DENGAN GEMINI
# =========================================================

def generate_answer(
    client,
    prompt,
    gemini_files=None
):

    contents = [prompt]

    if gemini_files:

        for gemini_file in gemini_files:

            contents.append(
                gemini_file
            )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
    )

    if not response:

        raise RuntimeError(
            "Gemini tidak memberikan respons."
        )

    answer = getattr(
        response,
        "text",
        None
    )

    if not answer:

        raise RuntimeError(
            "Gemini tidak mengembalikan teks jawaban."
        )

    return answer.strip()


# =========================================================
# PARSE OUTPUT
# =========================================================

def split_answer_and_references(text):

    if not text:
        return "", ""

    text = text.strip()

    text = text.replace(
        "**JAWABAN TUTON**",
        "JAWABAN TUTON"
    )

    text = text.replace(
        "**REFERENSI**",
        "REFERENSI"
    )

    if "REFERENSI" in text:

        parts = text.split(
            "REFERENSI",
            1
        )

        answer = parts[0]

        references = parts[1]

        answer = answer.replace(
            "JAWABAN TUTON",
            "",
            1
        ).strip()

        return (
            answer,
            references.strip()
        )

    answer = text.replace(
        "JAWABAN TUTON",
        "",
        1
    ).strip()

    return answer, ""


# =========================================================
# PROMPT VERSI LEBIH SANTAI
# =========================================================

def build_natural_prompt(answer):

    return f"""
Berikut draft jawaban diskusi mahasiswa:

--- MULAI DRAFT ---

{answer}

--- SELESAI DRAFT ---

Buat versi yang sedikit lebih natural dan santai,
tetapi tetap sopan dan sesuai untuk forum Tuton.

Pertahankan:

- makna
- konsep
- fakta
- contoh
- pendapat
- inti jawaban

Jangan menambahkan fakta baru.

Jangan mengubah kesimpulan menjadi sesuatu yang berbeda.

Perbaiki jika ada kalimat yang:
- terlalu kaku;
- terlalu panjang;
- terlalu berulang;
- terlalu seperti artikel jurnal;
- menggunakan transisi secara berlebihan.

Gunakan bahasa mahasiswa S1 yang wajar.

Jangan sengaja membuat kesalahan ejaan atau tata bahasa.

Tampilkan hanya hasil akhirnya.
"""


# =========================================================
# TAMPILAN MATA KULIAH (DI LUAR FORM AGAR INTERAKTIF)
# =========================================================

st.subheader("📚 Mata Kuliah")

course_options = list(COURSES.keys())

kode_mk = st.selectbox(
    "Kode Mata Kuliah",
    options=course_options,
    format_func=lambda kode: (
        f"{kode} — {COURSES[kode]['nama']}"
    )
)

# Ambil data langsung sesuai pilihan
selected_course = COURSES[kode_mk]
mata_kuliah = selected_course["nama"]
sks = selected_course["sks"]

st.info(
    f"📖 **{mata_kuliah}**  •  **{sks} SKS**"
)


# =========================================================
# FORM UTAMA
# =========================================================

with st.form("tuton_form"):

    st.subheader("👤 Data Mahasiswa")

    nama = st.text_input(
        "Nama lengkap",
        placeholder="Contoh: Ashad Bayu Saputra"
    )

    prodi = st.text_input(
        "Program Studi",
        value="S1 Sistem Informasi"
    )

    upbjj = st.text_input(
        "UPBJJ",
        placeholder="Contoh: Palangkaraya"
    )

    st.subheader("📝 Pertanyaan Diskusi")

    pertanyaan = st.text_area(
        "Masukkan soal diskusi",
        height=190,
        placeholder=(
            "Tempelkan soal diskusi Tuton di sini..."
        )
    )

    st.subheader("📄 Modul Tuton")

    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        accept_multiple_files=True,
        help=(
            "Opsional. Bisa PDF biasa maupun PDF hasil scan. "
            "Maksimal 50 MB per file."
        )
    )

    if modul:
        st.caption(
            f"📎 {len(modul)} file PDF dipilih"
        )

    st.subheader("✍️ Gaya Jawaban")

    style = st.selectbox(
        "Pilih gaya penulisan",
        [
            "Natural seperti mahasiswa",
            "Akademik",
            "Ringkas dan padat",
        ],
        index=0
    )

    length = st.selectbox(
        "Panjang jawaban",
        [
            "Pendek",
            "Sedang",
            "Panjang",
        ],
        index=1
    )

    submitted = st.form_submit_button(
        "🚀 Buat Jawaban Tuton",
        use_container_width=True
    )


# =========================================================
# PROSES
# =========================================================

if submitted:

    if not nama.strip():

        st.warning(
            "Silakan isi nama lengkap."
        )

        st.stop()

    if not pertanyaan.strip():

        st.warning(
            "Silakan masukkan soal diskusi."
        )

        st.stop()

    client = get_client()

    if not client:
        st.stop()

    try:

        # -------------------------------------------------
        # INSPEKSI MODUL
        # -------------------------------------------------

        inspections = []

        if modul:

            with st.spinner(
                "🔎 Memeriksa modul..."
            ):

                inspections = inspect_pdfs(
                    modul
                )

            too_large = [
                item["name"]
                for item in inspections
                if item["status"] == "too_large"
            ]

            if too_large:

                st.error(
                    "File berikut melebihi batas 50 MB:\n\n"
                    + "\n".join(
                        f"- {name}"
                        for name in too_large
                    )
                )

                st.stop()

            with st.expander(
                "📄 Status modul",
                expanded=False
            ):

                for item in inspections:

                    if item["status"] == "text":

                        st.success(
                            f"✅ {item['name']} — "
                            "teks berhasil dibaca"
                        )

                    elif item["status"] == "scan":

                        st.info(
                            f"🖼️ {item['name']} — "
                            "terdeteksi seperti PDF scan. "
                            "Akan dibaca langsung oleh Gemini."
                        )

        # -------------------------------------------------
        # UPLOAD PDF KE GEMINI
        # -------------------------------------------------

        gemini_files = []

        if modul:

            with st.spinner(
                "📤 Mengirim modul ke Gemini..."
            ):

                gemini_files = (
                    upload_pdfs_to_gemini(
                        client,
                        modul
                    )
                )

        # -------------------------------------------------
        # GABUNG TEKS YANG BERHASIL DIEKSTRAK
        # -------------------------------------------------

        extracted_texts = []

        for item in inspections:

            if item.get("text"):

                extracted_texts.append(
                    f"""
===== {item['name']} =====

{item['text']}
"""
                )

        module_text = "\n\n".join(
            extracted_texts
        )

        # -------------------------------------------------
        # INFO MODUL
        # -------------------------------------------------

        module_info = build_module_info(
            inspections
        )

        # -------------------------------------------------
        # REFERENSI
        # -------------------------------------------------

        static_references = (
            get_course_references(
                kode_mk
            )
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
            "🧠 Memahami soal dan menyusun jawaban..."
        ):

            raw_answer = generate_answer(
                client,
                prompt,
                gemini_files
            )

        # -------------------------------------------------
        # PARSE
        # -------------------------------------------------

        answer, references = (
            split_answer_and_references(
                raw_answer
            )
        )

        if not answer:
            answer = raw_answer

        # -------------------------------------------------
        # SIMPAN
        # -------------------------------------------------

        st.session_state.answer = answer

        st.session_state.references = (
            references
        )

        st.session_state.natural_answer = ""

        st.success(
            "✅ Jawaban berhasil dibuat."
        )

    except Exception as e:

        st.error(
            "❌ Terjadi kesalahan saat membuat jawaban."
        )

        with st.expander(
            "Detail error"
        ):

            st.code(
                str(e),
                language="text"
            )


# =========================================================
# TAMPILKAN HASIL
# =========================================================

if st.session_state.answer:

    st.divider()

    st.subheader("💬 Jawaban Tuton")

    st.text_area(
        "Hasil jawaban",

        value=st.session_state.answer,

        height=430,

        key="answer_display"
    )

    # -----------------------------------------------------
    # REFERENSI
    # -----------------------------------------------------

    if st.session_state.references:

        with st.expander(
            "📚 Referensi",
            expanded=True
        ):

            st.text(
                st.session_state.references
            )

    # -----------------------------------------------------
    # VERSI LEBIH SANTAI
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "✨ Mau dibuat sedikit lebih santai?"
    )

    st.caption(
        "Jawaban utama sudah dibuat dengan gaya natural. "
        "Fitur ini hanya pilihan tambahan."
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

                    natural_prompt = (
                        build_natural_prompt(
                            st.session_state.answer
                        )
                    )

                    response = (
                        client.models.generate_content(
                            model=MODEL_NAME,
                            contents=natural_prompt,
                        )
                    )

                    if response and response.text:

                        st.session_state.natural_answer = (
                            response.text.strip()
                        )

            except Exception as e:

                st.error(
                    f"Gagal membuat versi santai: {e}"
                )

    # -----------------------------------------------------
    # HASIL VERSI SANTAI
    # -----------------------------------------------------

    if st.session_state.natural_answer:

        st.text_area(
            "Versi lebih santai",

            value=st.session_state.natural_answer,

            height=430,

            key="natural_answer_display"
        )

        st.caption(
            "Baca dan sesuaikan kembali dengan pemahaman "
            "Anda sebelum digunakan."
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🎓 Tuton AI — Alat bantu penyusunan draft jawaban. "
    "Periksa kembali isi dan referensi sebelum digunakan."
)
