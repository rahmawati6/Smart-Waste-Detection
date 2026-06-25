from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class WasteItem:
    item_key: str
    item_name: str
    category: str
    price_per_kg: int
    recycle_potential: str
    recycle_type: str
    min_images_required: int = 50


WASTE_ITEMS: list[WasteItem] = [
    # Plastik
    WasteItem("botol_air_mineral", "Botol Air Mineral", "Plastik", 3500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("botol_plastik", "Botol Plastik", "Plastik", 3000, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("gelas_plastik", "Gelas Plastik", "Plastik", 2500, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("kantong_plastik", "Kantong Plastik", "Plastik", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("plastik_kresek", "Plastik Kresek", "Plastik", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("sedotan_plastik", "Sedotan Plastik", "Plastik", 800, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("bungkus_snack", "Bungkus Snack", "Plastik", 700, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("kemasan_mi_instan", "Kemasan Mi Instan", "Plastik", 900, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("styrofoam", "Styrofoam", "Plastik", 500, "Tidak Layak", "Tidak layak olah"),
    WasteItem("tutup_botol_plastik", "Tutup Botol Plastik", "Plastik", 2500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("botol_shampoo", "Botol Shampoo", "Plastik", 2800, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("botol_sabun", "Botol Sabun", "Plastik", 2800, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("ember_plastik", "Ember Plastik", "Plastik", 2200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("jerigen_plastik", "Jerigen Plastik", "Plastik", 3200, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("sachet_kopi", "Sachet Kopi", "Plastik", 700, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("sachet_sampo", "Sachet Sampo", "Plastik", 700, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("wadah_makanan_plastik", "Wadah Makanan Plastik", "Plastik", 1800, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("mainan_plastik", "Mainan Plastik", "Plastik", 1500, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    # Kertas
    WasteItem("kardus", "Kardus", "Kertas", 2200, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("koran", "Koran", "Kertas", 1800, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("majalah", "Majalah", "Kertas", 1700, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("kertas_hvs", "Kertas HVS", "Kertas", 2000, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("buku_bekas", "Buku Bekas", "Kertas", 1900, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("karton", "Karton", "Kertas", 2100, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("dus_makanan", "Dus Makanan", "Kertas", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("paper_bag", "Paper Bag", "Kertas", 1600, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("kertas_nasi", "Kertas Nasi", "Kertas", 400, "Tidak Layak", "Tidak layak olah"),
    WasteItem("struk_belanja", "Struk Belanja", "Kertas", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("amplop_bekas", "Amplop Bekas", "Kertas", 1500, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("kotak_susu_karton", "Kotak Susu Karton", "Kertas", 1000, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    # Logam
    WasteItem("kaleng_minuman", "Kaleng Minuman", "Logam", 9000, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("kaleng_makanan", "Kaleng Makanan", "Logam", 7500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("kaleng_cat", "Kaleng Cat", "Logam", 4500, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("tutup_botol_logam", "Tutup Botol Logam", "Logam", 5500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("besi_tua", "Besi Tua", "Logam", 5000, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("aluminium", "Aluminium", "Logam", 11000, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("paku_berkarat", "Paku Berkarat", "Logam", 2500, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("sendok_logam", "Sendok Logam", "Logam", 6500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("garpu_logam", "Garpu Logam", "Logam", 6500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("wajan_rusak", "Wajan Rusak", "Logam", 5500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("panci_rusak", "Panci Rusak", "Logam", 5500, "Layak Dijual", "Daur ulang / Dijual"),
    WasteItem("rangka_payung", "Rangka Payung", "Logam", 3000, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    # Kaca
    WasteItem("botol_kaca", "Botol Kaca", "Kaca", 1500, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("botol_sirup", "Botol Sirup", "Kaca", 1800, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("gelas_kaca", "Gelas Kaca", "Kaca", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("pecahan_kaca", "Pecahan Kaca", "Kaca", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("toples_kaca", "Toples Kaca", "Kaca", 1600, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("cermin_pecah", "Cermin Pecah", "Kaca", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("lampu_pijar", "Lampu Pijar", "Kaca", 200, "Tidak Layak", "Tidak layak olah"),
    WasteItem("lampu_neon", "Lampu Neon", "Kaca", 200, "Tidak Layak", "Tidak layak olah"),
    WasteItem("piring_kaca", "Piring Kaca", "Kaca", 1000, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("vas_kaca", "Vas Kaca", "Kaca", 1300, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    # Organik
    WasteItem("kulit_pisang", "Kulit Pisang", "Organik", 300, "Tidak Layak", "Kompos"),
    WasteItem("kulit_jeruk", "Kulit Jeruk", "Organik", 300, "Tidak Layak", "Kompos"),
    WasteItem("sisa_makanan", "Sisa Makanan", "Organik", 250, "Tidak Layak", "Kompos"),
    WasteItem("daun_kering", "Daun Kering", "Organik", 400, "Layak Daur Ulang", "Kompos"),
    WasteItem("sayuran_busuk", "Sayuran Busuk", "Organik", 250, "Tidak Layak", "Kompos"),
    WasteItem("buah_busuk", "Buah Busuk", "Organik", 250, "Tidak Layak", "Kompos"),
    WasteItem("ampas_kopi", "Ampas Kopi", "Organik", 500, "Layak Daur Ulang", "Kompos"),
    WasteItem("teh_celup", "Teh Celup", "Organik", 250, "Tidak Layak", "Kompos"),
    WasteItem("cangkang_telur", "Cangkang Telur", "Organik", 350, "Layak Daur Ulang", "Kompos"),
    WasteItem("tulang_ikan", "Tulang Ikan", "Organik", 200, "Tidak Layak", "Kompos"),
    # Elektronik
    WasteItem("kabel_usb", "Kabel USB", "Elektronik", 9000, "Layak Dijual", "Daur ulang elektronik"),
    WasteItem("charger_rusak", "Charger Rusak", "Elektronik", 7000, "Layak Dijual", "Daur ulang elektronik"),
    WasteItem("baterai", "Baterai", "Elektronik", 1000, "Tidak Layak", "Limbah B3"),
    WasteItem("remote_tv", "Remote TV", "Elektronik", 5000, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("mouse_rusak", "Mouse Rusak", "Elektronik", 6000, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("keyboard_rusak", "Keyboard Rusak", "Elektronik", 6500, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("pcb", "PCB", "Elektronik", 12000, "Layak Dijual", "Daur ulang elektronik"),
    WasteItem("handphone_rusak", "Handphone Rusak", "Elektronik", 15000, "Layak Dijual", "Daur ulang elektronik"),
    WasteItem("headset_rusak", "Headset Rusak", "Elektronik", 3500, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("speaker_rusak", "Speaker Rusak", "Elektronik", 6000, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("powerbank_rusak", "Powerbank Rusak", "Elektronik", 8000, "Layak Daur Ulang", "Daur ulang elektronik"),
    WasteItem("lampu_led", "Lampu LED", "Elektronik", 1000, "Tidak Layak", "Limbah elektronik"),
    # Karet/Kain
    WasteItem("ban_bekas", "Ban Bekas", "Karet/Kain", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("sandal_rusak", "Sandal Rusak", "Karet/Kain", 800, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("sepatu_rusak", "Sepatu Rusak", "Karet/Kain", 900, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("sepatu_bekas", "Sepatu Bekas", "Karet/Kain", 1000, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("baju_bekas", "Baju Bekas", "Karet/Kain", 1200, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("kain_perca", "Kain Perca", "Karet/Kain", 1000, "Layak Daur Ulang", "Daur ulang setelah dipilah"),
    WasteItem("tas_rusak", "Tas Rusak", "Karet/Kain", 900, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("sarung_tangan_karet", "Sarung Tangan Karet", "Karet/Kain", 600, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    WasteItem("masker_kain", "Masker Kain", "Karet/Kain", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("karpet_rusak", "Karpet Rusak", "Karet/Kain", 800, "Diproses Menjadi Energi", "Diproses menjadi energi"),
    # Campuran
    WasteItem("sampah_rumah_tangga", "Sampah Rumah Tangga", "Campuran", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("sampah_pasar", "Sampah Pasar", "Campuran", 300, "Tidak Layak", "Tidak layak olah"),
    WasteItem("sampah_jalanan", "Sampah Jalanan", "Campuran", 200, "Tidak Layak", "Tidak layak olah"),
    WasteItem("sampah_tidak_terpilah", "Sampah Tidak Terpilah", "Campuran", 150, "Tidak Layak", "Tidak layak olah"),
    WasteItem("popok_bekas", "Popok Bekas", "Campuran", 100, "Tidak Layak", "Tidak layak olah"),
    WasteItem("tisu_bekas", "Tisu Bekas", "Campuran", 100, "Tidak Layak", "Tidak layak olah"),
]

ITEM_BY_KEY = {item.item_key: item for item in WASTE_ITEMS}
ITEM_BY_NAME = {item.item_name.lower(): item for item in WASTE_ITEMS}

CATEGORY_GROUPS: dict[str, list[WasteItem]] = defaultdict(list)
for waste_item in WASTE_ITEMS:
    CATEGORY_GROUPS[waste_item.category].append(waste_item)
CATEGORY_GROUPS = dict(CATEGORY_GROUPS)

MAIN_CATEGORIES = list(CATEGORY_GROUPS.keys())
ITEM_KEYS = [item.item_key for item in WASTE_ITEMS]


def normalize_label(value: str | None) -> str:
    return (value or "").lower().strip().replace("-", "_").replace(" ", "_")


def get_item(item_key: str | None = None, item_name: str | None = None) -> WasteItem | None:
    if item_key and item_key in ITEM_BY_KEY:
        return ITEM_BY_KEY[item_key]
    if item_name and item_name.lower() in ITEM_BY_NAME:
        return ITEM_BY_NAME[item_name.lower()]
    normalized = normalize_label(item_name or item_key)
    return ITEM_BY_KEY.get(normalized)


def default_item_for_category(category: str | None) -> WasteItem:
    category = category or "Campuran"
    for item in WASTE_ITEMS:
        if item.category.lower() == category.lower():
            return item
    return ITEM_BY_KEY["sampah_tidak_terpilah"]


def as_db_rows() -> list[dict]:
    return [
        {
            "item_key": item.item_key,
            "item_name": item.item_name,
            "category": item.category,
            "price_per_kg": item.price_per_kg,
            "recycle_potential": item.recycle_potential,
            "recycle_type": item.recycle_type,
            "min_images_required": item.min_images_required,
        }
        for item in WASTE_ITEMS
    ]
