"""Menu Interaktif: Generate LAPIN dengan filter kategori."""
from datetime import date, timedelta
import questionary
from loguru import logger
from report.generator import generate_lapin

KATEGORI_VALID = {
    "Semua Kategori (Umum)": None,
    "Ancaman Malware": "malware",
    "Serangan Ransomware": "ransomware",
    "Kerentanan Sistem (Vulnerability)": "vulnerability",
    "Kebocoran Data (Data Breach)": "data-breach",
    "Serangan Phishing": "phishing",
    "Ancaman APT": "apt",
    "Serangan Siber (Cyber Attack)": "cyber-attack",
    "Kebijakan Keamanan (Security Policy)": "security-policy",
    "Lain-lain": "lain-lain",
}

def main():
    print("\n" + "="*50)
    print(" 📄 GENERATOR LAPORAN INFORMASI (LAPIN) - CTI")
    print("="*50 + "\n")

    # 1. Pilih Kategori
    pilihan_kategori_label = questionary.select(
        "Pilih kategori laporan yang ingin dibuat:",
        choices=list(KATEGORI_VALID.keys())
    ).ask()

    if not pilihan_kategori_label:
        print("❌ Dibatalkan.")
        return

    kategori_filter = KATEGORI_VALID[pilihan_kategori_label]

    # 2. Pilih Rentang Waktu
    pilihan_waktu = questionary.select(
        "Pilih rentang waktu berita (ke belakang):",
        choices=[
            "1 Hari Terakhir",
            "3 Hari Terakhir",
            "7 Hari Terakhir (1 Minggu)",
            "14 Hari Terakhir (2 Minggu)",
            "30 Hari Terakhir (1 Bulan)"
        ]
    ).ask()

    if not pilihan_waktu:
        print("❌ Dibatalkan.")
        return

    days_map = {
        "1 Hari Terakhir": 1,
        "3 Hari Terakhir": 3,
        "7 Hari Terakhir (1 Minggu)": 7,
        "14 Hari Terakhir (2 Minggu)": 14,
        "30 Hari Terakhir (1 Bulan)": 30,
    }
    days = days_map[pilihan_waktu]

    # 3. Konfirmasi
    konfirmasi = questionary.confirm(
        f"Buat LAPIN '{pilihan_kategori_label}' untuk {days} hari terakhir?"
    ).ask()

    if not konfirmasi:
        print("❌ Dibatalkan.")
        return

    # 4. Eksekusi Generator
    end = date.today()
    start = end - timedelta(days=days)

    print(f"\n⏳ Memproses pembuatan LAPIN... (Kategori: {kategori_filter or 'Semua'})")
    print("-" * 50)

    path = generate_lapin(start, end, kategori_filter=kategori_filter)

    if path:
        print(f"\n✅ BERHASIL! Laporan disimpan di:\n👉 {path}\n")
    else:
        print("\n❌ GAGAL: Tidak ada artikel yang cocok dengan kriteria tersebut.")
        print("   (Pastikan crawler sudah dijalankan atau coba perbesar rentang waktu).\n")
        
def generate_lapin_from_command(kategori: str = None) -> str:
    """
    Fungsi tanpa menu interaktif, dipanggil oleh WhatsApp Bot.
    Mengembalikan path file .docx yang dihasilkan.
    """
    from datetime import date, timedelta
    
    # Daftar kategori yang valid (mengambil dari dictionary KATEGORI_VALID di atas)
    valid_kategori_values = list(KATEGORI_VALID.values())
    
    # Jika kategori yang dikirim bot tidak ada di daftar, jadikan Umum (None)
    if kategori and kategori not in valid_kategori_values:
        kategori = None
        
    end = date.today()
    start = end - timedelta(days=7)  # Selalu ambil berita 7 hari ke belakang
    
    print(f"🤖 Bot meminta LAPIN: {kategori or 'Umum'} ({start} s/d {end})")
    
    # Panggil fungsi utama generator
    path = generate_lapin(start, end, kategori_filter=kategori)
    return path

if __name__ == "__main__":
    main()