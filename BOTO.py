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
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "firin_ekmekleri" not in data:
                data["firin_ekmekleri"] = []
            if "siparisler" not in data:
                data["siparisler"] = []
            if "gun_baslangic" not in data:
                data["gun_baslangic"] = []
            return data
    except Exception as e:
        logger.error(f"Veri yükleme hatası: {e}")
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": []}

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
    now = datetime.now()
    bugun_str = now.strftime("%Y-%m-%d")

    bugun_baslangic_doner = sum(
        g.get("adet", 0) for g in data.get("gun_baslangic", [])
        if g.get("tarih", "").startswith(bugun_str)
    )

    toplam_paket = sum(s.get("adet", 0) for s in data.get("siparisler", []) if s.get("tur") == "paket")
    toplam_salon = sum(s.get("adet", 0) for s in data.get("siparisler", []) if s.get("tur") == "salon")

    bugun_firin_ekmek = sum(
        f.get("adet", 0) for f in data.get("firin_ekmekleri", []) 
        if f.get("tarih", "").startswith(bugun_str)
    )
    toplam_firin_ekmek = sum(f.get("adet", 0) for f in data.get("firin_ekmekleri", []))

    toplam_tutar = (toplam_paket * PAKET_FIYAT) + (toplam_salon * SALON_FIYAT)

    return {
        "bugun_baslangic_doner": bugun_baslangic_doner,
        "toplam_paket": toplam_paket,
        "toplam_salon": toplam_salon,
        "bugun_firin_ekmek": bugun_firin_ekmek,
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
            InlineKeyboardButton("📊 Günlük / Genel Durum", callback_data="rapor_genel"),
        ],
        [
            InlineKeyboardButton("📜 Tüm İşlem Logları", callback_data="son_islemler"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 🤖 BOT KOMUTLARI & MENÜ (HERKESE AÇIK)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥙 **PREMIUM VIP DÖNER & EKMEK TAKİP BOTU**\n\n"
        "Aşağıdaki menüden güne başlangıç dönerini, satışları ve fırından gelen ekmekleri takip edebilirsin:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "gun_baslangic_ekle":
        context.user_data["beklenen_islem"] = "gun_baslangic"
        await query.message.reply_text("🥩 Güne başlarken takılan döner miktarı kaç kg/adet? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "ekle_paket":
        context.user_data["beklenen_islem"] = "paket_adet"
        await query.message.reply_text("📦 Kaç adet **PAKET** satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "ekle_salon":
        context.user_data["beklenen_islem"] = "salon_adet"
        await query.message.reply_text("🍽️ Kaç adet **SALON** satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "firin_ekmek_ekle":
        context.user_data["beklenen_islem"] = "firin_ekmek"
        await query.message.reply_text("🥖 Fırından kaç adet **EKMEK** geldi? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "rapor_genel":
        stats = get_stats()
        metin = (
            "📊 **DÖNER & EKMEK TAKİP RAPORU**\n"
            "-----------------------------------\n"
            f"🥩 **Güne Başlayan Döner:** {stats['bugun_baslangic_doner']}\n"
            f"📦 **Toplam Paket Satış:** {stats['toplam_paket']} Adet\n"
            f"🍽️ **Toplam Salon Satış:** {stats['toplam_salon']} Adet\n"
            f"💰 **Toplam Ciro:** {stats['toplam_tutar']} TL\n\n"
            f"🥖 **Bugün Fırından Gelen Ekmek:** {stats['bugun_firin_ekmek']} Adet\n"
            f"🥖 **Toplam Fırın Ekmek (Genel):** {stats['toplam_firin_ekmek']} Adet"
        )
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif data == "son_islemler":
        db = load_data()
        gb_list = db.get("gun_baslangic", [])
        s_list = db.get("siparisler", [])
        f_list = db.get("firin_ekmekleri", [])
        
        metin = "📜 **İŞLEM GEÇMİŞİ (LOGLAR):**\n\n"
        
        metin += "🥩 **Güne Başlangıç Dönerleri:**\n"
        if not gb_list:
            metin += "• Kayıt yok.\n"
        for g in reversed(gb_list[-5:]):
            metin += f"• [{g['tarih']}] {g['adet']} Adet/Kg Takıldı\n"

        metin += "\n📦 **Satış Geçmişi:**\n"
        if not s_list:
            metin += "• Satış yok.\n"
        for s in reversed(s_list[-5:]):
            metin += f"• [{s['tarih']}] {s['adet']} Adet {s['tur'].upper()} ({s['adet'] * (PAKET_FIYAT if s['tur'] == 'paket' else SALON_FIYAT)} TL)\n"
            
        metin += "\n🥖 **Fırın Ekmekleri:**\n"
        if not f_list:
            metin += "• Ekmek yok.\n"
        for f in reversed(f_list[-5:]):
            metin += f"• [{f['tarih']}] {f['adet']} Adet Ekmek Geldi\n"
            
        await query.message.reply_text(metin, reply_markup=get_main_keyboard())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    islem = context.user_data.get("beklenen_islem")
    if not islem:
        return

    text = update.message.text.strip()
    db = load_data()
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        sayi = int(text)
        if sayi <= 0:
            await update.message.reply_text("Lütfen 0'dan büyük geçerli bir sayı girin.")
            return

        if islem == "gun_baslangic":
            db["gun_baslangic"].append({"adet": sayi, "tarih": simdi})
            save_data(db)
            await update.message.reply_text(
                f"✅ **GÜNE BAŞLANGIÇ DÖNERİ EKLENDİ!**\n\n"
                f"🥩 Miktar: **{sayi}**\n"
                f"🕒 Saat: `{simdi}`",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        elif islem == "paket_adet":
            db["siparisler"].append({"tur": "paket", "adet": sayi, "tarih": simdi})
            save_data(db)
            tutar = sayi * PAKET_FIYAT
            await update.message.reply_text(
                f"✅ **PAKET SATIŞI EKLENDİ!**\n\n"
                f"📦 Adet: **{sayi}**\n"
                f"💰 Tutar: **{tutar} TL**\n"
                f"🕒 Saat: `{simdi}`",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        elif islem == "salon_adet":
            db["siparisler"].append({"tur": "salon", "adet": sayi, "tarih": simdi})
            save_data(db)
            tutar = sayi * SALON_FIYAT
            await update.message.reply_text(
                f"✅ **SALON SATIŞI EKLENDİ!**\n\n"
                f"🍽️ Adet: **{sayi}**\n"
                f"💰 Tutar: **{tutar} TL**\n"
                f"🕒 Saat: `{simdi}`",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        elif islem == "firin_ekmek":
            db["firin_ekmekleri"].append({"adet": sayi, "tarih": simdi})
            save_data(db)
            
            bugun_str = datetime.now().strftime("%Y-%m-%d")
            bugun_toplam = sum(
                f.get("adet", 0) for f in db["firin_ekmekleri"] 
                if f.get("tarih", "").startswith(bugun_str)
            )
            
            await update.message.reply_text(
                f"🥖 **FIRINDAN EKMEK EKLENDİ!**\n\n"
                f"➕ Gelen: **{sayi} Adet**\n"
                f"📅 **Bugün Gelen Toplam Ekmek:** **{bugun_toplam} Adet**\n"
                f"🕒 Saat: `{simdi}`",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )

        context.user_data["beklenen_islem"] = None
    except ValueError:
        await update.message.reply_text("⚠️ Lütfen sadece sayısal bir değer girin!")

# ==========================================
# 🚀 ANA ÇALIŞTIRMA BLOĞU
# ==========================================
def main():
    keep_alive()
    logger.info("Flask arka plan web sunucusu başlatıldı.")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot başlatılıyor...")
    application.run_polling()

if __name__ == "__main__":
    main()
