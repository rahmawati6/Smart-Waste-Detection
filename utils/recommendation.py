from utils.waste_catalog import get_item

CONDITION_PENALTY = {
    "Baik": 0,
    "Sedang": 0,
    "Rusak": 1,
    "Sangat rusak": 2,
}


def build_recommendation(category: str, condition: str, item_key: str | None = None) -> dict:
    """Tentukan potensi dan rekomendasi pengolahan otomatis."""
    item = get_item(item_key, category)
    base_potential = item.recycle_potential if item else "Tidak Layak"

    if condition == "Sangat rusak":
        return {
            "potential": "Tidak Layak",
            "action": "Tidak layak olah",
            "message": "Sampah ini tidak layak dijual dan perlu penanganan khusus.",
        }

    if condition == "Rusak" and base_potential == "Layak Dijual":
        base_potential = "Layak Daur Ulang"

    if base_potential == "Layak Dijual":
        return {
            "potential": "Layak Dijual",
            "action": "Daur ulang / Dijual",
            "message": "Sampah ini direkomendasikan untuk didaur ulang atau dijual karena masih memiliki nilai ekonomi.",
        }
    if base_potential == "Layak Daur Ulang":
        return {
            "potential": "Layak Daur Ulang",
            "action": "Daur ulang setelah dipilah",
            "message": "Sampah ini masih dapat dimanfaatkan, tetapi perlu dipilah dan dibersihkan terlebih dahulu.",
        }
    if base_potential == "Diproses Menjadi Energi":
        return {
            "potential": "Diproses Menjadi Energi",
            "action": "Diproses menjadi energi",
            "message": "Sampah ini kurang layak dijual, namun dapat diproses menjadi energi atau pengolahan lanjutan.",
        }
    return {
        "potential": "Tidak Layak",
        "action": "Tidak layak olah",
        "message": "Sampah ini tidak layak dijual dan perlu penanganan khusus.",
    }
