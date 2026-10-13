from datetime import datetime, timedelta
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
# 📁 VERİ TABANI / KALICI LOG İŞLEMLERİ
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

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID

# ==========================================
# 📊 HESAPLAMA & HAFTALIK LOG ANALİZİ
# ==========================================
def get_stats():
    data = load_data()
    now = datetime.now()
    bugun_baslangic = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hafta_baslangic = bugun_baslangic - timedelta(days=bugun_baslangic.weekday())

    toplam_paket = 0
    toplam_salon = 0
    hafta_paket = 0
    hafta_salon = 0

    for s in data.get("siparisler", []):
        adet = s.get("adet", 0)
        tur = s.get("tur")
        tarih_str = s.get("tarih")
        
        try:
            s_tarih = datetime.strptime(tarih_str, "%Y-%m-%d %H:%M")
        except Exception:
            s_tarih = now

        if tur == "paket":
            toplam_paket += adet
            if s_tarih >= hafta_baslangic:
                hafta_paket += adet
        elif tur == "salon":
            toplam_salon += adet
            if s_tarih >= hafta_baslangic:
                hafta_salon += adet

    toplam_odenen = sum(o.get("miktar", 0) for o in data.get("odemeler", []))
    toplam_tutar = (toplam_paket * PAKET_FIYAT) + (toplam_salon * SALON_FIYAT)
    kalan_borc = toplam_tutar - toplam_odenen

    hafta_tutar = (hafta_paket * PAKET_FIYAT) + (hafta_salon * SALON_FIYAT)

    return {
        "toplam_paket": toplam_paket,
        "toplam_salon": toplam_salon,
        "toplam_döner": toplam_paket + toplam_salon,
        "hafta_paket": hafta_paket,
        "hafta_salon": hafta_salon,
        "hafta_döner": hafta_paket + hafta_salon,
        "hafta_tutar": hafta_tutar,
        "toplam_tutar": toplam_tutar,
        "toplam_odenen": toplam_odenen,
        "kalan_borc": kalan_borc,
    }

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📦 Paket Ekle (140 TL)", callback_data="ekle_paket"),
            InlineKeyboardButton("🍽️ Salon Ekle (120 TL)", callback_data="ekle_salon"),
        ],
        [
            InlineKeyboardButton("💵 Ödeme Alındı", callback_data="odeme_yap"),
            InlineKeyboardButton("📅 Bu Haftanın Raporu", callback_data="rapor_hafta"),
        ],
        [
            InlineKeyboardButton("📊 Genel Durum / Borç", callback_data="rapor_genel"),
            InlineKeyboardButton("📜 Tüm Log Geçmişi", callback_data="son_islemler"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 🤖 BOT KOMUTLARI & MENÜ
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu botu kullanma yetkiniz yok.")
        return

    await update.message.reply_text(
        "🥙 **PREMIUM VIP DÖNER TAKİP BOTU**\n\n"
        "Aşağıdaki menüden ekmek/döner siparişi ekleyebilir, bu haftalık veya genel satış raporlarını ve silinmeyen işlem loglarını inceleyebilirsiniz:",
        reply_markup=get_main_keyboard(),
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
        await query.message.reply_text("📦 Kaç adet **PAKET** döner/ekmek satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "ekle_salon":
        context.user_data["beklenen_islem"] = "salon_adet"
        await query.message.reply_text("🍽️ Kaç adet **SALON** döner/ekmek satıldı? (Sadece sayı girin):", parse_mode="Markdown")
    elif data == "odeme_yap":
        context.user_data["beklenen_islem"] = "odeme_miktar"
        await query.message.reply_text("💵 Ne kadar **ÖDEME** alındı? (TL miktarını sayı olarak girin):", parse_mode="Markdown")
    elif data == "rapor_hafta":
        stats = get_stats()
        metin = (
            "📅 **BU HAFTANIN DÖNER / EKMEK SATIŞ RAPORU**\n"
            "-----------------------------------\n"
            f"📦 **Paket Satış:** {stats['hafta_paket']} Adet ({stats['hafta_paket'] * PAKET_FIYAT} TL)\n"
            f"🍽️ **Salon Satış:** {stats['hafta_salon']} Adet ({stats['hafta_salon'] * SALON_FIYAT} TL)\n"
            f"🥖 **Haftalık Toplam Ekmek/Döner:** {stats['hafta_döner']} Adet\n"
            f"💰 **Haftalık Toplam Ciro:** {stats['hafta_tutar']} TL"
        )
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif data == "rapor_genel":
        stats = get_stats()
        metin = (
            "📊 **GENEL HESAP & BORÇ DURUMU**\n"
            "-----------------------------------\n"
            f"📦 **Toplam Paket:** {stats['toplam_paket']} Adet\n"
            f"🍽️ **Toplam Salon:** {stats['toplam_salon']} Adet\n"
            f"🥖 **Toplam Satılan Ekmek:** {stats['toplam_döner']} Adet\n"
            f"💵 **Toplam Hesap Tutar:** {stats['toplam_tutar']} TL\n"
            f"✅ **Alınan Toplam Ödeme:** {stats['toplam_odenen']} TL\n"
            f"⚠️ **Kalan Borç / Bakiye:** {stats['kalan_borc']} TL"
        )
        await query.message.reply_text(metin, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif data == "son_islemler":
        db = load_data()
        s_list = db.get("siparisler", [])
        o_list = db.get("odemeler", [])
        
        metin = "📜 **TÜM SİPARİŞ GEÇMİŞİ (LOGLAR):**\n"
        if not s_list:
            metin += "Henüz sipariş kaydı yok.\n"
        for s in reversed(s_list):
            metin += f"• [{s['tarih']}] {s['adet']} Adet {s['tur'].upper()} ({s['adet'] * (PAKET_FIYAT if s['tur'] == 'paket' else SALON_FIYAT)} TL)\n"
            
        metin += "\n💵 **TÜM ÖDEME GEÇMİŞİ (LOGLAR):**\n"
        if not o_list:
            metin += "Henüz ödeme kaydı yok.\n"
        for o in reversed(o_list):
            metin += f"• [{o['tarih']}] {o['miktar']} TL Ödeme\n"
            
        await query.message.reply_text(metin, reply_markup=get_main_keyboard())

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
            await update.message.reply_text("Lütfen 0'dan büyük geçerli bir sayı girin.")
            return

        if islem == "paket_adet":
            yeni_kayit = {"tur": "paket", "adet": sayi, "tarih": simdi}
            db["siparisler"].append(yeni_kayit)
            save_data(db)
            tutar = sayi * PAKET_FIYAT
            await update.message.reply_text(
                f"✅ **YENİ EKLEME BAŞARILI!**\n\n"
                f"📦 Tür: **PAKET**\n"
                f"🔢 Adet / Ekmek: **{sayi}**\n"
                f"💰 Tutar: **{tutar} TL**\n"
                f"🕒 Tarih: `{simdi}`\n\n"
                f"*(Bu işlem kalıcı loglara eklendi)*",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        elif islem == "salon_adet":
            yeni_kayit = {"tur": "salon", "adet": sayi, "tarih": simdi}
            db["siparisler"].append(yeni_kayit)
            save_data(db)
            tutar = sayi * SALON_FIYAT
            await update.message.reply_text(
                f"✅ **YENİ EKLEME BAŞARILI!**\n\n"
                f"🍽️ Tür: **SALON**\n"
                f"🔢 Adet / Ekmek: **{sayi}**\n"
                f"💰 Tutar: **{tutar} TL**\n"
                f"🕒 Tarih: `{simdi}`\n\n"
                f"*(Bu işlem kalıcı loglara eklendi)*",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        elif islem == "odeme_miktar":
            yeni_odeme = {"miktar": sayi, "tarih": simdi}
            db["odemeler"].append(yeni_odeme)
            save_data(db)
            await update.message.reply_text(
                f"✅ **ÖDEME BAŞARIYLA KAYDEDİLDİ!**\n\n"
                f"💵 Miktar: **{sayi} TL**\n"
                f"🕒 Tarih: `{simdi}`",
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
