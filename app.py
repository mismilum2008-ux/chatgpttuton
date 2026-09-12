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

# =========================================================
# PROMPT UTAMA - JAWABAN TUTON
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

Gunakan modul PDF yang diberikan sebagai sumber utama.
Pahami isi modul terlebih dahulu sebelum menyusun jawaban.

Jika terdapat konsep yang relevan di dalam modul, prioritaskan
konsep tersebut daripada pengetahuan umum.

Gunakan pengetahuan umum hanya jika diperlukan untuk membantu
menjelaskan pertanyaan.

Jangan mengarang:
- nama penulis
- judul modul
- nomor modul
- nomor halaman
- kutipan
- referensi
"""
    else:
        sumber = """
MODUL TIDAK TERSEDIA.

Jawaban tetap harus dibuat berdasarkan konteks mata kuliah yang
dipilih dan pengetahuan akademik yang relevan.

Jangan mengklaim bahwa jawaban berasal dari modul tertentu.

Jangan mengarang:
- nama penulis
- judul modul
- nomor modul
- nomor halaman
- kutipan
- referensi
"""

    # -----------------------------------------------------
    # GAYA
    # -----------------------------------------------------

    if gaya == "Natural seperti mahasiswa":

        gaya_instruksi = """
GAYA UTAMA: NATURAL SEPERTI MAHASISWA

Tulis seperti mahasiswa S1 yang memahami materi kemudian
menjelaskannya dengan bahasa sendiri dalam forum Tuton.

Bahasanya harus:
- natural
- sopan
- mudah dipahami
- cukup akademis tetapi tidak kaku
- tidak seperti jurnal
- tidak seperti makalah
- tidak seperti artikel berita
- tidak terlalu sempurna
- tidak menggunakan kalimat yang berlebihan

Gunakan kalimat dengan panjang yang bervariasi.

Jangan membuat setiap paragraf memiliki pola yang sama.

Jangan memaksakan istilah akademik jika bahasa sederhana sudah
cukup untuk menjelaskan maksudnya.

Jika menggunakan istilah akademik, pastikan istilah tersebut
memang relevan dengan mata kuliah yang dipilih.

Jawaban sebaiknya terasa seperti mahasiswa sedang menyampaikan
pendapat setelah membaca dan memahami materi, bukan seperti
mesin yang sedang menjelaskan sebuah topik.
"""

    elif gaya == "Akademik":

        gaya_instruksi = """
GAYA: AKADEMIK

Gunakan bahasa akademik yang jelas, sistematis, objektif,
dan sesuai tingkat mahasiswa perguruan tinggi.

Tetap hindari kalimat yang terlalu bertele-tele.

Jangan membuat jawaban seperti jurnal penelitian kecuali
pertanyaan memang membutuhkan gaya tersebut.
"""

    else:

        gaya_instruksi = """
GAYA: RINGKAS DAN PADAT

Jawab langsung pada inti pertanyaan.

Gunakan bahasa yang sederhana tetapi tetap menunjukkan
pemahaman terhadap materi.

Hindari pembukaan dan penjelasan yang tidak diperlukan.
"""

    # -----------------------------------------------------
    # PANJANG
    # -----------------------------------------------------

    if panjang == "Pendek":

        panjang_instruksi = """
Target jawaban sekitar 3–5 paragraf.

Utamakan inti jawaban dan contoh yang paling relevan.
"""

    elif panjang == "Panjang":

        panjang_instruksi = """
Buat jawaban cukup lengkap dan mendalam.

Jelaskan konsep, alasan, hubungan antaride, dan contoh
jika memang diperlukan untuk menjawab pertanyaan.

Jangan menambahkan pembahasan hanya untuk membuat jawaban
terlihat panjang.
"""

    else:

        panjang_instruksi = """
Buat jawaban dengan panjang sedang.

Cukup lengkap untuk menjawab pertanyaan dengan baik,
tetapi jangan bertele-tele.
"""

    return f"""
Anda adalah asisten akademik yang membantu mahasiswa
Universitas Terbuka menyusun jawaban untuk forum Tutorial
Online (Tuton).

============================================================
DATA
============================================================

Nama mahasiswa:
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


============================================================
PERTANYAAN
============================================================

{pertanyaan}


============================================================
FOKUS MATA KULIAH
============================================================

Jawaban WAJIB berfokus pada:

{kode_mk} - {mata_kuliah}

Ini adalah aturan yang sangat penting.

Jangan mencampurkan materi dari mata kuliah lain hanya karena
konsepnya terlihat mirip.

Gunakan konsep yang memang relevan dengan mata kuliah tersebut.

Sebagai contoh, jika mata kuliah yang dipilih adalah Pendidikan
Kewarganegaraan, gunakan konsep yang memang berkaitan dengan
Pendidikan Kewarganegaraan.

Jangan tiba-tiba membawa konsep Pendidikan Agama Islam,
Manajemen, Sistem Informasi, atau bidang lain apabila pertanyaan
dapat dijawab tanpa konsep tersebut.

Jangan menggunakan istilah atau teori hanya supaya jawaban
terlihat lebih akademis.

Jika sebuah konsep dari bidang lain benar-benar diperlukan,
gunakan hanya jika hubungan tersebut memang diminta atau
relevan secara langsung dengan pertanyaan.


============================================================
SUMBER MATERI
============================================================

{sumber}

============================================================
ISI MODUL
============================================================

{module_text[:90000] if module_text else "(tidak ada modul)"}


============================================================
CARA MENJAWAB
============================================================

{gaya_instruksi}

{panjang_instruksi}

Jawab pertanyaan secara langsung.

Jika pertanyaan meminta penjelasan, berikan penjelasan.

Jika meminta alasan, berikan alasan.

Jika meminta bentuk atau jenis, jelaskan bentuk atau jenisnya.

Jika meminta contoh, berikan contoh yang masuk akal dan
berhubungan langsung dengan pembahasan.

Jangan menambahkan pembahasan yang tidak diperlukan.


============================================================
GAYA FORUM TUTON
============================================================

Jawaban harus terasa seperti tulisan mahasiswa yang sedang
menjawab forum diskusi.

Jangan menggunakan pembukaan template seperti:

"Halo Bapak/Ibu Tutor..."

"Izin menyampaikan pendapat..."

"Pada kesempatan ini saya akan membahas..."

"Sebagai mahasiswa..."

"Menurut saya, dalam era globalisasi yang semakin berkembang..."

Langsung masuk ke pembahasan.

Jangan menggunakan penutup template seperti:

"Demikian jawaban saya, semoga bermanfaat."

"Semoga jawaban ini dapat memberikan manfaat."

"Terima kasih."

Gunakan penutup hanya jika memang diperlukan.


============================================================
FORMAT OUTPUT - SANGAT PENTING
============================================================

Keluarkan jawaban dalam PLAIN TEXT.

JANGAN menggunakan Markdown.

JANGAN menggunakan tanda **.

JANGAN menggunakan tanda * untuk format tulisan.

JANGAN menggunakan tanda # sebagai judul.

JANGAN menggunakan heading seperti:
"### Pembahasan"

JANGAN menggunakan bullet point Markdown seperti:
"- ..."
"* ..."

JANGAN menggunakan tabel.

Utamakan paragraf biasa yang mengalir secara natural.

Penomoran 1., 2., 3. hanya boleh digunakan apabila pertanyaan
memang meminta beberapa bentuk, jenis, langkah, atau poin yang
perlu dibedakan.

Jangan membuat subjudul hanya untuk mempercantik tampilan.


============================================================
KETENTUAN PENTING
============================================================

Pertahankan ketepatan akademik.

Jangan mengarang fakta.

Jangan mengarang referensi.

Jangan mengarang kutipan.

Jangan mengarang nomor halaman.

Jangan mengarang isi modul.

Jika informasi tidak diketahui atau tidak terdapat dalam sumber,
gunakan pengetahuan akademik yang relevan tanpa membuat klaim
seolah-olah informasi tersebut berasal dari modul.


============================================================
HASIL AKHIR
============================================================

Keluarkan HANYA jawaban Tuton.

Jangan menjelaskan proses pembuatan jawaban.

Jangan menyebut bahwa Anda adalah AI.

Jangan menyebut instruksi ini.

Jangan memberikan catatan tambahan.

Hasil harus siap dibaca dan diedit oleh mahasiswa sebelum
dikumpulkan.
"""

# =========================================================
# PROMPT PARAFRASE / BUAT LEBIH NATURAL
# =========================================================

def build_paraphrase_prompt(jawaban, kode_mk, mata_kuliah):

    return f"""
Anda adalah editor bahasa untuk jawaban forum Tuton
mahasiswa Universitas Terbuka.

MATA KULIAH:
{kode_mk} - {mata_kuliah}


============================================================
TUGAS
============================================================

Edit dan parafrase jawaban berikut agar terasa lebih natural,
lebih luwes, dan lebih seperti tulisan mahasiswa yang memahami
materi lalu menuliskannya dengan bahasa sendiri.

Tujuannya bukan membuat jawaban menjadi lebih panjang.

Tujuannya adalah membuat bahasa lebih wajar dan enak dibaca
tanpa mengubah isi.


============================================================
ATURAN UTAMA
============================================================

1. Pertahankan makna utama jawaban.

2. Pertahankan fakta yang terdapat dalam jawaban.

3. Pertahankan argumen dan alasan yang digunakan.

4. Pertahankan contoh yang sudah ada.

5. Pertahankan kesimpulan atau inti pembahasan.

6. Jangan menambahkan teori baru.

7. Jangan menambahkan fakta baru.

8. Jangan menambahkan contoh baru.

9. Jangan menghilangkan poin penting.

10. Jangan mengubah jawaban menjadi lebih akademis.

11. Jangan membuat jawaban menjadi seperti jurnal atau makalah.

12. Tetap fokus pada mata kuliah:
{kode_mk} - {mata_kuliah}


============================================================
CARA MEMBUATNYA LEBIH NATURAL
============================================================

Ubah kalimat yang terasa terlalu kaku menjadi kalimat yang
lebih sederhana dan wajar.

Jika sebuah kalimat terlalu panjang, boleh dipecah menjadi
dua kalimat.

Jika beberapa kalimat memiliki pola yang sama, variasikan
susunannya.

Gunakan kata-kata yang umum digunakan mahasiswa ketika
menjelaskan pendapat dalam forum akademik.

Jangan menggunakan bahasa percakapan yang terlalu santai.

Jangan sengaja membuat kesalahan tata bahasa atau ejaan.

Jangan mengganti kata hanya untuk terlihat berbeda apabila
kata sebelumnya sudah natural.

Parafrase harus tetap terasa sebagai tulisan mahasiswa,
bukan tulisan yang sengaja dibuat "berantakan".


============================================================
HINDARI GAYA TEMPLATE
============================================================

Jangan menggunakan:

"Halo Bapak/Ibu Tutor..."

"Izin menyampaikan pendapat..."

"Pada kesempatan ini saya akan membahas..."

"Sebagai mahasiswa..."

"Di era globalisasi yang semakin berkembang..."

"Berdasarkan uraian di atas..."

"Hal ini menunjukkan bahwa..."

"Demikian jawaban saya, semoga bermanfaat."

Gunakan kalimat tersebut hanya jika memang secara alami
diperlukan oleh konteks, bukan sebagai template.


============================================================
FORMAT OUTPUT
============================================================

Hasil akhir HARUS berupa PLAIN TEXT.

JANGAN menggunakan Markdown.

JANGAN menggunakan:

**
*
#
###
- 
* 
tabel Markdown

Jangan menggunakan heading atau subheading kecuali memang
sudah sangat diperlukan oleh struktur jawaban.

Utamakan paragraf biasa.

Jika jawaban asli menggunakan penomoran karena pertanyaan
memang meminta beberapa poin, penomoran boleh dipertahankan
dengan format sederhana:

1. ...
2. ...
3. ...

Jangan membuat penomoran baru jika tidak diperlukan.


============================================================
JANGAN MENGUBAH ISI
============================================================

Jangan melakukan hal berikut:

- menambah teori
- menambah referensi
- menambah kutipan
- menambah fakta
- mengubah contoh
- mengubah kesimpulan
- memasukkan konsep dari mata kuliah lain
- mengubah maksud penulis

Jika jawaban asli sudah benar secara akademik, pertahankan
isi akademiknya.


============================================================
JAWABAN ASLI
============================================================

----------------------------------------

{jawaban}

----------------------------------------


============================================================
HASIL AKHIR
============================================================

Keluarkan hanya versi jawaban yang sudah dibuat lebih natural.

Jangan memberikan penjelasan sebelum atau sesudah jawaban.

Jangan mengatakan "Berikut hasil parafrase".

Jangan menjelaskan perubahan yang dilakukan.

Jangan menyebut AI.

Hasil akhir harus langsung berupa jawaban Tuton.
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

            st.session_state["answer"] = answer
            st.session_state["kode_mk"] = kode_mk
            st.session_state["mata_kuliah"] = mata_kuliah
            st.session_state["natural_answer"] = ""

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
# =========================================================
# PARAFRASE / BUAT LEBIH NATURAL
# =========================================================

if "answer" in st.session_state and st.session_state["answer"]:

    st.markdown("---")
    st.markdown("### ✨ Buat Jawaban Lebih Natural")

    st.caption(
        "Ubah gaya bahasa agar lebih natural seperti tulisan mahasiswa "
        "tanpa mengubah isi dan inti jawaban."
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
            st.error("GOOGLE_API_KEY belum dikonfigurasi.")
            st.stop()

        with st.spinner(
            "✍️ Sedang membuat versi yang lebih natural..."
        ):

            try:

                client = genai.Client(
                    api_key=api_key
                )

                response = client.interactions.create(
                    model="gemini-3.6-flash",
                    input=build_paraphrase_prompt(
                        st.session_state["answer"],
                        st.session_state["kode_mk"],
                        st.session_state["mata_kuliah"],
                    ),
                )

                st.session_state["natural_answer"] = (
                    response.output_text
                )

            except Exception as e:

                st.error(
                    f"Gagal membuat versi natural: {e}"
                )

    # -----------------------------------------------------
    # HASIL PARAFRASE
    # -----------------------------------------------------

    if st.session_state.get("natural_answer"):

        st.markdown("### 📝 Versi Lebih Natural")

        st.text_area(
            "Hasil parafrase — silakan edit jika diperlukan",
            st.session_state["natural_answer"],
            height=520,
        )
