from utils.waste_catalog import ITEM_BY_KEY, get_item


PRICE_PER_KG = {item.item_name: item.price_per_kg for item in ITEM_BY_KEY.values()}

CONDITION_FACTOR = {
    "Baik": 1.0,
    "Sedang": 0.75,
    "Rusak": 0.5,
    "Sangat rusak": 0.25,
}


def calculate_economic_value(category: str, condition: str, weight: float, item_key: str | None = None) -> dict:
    """Hitung nilai ekonomi berdasarkan berat, jenis sampah, dan kondisi."""
    safe_weight = max(float(weight or 0), 0)
    item = get_item(item_key, category)
    price = item.price_per_kg if item else 300
    factor = CONDITION_FACTOR.get(condition, 0.5)
    value = safe_weight * price * factor
    return {
        "price_per_kg": price,
        "condition_factor": factor,
        "economic_value": round(value, 2),
    }
