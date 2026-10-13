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
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": [], "gun_sonlari": []}
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
            return data
    except Exception as e:
        logger.error(f"Veri yükleme hatası: {e}")
        return {"siparisler": [], "firin_ekmekleri": [], "gun_baslangic": [], "gun_sonlari": []}

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
            "📊 **ANLIK DÖNER & EKMEK TAKİP RAPORU**\n"
            "-----------------------------------\n"
            f"🥩 **Güne Başlayan Döner:** {stats['bugun_baslangic_doner']}\n"
            f"📦 **Satılan Paket:** {stats['toplam_paket']} Adet ({stats['toplam_paket'] * PAKET_FIYAT} TL)\n"
            f"🍽️ **Satılan Salon:** {stats['toplam_salon']} Adet ({stats['toplam_salon'] * SALON_FIYAT} TL)\n"
            f"💰 **Toplam Ciro:** {stats['toplam_tutar']} TL\n\n"
            f"🥖 **Gelen Fırın Ekmek:** {stats['toplam_firin_ekmek']} Adet"
        )
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif data == "gunu_kapat_onay":
        keyboard = [
            [
                InlineKeyboardButton("✅ Evet, Günü Kapat ve Sıfırla", callback_data="gunu_kapat_kesin"),
                InlineKeyboardButton("❌ İptal Et", callback_data="iptal"),
            ]
        ]
        await query.message.reply_text(
            "⚠️ **GÜNÜ KAPATMAK İSTEDİĞİNİZE EMİN MİSİNİZ?**\n\n"
            "Günün tüm satış ve ekmek sayaçları sıfırlanacak ve rapor olarak kaydedilecektir.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif data == "gunu_kapat_kesin":
        db = load_data()
        stats = get_stats()
        simdi = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Gün sonu özetini kaydet
        gun_raporu = {
            "tarih": simdi,
            "baslangic_doner": stats["bugun_baslangic_doner"],
            "paket": stats["toplam_paket"],
            "salon": stats["toplam_salon"],
            "firin_ekmek": stats["toplam_firin_ekmek"],
            "ciro": stats["toplam_tutar"]
        }
        db["gun_sonlari"].append(gun_raporu)

        # Aktif gün sayaçlarını temizle
        db["siparisler"] = []
        db["firin_ekmekleri"] = []
        db["gun_baslangic"] = []
        save_data(db)

        metin = (
            "🌙 **GÜN BAŞARIYLA KAPATILDI & SIFIRLANDI!**\n"
            "-----------------------------------\n"
            f"🕒 **Kapanış Tarihi:** `{simdi}`\n"
            f"🥩 **Takılan Döner:** {gun_raporu['baslangic_doner']}\n"
            f"📦 **Satılan Paket:** {gun_raporu['paket']} Adet\n"
            f"🍽️ **Satılan Salon:** {gun_raporu['salon']} Adet\n"
            f"🥖 **Gelen Ekmek:** {gun_raporu['firin_ekmek']} Adet\n"
            f"💰 **TOPLAM GÜNLÜK CİRO:** {gun_raporu['ciro']} TL\n\n"
            "✨ *Sayaçlar yeni gün için sıfırlandı. Hayırlı işler!*"
        )
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif data == "iptal":
        await query.message.reply_text("❌ İşlem iptal edildi.", reply_markup=get_main_keyboard())
    elif data == "son_islemler":
        db = load_data()
        gs_list = db.get("gun_sonlari", [])
        
        metin = "📜 **GEÇMİŞ GÜN SONU RAPORLARI:**\n\n"
        if not gs_list:
            metin += "Henüz kapatılmış gün kaydı yok.\n"
        for gs in reversed(gs_list[-10:]):
            metin += (
                f"📅 **[{gs['tarih']}]**\n"
                f"• Paket: {gs['paket']} | Salon: {gs['salon']} | Ekmek: {gs['firin_ekmek']}\n"
                f"• Ciro: {gs['ciro']} TL\n"
                f"-----------------------------------\n"
            )
            
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")

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
            
            bugun_toplam = sum(f.get("adet", 0) for f in db["firin_ekmekleri"])
            
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
