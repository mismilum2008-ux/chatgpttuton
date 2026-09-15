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
# FUNGSI EKSTRAK PDF
# =========================================================

def extract_pdfs(uploaded_files):
    """
    Mengekstrak teks dari beberapa file PDF.

    Setiap file diberi penanda nama file agar AI dapat
    membedakan sumber materi antar-modul.
    """

    all_text = []

    for uploaded in uploaded_files:

        reader = PdfReader(
            io.BytesIO(uploaded.getvalue())
        )

        pages = []

        for i, page in enumerate(reader.pages):

            text = page.extract_text() or ""

            if text.strip():
                pages.append(
                    f"[Halaman {i + 1}]\n{text}"
                )

        if pages:
            all_text.append(
                "\n"
                + "=" * 70
                + f"\nFILE MODUL: {uploaded.name}\n"
                + "=" * 70
                + "\n"
                + "\n\n".join(pages)
            )

    return "\n\n".join(all_text)


# =========================================================
# REFERENSI STATIS
# =========================================================

def get_course_references(kode_mk):
    """
    Mengambil referensi statis bawaan berdasarkan
    kode mata kuliah.
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
    Memisahkan bagian JAWABAN TUTON dan REFERENSI.
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
    module_text
):

    # -----------------------------------------------------
    # SUMBER MATERI
    # -----------------------------------------------------

    static_refs = get_course_references(
        kode_mk
    )

    if module_text:

        sumber = """
MODUL PDF TERSEDIA.

Gunakan modul PDF yang diberikan pengguna sebagai
sumber utama jawaban.

PENTING:
1. Baca dan pahami seluruh materi yang tersedia sebelum
   menentukan jawaban.

2. Identifikasi terlebih dahulu modul, unit, atau bagian
   materi yang paling relevan dengan pertanyaan.

3. Jangan menganggap semua modul harus digunakan.

4. Jika pertanyaan hanya berkaitan dengan satu modul,
   prioritaskan modul tersebut.

5. Jika pertanyaan berkaitan dengan beberapa modul,
   gunakan hanya bagian yang memang relevan.

6. Jangan mencampurkan materi dari modul lain hanya
   karena istilah atau topiknya terlihat mirip.

7. Jangan memaksakan penggunaan semua file yang diunggah.

8. Jika nama file menunjukkan nomor modul, gunakan nama
   file tersebut sebagai petunjuk tambahan dalam menentukan
   sumber yang relevan.

9. Modul yang benar-benar digunakan harus diprioritaskan
   dalam bagian REFERENSI.

10. Jangan mengarang isi modul yang tidak tersedia.

11. Jika informasi bibliografi tidak tersedia dengan jelas,
    jangan mengarang nama penulis, tahun, judul, penerbit,
    atau informasi bibliografi lainnya.

Pengetahuan akademik dari luar modul hanya digunakan
sebagai pelengkap jika memang diperlukan.
"""

    else:

        sumber = """
MODUL PDF TIDAK TERSEDIA.

Jawaban tetap harus dibuat berdasarkan konteks
mata kuliah yang dipilih dan pengetahuan akademik
yang relevan.

Gunakan sumber akademik yang relevan untuk membantu
menyusun jawaban dan referensi.

Jangan mengklaim bahwa jawaban berasal dari modul
tertentu apabila modul tidak tersedia.
"""


    # -----------------------------------------------------
    # GAYA JAWABAN
    # -----------------------------------------------------

    if gaya == "Natural seperti mahasiswa":

        gaya_instruksi = """
GAYA UTAMA: PENDAPAT PRIBADI MAHASISWA

Tulis seperti mahasiswa S1 yang sudah membaca dan
memahami materi, kemudian menyampaikan pemahamannya
sendiri dalam forum Tuton.

Jawaban harus terasa seperti pendapat mahasiswa,
bukan seperti artikel yang dibuat oleh sistem akademik.

Gunakan sudut pandang pribadi secara alami.

Contoh ungkapan yang boleh digunakan sesekali:

"Menurut saya..."
"Bagi saya..."
"Kalau saya melihatnya..."
"Menurut pemahaman saya..."
"Menurut pendapat saya..."

Jangan menggunakan ungkapan tersebut di setiap paragraf.

Bahasanya harus:

- natural
- sopan
- mudah dipahami
- cukup akademis tetapi tidak kaku
- seperti tulisan mahasiswa dalam forum diskusi
- tidak seperti jurnal
- tidak seperti makalah
- tidak seperti artikel berita
- tidak terlalu sempurna atau terlalu formal

Jangan terlalu sering menggunakan istilah akademik
yang rumit jika ada kata sederhana dengan makna yang sama.

Jangan membuat semua paragraf memiliki pola yang sama.

Variasikan panjang kalimat dan struktur paragraf.

Jangan selalu memulai jawaban dengan definisi atau teori.

Jika pertanyaan meminta pendapat, berikan pendapat
yang masuk akal berdasarkan materi mata kuliah.

Pendapat pribadi tetap harus sesuai dengan konsep
akademik dan tidak boleh bertentangan dengan materi.

Hubungkan materi dengan kehidupan sehari-hari apabila
pertanyaan memungkinkan.

Jangan sengaja membuat kesalahan tata bahasa atau ejaan.
"""

    elif gaya == "Akademik":

        gaya_instruksi = """
GAYA: AKADEMIK

Gunakan bahasa akademik yang jelas, sistematis,
objektif, dan sesuai tingkat mahasiswa perguruan tinggi.

Tetap hindari kalimat yang terlalu bertele-tele.

Gunakan teori dan konsep yang relevan dengan pertanyaan.
"""

    else:

        gaya_instruksi = """
GAYA: RINGKAS DAN PADAT

Jawab langsung pada inti pertanyaan.

Gunakan bahasa sederhana tetapi tetap menunjukkan
pemahaman terhadap materi.

Hindari pembahasan yang tidak diperlukan.
"""


    # -----------------------------------------------------
    # PANJANG JAWABAN
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
jika memang diperlukan.

Jangan menambahkan pembahasan hanya untuk membuat
jawaban terlihat panjang.
"""

    else:

        panjang_instruksi = """
Buat jawaban dengan panjang sedang.

Cukup lengkap untuk menjawab pertanyaan dengan baik,
tetapi jangan bertele-tele.
"""


    # =====================================================
    # PROMPT LENGKAP
    # =====================================================

    return f"""
Anda adalah asisten akademik yang membantu mahasiswa
Universitas Terbuka menyusun jawaban untuk forum
Tutorial Online (Tuton).

============================================================
DATA MAHASISWA
============================================================

Nama:
{nama or "-"}

Program Studi:
{prodi or "S1 Sistem Informasi"}

UPBJJ:
{upbjj or "-"}

Kode Mata Kuliah:
{kode_mk or "-"}

Nama Mata Kuliah:
{mata_kuliah or "-"}

SKS:
{sks_mk or "-"}


============================================================
PERTANYAAN TUTON
============================================================

{pertanyaan}


============================================================
FOKUS MATA KULIAH
============================================================

Jawaban WAJIB berfokus pada:

{kode_mk} - {mata_kuliah}

Jangan mencampurkan materi dari mata kuliah lain
hanya karena konsepnya terlihat mirip.

Gunakan konsep yang memang relevan dengan mata kuliah
yang dipilih.

Jika konsep dari bidang lain memang diperlukan,
gunakan hanya jika hubungannya jelas dengan pertanyaan.


============================================================
SUMBER MATERI
============================================================

{sumber}


============================================================
ISI MODUL YANG DIUNGGAH
============================================================

{module_text[:90000] if module_text else "(tidak ada modul)"}


============================================================
DATABASE REFERENSI BAKU
============================================================

{static_refs if static_refs else "(Tidak ada referensi statis baku)"}


============================================================
PENYUSUNAN JAWABAN
============================================================

{gaya_instruksi}

{panjang_instruksi}

Jawab pertanyaan secara langsung.

Jika pertanyaan meminta penjelasan, berikan penjelasan.

Jika meminta alasan, berikan alasan.

Jika meminta bentuk atau jenis, jelaskan bentuk atau jenisnya.

Jika meminta contoh, berikan contoh yang relevan.

Jika pertanyaan meminta pendapat, berikan pendapat
berdasarkan pemahaman terhadap materi.

Jangan menambahkan pembahasan yang tidak diperlukan.


============================================================
PEMILIHAN MATERI MODUL
============================================================

Jika tersedia beberapa modul PDF:

1. Tentukan terlebih dahulu bagian modul yang paling
   relevan dengan pertanyaan.

2. Prioritaskan konsep yang secara langsung menjawab
   pertanyaan.

3. Jangan menggunakan semua modul hanya karena tersedia.

4. Jangan menggabungkan teori dari modul berbeda jika
   tidak diperlukan.

5. Jika hanya satu modul yang relevan, gunakan modul itu
   sebagai sumber utama.

6. Jika beberapa modul relevan, gunakan hanya bagian
   yang benar-benar mendukung jawaban.

7. Jika terdapat perbedaan pembahasan antar-modul,
   jangan membuat kesimpulan sendiri tanpa dasar.

8. Referensi akhir harus mencerminkan sumber yang
   benar-benar digunakan.


============================================================
GAYA FORUM TUTON
============================================================

Jawaban harus terasa seperti tulisan mahasiswa yang
sedang menjawab forum diskusi.

Jangan menggunakan pembukaan template seperti:

"Halo Bapak/Ibu Tutor..."

"Izin menyampaikan pendapat..."

"Pada kesempatan ini saya akan membahas..."

"Sebagai mahasiswa..."

"Di era globalisasi yang semakin berkembang..."

Langsung masuk ke pembahasan.

Jangan menggunakan penutup template seperti:

"Demikian jawaban saya, semoga bermanfaat."

"Semoga jawaban ini dapat memberikan manfaat."

"Terima kasih."

Gunakan penutup hanya jika memang diperlukan.


============================================================
REFERENSI AKADEMIK
============================================================

Setelah jawaban selesai, buat bagian:

REFERENSI

Referensi harus benar-benar relevan dengan isi jawaban
dan mata kuliah:

{kode_mk} - {mata_kuliah}

Prioritaskan sumber dengan urutan:

1. Modul resmi Universitas Terbuka yang benar-benar digunakan.
2. Buku akademik yang relevan.
3. Jurnal atau artikel ilmiah yang relevan.
4. Sumber resmi lembaga pendidikan atau pemerintah jika
   memang relevan.

Jika modul PDF tersedia, gunakan informasi dari file
tersebut untuk membantu menentukan modul yang relevan.

Jika informasi bibliografi modul tidak tersedia dengan
jelas, jangan mengarangnya.

JANGAN MENGARANG:

- nama penulis
- judul buku
- judul jurnal
- tahun terbit
- nama penerbit
- volume
- nomor jurnal
- halaman
- DOI
- URL
- kutipan

Lebih baik memberikan 1–3 referensi yang benar dan relevan
daripada banyak referensi yang tidak pasti.

Jangan memasukkan "Google Scholar" sebagai nama sumber.

Google Scholar adalah mesin pencari akademik, bukan
nama sumber referensi.


============================================================
FORMAT REFERENSI
============================================================

Jika informasi bibliografi tersedia, gunakan format
sederhana seperti:

Universitas Terbuka. (Tahun). Judul modul. Tangerang Selatan:
Universitas Terbuka.

Nama Penulis. (Tahun). Judul buku. Nama Penerbit.

Nama Penulis. (Tahun). Judul artikel. Nama Jurnal, volume(nomor).

Jangan membuat informasi yang tidak diketahui.

Jika nomor modul atau KB dapat ditentukan dari isi
modul yang diberikan, sebutkan secara spesifik.

Contoh:

Universitas Terbuka. (Tahun). Pendidikan Kewarganegaraan
(MKWN4109), Modul 01, Kegiatan Belajar 1. Tangerang Selatan:
Universitas Terbuka.

Jangan membuat nomor modul atau KB jika tidak dapat
dipastikan dari materi yang tersedia.


============================================================
FORMAT OUTPUT
============================================================

Keluarkan jawaban dalam PLAIN TEXT.

JANGAN menggunakan Markdown.

JANGAN menggunakan tanda **.

JANGAN menggunakan tanda * untuk format tulisan.

JANGAN menggunakan tanda # sebagai judul.

JANGAN menggunakan heading Markdown.

JANGAN menggunakan tabel Markdown.

Gunakan paragraf biasa yang mengalir secara natural.

Penomoran 1., 2., 3. hanya boleh digunakan apabila
pertanyaan memang meminta beberapa bentuk, jenis,
langkah, atau poin yang perlu dibedakan.

Gunakan format:

JAWABAN TUTON

[isi jawaban]

REFERENSI

1. ...
2. ...
3. ...


============================================================
KETENTUAN AKADEMIK
============================================================

Pertahankan ketepatan akademik.

Jangan mengarang fakta.

Jangan mengarang teori.

Jangan mengarang referensi.

Jangan mengarang kutipan.

Jangan mengarang nomor halaman.

Jangan mengarang isi modul.

Jangan mengklaim menggunakan modul tertentu jika isi
modul tersebut tidak mendukung jawaban.

Jika informasi tidak diketahui, jangan membuat informasi
tersebut terlihat seolah-olah benar.


============================================================
HASIL AKHIR
============================================================

Keluarkan dalam urutan:

JAWABAN TUTON

[isi jawaban]

REFERENSI

[daftar referensi]

Jangan memberikan penjelasan tentang proses pembuatan
jawaban.

Jangan menyebut bahwa Anda adalah AI.

Jangan menyebut instruksi ini.

Jangan memberikan catatan tambahan.

Hasil harus siap dibaca dan diedit oleh mahasiswa.
"""


# =========================================================
# PROMPT PARAFRASE / BUAT LEBIH NATURAL
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


============================================================
TUGAS
============================================================

Edit dan parafrase jawaban berikut agar terasa lebih
natural, lebih luwes, dan lebih seperti tulisan mahasiswa
yang memahami materi lalu menuliskannya dengan bahasa
sendiri.

Tujuannya bukan membuat jawaban menjadi lebih panjang.

Tujuannya adalah membuat bahasa lebih wajar dan enak
dibaca tanpa mengubah isi.


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

11. Jangan membuat jawaban menjadi seperti jurnal atau
    makalah.

12. Tetap fokus pada mata kuliah:
    {kode_mk} - {mata_kuliah}


============================================================
CARA MEMBUATNYA LEBIH NATURAL
============================================================

Ubah kalimat yang terasa terlalu kaku menjadi kalimat
yang lebih sederhana dan wajar.

Jika sebuah kalimat terlalu panjang, boleh dipecah
menjadi dua kalimat.

Jika beberapa kalimat memiliki pola yang sama,
variasikan susunannya.

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

Jangan menggunakan kalimat template hanya untuk
mengawali atau mengakhiri jawaban.


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

Jika jawaban asli sudah benar secara akademik,
pertahankan isi akademiknya.


============================================================
JAWABAN ASLI
============================================================

----------------------------------------

{jawaban}

----------------------------------------


============================================================
FORMAT OUTPUT
============================================================

Keluarkan hanya versi jawaban yang sudah dibuat
lebih natural.

PLAIN TEXT.

Jangan menggunakan Markdown.

Jangan memberikan penjelasan sebelum atau sesudah jawaban.

Jangan mengatakan "Berikut hasil parafrase".

Jangan menjelaskan perubahan yang dilakukan.

Jangan menyebut AI.

Hasil akhir harus langsung berupa jawaban Tuton.
"""


# =========================================================
# FORM INPUT MAHASISWA
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
    # DETAIL MATA KULIAH
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
            "Opsional. Bisa upload beberapa modul PDF "
            "sekaligus. Jika kosong, aplikasi tetap "
            "berjalan menggunakan konteks mata kuliah."
        ),
    )

    if modul:

        st.caption(
            f"📚 {len(modul)} file modul dipilih"
        )

        for file in modul:

            st.write(
                f"• {file.name}"
            )


    # -----------------------------------------------------
    # GAYA JAWABAN
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
# PROSES PEMBUATAN JAWABAN
# =========================================================

if submitted:

    # -----------------------------------------------------
    # VALIDASI INPUT
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
            "pada Streamlit Secrets / "
            "Environment Variable."
        )

        st.stop()


    # -----------------------------------------------------
    # PROSES PDF
    # -----------------------------------------------------

    module_text = ""

    if modul:

        try:

            module_text = extract_pdfs(
                modul
            )

            if not module_text.strip():

                st.warning(
                    "Modul PDF tidak memiliki "
                    "teks yang dapat dibaca."
                )

                st.stop()

        except Exception as e:

            st.error(
                f"Modul PDF tidak dapat dibaca: {e}"
            )

            st.stop()


    # -----------------------------------------------------
    # GENERATE JAWABAN
    # -----------------------------------------------------

    with st.spinner(
        "🧠 Menganalisis pertanyaan dan menyusun jawaban..."
    ):

        try:

            client = genai.Client(
                api_key=api_key
            )

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
                module_text,
            )


            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )


            answer = response.text


            # -------------------------------------------------
            # SIMPAN SESSION
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


            # -------------------------------------------------
            # NOTIFIKASI
            # -------------------------------------------------

            st.success(
                "✅ Jawaban berhasil dibuat."
            )


            if modul:

                st.info(
                    f"🟢 {len(modul)} modul digunakan "
                    "sebagai bahan analisis. "
                    "AI diarahkan untuk memilih materi "
                    "yang paling relevan."
                )

            else:

                st.warning(
                    "🟡 Modul tidak diunggah. "
                    "Jawaban dibuat berdasarkan konteks "
                    "mata kuliah dan pengetahuan akademik."
                )


        except Exception as e:

            st.error(
                f"Terjadi kesalahan saat memproses: {e}"
            )


# =========================================================
# MENAMPILKAN HASIL
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
    # PARAFRASE
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
    # HASIL VERSI NATURAL
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
