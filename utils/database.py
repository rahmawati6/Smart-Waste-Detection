from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from utils.waste_catalog import as_db_rows, default_item_for_category, get_item

from werkzeug.security import check_password_hash, generate_password_hash

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover - handled with a clear runtime message
    pymysql = None
    DictCursor = None


MYSQL_HOST = os.environ.get("ECOLENS_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("ECOLENS_MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("ECOLENS_MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("ECOLENS_MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("ECOLENS_MYSQL_DATABASE", "ecolens_db")
ADMIN_USERNAME = os.environ.get("ECOLENS_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ECOLENS_ADMIN_PASSWORD")


def _require_pymysql() -> None:
    if pymysql is None:
        raise RuntimeError(
            "PyMySQL belum terpasang. Jalankan: pip install pymysql "
            "atau install ulang dependency dengan: pip install -r requirements.txt"
        )


def _connection(database: str | None = MYSQL_DATABASE):
    _require_pymysql()
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def init_db(path: Path | None = None) -> None:
    """Buat database MySQL Laragon dan tabel analysis_results jika belum ada.

    Parameter ``path`` tetap diterima agar kompatibel dengan pemanggilan lama
    di app.py, tetapi penyimpanan utama sekarang menggunakan MySQL/phpMyAdmin.
    """
    with _connection(database=None) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

    with _connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    image_path VARCHAR(255),
                    item_key VARCHAR(100),
                    waste_type VARCHAR(50),
                    category VARCHAR(50),
                    condition_status VARCHAR(50),
                    recycle_potential VARCHAR(50),
                    weight FLOAT,
                    price_per_kg INT,
                    economic_value INT,
                    recommendation TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS waste_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    item_key VARCHAR(100) NOT NULL UNIQUE,
                    item_name VARCHAR(100) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    price_per_kg INT NOT NULL DEFAULT 0,
                    recycle_potential VARCHAR(50) NOT NULL,
                    recycle_type VARCHAR(100) NOT NULL,
                    min_images_required INT NOT NULL DEFAULT 50
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'Administrator',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    item_key VARCHAR(100) NOT NULL,
                    item_name VARCHAR(100) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    split_name VARCHAR(20) NOT NULL,
                    image_path VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_dataset_item (item_key),
                    INDEX idx_dataset_category (category)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            _ensure_analysis_columns(cursor)
            _seed_waste_items(cursor)
            _seed_default_user(cursor)
            _backfill_analysis_metadata(cursor)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (MYSQL_DATABASE, table_name, column_name),
    )
    return int(cursor.fetchone()["total"] or 0) > 0


def _ensure_analysis_columns(cursor) -> None:
    columns = {
        "item_key": "VARCHAR(100)",
        "category": "VARCHAR(50)",
        "price_per_kg": "INT",
    }
    for column, definition in columns.items():
        if not _column_exists(cursor, "analysis_results", column):
            cursor.execute(f"ALTER TABLE analysis_results ADD COLUMN {column} {definition}")


def _seed_waste_items(cursor) -> None:
    rows = as_db_rows()
    cursor.executemany(
        """
        INSERT INTO waste_items (
            item_key, item_name, category, price_per_kg,
            recycle_potential, recycle_type, min_images_required
        ) VALUES (
            %(item_key)s, %(item_name)s, %(category)s, %(price_per_kg)s,
            %(recycle_potential)s, %(recycle_type)s, %(min_images_required)s
        )
        ON DUPLICATE KEY UPDATE
            item_name = VALUES(item_name),
            category = VALUES(category),
            price_per_kg = VALUES(price_per_kg),
            recycle_potential = VALUES(recycle_potential),
            recycle_type = VALUES(recycle_type),
            min_images_required = VALUES(min_images_required)
        """,
        rows,
    )


def _seed_default_user(cursor) -> None:
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE username = %s", (ADMIN_USERNAME,))
    if int(cursor.fetchone()["total"] or 0) == 0 and ADMIN_PASSWORD:
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, %s)
            """,
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Administrator"),
        )


def verify_user(username: str, password: str) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            if not row:
                return False
            return check_password_hash(row["password_hash"], password)


def insert_dataset_image(item_key: str, split_name: str, image_path: str) -> int:
    item = get_item(item_key)
    if item is None:
        raise ValueError("Jenis dataset tidak valid.")
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO dataset_images (item_key, item_name, category, split_name, image_path)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (item.item_key, item.item_name, item.category, split_name, image_path),
            )
            return int(cursor.lastrowid)


def _resolve_catalog_item(row: dict[str, Any]) -> dict[str, Any]:
    item = get_item(row.get("item_key"), row.get("waste_type"))
    if item is None:
        item = default_item_for_category(row.get("category") or row.get("waste_type"))
    return {
        "item_key": item.item_key,
        "waste_type": item.item_name,
        "category": item.category,
        "price_per_kg": item.price_per_kg,
        "recycle_potential": row.get("recycle_potential") or item.recycle_potential,
    }


def _backfill_analysis_metadata(cursor) -> None:
    cursor.execute(
        """
        SELECT id, item_key, waste_type, category, recycle_potential
        FROM analysis_results
        WHERE item_key IS NULL OR category IS NULL OR price_per_kg IS NULL
        """
    )
    rows = cursor.fetchall()
    for row in rows:
        resolved = _resolve_catalog_item(row)
        cursor.execute(
            """
            UPDATE analysis_results
            SET item_key = %s, waste_type = %s, category = %s,
                price_per_kg = %s, recycle_potential = %s
            WHERE id = %s
            """,
            (
                resolved["item_key"],
                resolved["waste_type"],
                resolved["category"],
                resolved["price_per_kg"],
                resolved["recycle_potential"],
                row["id"],
            ),
        )


def connect():
    """Koneksi langsung ke database MySQL EcoLens."""
    return _connection()


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")


def _normalize_recycle_potential(data: dict) -> str:
    action = str(data.get("processing_action") or data.get("recommendation") or "")
    potential = str(data.get("potential") or data.get("recycle_potential") or "")

    if "Tidak layak" in action:
        return "Tidak Layak"
    if "energi" in action.lower():
        return "Diproses Menjadi Energi"
    if "Dijual" in action:
        return "Layak Dijual"
    if "Daur ulang" in action:
        return "Layak Daur Ulang"
    if potential in {"Layak Daur Ulang", "Layak Dijual", "Diproses Menjadi Energi", "Tidak Layak"}:
        return potential
    if potential.lower() == "tinggi":
        return "Layak Dijual"
    if potential.lower() == "sedang":
        return "Layak Daur Ulang"
    if potential.lower() == "rendah":
        return "Diproses Menjadi Energi"
    return "Tidak Layak"


def _legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    """Alias kolom MySQL ke nama lama agar template/route lain tetap kompatibel."""
    weight = float(row.get("weight") or 0)
    economic_value = int(row.get("economic_value") or 0)
    price_per_kg = int(row.get("price_per_kg") or (economic_value / weight if weight else 0))
    waste_type = row.get("waste_type") or "Tidak Dikenali"
    category = row.get("category") or waste_type
    recycle_potential = row.get("recycle_potential") or "Tidak Layak"
    recommendation = row.get("recommendation") or "-"

    return {
        **row,
        "created_at": _format_datetime(row.get("created_at")),
        "item_key": row.get("item_key") or "",
        "item_name": waste_type,
        "category": category,
        "waste_type": waste_type,
        "condition": row.get("condition_status") or "-",
        "potential": recycle_potential,
        "processing_action": recycle_potential,
        "source": "MySQL phpMyAdmin",
        "detected_label": waste_type,
        "confidence": 1.0,
        "price_per_kg": price_per_kg,
        "recommendation": recommendation,
    }


def insert_analysis(data: dict) -> int:
    item = get_item(data.get("item_key"), data.get("item_name") or data.get("waste_type") or data.get("category"))
    if item is None:
        item = default_item_for_category(data.get("category"))
    recycle_potential = data.get("recycle_potential") or item.recycle_potential or _normalize_recycle_potential(data)
    payload = {
        "image_path": data.get("image_path", ""),
        "item_key": item.item_key,
        "waste_type": item.item_name,
        "category": item.category,
        "condition_status": data.get("condition") or data.get("condition_status") or "-",
        "recycle_potential": recycle_potential,
        "weight": float(data.get("weight") or 0),
        "price_per_kg": int(data.get("price_per_kg") or item.price_per_kg),
        "economic_value": int(float(data.get("economic_value") or 0)),
        "recommendation": data.get("recommendation") or data.get("processing_action") or "-",
        "created_at": data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analysis_results (
                    image_path, item_key, waste_type, category, condition_status, recycle_potential,
                    weight, price_per_kg, economic_value, recommendation, created_at
                ) VALUES (
                    %(image_path)s, %(item_key)s, %(waste_type)s, %(category)s, %(condition_status)s, %(recycle_potential)s,
                    %(weight)s, %(price_per_kg)s, %(economic_value)s, %(recommendation)s, %(created_at)s
                )
                """,
                payload,
            )
            return int(cursor.lastrowid)


def fetch_analysis(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM analysis_results
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [_legacy_row(row) for row in cursor.fetchall()]


def get_report_rows(start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM analysis_results WHERE 1=1"
    params: list[str] = []
    if start_date:
        query += " AND DATE(created_at) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        query += " AND DATE(created_at) <= DATE(%s)"
        params.append(end_date)
    query += " ORDER BY created_at DESC, id DESC"

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return [_legacy_row(row) for row in cursor.fetchall()]


def get_dashboard_stats() -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM analysis_results")
            total = int(cursor.fetchone()["total"] or 0)

            cursor.execute(
                """
                SELECT COALESCE(category, waste_type) AS category, COUNT(*) AS total
                FROM analysis_results
                GROUP BY COALESCE(category, waste_type)
                ORDER BY total DESC
                """
            )
            category_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT DATE(created_at) AS tanggal, COUNT(*) AS total
                FROM analysis_results
                GROUP BY DATE(created_at)
                ORDER BY tanggal ASC
                """
            )
            trend_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT recycle_potential, COUNT(*) AS total
                FROM analysis_results
                GROUP BY recycle_potential
                ORDER BY total DESC
                """
            )
            potential_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT COALESCE(SUM(economic_value), 0) AS total_nilai
                FROM analysis_results
                """
            )
            value = int(cursor.fetchone()["total_nilai"] or 0)

            cursor.execute(
                """
                SELECT image_path, item_key, waste_type, category, condition_status, recycle_potential,
                       weight, price_per_kg, economic_value, recommendation, created_at
                FROM analysis_results
                ORDER BY created_at DESC, id DESC
                LIMIT 10
                """
            )
            latest_rows = cursor.fetchall()

            cursor.execute(
                "SELECT COUNT(*) AS total FROM analysis_results WHERE recycle_potential = %s",
                ("Layak Daur Ulang",),
            )
            recycle = int(cursor.fetchone()["total"] or 0)

            cursor.execute(
                "SELECT COUNT(*) AS total FROM analysis_results WHERE recycle_potential = %s",
                ("Layak Dijual",),
            )
            sell = int(cursor.fetchone()["total"] or 0)

            cursor.execute(
                "SELECT COUNT(*) AS total FROM analysis_results WHERE recycle_potential = %s",
                ("Diproses Menjadi Energi",),
            )
            energy = int(cursor.fetchone()["total"] or 0)

            cursor.execute(
                "SELECT COUNT(*) AS total FROM analysis_results WHERE recycle_potential = %s",
                ("Tidak Layak",),
            )
            not_eligible = int(cursor.fetchone()["total"] or 0)

    categories = [
        {"category": row["category"] or "Tidak Dikenali", "total": int(row["total"] or 0)}
        for row in category_rows
    ]
    category_chart = [
        {
            "label": row["category"],
            "count": row["total"],
            "percentage": round((row["total"] / total * 100), 1) if total else 0,
        }
        for row in categories
    ]
    trend_chart = [
        {
            "label": _format_datetime(row["tanggal"]),
            "date": _format_datetime(row["tanggal"]),
            "count": int(row["total"] or 0),
        }
        for row in trend_rows
    ]
    potential_chart = [
        {"label": row["recycle_potential"] or "Tidak Layak", "count": int(row["total"] or 0)}
        for row in potential_rows
    ]

    return {
        "total": total,
        "recycle": recycle,
        "sell": sell,
        "energy": energy,
        "not_eligible": not_eligible,
        "value": value,
        "latest": [_legacy_row(row) for row in latest_rows],
        "categories": categories,
        "category_chart": category_chart,
        "trend_chart": trend_chart,
        "potential_chart": potential_chart,
    }
