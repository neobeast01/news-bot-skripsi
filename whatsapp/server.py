import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks
from dotenv import load_dotenv
from loguru import logger

# Import fungsi generator LAPIN kita
from tools.generate_lapin_tematik import generate_lapin_from_command

load_dotenv()

app = FastAPI()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
API_URL = f"https://graph.facebook.com/v20.0/{PHONE_ID}"

# ============================================================
# 1. Endpoint Verifikasi Webhook (Wajib untuk Meta)
# ============================================================
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ Webhook berhasil diverifikasi oleh Meta!")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning("❌ Verifikasi webhook gagal. Token tidak cocok.")
    return Response(status_code=403)

# ============================================================
# 2. Endpoint Menerima Pesan Masuk
# ============================================================
@app.post("/webhook")
async def receive_message(request: Request, bg_tasks: BackgroundTasks):
    # TAMBAHKAN LOG INI UNTUK MELIHAT APAKAH SERVER MENERIMA DATA
    logger.info("🔔 Ada tembakan masuk dari Meta/Ngrok!") 
    
    body = await request.json()
    
    # TAMBAHKAN LOG INI UNTUK MELIHAT ISI PESANNYA
    logger.debug(f"Isi payload: {body}") 

    if body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}
    # ... sisa kode ke bawah biarkan sama ...

# ============================================================
# 3. Fungsi Pemroses Perintah (Command)
# ============================================================
def process_command(sender_id: str, text: str):
    # 1. Kirim pesan konfirmasi ke pengirim
    send_text_message(sender_id, f"⏳ Memproses permintaan: *{text}*\nMohon tunggu sebentar...")
    
    # 2. Cek Command
    if text.startswith("/lapin"):
        parts = text.split()
        kategori = parts[1] if len(parts) > 1 else None
        
        # Panggil fungsi generator
        file_path = generate_lapin_from_command(kategori)
        
        if file_path and os.path.exists(file_path):
            send_text_message(sender_id, "✅ Laporan berhasil dibuat. Sedang mengirim dokumen...")
            send_document_message(sender_id, file_path)
        else:
            send_text_message(sender_id, "❌ Gagal membuat laporan. Pastikan data berita tersedia atau cek log sistem.")
    else:
        send_text_message(sender_id, "Perintah tidak dikenali.\n\n*Format Perintah:*\n/lapin\n/lapin [kategori]\n\n_Contoh:_\n/lapin ransomware\n/lapin malware")

# ============================================================
# 4. Helper: Kirim Pesan Teks
# ============================================================
def send_text_message(to: str, text: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    try:
        resp = requests.post(f"{API_URL}/messages", headers=headers, json=data)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Gagal kirim teks: {e}")

# ============================================================
# 5. Helper: Kirim Dokumen (Word)
# ============================================================
def send_document_message(to: str, file_path: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    # A. Upload Media
    upload_url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/media"
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            }
            data = {"messaging_product": "whatsapp"}
            resp = requests.post(upload_url, headers=headers, files=files, data=data).json()
        
        if "id" not in resp:
            logger.error(f"Gagal upload media: {resp}")
            send_text_message(to, "❌ Gagal mengunggah dokumen ke server WhatsApp.")
            return

        media_id = resp["id"]

        # B. Kirim Media
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": os.path.basename(file_path)
            }
        }
        send_resp = requests.post(f"{API_URL}/messages", headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}, json=data)
        logger.info(f"Status kirim dokumen: {send_resp.status_code}")
    except Exception as e:
        logger.error(f"Gagal kirim dokumen: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)