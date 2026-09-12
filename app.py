import os
import io
import streamlit as st
from pypdf import PdfReader
from google import genai
from courses import COURSES


# =========================================================
# KONFIGURASI
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
# EKSTRAK PDF
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
    mata_kuliah,
    sks_mk,
    pertanyaan,
    gaya,
    panjang,
    module_text,
):

    if module_text:
        sumber = """
MODUL TERSEDIA.

Gunakan isi modul yang diberikan sebagai sumber utama.
Gunakan pengetahuan umum hanya untuk membantu menjelaskan
materi yang masih kurang.

Jangan mengarang nomor halaman.
Jangan membuat kutipan atau referensi yang tidak terdapat
dalam materi.
"""
    else:
        sumber = """
MODUL TIDAK TERSEDIA.

Gunakan konteks mata kuliah yang diberikan dan pengetahuan
akademik yang relevan.

Jangan mengklaim bahwa jawaban berasal dari modul UT tertentu.
Jangan membuat nomor halaman, kutipan, atau referensi palsu.
"""

    # -----------------------------------------------------
    # ATURAN KHUSUS GAYA NATURAL
    # -----------------------------------------------------

    if gaya == "Natural seperti mahasiswa":
        gaya_instruksi = """
GAYA NATURAL SEPERTI MAHASISWA:

Tulis seperti mahasiswa S1 yang benar-benar memahami materi
dan sedang menjawab forum diskusi Tuton.

Gunakan bahasa Indonesia yang:
- natural
- sopan
- akademis tetapi tidak kaku
- tidak terlalu sempurna atau terlalu formal
- mengalir seperti tulisan manusia
- menggunakan kalimat dengan panjang yang bervariasi

Hindari:
- bahasa seperti artikel jurnal
- terlalu banyak subjudul
- terlalu banyak poin bernomor
- istilah bahasa Inggris yang tidak diperlukan
- kalimat pembuka yang klise
- kalimat seperti "Dalam era globalisasi yang semakin berkembang..."
- kalimat yang terdengar seperti template AI
- pengulangan kesimpulan yang sama dengan isi sebelumnya

Tidak perlu memaksakan struktur bernomor jika jawaban lebih
natural jika ditulis dalam beberapa paragraf.

Jawaban tetap harus menunjukkan pemahaman terhadap materi.
"""

    elif gaya == "Akademik":
        gaya_instruksi = """
GAYA AKADEMIK:

Gunakan bahasa akademik yang jelas, sistematis, objektif,
dan sesuai dengan tingkat mahasiswa perguruan tinggi.

Gunakan istilah ilmiah hanya jika memang relevan.
"""

    else:
        gaya_instruksi = """
GAYA RINGKAS DAN PADAT:

Jawab langsung pada inti persoalan.
Hindari pembukaan panjang dan penjelasan yang tidak diperlukan.
Tetap berikan alasan atau contoh jika diperlukan.
"""

    # -----------------------------------------------------
    # INSTRUKSI PANJANG
    # -----------------------------------------------------

    if panjang == "Pendek":
        panjang_instruksi = """
Buat jawaban relatif singkat, sekitar 3–5 paragraf.
"""
    elif panjang == "Panjang":
        panjang_instruksi = """
Buat jawaban cukup lengkap dan mendalam.
Jelaskan alasan, konsep, dan contoh jika relevan.
"""
    else:
        panjang_instruksi = """
Buat jawaban dengan panjang sedang.
Cukup lengkap untuk menjawab pertanyaan tetapi tidak bertele-tele.
"""

    return f"""
Anda adalah asisten akademik untuk membantu mahasiswa
Universitas Terbuka menyusun jawaban diskusi Tuton.

==================================================
KONTEKS MAHASISWA
==================================================

Nama:
{nama or "-"}

Program studi:
{prodi or "S1 Sistem Informasi"}

UPBJJ:
{upbjj or "-"}

Kode mata kuliah:
{kode_mk or "-"}

Nama mata kuliah:
{mata_kuliah or "-"}

SKS:
{sks_mk or "-"}


==================================================
PERTANYAAN TUTON
==================================================

{pertanyaan}


==================================================
ATURAN PALING PENTING
==================================================

1. Jawaban HARUS berfokus pada mata kuliah yang dipilih.

2. Jangan mencampurkan materi dari mata kuliah lain hanya
   karena konsep tersebut terlihat berkaitan.

3. Contoh:
   Jika mata kuliah yang dipilih adalah Pendidikan Kewarganegaraan,
   fokus utama harus Pendidikan Kewarganegaraan.

4. Jangan tiba-tiba memasukkan konsep Pendidikan Agama Islam,
   Manajemen, Sistem Informasi, atau mata kuliah lain kecuali
   pertanyaan memang secara eksplisit meminta hubungan dengan
   bidang tersebut.

5. Jangan menganggap semua pertanyaan membutuhkan perspektif
   agama, teknologi, manajemen, atau bidang lain.

6. Jika pertanyaan dapat dijawab sepenuhnya menggunakan konsep
   mata kuliah yang dipilih, JANGAN membawa konsep dari bidang lain.

7. Jika ada informasi yang tidak diketahui, jangan mengarang.

8. Jangan membuat nama penulis, judul modul, nomor modul,
   nomor halaman, kutipan, teori, atau referensi palsu.

9. Jika modul PDF tersedia, prioritaskan isi modul tersebut.

10. Jika modul tidak tersedia, jawab berdasarkan pengetahuan
    akademik yang relevan dengan mata kuliah.


==================================================
GAYA PENULISAN
==================================================

{gaya_instruksi}

{panjang_instruksi}


==================================================
FORMAT JAWABAN
==================================================

Untuk jawaban Natural seperti mahasiswa, gunakan struktur
yang terasa seperti tanggapan forum diskusi.

Tidak wajib menggunakan banyak subjudul atau daftar bernomor.

Namun jawaban harus tetap:
- menjawab pertanyaan secara langsung
- memiliki argumentasi
- memberikan contoh jika diperlukan
- memiliki penutup atau kesimpulan yang wajar

Jangan menambahkan kalimat:
"Demikian jawaban saya, semoga bermanfaat"
atau kalimat template sejenis kecuali benar-benar diperlukan.

Jangan mengawali jawaban dengan:
"Perkenalkan saya..."
karena identitas mahasiswa sudah tersedia di sistem.


==================================================
SUMBER
==================================================

{sumber}


==================================================
ISI MODUL
==================================================

{module_text[:90000] if module_text else "(tidak ada modul)"}
"""

# =========================================================
# PROMPT PARAFRASE / BUAT LEBIH NATURAL
# =========================================================

def build_paraphrase_prompt(jawaban, kode_mk, mata_kuliah):
    return f"""
Anda adalah editor jawaban Tuton mahasiswa Universitas Terbuka.

MATA KULIAH:
Kode: {kode_mk}
Nama: {mata_kuliah}

TUGAS:
Parafrase jawaban berikut agar terasa lebih natural, wajar,
dan seperti tulisan mahasiswa S1 yang benar-benar memahami
materi dan menuliskannya sendiri.

ATURAN WAJIB:

1. Pertahankan seluruh makna, fakta, argumen, dan contoh penting
   dari jawaban asli.

2. Jangan menambahkan teori, fakta, contoh, atau informasi baru.

3. Jangan menghilangkan poin penting dari jawaban asli.

4. Jangan mengubah maksud atau kesimpulan utama.

5. Tetap fokus hanya pada mata kuliah yang dipilih.

6. Gunakan bahasa Indonesia yang natural, sopan, dan mudah dibaca.

7. Gaya tulisan seperti mahasiswa yang sedang menjawab forum Tuton,
   bukan seperti jurnal ilmiah atau artikel formal.

8. Kurangi kalimat yang terlalu sempurna, terlalu kaku, atau terlalu
   panjang jika sebenarnya bisa ditulis dengan lebih sederhana.

9. Jangan menggunakan terlalu banyak subjudul atau penomoran jika
   tidak diperlukan.

10. Gunakan istilah bahasa Indonesia jika tersedia dan lebih wajar
    daripada istilah bahasa Inggris.

11. Hindari pembukaan template seperti:
    "Halo Bapak/Ibu Tutor..."
    "Izin menyampaikan..."
    "Pada kesempatan ini..."
    "Sebagai mahasiswa..."

12. Hindari penutup template seperti:
    "Demikian jawaban saya, semoga bermanfaat."

13. Buat perpindahan antarparagraf terasa alami.

14. Variasikan panjang kalimat agar tidak terasa seperti pola tulisan
    yang dibuat secara otomatis.

15. Jangan sengaja membuat kesalahan ejaan atau tata bahasa.

16. Jangan menjelaskan proses parafrase.

17. Keluarkan HANYA jawaban yang sudah diparafrasekan.

JAWABAN ASLI:
----------------------------------------

{jawaban}

----------------------------------------
HASIL PARAFRASE:
"""
# =========================================================
# FORM
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

    # -----------------------------------------------------
    # DETAIL MATA KULIAH
    # -----------------------------------------------------

    if kode_mk:

        mata_kuliah = COURSES[kode_mk]["nama"]
        sks_mk = COURSES[kode_mk]["sks"]

        st.caption(
            f"📚 {kode_mk} — {mata_kuliah} • {sks_mk} SKS"
        )

    else:

        mata_kuliah = ""
        sks_mk = ""

    # -----------------------------------------------------
    # PERTANYAAN
    # -----------------------------------------------------

    st.subheader("📝 Pertanyaan / Topik Diskusi")

    pertanyaan = st.text_area(
        "Masukkan pertanyaan Tuton",
        height=180,
        placeholder=(
            "Contoh: Jelaskan bagaimana penerapan konsep "
            "tersebut dalam kehidupan sehari-hari..."
        ),
    )

    # -----------------------------------------------------
    # MODUL
    # -----------------------------------------------------

    st.subheader("📚 Modul (opsional)")

    modul = st.file_uploader(
        "Upload modul PDF jika tersedia",
        type=["pdf"],
        help=(
            "Tidak wajib. Tanpa modul, aplikasi tetap berjalan "
            "menggunakan konteks mata kuliah."
        ),
    )

    # -----------------------------------------------------
    # GAYA
    # -----------------------------------------------------

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
# PROSES AI
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

    # -----------------------------------------------------
    # API KEY
    # -----------------------------------------------------

    api_key = st.secrets.get(
        "GOOGLE_API_KEY",
        os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:

        st.warning(
            "API AI belum dikonfigurasi."
        )

        st.info(
            "Tambahkan GOOGLE_API_KEY pada Secrets Streamlit."
        )

        st.stop()

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    module_text = ""

    if modul:

        try:

            module_text = extract_pdf(modul)

        except Exception as e:

            st.error(
                f"Modul PDF tidak dapat dibaca: {e}"
            )

            st.stop()

    # -----------------------------------------------------
    # GENERATE
    # -----------------------------------------------------

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

            # -------------------------------------------------
            # HASIL
            # -------------------------------------------------

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
