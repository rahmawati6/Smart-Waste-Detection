from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.waste_catalog import CATEGORY_GROUPS, ITEM_BY_KEY, WasteItem, get_item


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RESIZE_MAX_SIZE = 640
MAIN_CATEGORY_DIRS = {
    "Plastik": "plastik",
    "Kertas": "kertas",
    "Logam": "logam",
    "Kaca": "kaca",
    "Organik": "organik",
    "Elektronik": "elektronik",
    "Karet/Kain": "karet_kain",
    "Campuran": "campuran",
}
LEGACY_CATEGORY_DEFAULTS = {
    "plastik": "botol_plastik",
    "kertas": "kardus",
    "logam": "kaleng_minuman",
    "kaca": "botol_kaca",
    "organik": "sisa_makanan",
    "elektronik": "kabel_usb",
    "karet_kain": "baju_bekas",
    "campuran": "sampah_tidak_terpilah",
}
SPECIFIC_HINTS = {
    "botol_air": "botol_air_mineral",
    "aqua": "botol_air_mineral",
    "mineral": "botol_air_mineral",
    "botol_plastik": "botol_plastik",
    "plastic_bottle": "botol_plastik",
    "bottle": "botol_plastik",
    "botol": "botol_plastik",
    "gelas_plastik": "gelas_plastik",
    "cup": "gelas_plastik",
    "kantong": "kantong_plastik",
    "kresek": "plastik_kresek",
    "snack": "bungkus_snack",
    "mie": "kemasan_mi_instan",
    "mi_instan": "kemasan_mi_instan",
    "styrofoam": "styrofoam",
    "kardus": "kardus",
    "cardboard": "kardus",
    "koran": "koran",
    "newspaper": "koran",
    "majalah": "majalah",
    "hvs": "kertas_hvs",
    "paper": "kertas_hvs",
    "karton": "karton",
    "kaleng_minuman": "kaleng_minuman",
    "soda_can": "kaleng_minuman",
    "can": "kaleng_minuman",
    "kaleng": "kaleng_minuman",
    "kaleng_makanan": "kaleng_makanan",
    "besi": "besi_tua",
    "aluminium": "aluminium",
    "botol_kaca": "botol_kaca",
    "glass_bottle": "botol_kaca",
    "gelas_kaca": "gelas_kaca",
    "pecahan": "pecahan_kaca",
    "toples": "toples_kaca",
    "pisang": "kulit_pisang",
    "banana": "kulit_pisang",
    "jeruk": "kulit_jeruk",
    "orange": "kulit_jeruk",
    "sisa_makanan": "sisa_makanan",
    "food": "sisa_makanan",
    "daun": "daun_kering",
    "leaf": "daun_kering",
    "kabel": "kabel_usb",
    "usb": "kabel_usb",
    "charger": "charger_rusak",
    "baterai": "baterai",
    "battery": "baterai",
    "pcb": "pcb",
    "ban": "ban_bekas",
    "tire": "ban_bekas",
    "sepatu": "sepatu_rusak",
    "shoe": "sepatu_rusak",
    "baju": "baju_bekas",
    "clothes": "baju_bekas",
    "kain": "kain_perca",
    "pasar": "sampah_pasar",
    "rumah_tangga": "sampah_rumah_tangga",
    "jalan": "sampah_jalanan",
    "campuran": "sampah_tidak_terpilah",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def dataset_root() -> Path:
    return project_root() / "dataset"


def category_dir(category: str) -> str:
    return MAIN_CATEGORY_DIRS.get(category, category.lower().replace("/", "_"))


def ensure_sort_structure(root: Path) -> None:
    (root / "raw" / "semua_gambar_awal").mkdir(parents=True, exist_ok=True)
    for category_name, dirname in MAIN_CATEGORY_DIRS.items():
        (root / "categorized" / dirname).mkdir(parents=True, exist_ok=True)
        for item in CATEGORY_GROUPS.get(category_name, []):
            (root / "specific" / dirname / item.item_key).mkdir(parents=True, exist_ok=True)
    (root / "unknown").mkdir(parents=True, exist_ok=True)


def image_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalized_image_digest(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((RESIZE_MAX_SIZE, RESIZE_MAX_SIZE), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=88, optimize=True)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def validate_and_resize(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image.verify()
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((RESIZE_MAX_SIZE, RESIZE_MAX_SIZE), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=88, optimize=True)


def iter_source_images(root: Path):
    raw_dir = root / "raw"
    yield from (path for path in raw_dir.rglob("*") if path.is_file())


def bootstrap_raw_from_existing(root: Path) -> int:
    raw_target = root / "raw" / "semua_gambar_awal"
    copied = 0
    if any(path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS for path in raw_target.glob("*")):
        return 0
    seen = {normalized_image_digest(path) for path in raw_target.glob("*.jpg") if path.is_file()}
    for split in ("train", "valid", "test"):
        split_dir = root / split
        if not split_dir.exists():
            continue
        for path in split_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            try:
                digest = normalized_image_digest(path)
            except OSError:
                continue
            if digest in seen:
                continue
            target = raw_target / f"{path.parent.name}_{path.stem}_{uuid.uuid4().hex[:8]}.jpg"
            try:
                validate_and_resize(path, target)
                seen.add(normalized_image_digest(target))
                copied += 1
            except (OSError, UnidentifiedImageError):
                continue
    return copied


def infer_from_path(path: Path) -> tuple[WasteItem | None, float, str]:
    text = " ".join(part.lower().replace("-", "_") for part in path.parts[-5:])
    for hint, item_key in SPECIFIC_HINTS.items():
        if hint in text:
            return get_item(item_key), 0.9, f"filename:{hint}"
    for category_dirname, default_item_key in LEGACY_CATEGORY_DEFAULTS.items():
        if category_dirname in text:
            return get_item(default_item_key), 0.62, f"category-folder:{category_dirname}"
    return None, 0.0, "unknown"


def infer_with_yolo(path: Path) -> tuple[WasteItem | None, float, str]:
    try:
        from utils.detector import WasteDetector

        if not hasattr(infer_with_yolo, "_detector"):
            infer_with_yolo._detector = WasteDetector(project_root() / "models" / "yolov8_waste.pt")
        detector = infer_with_yolo._detector
        result = detector.analyze(path)
        item = get_item(result.get("item_key"), result.get("item_name"))
        confidence = float(result.get("confidence") or 0)
        if item and confidence >= 0.5:
            return item, confidence, "yolo"
    except Exception:
        pass
    return None, 0.0, "yolo-unavailable"


def unique_target(base_dir: Path, source: Path, item_key: str = "") -> Path:
    stem = source.stem.lower().replace(" ", "_")
    prefix = f"{item_key}_" if item_key else ""
    target = base_dir / f"{prefix}{stem}.jpg"
    if not target.exists():
        return target
    return base_dir / f"{prefix}{stem}_{uuid.uuid4().hex[:8]}.jpg"


def empty_specific_folders(root: Path) -> list[str]:
    empty: list[str] = []
    for category_name, items in CATEGORY_GROUPS.items():
        dirname = category_dir(category_name)
        for item in items:
            folder = root / "specific" / dirname / item.item_key
            if not any(path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS for path in folder.glob("*")):
                empty.append(f"{dirname}/{item.item_key}")
    return empty


def existing_specific_output_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    specific_root = root / "specific"
    if not specific_root.exists():
        return keys
    for path in specific_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            item_key = path.parent.name
            keys.add(f"{normalized_image_digest(path)}:{item_key}")
        except OSError:
            continue
    return keys


def clean_sorted_outputs(root: Path) -> int:
    """Hapus duplikat di hasil categorized/specific/unknown tanpa menyentuh dataset/raw."""
    removed = 0
    for folder in (root / "categorized", root / "specific", root / "unknown"):
        if not folder.exists():
            continue
        seen: set[str] = set()
        for path in folder.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            try:
                digest = normalized_image_digest(path)
            except OSError:
                path.unlink(missing_ok=True)
                removed += 1
                continue
            scoped_key = f"{path.parent}:{digest}"
            if scoped_key in seen:
                path.unlink(missing_ok=True)
                removed += 1
            else:
                seen.add(scoped_key)
    return removed


def sort_dataset(use_yolo: bool = True, bootstrap_raw: bool = True) -> dict:
    root = dataset_root()
    ensure_sort_structure(root)
    preclean_removed = clean_sorted_outputs(root)
    bootstrapped = bootstrap_raw_from_existing(root) if bootstrap_raw else 0

    total = categorized = specific = unknown = invalid = duplicates = 0
    method_counter: Counter[str] = Counter()
    seen_raw: set[str] = set()
    seen_outputs: set[str] = existing_specific_output_keys(root)

    for image_path in iter_source_images(root):
        total += 1
        if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            invalid += 1
            continue
        try:
            digest = normalized_image_digest(image_path)
        except OSError:
            invalid += 1
            continue
        if digest in seen_raw:
            duplicates += 1
            continue
        seen_raw.add(digest)

        item, confidence, method = infer_from_path(image_path)
        if item is None and use_yolo:
            item, confidence, method = infer_with_yolo(image_path)

        try:
            if item is None or confidence < 0.5:
                target = unique_target(root / "unknown", image_path)
                validate_and_resize(image_path, target)
                unknown += 1
                method_counter["unknown"] += 1
                continue

            dirname = category_dir(item.category)
            categorized_target = unique_target(root / "categorized" / dirname, image_path, item.item_key)
            specific_target = unique_target(root / "specific" / dirname / item.item_key, image_path, item.item_key)
            output_digest_key = f"{digest}:{item.item_key}"
            if output_digest_key in seen_outputs:
                duplicates += 1
                continue
            validate_and_resize(image_path, categorized_target)
            validate_and_resize(image_path, specific_target)
            seen_outputs.add(output_digest_key)
            categorized += 1
            specific += 1
            method_counter[method] += 1
        except (OSError, UnidentifiedImageError):
            invalid += 1

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bootstrapped_raw": bootstrapped,
        "preclean_removed_duplicates": preclean_removed,
        "total_images_read": total,
        "categorized": categorized,
        "specific": specific,
        "unknown": unknown,
        "invalid": invalid,
        "duplicates": duplicates,
        "methods": dict(method_counter),
        "empty_specific_folders": empty_specific_folders(root),
    }
    report_path = root / "sort_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Kelompokkan dataset EcoLens ke kategori umum dan jenis spesifik.")
    parser.add_argument("--no-yolo", action="store_true", help="Gunakan filename/folder hint saja tanpa YOLO fallback.")
    parser.add_argument("--no-bootstrap", action="store_true", help="Jangan copy gambar train/valid/test lama ke dataset/raw.")
    args = parser.parse_args()

    report = sort_dataset(use_yolo=not args.no_yolo, bootstrap_raw=not args.no_bootstrap)
    print("AUTO SORT DATASET SELESAI")
    print(f"Raw bootstrap       : {report['bootstrapped_raw']}")
    print(f"Total dibaca        : {report['total_images_read']}")
    print(f"Masuk categorized   : {report['categorized']}")
    print(f"Masuk specific      : {report['specific']}")
    print(f"Masuk unknown       : {report['unknown']}")
    print(f"Invalid             : {report['invalid']}")
    print(f"Duplikat            : {report['duplicates']}")
    print(f"Folder kosong       : {len(report['empty_specific_folders'])}")
    print(f"Laporan             : {dataset_root() / 'sort_report.json'}")


if __name__ == "__main__":
    main()
