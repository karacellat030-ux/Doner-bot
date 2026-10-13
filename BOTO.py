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

PAKET_FIYAT = 140
SALON_FIYAT = 120

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "doner_data.json")

# ==========================================
# 📁 VERİ TABANI / KALICI DOSYA İŞLEMLERİ
# ==========================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": [], "gun_sonlari": [], "beklenen_islem": None}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "firin_ekmekleri" not in data:
                data["firin_ekmekleri"] = []
            if "siparisler" not in data:
                data["siparisler"] = []
            if "gun_baslangic" not in data:
                data["gun_baslangic"] = []
            if "gun_sonlari" not in data:
                data["gun_sonlari"] = []
            if "beklenen_islem" not in data:
                data["beklenen_islem"] = None
            return data
    except Exception as e:
        logger.error(f"Veri yükleme hatası: {e}")
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": [], "gun_sonlari": [], "beklenen_islem": None}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        logger.error(f"Veri kaydetme hatası: {e}")

# ==========================================
# 📊 HESAPLAMA & ANALİZ
# ==========================================
def get_stats():
    data = load_data()

    bugun_baslangic_doner = sum(g.get("adet", 0) for g in data.get("gun_baslangic", []))
    toplam_paket = sum(s.get("adet", 0) for s in data.get("siparisler", []) if s.get("tur") == "paket")
    toplam_salon = sum(s.get("adet", 0) for s in data.get("siparisler", []) if s.get("tur") == "salon")
    toplam_firin_ekmek = sum(f.get("adet", 0) for f in data.get("firin_ekmekleri", []))
    toplam_tutar = (toplam_paket * PAKET_FIYAT) + (toplam_salon * SALON_FIYAT)

    return {
        "bugun_baslangic_doner": bugun_baslangic_doner,
        "toplam_paket": toplam_paket,
        "toplam_salon": toplam_salon,
        "toplam_firin_ekmek": toplam_firin_ekmek,
        "toplam_tutar": toplam_tutar,
    }

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🥩 Güne Başlangıç Döner Ekle", callback_data="gun_baslangic_ekle"),
        ],
        [
            InlineKeyboardButton("📦 Paket Ekle (140 TL)", callback_data="ekle_paket"),
            InlineKeyboardButton("🍽️ Salon Ekle (120 TL)", callback_data="ekle_salon"),
        ],
        [
            InlineKeyboardButton("🥖 Fırın Ekmek Ekle", callback_data="firin_ekmek_ekle"),
            InlineKeyboardButton("📊 Anlık Durum Raporu", callback_data="rapor_genel"),
        ],
        [
            InlineKeyboardButton("🌙 Günü Kapat (Sıfırla)", callback_data="gunu_kapat_onay"),
            InlineKeyboardButton("📜 Tüm İşlem Logları", callback_data="son_islemler"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 🤖 BOT KOMUTLARI & MENÜ
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_data()
    db["beklenen_islem"] = None
    save_data(db)
    
    await update.message.reply_text(
        "🥙 **PREMIUM VIP DÖNER & EKMEK TAKİP BOTU**\n\n"
        "Aşağıdaki menüden güne başlangıç dönerini, satışları, fırından gelen ekmekleri takip edebilir veya günü kapatabilirsiniz:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    db = load_data()

    if data == "gun_baslangic_ekle":
        db["beklenen_islem"] = "gun_baslangic"
        save_data(db)
        await query.message.reply_text("🥩 Güne başlarken takılan döner miktarı kaç kg/adet? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "ekle_paket":
        db["beklenen_islem"] = "paket_adet"
        save_data(db)
        await query.message.reply_text("📦 Kaç adet **PAKET** satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "ekle_salon":
        db["beklenen_islem"] = "salon_adet"
        save_data(db)
        await query.message.reply_text("🍽️ Kaç adet **SALON** satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "firin_ekmek_ekle":
        db["beklenen_islem"] = "firin_ekmek"
        save_data(db)
        await query.message.reply_text("🥖 Fırından kaç adet **EKMEK** geldi? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "rapor_genel":
        db["beklenen_islem"] = None
        save_data(db)
        stats = get_stats()
        metin = (
            "📊 **
