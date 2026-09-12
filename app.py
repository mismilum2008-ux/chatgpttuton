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

# =========================================================
# PROMPT UTAMA - JAWABAN TUTON + REFERENSI
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

Gunakan modul PDF yang diberikan sebagai sumber utama jawaban.

Pahami isi modul terlebih dahulu sebelum menyusun jawaban.
Jika terdapat konsep, istilah, definisi, atau pembahasan yang
relevan di dalam modul, prioritaskan materi tersebut.

Modul yang diberikan pengguna juga harus menjadi sumber utama
dalam bagian REFERENSI.

Jika informasi bibliografi modul tidak tersedia dengan jelas,
jangan mengarang nama penulis, tahun, judul, penerbit, atau
informasi lainnya.

Pengetahuan umum hanya digunakan sebagai pelengkap apabila
diperlukan.
"""
    else:
        sumber = """
MODUL TIDAK TERSEDIA.

Jawaban tetap harus dibuat berdasarkan konteks mata kuliah
yang dipilih dan pengetahuan akademik yang relevan.

Gunakan sumber akademik yang relevan untuk membantu menyusun
jawaban dan referensi.

Jangan mengklaim bahwa jawaban berasal dari modul tertentu
apabila modul tersebut tidak tersedia.
"""

    if gaya == "Natural seperti mahasiswa":
         gaya_instruksi = """
GAYA UTAMA: PENDAPAT PRIBADI MAHASISWA

Tulis seperti mahasiswa S1 yang sudah membaca dan memahami
materi, kemudian menyampaikan pemahamannya sendiri dalam forum
Tuton.

Jawaban harus terasa seperti pendapat mahasiswa, bukan seperti
artikel yang dibuat oleh sistem akademik.

Gunakan sudut pandang pribadi secara alami. Sesekali gunakan
ungkapan seperti:

"Menurut saya..."
"Bagi saya..."
"Kalau saya melihatnya..."
"Menurut pemahaman saya..."
"Menurut pendapat saya..."

Namun JANGAN menggunakan ungkapan tersebut di setiap paragraf.
Gunakan hanya ketika memang sesuai dengan alur pembahasan.

Mahasiswa boleh menjelaskan konsep terlebih dahulu kemudian
memberikan pendapat atau contoh berdasarkan pemahamannya.

Hubungkan materi dengan kehidupan sehari-hari apabila pertanyaan
memungkinkan.

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

Jangan terlalu sering menggunakan istilah akademik yang rumit
jika ada kata sederhana yang memiliki makna sama.

Jangan membuat semua paragraf memiliki pola yang sama.

Variasikan panjang kalimat dan struktur paragraf.

Jangan selalu memulai jawaban dengan definisi atau teori.

Jika pertanyaan meminta pendapat, berikan pendapat yang masuk
akal berdasarkan materi mata kuliah.

Pendapat pribadi tetap harus sesuai dengan konsep akademik dan
tidak boleh bertentangan dengan materi.

Contoh gaya yang diinginkan:

"Menurut saya, partisipasi warga negara sangat penting karena
demokrasi tidak akan berjalan dengan baik kalau masyarakat hanya
menjadi penonton."

"Kalau saya melihatnya, bentuk partisipasi tidak harus selalu
dalam kegiatan politik. Hal-hal sederhana seperti ikut
musyawarah atau menyampaikan pendapat dengan cara yang baik juga
termasuk bentuk partisipasi."

"Bagi saya, contoh tersebut menunjukkan bahwa demokrasi sebenarnya
cukup dekat dengan kehidupan sehari-hari."

Jangan menyalin contoh kalimat di atas secara otomatis.
Gunakan hanya sebagai gambaran gaya bahasa.

Yang paling penting, jawaban harus terasa seperti mahasiswa
yang sedang menjelaskan pemahamannya sendiri setelah mempelajari
materi.
"""
    elif gaya == "Akademik":
        gaya_instruksi = """
GAYA: AKADEMIK

Gunakan bahasa akademik yang jelas, sistematis, objektif,
dan sesuai tingkat mahasiswa perguruan tinggi.

Tetap hindari kalimat yang terlalu bertele-tele.
"""
    else:
        gaya_instruksi = """
GAYA: RINGKAS DAN PADAT

Jawab langsung pada inti pertanyaan.

Gunakan bahasa sederhana tetapi tetap menunjukkan
pemahaman terhadap materi.
"""

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

Ini adalah aturan yang sangat penting.

Jangan mencampurkan materi dari mata kuliah lain hanya karena
konsepnya terlihat mirip.

Gunakan konsep yang memang relevan dengan mata kuliah tersebut.

Contoh:

Jika mata kuliah adalah Pendidikan Kewarganegaraan, gunakan
konsep yang relevan dengan Pendidikan Kewarganegaraan.

Jangan memasukkan konsep Pendidikan Agama Islam, Manajemen,
Sistem Informasi, atau bidang lain apabila konsep tersebut
tidak diperlukan untuk menjawab pertanyaan.

Jangan menggunakan istilah atau teori hanya agar jawaban
terlihat lebih akademis.

Jika konsep dari bidang lain memang diperlukan, gunakan hanya
jika hubungan dengan pertanyaan sangat jelas.


============================================================
SUMBER MATERI
============================================================

{sumber}


============================================================
ISI MODUL
============================================================

{module_text[:90000] if module_text else "(tidak ada modul)"}


============================================================
PENYUSUNAN JAWABAN
============================================================

{gaya_instruksi}

{panjang_instruksi}

Jawab pertanyaan secara langsung.

Jika pertanyaan meminta penjelasan, berikan penjelasan.

Jika meminta alasan, berikan alasan.

Jika meminta bentuk atau jenis, jelaskan bentuk atau jenisnya.

Jika meminta contoh, berikan contoh yang relevan dengan
pembahasan.

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

Referensi harus benar-benar relevan dengan isi jawaban dan
mata kuliah:

{kode_mk} - {mata_kuliah}

Prioritaskan sumber dengan urutan:

1. Modul resmi Universitas Terbuka yang digunakan.
2. Buku akademik yang relevan.
3. Jurnal atau artikel ilmiah yang relevan.
4. Sumber resmi dari lembaga pendidikan atau pemerintah jika
   memang relevan.

Jika menggunakan modul yang tersedia, masukkan modul tersebut
sebagai referensi utama.

Jika menggunakan buku atau jurnal, hanya cantumkan informasi
bibliografi yang benar-benar diketahui atau dapat dipastikan.

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

Jangan membuat referensi hanya karena terdengar meyakinkan.

Lebih baik memberikan 1–3 referensi yang benar dan relevan
daripada banyak referensi yang tidak pasti.

Jangan memasukkan Google Scholar sebagai nama sumber.

Google Scholar adalah mesin pencari akademik, bukan sumber
referensi.

Jika sumbernya berupa artikel jurnal yang ditemukan melalui
Google Scholar, tuliskan informasi artikel atau jurnalnya,
bukan "Google Scholar" sebagai referensi.


============================================================
FORMAT REFERENSI
============================================================

Gunakan format sederhana seperti:

REFERENSI

Universitas Terbuka. (Tahun). Judul modul. Tangerang Selatan:
Universitas Terbuka.

Nama Penulis. (Tahun). Judul buku. Nama Penerbit.

Nama Penulis. (Tahun). Judul artikel. Nama Jurnal, volume(nomor).

Jangan membuat informasi yang tidak diketahui.


============================================================
FORMAT OUTPUT - SANGAT PENTING
============================================================

Keluarkan jawaban dalam PLAIN TEXT.

JANGAN menggunakan Markdown.

JANGAN menggunakan tanda **.

JANGAN menggunakan tanda * untuk format tulisan.

JANGAN menggunakan tanda # sebagai judul.

JANGAN menggunakan heading Markdown.

JANGAN menggunakan bullet point Markdown.

JANGAN menggunakan tabel Markdown.

Gunakan paragraf biasa yang mengalir secara natural.

Penomoran 1., 2., 3. hanya boleh digunakan apabila pertanyaan
memang meminta beberapa bentuk, jenis, langkah, atau poin yang
perlu dibedakan.

Untuk bagian REFERENSI, setiap sumber boleh ditulis dalam
paragraf terpisah.

Gunakan format:

REFERENSI

1. ...
2. ...
3. ...

jika terdapat lebih dari satu sumber.


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


Jangan memberikan penjelasan tentang proses pembuatan jawaban.

Jangan menyebut bahwa Anda adalah AI.

Jangan menyebut instruksi ini.

Jangan memberikan catatan tambahan.

Hasil harus siap dibaca dan diedit oleh mahasiswa.
"""

# =========================================================
# PROMPT PARAFRASE / BUAT LEBIH NATURAL
# =========================================================
def split_answer_and_references(text):
    marker = "REFERENSI"

    if marker in text:
        parts = text.split(marker, 1)

        answer_part = parts[0]
        references_part = parts[1]

        answer_part = answer_part.replace(
            "JAWABAN TUTON",
            "",
            1
        ).strip()

        references_part = references_part.strip()

        return answer_part, references_part

    return text.strip(), ""
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

                original_answer = st.session_state["answer"]

jawaban_utama, referensi = split_answer_and_references(
    original_answer
)

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=build_paraphrase_prompt(
        jawaban_utama,
        st.session_state["kode_mk"],
        st.session_state["mata_kuliah"],
    ),
)

natural_body = response.output_text.strip()

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

st.session_state["natural_answer"] = natural_answer

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
