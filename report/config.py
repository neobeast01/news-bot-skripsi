"""Konfigurasi laporan LAPIN."""

# Identitas penyusun
NIT = "23201188"
NAMA = "Muhammad Fajriansyah"
JABATAN = "Taruna Program Studi Keamanan dan Intelijen Siber"
INSTANSI = "Sekolah Tinggi Intelijen Negara"

# KOP SURAT (bagian atas)
KOP_BARIS_1 = "BADAN INTELIJEN NEGARA"
KOP_BARIS_2 = "SEKOLAH TINGGI INTELIJEN NEGARA"
KOP_BARIS_3 = ""  # baris alamat/telepon (kosongkan kalau tidak perlu)
TAMPILKAN_GARIS_KOP = True

# Metadata laporan
DEFAULT_KEPADA = "Yth. Kepala Panitia Pra OJT STIN"
DEFAULT_DARI = f"{NAMA}"
DEFAULT_TEMBUSAN = "-"
DEFAULT_NILAI = "C-3"

# Konteks kejadian
TEMPAT_KEJADIAN = (
    "Auditorium Gedung Sam Ratulangi, Sekolah Tinggi Intelijen Negara, "
    "Kabupaten Bogor, Jawa Barat"
)
WAKTU_LAPOR = "11.30"

# Kode klasifikasi
KODE_LAPORAN = "LI"
TAMPILKAN_LAMPIRAN = False

# Font (Times New Roman untuk dokumen formal)
FONT_NAME = "Times New Roman"
FONT_SIZE = 12