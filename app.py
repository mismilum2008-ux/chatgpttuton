import os
import io
import time
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
# TAMPILAN UTAMA
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

.file-info {
    padding: 10px 14px;
    border-radius: 10px;
    background: #f4f7fb;
    margin-top: 8px;
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
# HELPER: EXTRACT TEXT LOKAL
# =========================================================

def extract_pdf_text(uploaded_file):
    """
    Mencoba mengambil text layer dari PDF.

    Ini hanya sebagai pemeriksaan/fallback.
    Untuk PDF scan, Gemini tetap akan membaca PDF asli.
    """

    try:
        reader = PdfReader(
            io.BytesIO(uploaded_file.getvalue())
        )

        pages = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""

            if text.strip():
                pages.append(
                    f"[Halaman {i + 1}]\n{text}"
                )

        return "\n\n".join(pages)

    except Exception:
        return ""


# =========================================================
# MEMERIKSA PDF
# =========================================================

def inspect_uploaded_pdfs(uploaded_files):
    """
    Memeriksa apakah PDF memiliki text layer.

    Hasilnya hanya digunakan sebagai informasi tambahan.
    PDF asli tetap dikirim ke Gemini.
    """

    results = []

    for uploaded in uploaded_files:

        text = extract_pdf_text(uploaded)

        if text.strip():
            status = "text layer terdeteksi"
        else:
            status = "kemungkinan PDF scan/gambar"

        results.append({
            "name": uploaded.name,
            "status": status,
            "text": text,
        })

    return results


# =========================================================
# REFERENSI STATIS
# =========================================================

def get_course_references(kode_mk):
    """
    Mengambil referensi statis berdasarkan kode mata kuliah.
    """

    references = COURSE_REFERENCES.get(
        kode_mk,
        []
    )

    if not references:
        return ""

    lines = [
        f"{i}. {item['referensi']}"
        for i, item in enumerate(
            references,
            start=1
        )
    ]

    return "\n".join(lines)


# =========================================================
# MEMISAHKAN JAWABAN DAN REFERENSI
# =========================================================

def split_answer_and_references(text):
    """
    Memisahkan bagian jawaban dan referensi.
    """

    marker = "REFERENSI"

    if marker in text:

        parts = text.split(
            marker,
            1
        )

        answer_part = (
            parts[0]
            .replace(
                "JAWABAN TUTON",
                "",
                1
            )
            .strip()
        )

        references_part = (
            parts[1]
            .strip()
        )

        return (
            answer_part,
            references_part
        )

    return (
        text.strip(),
        ""
    )


# =========================================================
# PROMPT UTAMA
# =========================================================

def build_prompt(
    nama,
    prodi,
    upbjj,
    kode_mk,
    mata_kuliah,
    sks_mk,
    pertanyaan,
    gaya,
    panjang,
    module_info
):

    static_refs = get_course_references(
        kode_mk
    )

    # -----------------------------------------------------
    # INFORMASI MODUL
    # -----------------------------------------------------

    if module_info:

        daftar_modul = "\n".join(
            [
                f"- {item['name']} "
                f"({item['status']})"
                for item in module_info
            ]
        )

        sumber = f"""
MODUL PDF TERSEDIA.

PDF diberikan langsung kepada model melalui Gemini Files API.

Gemini harus membaca dokumen PDF secara langsung.

Daftar file:

{daftar_modul}

PENTING:

1. PDF dapat berupa PDF teks biasa maupun PDF hasil scan/gambar.

2. Jika PDF berupa scan/gambar, baca isi halaman melalui kemampuan
   pemahaman dokumen/visual. Jangan menganggap dokumen kosong hanya
   karena tidak memiliki text layer.

3. Identifikasi terlebih dahulu materi yang paling relevan dengan
   pertanyaan Tuton.

4. Jangan menganggap semua modul harus digunakan.

5. Jika pertanyaan hanya berkaitan dengan satu modul, prioritaskan
   modul tersebut.

6. Jika beberapa modul relevan, gunakan hanya bagian yang benar-benar
   diperlukan.

7. Jangan mencampurkan materi dari modul yang tidak relevan.

8. Gunakan isi PDF sebagai sumber utama.

9. Jika dapat menentukan nomor Modul, Unit, atau Kegiatan Belajar,
   gunakan informasi tersebut.

10. Jika dapat menentukan halaman yang relevan dari PDF, gunakan
    informasi halaman tersebut dalam referensi atau penjelasan.

11. Jangan mengarang nomor halaman, nomor modul, KB, penulis,
    tahun, penerbit, atau informasi bibliografi lain yang tidak
    dapat dipastikan dari dokumen.

12. Jika informasi bibliografi tidak terlihat atau tidak dapat
    dipastikan, jangan mengarangnya.

13. Jangan memaksakan penggunaan seluruh file PDF.
"""

    else:

        daftar_modul = "(Tidak ada PDF yang diunggah)"

        sumber = """
MODUL PDF TIDAK TERSEDIA.

Jawaban tetap harus dibuat berdasarkan konteks mata kuliah
yang dipilih dan pengetahuan akademik yang relevan.

Gunakan referensi akademik yang benar-benar relevan.

Jangan mengklaim menggunakan modul tertentu jika modul
tidak tersedia.
"""


    # -----------------------------------------------------
    # GAYA
    # -----------------------------------------------------

    if gaya == "Natural seperti mahasiswa":

        gaya_instruksi = """
GAYA UTAMA: NATURAL SEPERTI MAHASISWA

Tulis seperti mahasiswa S1 yang memahami materi lalu
menjelaskannya dengan bahasa sendiri.

Gunakan bahasa:

- natural
- sopan
- sederhana
- cukup akademis
- tidak kaku
- tidak bertele-tele

Gunakan sudut pandang pribadi secara wajar.

Contoh yang boleh digunakan sesekali:

"Menurut saya..."
"Bagi saya..."
"Menurut pemahaman saya..."
"Kalau saya melihatnya..."

Jangan menggunakan ungkapan tersebut di setiap paragraf.

Jangan membuat tulisan seperti jurnal atau makalah.

Jangan membuat semua paragraf memiliki pola yang sama.

Variasikan panjang kalimat.

Hubungkan materi dengan contoh kehidupan sehari-hari
jika memang relevan.

Jangan sengaja membuat kesalahan tata bahasa atau ejaan.
"""

    elif gaya == "Akademik":

        gaya_instruksi = """
GAYA: AKADEMIK

Gunakan bahasa akademik yang jelas, sistematis,
objektif, dan sesuai tingkat mahasiswa perguruan tinggi.

Tetap hindari kalimat yang terlalu panjang
dan tidak diperlukan.
"""

    else:

        gaya_instruksi = """
GAYA: RINGKAS DAN PADAT

Jawab langsung pada inti pertanyaan.

Gunakan bahasa sederhana tetapi tetap akademis.

Hindari pembahasan yang tidak diperlukan.
"""


    # -----------------------------------------------------
    # PANJANG
    # -----------------------------------------------------

    if panjang == "Pendek":

        panjang_instruksi = """
Target sekitar 3–5 paragraf.
Utamakan inti jawaban.
"""

    elif panjang == "Panjang":

        panjang_instruksi = """
Buat jawaban cukup lengkap dan mendalam.

Jelaskan konsep, alasan, hubungan antaride,
dan contoh jika diperlukan.

Jangan menambahkan pembahasan hanya untuk
membuat jawaban lebih panjang.
"""

    else:

        panjang_instruksi = """
Buat jawaban dengan panjang sedang dan cukup lengkap.
"""


    # =====================================================
    # PROMPT
    # =====================================================

    return f"""
Anda adalah asisten akademik yang membantu mahasiswa
Universitas Terbuka menyusun jawaban forum Tutorial Online
(Tuton).

============================================================
DATA MAHASISWA
============================================================

Nama:
{nama or "-"}

Program Studi:
{prodi or "-"}

UPBJJ:
{upbjj or "-"}

Mata Kuliah:
{kode_mk} - {mata_kuliah}

SKS:
{sks_mk}


============================================================
PERTANYAAN TUTON
============================================================

{pertanyaan}


============================================================
FOKUS MATA KULIAH
============================================================

Jawaban WAJIB berfokus pada:

{kode_mk} - {mata_kuliah}

Jangan mencampurkan konsep dari mata kuliah lain
jika tidak relevan.


============================================================
SUMBER MODUL
============================================================

{sumber}


============================================================
FILE MODUL
============================================================

{daftar_modul}


============================================================
DATABASE REFERENSI BAKU
============================================================

{static_refs if static_refs else "(Tidak ada referensi statis baku)"}


============================================================
ATURAN PENYUSUNAN
============================================================

{gaya_instruksi}

{panjang_instruksi}

Jawab pertanyaan secara langsung.

Jika pertanyaan meminta penjelasan, jelaskan.

Jika pertanyaan meminta alasan, berikan alasan.

Jika meminta contoh, berikan contoh.

Jika meminta pendapat, berikan pendapat berdasarkan
pemahaman terhadap materi.

Jangan menambahkan pembahasan yang tidak diperlukan.


============================================================
PEMILIHAN MATERI
============================================================

Jika terdapat beberapa PDF:

1. Cari terlebih dahulu materi yang berhubungan langsung
   dengan pertanyaan.

2. Tentukan modul yang paling relevan.

3. Jangan menggunakan semua modul hanya karena tersedia.

4. Jika hanya satu modul relevan, prioritaskan modul itu.

5. Jika beberapa modul relevan, gunakan hanya bagian yang
   mendukung jawaban.

6. Jangan mencampurkan teori yang tidak berkaitan.

7. Jika isi PDF scan, baca teks yang terlihat pada halaman
   menggunakan kemampuan pemahaman dokumen.

8. Jangan menyatakan PDF tidak dapat dibaca hanya karena
   tidak memiliki text layer.


============================================================
GAYA FORUM TUTON
============================================================

Jawaban harus terasa seperti mahasiswa yang sedang
menyampaikan pendapat dalam forum akademik.

Hindari pembukaan template seperti:

"Halo Bapak/Ibu Tutor..."

"Izin menyampaikan pendapat..."

"Pada kesempatan ini saya akan membahas..."

"Sebagai mahasiswa..."

"Di era globalisasi yang semakin berkembang..."

Langsung masuk ke pembahasan.

Hindari penutup template seperti:

"Demikian jawaban saya, semoga bermanfaat."

"Semoga jawaban ini dapat memberikan manfaat."

Jangan membuat jawaban terdengar seperti artikel
yang dibuat secara otomatis.


============================================================
REFERENSI
============================================================

Setelah jawaban, buat bagian REFERENSI.

Prioritaskan:

1. Modul Universitas Terbuka yang benar-benar digunakan.
2. Buku akademik yang relevan.
3. Jurnal ilmiah yang relevan.
4. Sumber resmi pemerintah/lembaga jika relevan.

Jika modul PDF tersedia, gunakan modul yang benar-benar
dipakai sebagai sumber utama.

Jangan mengarang:

- penulis
- judul
- tahun
- penerbit
- volume
- nomor
- halaman
- DOI
- URL
- kutipan

Lebih baik 1–3 referensi yang benar daripada banyak
referensi yang tidak pasti.

Jangan menggunakan "Google Scholar" sebagai nama sumber.


============================================================
FORMAT OUTPUT
============================================================

Keluarkan PLAIN TEXT.

Jangan gunakan Markdown.

Jangan gunakan tanda **.

Jangan gunakan tanda #.

Jangan gunakan tabel Markdown.

Gunakan format:

JAWABAN TUTON

[isi jawaban]

REFERENSI

1. ...
2. ...
3. ...


============================================================
KETENTUAN PENTING
============================================================

Jangan mengarang isi modul.

Jangan mengarang fakta.

Jangan mengarang referensi.

Jangan mengarang halaman.

Jangan mengarang nomor Modul atau KB.

Jika informasi tidak dapat dipastikan, jangan membuatnya
seolah-olah benar.

Jangan menyebut bahwa Anda adalah AI.

Jangan menjelaskan proses internal.

Hasil akhir harus langsung berupa jawaban Tuton.
"""


# =========================================================
# PROMPT PARAFRASE
# =========================================================

def build_paraphrase_prompt(
    jawaban,
    kode_mk,
    mata_kuliah
):

    return f"""
Anda adalah editor bahasa untuk jawaban forum Tuton
mahasiswa Universitas Terbuka.

MATA KULIAH:
{kode_mk} - {mata_kuliah}


TUGAS:

Edit jawaban berikut agar lebih natural dan luwes
seperti tulisan mahasiswa yang memahami materi
dan menjelaskannya dengan bahasa sendiri.

Jangan mengubah makna.


ATURAN:

1. Pertahankan fakta.

2. Pertahankan argumen.

3. Pertahankan contoh.

4. Pertahankan kesimpulan.

5. Jangan menambahkan teori baru.

6. Jangan menambahkan fakta baru.

7. Jangan menambahkan referensi baru.

8. Jangan mengubah isi akademik.

9. Jangan membuat tulisan seperti jurnal.

10. Jangan membuat tulisan terlalu formal.

11. Jangan sengaja membuat kesalahan tata bahasa.

12. Variasikan struktur kalimat.

13. Buat kalimat yang terasa wajar untuk mahasiswa.


HINDARI:

"Halo Bapak/Ibu Tutor..."

"Izin menyampaikan pendapat..."

"Pada kesempatan ini..."

"Sebagai mahasiswa..."

"Di era globalisasi..."

"Demikian jawaban saya, semoga bermanfaat."


JAWABAN ASLI:

{jawaban}


FORMAT:

Keluarkan hanya hasil editan.

PLAIN TEXT.

Jangan menjelaskan perubahan.

Jangan mengatakan "Berikut hasil parafrase".

Jangan menyebut AI.
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

        course_options = (
            [""]
            + list(COURSES.keys())
        )

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


    # -----------------------------------------------------
    # MATA KULIAH
    # -----------------------------------------------------

    if kode_mk:

        mata_kuliah = (
            COURSES[kode_mk]["nama"]
        )

        sks_mk = (
            COURSES[kode_mk]["sks"]
        )

        st.caption(
            f"📚 {kode_mk} — "
            f"{mata_kuliah} • "
            f"{sks_mk} SKS"
        )

    else:

        mata_kuliah = ""
        sks_mk = ""


    # -----------------------------------------------------
    # PERTANYAAN
    # -----------------------------------------------------

    st.subheader(
        "📝 Pertanyaan / Topik Diskusi"
    )

    pertanyaan = st.text_area(
        "Masukkan pertanyaan Tuton",
        height=160,
        placeholder=(
            "Contoh: Jelaskan bagaimana penerapan "
            "konsep tersebut dalam kehidupan sehari-hari..."
        ),
    )


    # -----------------------------------------------------
    # MODUL
    # -----------------------------------------------------

    st.subheader(
        "📚 Modul (Opsional)"
    )

    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        accept_multiple_files=True,
        help=(
            "Bisa upload beberapa modul sekaligus. "
            "PDF biasa maupun PDF hasil scan dapat digunakan."
        ),
    )


    # -----------------------------------------------------
    # INFORMASI FILE
    # -----------------------------------------------------

    if modul:

        st.caption(
            f"📚 {len(modul)} file modul dipilih"
        )

        for file in modul:

            file_size_mb = (
                file.size / (1024 * 1024)
            )

            st.write(
                f"• {file.name} "
                f"({file_size_mb:.2f} MB)"
            )


    # -----------------------------------------------------
    # PENGATURAN
    # -----------------------------------------------------

    st.subheader(
        "⚙️ Pengaturan Jawaban"
    )

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
# PROSES UTAMA
# =========================================================

if submitted:

    # -----------------------------------------------------
    # VALIDASI
    # -----------------------------------------------------

    if not nama.strip():

        st.error(
            "Nama lengkap belum diisi."
        )

        st.stop()


    if not kode_mk:

        st.error(
            "Mata kuliah belum dipilih."
        )

        st.stop()


    if not pertanyaan.strip():

        st.error(
            "Pertanyaan Tuton belum diisi."
        )

        st.stop()


    # -----------------------------------------------------
    # API KEY
    # -----------------------------------------------------

    api_key = st.secrets.get(
        "GOOGLE_API_KEY",
        os.getenv("GOOGLE_API_KEY")
    )


    if not api_key:

        st.warning(
            "API Key belum dikonfigurasi "
            "pada Streamlit Secrets / Environment Variable."
        )

        st.stop()


    # -----------------------------------------------------
    # CLIENT GEMINI
    # -----------------------------------------------------

    try:

        client = genai.Client(
            api_key=api_key
        )

    except Exception as e:

        st.error(
            f"Gagal membuat koneksi Gemini: {e}"
        )

        st.stop()


    # -----------------------------------------------------
    # PERIKSA PDF
    # -----------------------------------------------------

    module_info = []

    if modul:

        with st.spinner(
            "📚 Memeriksa modul PDF..."
        ):

            try:

                module_info = (
                    inspect_uploaded_pdfs(
                        modul
                    )
                )

            except Exception as e:

                st.error(
                    f"Gagal memeriksa PDF: {e}"
                )

                st.stop()


    # -----------------------------------------------------
    # UPLOAD PDF KE GEMINI FILES API
    # -----------------------------------------------------

    uploaded_gemini_files = []

    if modul:

        with st.spinner(
            "☁️ Mengunggah modul ke Gemini..."
        ):

            try:

                for uploaded in modul:

                    # Pastikan pointer berada di awal
                    uploaded.seek(0)

                    # Gemini SDK menerima file-like object.
                    gemini_file = client.files.upload(
                        file=uploaded,
                        config={
                            "mime_type": "application/pdf",
                            "display_name": uploaded.name,
                        },
                    )

                    uploaded_gemini_files.append(
                        gemini_file
                    )

                st.success(
                    f"✅ {len(uploaded_gemini_files)} "
                    "modul berhasil diunggah ke Gemini."
                )

            except Exception as e:

                st.error(
                    "Gagal mengunggah PDF ke Gemini. "
                    f"Detail: {e}"
                )

                st.stop()


    # =====================================================
    # BUILD PROMPT
    # =====================================================

    prompt = build_prompt(
        nama,
        prodi,
        upbjj,
        kode_mk,
        mata_kuliah,
        sks_mk,
        pertanyaan,
        gaya,
        panjang,
        module_info,
    )


    # =====================================================
    # GENERATE
    # =====================================================

    with st.spinner(
        "🧠 Menganalisis pertanyaan dan menyusun jawaban..."
    ):

        try:

            # -------------------------------------------------
            # TANPA PDF
            # -------------------------------------------------

            if not uploaded_gemini_files:

                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )


            # -------------------------------------------------
            # DENGAN PDF
            # -------------------------------------------------

            else:

                contents = []

                # Prompt utama
                contents.append(
                    prompt
                )

                # Semua PDF
                for gemini_file in uploaded_gemini_files:

                    contents.append(
                        gemini_file
                    )


                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents,
                )


            # -------------------------------------------------
            # HASIL
            # -------------------------------------------------

            if not response.text:

                st.error(
                    "Gemini tidak mengembalikan jawaban."
                )

                st.stop()


            answer = response.text.strip()


            # -------------------------------------------------
            # SESSION STATE
            # -------------------------------------------------

            st.session_state["answer"] = (
                answer
            )

            st.session_state["kode_mk"] = (
                kode_mk
            )

            st.session_state["mata_kuliah"] = (
                mata_kuliah
            )

            st.session_state["natural_answer"] = ""


            st.success(
                "✅ Jawaban berhasil dibuat."
            )


            # -------------------------------------------------
            # INFO PDF
            # -------------------------------------------------

            if modul:

                scan_count = sum(
                    1
                    for item in module_info
                    if "scan" in item["status"]
                )

                text_count = (
                    len(module_info)
                    - scan_count
                )


                if scan_count > 0:

                    st.info(
                        f"📖 {len(modul)} modul diproses. "
                        f"{scan_count} file terdeteksi sebagai "
                        "kemungkinan PDF scan/gambar dan "
                        "dibaca langsung oleh Gemini."
                    )

                else:

                    st.info(
                        f"📖 {len(modul)} modul diproses "
                        "langsung oleh Gemini."
                    )

            else:

                st.warning(
                    "🟡 Modul tidak diunggah. "
                    "Jawaban dibuat berdasarkan konteks "
                    "mata kuliah dan pengetahuan akademik."
                )


        except Exception as e:

            st.error(
                "Terjadi kesalahan saat memproses jawaban."
            )

            st.exception(e)


# =========================================================
# HASIL JAWABAN
# =========================================================

if st.session_state.get(
    "answer"
):

    st.markdown("---")

    st.markdown(
        "### 📄 Hasil Jawaban"
    )


    st.text_area(
        "Silakan salin atau edit sebelum dikumpulkan",
        st.session_state["answer"],
        height=450,
    )


    # =====================================================
    # NATURAL
    # =====================================================

    st.markdown(
        "### ✨ Buat Jawaban Lebih Natural"
    )

    st.caption(
        "Ubah gaya bahasa agar lebih luwes tanpa "
        "mengubah isi materi."
    )


    if st.button(
        "✨ Buat Lebih Natural",
        use_container_width=True
    ):

        api_key = st.secrets.get(
            "GOOGLE_API_KEY",
            os.getenv("GOOGLE_API_KEY")
        )


        if not api_key:

            st.error(
                "GOOGLE_API_KEY belum dikonfigurasi."
            )

            st.stop()


        original_answer = (
            st.session_state["answer"]
        )


        jawaban_utama, referensi = (
            split_answer_and_references(
                original_answer
            )
        )


        with st.spinner(
            "✍️ Sedang membuat versi yang lebih natural..."
        ):

            try:

                client = genai.Client(
                    api_key=api_key
                )


                para_prompt = (
                    build_paraphrase_prompt(
                        jawaban_utama,
                        st.session_state["kode_mk"],
                        st.session_state["mata_kuliah"],
                    )
                )


                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=para_prompt,
                )


                natural_body = (
                    response.text.strip()
                )


                if referensi:

                    natural_answer = (
                        "JAWABAN TUTON\n\n"
                        + natural_body
                        + "\n\nREFERENSI\n\n"
                        + referensi
                    )

                else:

                    natural_answer = (
                        "JAWABAN TUTON\n\n"
                        + natural_body
                    )


                st.session_state[
                    "natural_answer"
                ] = natural_answer


            except Exception as e:

                st.error(
                    f"Gagal membuat versi natural: {e}"
                )


    # =====================================================
    # HASIL NATURAL
    # =====================================================

    if st.session_state.get(
        "natural_answer"
    ):

        st.markdown(
            "### 📝 Versi Lebih Natural"
        )


        st.text_area(
            "Hasil parafrase — silakan edit jika diperlukan",
            st.session_state["natural_answer"],
            height=450,
        )
