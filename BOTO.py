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
            InlineKeyboardButton("🍽️ Salon Ekle", callback_data="ekle_salon"),
        ],
        [
            InlineKeyboardButton("💵 Ödeme Yapıldı", callback_data="odeme_yap"),
            InlineKeyboardButton("📊 Rapor / Durum", callback_data="rapor"),
        ],
        [InlineKeyboardButton("📜 Son İşlemler", callback_data="son_islemler")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🥙 **VIP Döner Takip Botuna Hoş Geldin Reis!**\nAşağıdaki menüden işlemini seçebilirsin:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔ Yetkiniz yok.")
        return

    data = query.data

    if data == "ekle_paket":
        context.user_data["beklenen_islem"] = "paket_adet"
        await query.message.reply_text("📦 Kaç adet **PAKET** döner eklensin? (Sayı girin):", parse_mode="Markdown")
    elif data == "ekle_salon":
        context.user_data["beklenen_islem"] = "salon_adet"
        await query.message.reply_text("🍽️ Kaç adet **SALON** döner eklensin? (Sayı girin):", parse_mode="Markdown")
    elif data == "odeme_yap":
        context.user_data["beklenen_islem"] = "odeme_miktar"
        await query.message.reply_text("💵 Ne kadar **ÖDEME** yapıldı? (TL miktarını sayı olarak girin):", parse_mode="Markdown")
    elif data == "rapor":
        stats = get_stats()
        metin = (
            "📊 **DÖNER TAKİP RAPORU**\n\n"
            f"📦 **Paket Döner:** {stats['paket']} Adet ({stats['paket'] * PAKET_FIYAT} TL)\n"
            f"🍽️ **Salon Döner:** {stats['salon']} Adet ({stats['salon'] * SALON_FIYAT} TL)\n"
            f"-----------------------------------\n"
            f"💰 **Toplam Tutar:** {stats['tutar']} TL\n"
            f"✅ **Ödenen Miktar:** {stats['odenen']} TL\n"
            f"⚠️ **Kalan Borç:** {stats['borc']} TL"
        )
        await query.message.reply_text(metin, parse_mode="Markdown")
    elif data == "son_islemler":
        db = load_data()
        s_list = db["siparisler"][-5:]
        o_list = db["odemeler"][-5:]
        
        metin = "📜 **SON 5 SİPARİŞ:**\n"
        if not s_list:
            metin += "Henüz sipariş yok.\n"
        for s in reversed(s_list):
            metin += f"• {s['tarih']} - {s['adet']} Adet {s['tur'].upper()}\n"
            
        metin += "\n💵 **SON 5 ÖDEME:**\n"
        if not o_list:
            metin += "Henüz ödeme yok.\n"
        for o in reversed(o_list):
            metin += f"• {o['tarih']} - {o['miktar']} TL\n"
            
        await query.message.reply_text(metin)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    islem = context.user_data.get("beklenen_islem")
    if not islem:
        return

    text = update.message.text.strip()
    db = load_data()
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        sayi = int(text)
        if sayi <= 0:
            await update.message.reply_text("Lütfen 0'dan büyük bir sayı girin.")
            return

        if islem == "paket_adet":
            db["siparisler"].append({"tur": "paket", "adet": sayi, "tarih": simdi})
            save_data(db)
            await update.message.reply_text(f"✅ {sayi} adet **PAKET** döner kaydedildi!", parse_mode="Markdown")
        elif islem == "salon_adet":
            db["siparisler"].append({"tur": "salon", "adet": sayi, "tarih": simdi})
            save_data(db)
            await update.message.reply_text(f"✅ {sayi} adet **SALON** döner kaydedildi!", parse_mode="Markdown")
        elif islem == "odeme_miktar":
            db["odemeler"].append({"miktar": sayi, "tarih": simdi})
            save_data(db)
            await update.message.reply_text(f"✅ {sayi} TL **ÖDEME** kaydedildi!", parse_mode="Markdown")

        context.user_data["beklenen_islem"] = None
    except ValueError:
        await update.message.reply_text("⚠️ Lütfen sadece geçerli bir sayı girin!")

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
