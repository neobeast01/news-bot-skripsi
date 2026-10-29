"""Generator LAPIN — sesuai template STIN persis."""
import re
from datetime import datetime, date, timedelta
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from loguru import logger

from storage.db import get_conn
from report import config


GLOSSARY_PATH = Path(__file__).parent.parent / "nlp" / "data" / "cyber_dict" / "glossary_id.txt"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
          "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

KATEGORI_LABEL = {
    "malware": "Ancaman Malware",
    "ransomware": "Serangan Ransomware",
    "vulnerability": "Kerentanan Sistem",
    "data-breach": "Kebocoran Data",
    "phishing": "Serangan Phishing",
    "apt": "Ancaman APT",
    "cyber-attack": "Serangan Siber",
    "security-policy": "Kebijakan Keamanan Siber",
    "lain-lain": "Perkembangan Keamanan Siber",
}

KATEGORI_HAL = {
    "malware": "Ancaman Malware",
    "ransomware": "Serangan Ransomware",
    "vulnerability": "Kerentanan Sistem",
    "data-breach": "Kebocoran Data",
    "phishing": "Serangan Phishing",
    "apt": "Ancaman APT",
    "cyber-attack": "Serangan Siber",
    "security-policy": "Kebijakan Keamanan Siber",
    "lain-lain": "Perkembangan Keamanan Siber",
}


# ============================================================
# Glossary
# ============================================================
def _load_glossary():
    d = {}
    if not GLOSSARY_PATH.exists():
        return d
    with open(GLOSSARY_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip().lower()] = v.strip()
    return d


_GLOSSARY = _load_glossary()


def _apply_glossary(text):
    if not text or not _GLOSSARY:
        return text
    for en, id_word in sorted(_GLOSSARY.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(r"\b" + re.escape(en) + r"\b", re.IGNORECASE)
        text = pattern.sub(id_word, text)
    return text

def _netralisasi(text):
    """Ganti kata ganti orang pertama jadi netral/pasif."""
    if not text:
        return text
    REPLACEMENTS = [
        (r"\b[Kk]ami\s+menemukan(nya)?\b", r"ditemukan\1"),
        (r"\b[Kk]ami\s+melihat\b", "terlihat"),
        (r"\b[Kk]ami\s+mengamati\b", "teramati"),
        (r"\b[Kk]ami\s+mendeteksi\b", "terdeteksi"),
        (r"\b[Kk]ami\s+melaporkan\b", "dilaporkan"),
        (r"\b[Kk]ami\b", "pihak peneliti"),
        (r"\b[Kk]ita\b", ""),
        (r"\b[Ss]aya\b", ""),
        (r"\b[Aa]ku\b", ""),
    ]
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# Helper
# ============================================================
def _format_tanggal(dt):
    if not dt:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return dt
    return f"{dt.day} {_BULAN[dt.month-1]} {dt.year}"


def _roman_month(m):
    return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][m - 1]


def _remove_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        b = OxmlElement(f'w:{name}')
        b.set(qn('w:val'), 'none')
        b.set(qn('w:sz'), '0')
        b.set(qn('w:space'), '0')
        b.set(qn('w:color'), 'auto')
        borders.append(b)
    tblPr.append(borders)


def _add_bottom_border(paragraph, sz=12):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(sz))
    bottom.set(qn('w:space'), '6')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_full_width_line(doc, space_before=6, space_after=10):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    _add_bottom_border(p, sz=12)
    return p


def _add_meta_line(doc, label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.left_indent = Cm(4.5)
    p.paragraph_format.first_line_indent = Cm(-3.0)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(4.0), WD_TAB_ALIGNMENT.LEFT)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(4.5), WD_TAB_ALIGNMENT.LEFT)
    r = p.add_run(f"{label}\t:\t{value}")
    r.font.size = Pt(12)
    r.font.name = "Arial"
    return p


def _add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(12)
    r.font.name = "Arial"
    return p


# ============================================================
# Fetch
# ============================================================
def fetch_main_article(start_date, end_date, kategori_filter=None, max_age_hours=None):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        sql = """
            SELECT a.id, a.title, a.url, a.published_at, a.category,
                   a.language, a.content_raw, a.content_id,
                   s.name AS source_name
              FROM articles a
              LEFT JOIN sources s ON s.id = a.source_id
             WHERE a.published_at BETWEEN %s AND %s
               AND (a.language = 'id' OR a.content_id IS NOT NULL)
        """
        params = [start_date, end_date + timedelta(days=1)]

        if kategori_filter:
            sql += " AND a.category = %s"
            params.append(kategori_filter)

        if max_age_hours:
            sql += " AND a.published_at >= NOW() - INTERVAL %s HOUR"
            params.append(max_age_hours)

        sql += " ORDER BY a.published_at DESC LIMIT 1"

        cur.execute(sql, tuple(params))
        row = cur.fetchone()
        cur.close()
    return row


def fetch_entities(article_id):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT entity_type, entity_value FROM extractions WHERE article_id = %s",
            (article_id,),
        )
        rows = cur.fetchall()
        cur.close()
    result = {}
    for r in rows:
        result.setdefault(r["entity_type"], []).append(r["entity_value"])
    return result


def get_next_nomor_urut():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT report_code FROM reports WHERE YEAR(generated_at) = YEAR(NOW())")
        rows = cur.fetchall()
        cur.close()
    max_n = 0
    for (code,) in rows:
        m = re.search(r"LI-(\d+)", code or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{max_n + 1:03d}"


# ============================================================
# Narasi
# ============================================================
def _extract_sentences(text, max_count=6, min_length=140):
    """Ekstrak kalimat, gabung yang pendek jadi satu poin panjang."""
    if not text:
        return []
    text = re.sub(r"\s+", " ", text.strip())

    # Filter awal
    raw = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        s = s.strip()
        if len(s) < 30:
            continue
        low = s.lower()
        if any(low.startswith(x) for x in [
            "baca", "advertisement", "copyright", "subscribe",
            "the post", "image", "share this", "follow us",
            "klik", "baca juga", "simak", "lihat juga"
        ]):
            continue
        raw.append(s)

    # Gabungkan kalimat pendek → poin panjang
    sentences = []
    buffer = ""
    for s in raw:
        buffer = (buffer + " " + s).strip() if buffer else s
        if len(buffer) >= min_length:
            sentences.append(buffer)
            buffer = ""
            if len(sentences) >= max_count:
                break
    if buffer and len(sentences) < max_count:
        sentences.append(buffer)

    return sentences


def _buat_hal(article, entities):
    prefix = "Hasil Pengamatan Informasi Mengenai"
    judul = (article.get("title") or "").strip()
    j = judul.lower()
    kategori = (article.get("category") or "").lower()

    # 1. JENIS
    ACTION_MAP = [
        (r"\bstole\b|\bstolen\b|\bsteal\b", "Pencurian Data"),
        (r"\bransomware\b", "Serangan Ransomware"),
        (r"\bdata breach\b|\bbreached\b|\bleaked\b", "Kebocoran Data"),
        (r"\bphishing\b", "Serangan Phishing"),
        (r"\bddos\b", "Serangan DDoS"),
        (r"\bzero-?day\b", "Kerentanan Zero-Day"),
        (r"\bvulnerabilit|\bflaw\b|\bflaws\b", "Kerentanan Sistem"),
        (r"\bmalware\b", "Infeksi Malware"),
        (r"\bexploit", "Eksploitasi Sistem"),
        (r"\bcompromis", "Kompromi Sistem"),
        (r"\bcyberattack\b|\battack", "Serangan Siber"),
        (r"\bhack|\barrest", "Peretasan Sistem"),
    ]
    jenis = ""
    for pattern, label in ACTION_MAP:
        if re.search(pattern, j):
            jenis = label
            break
    if not jenis:
        jenis = KATEGORI_HAL.get(kategori, "Keamanan Siber")

    # 2. MODUS (cara serangan)
    MODUS_MAP = [
        (r"\bclaude code\b|\bai[- ]augmented\b|\bai orchestrat|\bai-orchestrat|\bai[- ]powered\b", "Berbasis AI"),
        (r"\bzero-?day\b", "Eksploitasi Zero-Day"),
        (r"\bsql injection\b", "Injeksi SQL"),
        (r"\bsocial engineering\b", "Rekayasa Sosial"),
        (r"\bclickfix\b", "Teknik ClickFix"),
        (r"\bsupply chain\b", "Rantai Pasok"),
    ]
    modus = ""
    for pattern, label in MODUS_MAP:
        if re.search(pattern, j):
            modus = label
            break

    # 3. TARGET
    TARGET_MAP = [
        ("idcf cloud", "IDCF Cloud"), ("wordpress", "WordPress"),
        ("netscaler", "NetScaler"), ("citrix", "Citrix"),
        ("sonicwall", "SonicWall"), ("gitlab", "GitLab"),
        ("atlassian", "Atlassian"), ("microsoft", "Microsoft"),
        ("apple", "Apple"), ("google", "Google"),
        ("iphone", "iPhone"), ("canonical", "Canonical"),
        ("ubuntu", "Ubuntu"), ("azure", "Azure"),
        ("ledger", "Ledger"), ("ahold", "Ahold Delhaize"),
    ]
    target = ""
    for key, val in TARGET_MAP:
        if key in j:
            target = val
            break

    # 4. KUANTITAS + OBJEK
    qty = ""
    m = re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{4,})\b", judul)
    if m:
        qty = m.group(1).replace(",", ".")

    OBJECT_MAP = [
        (r"\brecords?\b", "Catatan"),
        (r"\bpeople\b|\bindividuals?\b", "Warga"),
        (r"\busers?\b", "Pengguna"),
        (r"\bcustomers?\b", "Pelanggan"),
        (r"\baccounts?\b", "Akun"),
        (r"\bsites?\b|\bwebsites?\b", "Situs Web"),
        (r"\bservers?\b", "Peladen"),
    ]
    objek = ""
    for pattern, label in OBJECT_MAP:
        if re.search(pattern, j):
            objek = label
            break

    # 5. LOKASI
    LOKASI_MAP = {
        "ukrain": "Ukraina", "russia": "Rusia", "russian": "Rusia",
        "chinese": "Tiongkok", "china": "Tiongkok",
        "japan": "Jepang", "japanese": "Jepang",
        "south korea": "Korea Selatan", "indonesia": "Indonesia",
        "poland": "Polandia", "polish": "Polandia",
        "netherlands": "Belanda", "dutch": "Belanda",
        "norway": "Norwegia", "norwegian": "Norwegia",
        "american": "Amerika Serikat", "u.s.": "Amerika Serikat",
        "french": "Prancis", "france": "Prancis",
    }
    lokasi = ""
    for key, val in LOKASI_MAP.items():
        if key in j:
            lokasi = val
            break

    # 6. AKTOR — dari entities dulu, fallback: ekstrak CapitalCase dari judul
    aktor = ""
    if entities:
        apt = entities.get("threat_actor") or []
        mal = entities.get("malware") or []
        aktor = apt[0] if apt else (mal[0] if mal else "")
    if not aktor:
        # Pattern: kata CamelCase seperti "CyberXero", "ShinyHunters"
        m = re.search(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", judul)
        if m:
            aktor = m.group(1)

    # === SUSUN (prioritas: jenis → modus → target → qty objek → lokasi → aktor) ===
    parts = [jenis]
    if modus:
        parts.append(modus)
    if target:
        parts.append(f"terhadap {target}")
    if qty and objek:
        parts.append(f"{qty} {objek}")
    elif objek:
        parts.append(objek)
    if lokasi:
        parts.append(f"di {lokasi}")
    if aktor:
        parts.append(f"oleh {aktor}")

    detail = " ".join(parts)
    words = detail.split()
    if len(words) > 12:
        words = words[:12]
    detail = " ".join(words)

    return f"{prefix} {detail}"


def _buat_pembuka(article, sentences, hal=None):
    """Pembuka pakai waktu real-time + topik dari Hal."""
    source = article.get("source_name") or "media keamanan siber"

    # Ambil topik dari "Hal" (buang prefix)
    if hal:
        topik = hal.replace("Hasil Pengamatan Informasi Mengenai ", "").strip()
    else:
        kategori = (article.get("category") or "").lower()
        topik = KATEGORI_LABEL.get(kategori, "keamanan siber")

    now = datetime.now()
    tgl_now = f"{now.day} {_BULAN[now.month-1]} {now.year}"
    jam_now = now.strftime("%H.%M")

    return _apply_glossary(
        f"Pada {tgl_now} pukul {jam_now} WIB, bertempat di "
        f"{config.TEMPAT_KEJADIAN}, diperoleh informasi dari media "
        f"keamanan siber {source.capitalize()} mengenai {topik}. "
        f"Berdasarkan hasil pengamatan diperoleh informasi sebagai berikut:"
    )


# Template analisis per kategori: (analisis, rekomendasi)
CATATAN_TEMPLATES = {
    "ransomware": {
        "analisis": (
            "Serangan ransomware terhadap {target} menunjukkan bahwa model "
            "bisnis kriminal ransomware-as-a-service terus berkembang dan "
            "menargetkan infrastruktur vital. Kelompok ransomware kini tidak "
            "hanya mengekripsi data, tetapi juga melakukan eksfiltrasi data "
            "untuk memperbesar tekanan melalui ancaman kebocoran publik. "
            "Dampak terhadap layanan publik dan operasional menunjukkan bahwa "
            "ketahanan sistem tidak cukup hanya mengandalkan antivirus, tetapi "
            "memerlukan strategi pemulihan yang teruji."
        ),
        "rekomendasi": (
            "Langkah mitigasi yang perlu diprioritaskan meliputi penyediaan "
            "cadangan data yang terisolasi (immutable backup) dan tidak "
            "terhubung ke jaringan produksi, segmentasi jaringan untuk "
            "membatasi pergerakan lateral, penerapan autentikasi multifaktor "
            "pada akun administratif, serta pengujian berkala terhadap "
            "prosedur pemulihan. Selain itu, pemantauan anomali aktivitas "
            "enkripsi dan koordinasi cepat dengan pihak berwenang menjadi "
            "kunci untuk mempercepat respons."
        ),
    },
    "malware": {
        "analisis": (
            "Kehadiran malware {malware_list} menunjukkan bahwa teknik "
            "penyebaran dan persistensi pelaku terus berevolusi. Malware "
            "modern sering memanfaatkan saluran komunikasi terenkripsi "
            "peer-to-peer (P2P) atau protokol yang sah untuk menghindari "
            "deteksi berbasis domain dan signature. Kemampuan malware "
            "beradaptasi dengan lingkungan korban menunjukkan perlunya "
            "pendekatan deteksi berbasis perilaku (behavior-based), bukan "
            "hanya bergantung pada indikator statis."
        ),
        "rekomendasi": (
            "Prioritas penguatan meliputi penerapan solusi endpoint detection "
            "and response (EDR) yang mampu mendeteksi aktivitas abnormal, "
            "sandboxing untuk analisis berkas mencurigakan, pembaruan rutin "
            "sistem operasi dan aplikasi, serta pembatasan hak akses pengguna "
            "sesuai prinsip least privilege. Edukasi kepada pengguna mengenai "
            "teknik rekayasa sosial berbasis ClickFix dan serupa juga "
            "diperlukan untuk memutus rantai infeksi pada tahap awal."
        ),
    },
    "vulnerability": {
        "analisis": (
            "Kerentanan {cve_list} dengan skor CVSS tinggi menunjukkan bahwa "
            "celah keamanan pada perangkat lunak komersial tetap menjadi "
            "vektor serangan utama. Exploitasi di alam liar yang terjadi "
            "dalam hitungan hari setelah publikasi CVE menegaskan bahwa "
            "jendela waktu antara pengungkapan dan eksploitasi semakin "
            "pendek. Keterlambatan penerapan patch pada sistem yang terekspos "
            "internet dapat menimbulkan risiko kompromi yang signifikan."
        ),
        "rekomendasi": (
            "Manajemen patch harus diprioritaskan dengan pendekatan berbasis "
            "risiko, di mana kerentanan dengan exploit aktif dan eksposur "
            "publik ditangani lebih dulu. Untuk sistem yang belum dapat "
            "di-patch segera, perlu diterapkan kompensasi berupa virtual "
            "patching melalui web application firewall (WAF) atau aturan "
            "segmentasi jaringan. Pemantauan log akses dan indikator "
            "kompromi (IOC) terkait CVE tersebut juga harus diaktifkan untuk "
            "deteksi dini."
        ),
    },
    "data-breach": {
        "analisis": (
            "Insiden kebocoran data yang melibatkan {data_count} menunjukkan "
            "bahwa perlindungan data pribadi masih menjadi tantangan serius "
            "dalam ekosistem digital. Kebocoran tidak hanya berdampak pada "
            "kerugian finansial dan reputasi organisasi, tetapi juga "
            "membuka peluang penyalahgunaan data untuk penipuan, phishing "
            "bertarget, dan pencurian identitas. Dari perspektif regulasi, "
            "insiden semacam ini berpotensi melanggar ketentuan perlindungan "
            "data pribadi yang berlaku."
        ),
        "rekomendasi": (
            "Langkah penguatan meliputi enkripsi data sensitif baik saat "
            "disimpan maupun saat dikirim, penerapan kontrol akses berbasis "
            "peran (role-based access control), serta pemantauan aktivitas "
            "akses data yang tidak wajar. Organisasi juga perlu menyiapkan "
            "prosedur notifikasi insiden kepada pihak berwenang dan pemilik "
            "data sesuai ketentuan, sekaligus melakukan audit menyeluruh "
            "untuk mengidentifikasi akar penyebab kebocoran."
        ),
    },
    "phishing": {
        "analisis": (
            "Serangan phishing yang menargetkan {target} menunjukkan bahwa "
            "rekayasa sosial tetap menjadi teknik yang efektif karena "
            "mengeksploitasi faktor manusia, bukan kelemahan teknis semata. "
            "Pelaku memanfaatkan domain mirip, portal iklan palsu, dan "
            "halaman tiruan layanan populer untuk mencuri kredensial. "
            "Pemanfaatan layanan cloud dan AI generatif untuk membuat pesan "
            "phishing yang lebih meyakinkan turut meningkatkan tingkat "
            "keberhasilan serangan."
        ),
        "rekomendasi": (
            "Mitigasi perlu menyentuh tiga lapisan: manusia, proses, dan "
            "teknologi. Pada lapisan manusia, kampanye kesadaran keamanan "
            "harus dilakukan secara berkala dengan simulasi phishing. Pada "
            "lapisan proses, verifikasi berlapis untuk permintaan sensitif "
            "perlu diterapkan. Pada lapisan teknologi, penerapan autentikasi "
            "multifaktor berbasis token atau biometrik, penyaringan email "
            "gateway, dan pemantauan domain tiruan harus diaktifkan."
        ),
    },
    "apt": {
        "analisis": (
            "Aktivitas kelompok {aktor} menunjukkan bahwa ancaman tingkat "
            "lanjut (advanced persistent threat) tetap menjadi salah satu "
            "risiko strategis tertinggi. Kelompok APT umumnya beroperasi "
            "dengan dukungan negara (state-sponsored), memiliki sumber daya "
            "besar, dan menargetkan kepentingan strategis seperti "
            "infrastruktur kritis, data pemerintah, dan industri pertahanan. "
            "Karakteristik serangan yang diam-diam, bertahap, dan berjangka "
            "panjang membuat deteksi berbasis signature tidak cukup efektif."
        ),
        "rekomendasi": (
            "Penanganan APT memerlukan pendekatan threat-informed defense, "
            "yaitu dengan memahami taktik, teknik, dan prosedur (TTP) yang "
            "digunakan kelompok sasaran. Aktivitas threat hunting proaktif, "
            "berbagi informasi melalui platform threat intelligence, serta "
            "penguatan koordinasi antar lembaga menjadi kunci. Di tingkat "
            "teknis, deteksi berbasis anomali, monitoring lalu lintas "
            "keluar-masuk (egress filtering), dan pembatasan akses ke aset "
            "kritikal perlu diperkuat."
        ),
    },
    "cyber-attack": {
        "analisis": (
            "Serangan siber terhadap {target} menunjukkan bahwa vektor "
            "serangan tidak lagi terbatas pada sistem informasi utama, "
            "tetapi juga menyentuh perangkat operasional dan infrastruktur "
            "pendukung. Motif pelaku bervariasi dari finansial, ideologis, "
            "hingga geopolitik. Dampak serangan dapat bersifat langsung "
            "berupa gangguan layanan, maupun tidak langsung berupa kerugian "
            "reputasi dan kepercayaan publik."
        ),
        "rekomendasi": (
            "Penguatan pertahanan perlu mencakup pemetaan aset digital dan "
            "penilaian kerentanan secara berkala, penerapan arsitektur zero "
            "trust pada akses ke sistem penting, serta penyusunan rencana "
            "respons insiden yang teruji. Koordinasi dengan otoritas siber "
            "nasional dan berbagi informasi tentang indikator serangan "
            "dengan mitra sektor serupa dapat mempercepat deteksi dan "
            "mitigasi ancaman serupa."
        ),
    },
    "security-policy": {
        "analisis": (
            "Perkembangan kebijakan dan regulasi keamanan siber menunjukkan "
            "meningkatnya kesadaran akan pentingnya tata kelola keamanan "
            "informasi di tingkat nasional maupun sektoral. Kebijakan yang "
            "adaptif terhadap dinamika ancaman menjadi kebutuhan, terutama "
            "dalam menghadapi lanskap ancaman yang terus berubah. Implikasi "
            "kebijakan tidak hanya pada aspek kepatuhan, tetapi juga pada "
            "kesiapan sumber daya manusia dan infrastruktur pendukung."
        ),
        "rekomendasi": (
            "Organisasi perlu memastikan kesesuaian operasional dengan "
            "regulasi yang berlaku melalui pemetaan kontrol dan audit "
            "berkala. Peningkatan kapasitas SDM keamanan siber melalui "
            "pelatihan dan sertifikasi menjadi prioritas, diikuti dengan "
            "penguatan kolaborasi lintas sektor melalui forum berbagi "
            "informasi dan latihan bersama."
        ),
    },
    "lain-lain": {
        "analisis": (
            "Perkembangan keamanan siber pada periode ini menunjukkan bahwa "
            "ancaman siber terus menjadi perhatian utama dalam ekosistem "
            "digital. Insiden yang terjadi menggambarkan kompleksitas "
            "interaksi antara faktor teknis, manusia, dan kebijakan yang "
            "memengaruhi postur keamanan suatu organisasi maupun negara."
        ),
        "rekomendasi": (
            "Peningkatan kesadaran dan kesiapan menghadapi ancaman digital "
            "perlu dilakukan secara berkelanjutan, mulai dari penerapan "
            "prinsip dasar higiene siber, penguatan prosedur respons "
            "insiden, hingga peningkatan kolaborasi dengan pihak terkait."
        ),
    },
}


def _buat_catatan(article, sentences, entities):
    kategori = (article.get("category") or "lain-lain").lower()
    tpl = CATATAN_TEMPLATES.get(kategori, CATATAN_TEMPLATES["lain-lain"])

    # === Konteks spesifik ===
    target = _deteksi_target(article)
    cve_list = entities.get("cve", []) if entities else []
    malware_list = entities.get("malware", []) if entities else []
    aktor_list = entities.get("threat_actor", []) if entities else []

    # Data statistik
    cve_str = ", ".join(cve_list[:3]) if cve_list else "beberapa kerentanan"
    malware_str = ", ".join(malware_list[:2]) if malware_list else "malware terkait"
    aktor_str = aktor_list[0] if aktor_list else "kelompok ancaman terkait"

    # Hitung kuantitas dari judul
    import re as _re
    m = _re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{4,})\b", article.get("title") or "")
    data_count = m.group(1).replace(",", ".") if m else "sejumlah data"

    # === Para 1: KONTEKS ===
    para1 = (
        f"Insiden ini merupakan bagian dari dinamika ancaman siber yang "
        f"terus berkembang. Karakteristik serangan menunjukkan pola yang "
        f"perlu dicermati, terutama dari sisi teknik, target, dan dampak "
        f"yang ditimbulkan. "
    )

    # === Para 2: ANALISIS (dari template kategori) ===
    para2 = tpl["analisis"].format(
        target=target,
        cve_list=cve_str,
        malware_list=malware_str,
        aktor=aktor_str,
        data_count=data_count,
    )

    # === Para 3: REKOMENDASI (dari template kategori) ===
    para3 = tpl["rekomendasi"]

    # === Para 4: KETERLACAKAN & VERIFIKASI ===
    para4 = (
        "Seluruh informasi dalam laporan ini disusun berdasarkan sumber "
        "terbuka yang dapat ditelusuri, dengan setiap entitas teknis "
        "(CVE, malware, aktor) disertai bukti kalimat sumbernya pada basis "
        "data. Mengingat karakteristik sumber terbuka yang dapat berubah "
        "dan memerlukan validasi, informasi ini perlu diverifikasi lebih "
        "lanjut melalui koordinasi dengan pihak berwenang sebelum "
        "dijadikan dasar pengambilan keputusan strategis."
    )

    # Apply glossary ke semua paragraf
    return [
        _apply_glossary(para1),
        _apply_glossary(para2),
        _apply_glossary(para3),
        _apply_glossary(para4),
    ]


def _deteksi_target(article):
    """Ambil target spesifik dari judul."""
    judul = (article.get("title") or "").lower()
    TARGET_MAP = [
        ("idcf cloud", "layanan cloud IDCF Cloud"),
        ("wordpress", "platform WordPress"),
        ("netscaler", "perangkat NetScaler"),
        ("citrix", "sistem Citrix"),
        ("sonicwall", "perangkat SonicWall"),
        ("gitlab", "platform GitLab"),
        ("atlassian", "platform Atlassian"),
        ("microsoft", "sistem Microsoft"),
        ("apple", "perangkat Apple"),
        ("iphone", "perangkat iPhone"),
        ("google", "layanan Google"),
        ("azure", "layanan cloud Azure"),
        ("aws", "layanan cloud AWS"),
        ("bank", "sektor perbankan"),
        ("supermarket", "sektor ritel"),
        ("government", "instansi pemerintah"),
        ("hospital", "sektor kesehatan"),
    ]
    for key, val in TARGET_MAP:
        if key in judul:
            return val
    return "organisasi target"


# ============================================================
# Generate
# ============================================================
def generate_lapin(start_date, end_date, kepada=None, dari=None,
                   tembusan=None, nilai=None, hal=None,
                   kategori_filter=None, max_age_hours=None):
    kepada = kepada or config.DEFAULT_KEPADA
    dari = dari or config.DEFAULT_DARI
    tembusan = tembusan or config.DEFAULT_TEMBUSAN
    nilai = nilai or config.DEFAULT_NILAI

    article = fetch_main_article(
        start_date, end_date,
        kategori_filter=kategori_filter,
        max_age_hours=max_age_hours,
    )
    if not article:
        if kategori_filter:
            logger.warning(f"Tidak ada artikel kategori '{kategori_filter}' yang punya terjemahan.")
        else:
            logger.warning("Tidak ada artikel utama yang punya terjemahan.")
        return None
    
        # --- TAMBAHKAN LOGIKA TRANSLATE ON-DEMAND DI SINI ---
    if not article.get("content_id") and article.get("language") == "en":
        from nlp.translator import translate_to_id
        from storage.db import get_conn
        logger.info(f"Menerjemahkan artikel on-demand: {article['title'][:50]}...")
        translated_text = translate_to_id(article["content_raw"] or "")
        
        # Simpan ke DB agar tidak translate ulang
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE articles SET content_id = %s, translated_at = NOW() WHERE id = %s",
                (translated_text, article["id"])
            )
            conn.commit()
            cur.close()
        
        # Update variabel artikel di memori
        article["content_id"] = translated_text
    # ----------------------------------------------------

    entities = fetch_entities(article["id"])
    konten = article.get("content_id") or article.get("content_raw") or ""
    sentences = _extract_sentences(konten, max_count=6)
    if not sentences:
        logger.warning("Artikel tidak punya kalimat bermakna.")
        return None

    hal = hal or _buat_hal(article, entities)

    now = datetime.now()
    urut = get_next_nomor_urut()
    nomor = f"{config.NIT}/{config.KODE_LAPORAN}-{urut}/{_roman_month(now.month)}/{now.year}"

    # === DOKUMEN ===
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.5)
    sec.left_margin = Cm(3.0)
    sec.right_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5
    style.paragraph_format.space_after = Pt(6)
    rpr = style.element.get_or_add_rPr()
    rFonts = rpr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rpr.append(rFonts)
    rFonts.set(qn('w:ascii'), 'Arial')
    rFonts.set(qn('w:hAnsi'), 'Arial')
    rFonts.set(qn('w:cs'), 'Arial')

    # ============ LETTERHEAD ============
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.right_indent = Cm(7.5)
    r = p.add_run("BADAN INTELIJEN NEGARA")
    r.bold = True
    r.font.size = Pt(12)
    r.font.name = "Arial"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.right_indent = Cm(7.5)
    r = p.add_run("SEKOLAH TINGGI INTELIJEN NEGARA")
    r.bold = True
    r.font.size = Pt(12)
    r.font.name = "Arial"
    _add_bottom_border(p, sz=12)

    # Spacer
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.line_spacing = 1.0

    # ============ JUDUL ============
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run("LAPORAN INFORMASI")
    r.underline = True
    r.font.size = Pt(12)
    r.font.name = "Arial"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(16)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(f"Nomor: {nomor}")
    r.font.size = Pt(12)
    r.font.name = "Arial"

    # ============ METADATA ============
    _add_meta_line(doc, "Kepada", kepada)
    _add_meta_line(doc, "Dari", dari)
    _add_meta_line(doc, "Tembusan", tembusan)
    _add_meta_line(doc, "Hal", hal)
    _add_meta_line(doc, "Nilai", nilai)

    # ============ GARIS ATAS I. FAKTA-FAKTA ============
    _add_full_width_line(doc, space_before=10, space_after=12)

    # ============ I. FAKTA-FAKTA ============
    _add_heading(doc, "I. FAKTA-FAKTA")

    pembuka = doc.add_paragraph()
    pembuka.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pembuka.paragraph_format.space_after = Pt(10)
    pembuka.add_run(_buat_pembuka(article, sentences, hal=hal))

        # Poin 1, 2, 3, ... (mulai dari kalimat ke-3; 2 pertama sudah jadi lead pembuka)
    detail_sentences = sentences[:6]
    for i, sent in enumerate(detail_sentences, 1):
        if not sent.endswith("."):
            sent += "."
        sent = _apply_glossary(sent)
        sent = _netralisasi(sent)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.75)
        p.add_run(f"{i}.\t{sent}")
        
    # ============ II. CATATAN ============
    _add_heading(doc, "II. CATATAN")
    for par in _buat_catatan(article, sentences, entities):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(8)
        p.add_run(par)

    # ============ AUTENTIKASI ============
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("Autentikasi:")
    for _ in range(4):
        doc.add_paragraph()

    # Simpan
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"LAPIN_{ts}.docx"
    doc.save(out_path)
    logger.info(f"Laporan disimpan: {out_path}")

    _record_report(nomor, start_date, end_date, hal, 1, out_path)
    return out_path


def _record_report(report_code, start_date, end_date, title, total, path):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO reports
                  (report_code, period_start, period_end, title, total_articles, file_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (report_code, start_date, end_date, title, total, str(path)),
            )
            conn.commit()
            cur.close()
    except Exception as e:
        logger.warning(f"Gagal simpan ke tabel reports: {e}")


if __name__ == "__main__":
    end = date.today()
    start = end - timedelta(days=7)
    generate_lapin(start, end)