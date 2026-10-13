from datetime import datetime
import json
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging ayarları
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
# ⚙️ BİLGİLERİN
# =========================================================
BOT_TOKEN = "8898839173:AAFS5DVcWsL5JOQdwrkWrPUu4JoaTrf_h4U"
ADMIN_USER_ID =7964555286# Kendi Telegram ID'n ile değiştir
# =========================================================

VERI_DOSYASI = "doner_veri.json"
PAKET_FIYAT = 140
SALON_FIYAT = 120


def varsayilan_veri_yukle():
    return {
        "aktif_gun": False,
        "kilo": 0.0,
        "paket_sayisi": 0,
        "salon_sayisi": 0,
        "eleman_sayisi": 0,
        "firin_gelen_adet": 0,
        "gecmis_gunler": {},
    }


def veri_oku():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return varsayilan_veri_yukle()


def veri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)


# Ana Menü / Canlı Panel Tasarımı
def ana_menu_keyboard(aktif_gun=False):
    if not aktif_gun:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("☀️ Gün Başı Yap (Kilo Gir)", callback_data="gun_basi")]]
        )

    keyboard = [
        [
            InlineKeyboardButton("🛵 Paket Ekle (+N)", callback_data="sec_paket_ekle"),
            InlineKeyboardButton("🍽️ Salon Ekle (+N)", callback_data="sec_salon_ekle"),
        ],
        [
            InlineKeyboardButton("👥 Eleman Yedi (+N)", callback_data="sec_eleman_ekle"),
            InlineKeyboardButton("🥖 Fırın Ekmek Ekle (Tane)", callback_data="sec_firin_ekle"),
        ],
        [
            InlineKeyboardButton("📊 Anlık Durum & Fırın Kontrolü", callback_data="anlik_durum"),
            InlineKeyboardButton("🌙 Gün Sonu Raporu", callback_data="gun_sonu"),
        ],
        [InlineKeyboardButton("📅 Haftalık Özet Rapor", callback_data="haftalik_rapor")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Üst Kısımda Anlık Listelenen Canlı Panel Metni
def panel_metni_olustur(veri, baslik="👑 **VIP DÖNER TAKİP PANELİ**"):
    if not veri["aktif_gun"]:
        return f"{baslik}\n\n🔴 **Durum:** Henüz gün başı yapılmadı.\n💡 Başlamak için aşağıdaki butona basın:"
    
    toplam_satis = veri["paket_sayisi"] + veri["salon_sayisi"]
    toplam_cikan = toplam_satis + veri["eleman_sayisi"]
    toplam_ciro = (veri["paket_sayisi"] * PAKET_FIYAT) + (veri["salon_sayisi"] * SALON_FIYAT)
    getirilen_ekmek = veri.get("firin_gelen_adet", 0)
    
    return (
        f"{baslik}\n\n"
        f"🟢 **Aktif Gün Et:** {veri['kilo']} kg\n"
        f"------------------------------\n"
        f"🛵 Paket Satış: **{veri['paket_sayisi']} Adet**\n"
        f"🍽️ Salon Satış: **{veri['salon_sayisi']} Adet**\n"
        f"👥 Eleman Yenen: **{veri['eleman_sayisi']} Adet**\n"
        f"🥖 Gelen Ekmek: **{getirilen_ekmek} Adet**\n"
        f"------------------------------\n"
        f"🌯 Toplam Çıkan Döner: **{toplam_cikan} Adet**\n"
        f"💰 Anlık Ciro: **{toplam_ciro} TL**"
    )


def yetkili_mi(user_id):
    if ADMIN_USER_ID == 123456789:
        return True
    return user_id == ADMIN_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not yetkili_mi(user.id):
        await update.message.reply_text("⚠️ Bu botu kullanma yetkiniz bulunmamaktadır.")
        return

    veri = veri_oku()
    metin = panel_metni_olustur(veri, f"👑 **VIP DÖNER TAKİP PANELİ**\nHoş geldiniz, {user.first_name} Usta! 🥙")
    markup = ana_menu_keyboard(veri["aktif_gun"])

    await update.message.reply_text(metin, parse_mode="Markdown", reply_markup=markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not yetkili_mi(user.id):
        await query.answer("Bu işlemi yapmaya yetkiniz yok!", show_alert=True)
        return

    await query.answer()
    data = query.data
    veri = veri_oku()

    if data == "gun_basi":
        context.user_data["beklenen_islem"] = "kilo_giris"
        await query.edit_message_text(
            "⚖️ **GÜN BAŞI İŞLEMİ**\n\nLütfen tezgaha takılan döner miktarını **kg** olarak yazıp gönderin (Örn: 15 veya 17.5):",
            parse_mode="Markdown",
        )

    elif data == "sec_paket_ekle":
        if not veri["aktif_gun"]:
            return
        context.user_data["beklenen_islem"] = "paket_ekle_adet"
        await query.edit_message_text("🛵 **PAKET DÖNER EKLEME**\n\nKaç adet paket döner ekleneceğini yazın (Örn: 4):", parse_mode="Markdown")

    elif data == "sec_salon_ekle":
        if not veri["aktif_gun"]:
            return
        context.user_data["beklenen_islem"] = "salon_ekle_adet"
        await query.edit_message_text("🍽️ **SALON DÖNER EKLEME**\n\nKaç adet salon döner ekleneceğini yazın (Örn: 3):", parse_mode="Markdown")

    elif data == "sec_eleman_ekle":
        if not veri["aktif_gun"]:
            return
        context.user_data["beklenen_islem"] = "eleman_ekle_adet"
        await query.edit_message_text("👥 **ELEMAN YENEN DÖNER EKLEME**\n\nKaç adet eleman yediğini yazın (Örn: 1):", parse_mode="Markdown")

    elif data == "sec_firin_ekle":
        if not veri["aktif_gun"]:
            return
        context.user_data["beklenen_islem"] = "firin_ekle_adet"
        await query.edit_message_text("🥖 **FIRIN EKMEK GİRİŞİ**\n\nFırıncının getirdiği ekmek miktarını **tane** yazın (Örn: 60):", parse_mode="Markdown")

    elif data == "anlik_durum":
        if not veri["aktif_gun"]:
            await query.edit_message_text("⚠️ Henüz açılmış aktif bir gün yok.", reply_markup=ana_menu_keyboard(False))
            return

        toplam_satis = veri["paket_sayisi"] + veri["salon_sayisi"]
        toplam_cikan = toplam_satis + veri["eleman_sayisi"]
        toplam_ciro = (veri["paket_sayisi"] * PAKET_FIYAT) + (veri["salon_sayisi"] * SALON_FIYAT)
        kilo = veri["kilo"]
        kilo_basi_doner = round(toplam_cikan / kilo, 2) if kilo > 0 else 0

        getirilen_ekmek = veri.get("firin_gelen_adet", 0)
        fark = getirilen_ekmek - toplam_cikan

        if getirilen_ekmek == 0:
            firin_durum_metni = "🥖 Henüz fırın ekmek girişi yapılmadı."
        elif fark > 0:
            firin_durum_metni = f"⚠️ Fırıncı **{fark} adet fazla** ekmek getirmiş."
        elif fark < 0:
            firin_durum_metni = f"🚨 Dikkat! Getirilen ekmek çıkan dönerden **{abs(fark)} adet eksik**!"
        else:
            firin_durum_metni = "✅ Fırıncının getirdiği ekmek ile çıkan döner tam uyuşuyor!"

        metin = (
            f"📊 **ANLIK DETAYLI DURUM & FIRIN KONTROLÜ**\n\n"
            f"⚖️ Takılan Et: **{kilo} kg**\n"
            f"🛵 Paket Satış: **{veri['paket_sayisi']} Adet**\n"
            f"🍽️ Salon Satış: **{veri['salon_sayisi']} Adet**\n"
            f"👥 Eleman Yenen: **{veri['eleman_sayisi']} Adet**\n"
            f"------------------------------\n"
            f"🌯 Toplam Çıkan Döner: **{toplam_cikan} Adet**\n"
            f"💰 Toplam Ciro: **{toplam_ciro} TL**\n\n"
            f"🥖 **FIRINCI KONTROL PANELİ:**\n"
            f"▪️ Gelen Toplam Ekmek: **{getirilen_ekmek} adet**\n"
            f"▪️ Durum Analizi: {firin_durum_metni}\n\n"
            f"📈 **VERİMLİLİK:** 1 kg etten **{kilo_basi_doner} adet** döner çıktı."
        )
        await query.edit_message_text(metin, parse_mode="Markdown", reply_markup=ana_menu_keyboard(True))

    elif data == "gun_sonu":
        if not veri["aktif_gun"]:
            return

        toplam
