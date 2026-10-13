from datetime import datetime
import json
import logging
import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 🌐 RENDER KAPANMA ENGELLEYİCİ (FLASK)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "VIP Döner Takip Botu 7/24 Aktif!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==========================================
# ⚙️ LOGGING VE BOT BİLGİLERİ
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8898839173:AAFS5DVcWsL5JOQdwrkWrPUu4JoaTrf_h4U"
ADMIN_USER_ID = 7964555286

PAKET_FIYAT = 140
SALON_FIYAT = 120
DATA_FILE = "doner_data.json"

# ==========================================
# 📁 VERİ TABANI / DOSYA İŞLEMLERİ
# ==========================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"siparisler": [], "odemeler": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Veri yükleme hatası: {e}")
        return {"siparisler": [], "odemeler": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Veri kaydetme hatası: {e}")

# ==========================================
# 📊 HESAPLAMA FONKSİYONLARI
# ==========================================
def get_stats():
    data = load_data()
    toplam_paket = sum(s["adet"] for s in data["siparisler"] if s["tur"] == "paket")
    toplam_salon = sum(s["adet"] for s in data["siparisler"] if s["tur"] == "salon")
    toplam_odenen = sum(o["miktar"] for o in data["odemeler"])
    
    toplam_tutar = (toplam_paket * PAKET_FIYAT) + (toplam_salon * SALON_FIYAT)
    kalan_borc = toplam_tutar - toplam_odenen

    return {
        "paket": toplam_paket,
        "salon": toplam_salon,
        "tutar": toplam_tutar,
        "odenen": toplam_odenen,
        "borc": kalan_borc,
    }

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID

# ==========================================
# 🤖 BOT KOMUTLARI
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok.")
        return

    keyboard = [
        [
            InlineKeyboardButton("📦 Paket Ekle", callback_data="ekle_paket"),
            InlineKeyboardButton("🍽️ Salon Ekle", callback_data
