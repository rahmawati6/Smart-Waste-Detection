from __future__ import annotations

from datetime import datetime, timedelta

try:
    from database import MYSQL_DATABASE, connect, init_db
    from waste_catalog import get_item
except ImportError:
    from utils.database import MYSQL_DATABASE, connect, init_db
    from utils.waste_catalog import get_item


DEMO_ROWS = [
    ("static/img/logo-badge.png", "Botol Plastik", "Baik", "Layak Dijual", 0.30, 9000, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Kardus", "Sedang", "Layak Daur Ulang", 0.50, 3000, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kaleng Minuman", "Baik", "Layak Dijual", 0.20, 12000, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Botol Kaca", "Rusak", "Diproses Menjadi Energi", 0.40, 750, "Diproses menjadi energi"),
    ("static/img/logo-badge.png", "Sisa Makanan", "Sedang", "Tidak Layak", 0.60, 250, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Baju Bekas", "Baik", "Layak Daur Ulang", 0.70, 2500, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kabel USB", "Rusak", "Diproses Menjadi Energi", 0.25, 5000, "Diproses menjadi energi"),
    ("static/img/logo-badge.png", "Sampah Campuran", "Rusak", "Tidak Layak", 0.80, 100, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Botol Plastik", "Baik", "Layak Dijual", 0.35, 10500, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Kardus", "Baik", "Layak Daur Ulang", 0.45, 3600, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kaleng Minuman", "Sedang", "Layak Dijual", 0.18, 9500, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Botol Kaca", "Baik", "Layak Daur Ulang", 0.55, 1800, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Sisa Makanan", "Baik", "Tidak Layak", 0.65, 300, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Baju Bekas", "Sedang", "Layak Daur Ulang", 0.75, 2200, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kabel USB", "Sedang", "Diproses Menjadi Energi", 0.28, 4600, "Diproses menjadi energi"),
    ("static/img/logo-badge.png", "Sampah Campuran", "Sedang", "Tidak Layak", 0.72, 120, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Botol Plastik", "Sedang", "Layak Daur Ulang", 0.32, 7200, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kardus", "Baik", "Layak Dijual", 0.62, 5200, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Kaleng Minuman", "Baik", "Layak Dijual", 0.22, 13200, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Botol Kaca", "Sedang", "Layak Daur Ulang", 0.48, 1400, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Sisa Makanan", "Rusak", "Tidak Layak", 0.58, 150, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Baju Bekas", "Rusak", "Diproses Menjadi Energi", 0.66, 900, "Diproses menjadi energi"),
    ("static/img/logo-badge.png", "Kabel USB", "Baik", "Layak Dijual", 0.30, 7800, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Sampah Campuran", "Baik", "Layak Daur Ulang", 0.70, 650, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Botol Plastik", "Baik", "Layak Dijual", 0.27, 8100, "Daur ulang / Dijual"),
    ("static/img/logo-badge.png", "Kardus", "Sedang", "Layak Daur Ulang", 0.52, 3100, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Kaleng Minuman", "Rusak", "Diproses Menjadi Energi", 0.19, 6200, "Diproses menjadi energi"),
    ("static/img/logo-badge.png", "Botol Kaca", "Baik", "Layak Daur Ulang", 0.51, 1700, "Daur ulang setelah dipilah"),
    ("static/img/logo-badge.png", "Sisa Makanan", "Sedang", "Tidak Layak", 0.74, 200, "Tidak layak olah"),
    ("static/img/logo-badge.png", "Sampah Campuran", "Rusak", "Tidak Layak", 0.88, 80, "Tidak layak olah"),
]


def main() -> None:
    init_db()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM analysis_results")
            current_total = int(cursor.fetchone()["total"] or 0)
            if current_total >= 30:
                print(f"Database {MYSQL_DATABASE}.analysis_results sudah berisi {current_total} data. Seed dilewati.")
                return

            now = datetime.now()
            rows = []
            for index, row in enumerate(DEMO_ROWS):
                image_path, item_name, condition_status, recycle_potential, weight, economic_value, recommendation = row
                item = get_item(item_name=item_name)
                if item is None:
                    continue
                created_at = now - timedelta(days=(len(DEMO_ROWS) - index - 1) // 3, hours=index % 6, minutes=index * 3)
                rows.append((
                    image_path,
                    item.item_key,
                    item.item_name,
                    item.category,
                    condition_status,
                    recycle_potential,
                    weight,
                    item.price_per_kg,
                    economic_value,
                    recommendation,
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ))

            cursor.executemany(
                """
                INSERT INTO analysis_results (
                    image_path, item_key, waste_type, category, condition_status, recycle_potential,
                    weight, price_per_kg, economic_value, recommendation, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )

    print(f"Seed demo selesai. {len(DEMO_ROWS)} data masuk ke {MYSQL_DATABASE}.analysis_results.")


if __name__ == "__main__":
    main()
