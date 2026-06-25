from __future__ import annotations

import argparse
import hashlib
import random
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError

from utils.waste_catalog import CATEGORY_GROUPS, ITEM_BY_KEY, ITEM_KEYS


CATEGORIES = ITEM_KEYS
SPLITS = ["train", "valid", "test"]
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIN_DEMO_PER_CATEGORY = 50
RESIZE_MAX_SIZE = 640
LEGACY_CATEGORY_DEFAULTS = {
    "plastik": "botol_plastik",
    "kertas": "kardus",
    "logam": "kaleng_minuman",
    "kaca": "botol_kaca",
    "karet_kain": "baju_bekas",
    "organik": "sisa_makanan",
    "elektronik": "kabel_usb",
    "campuran": "sampah_tidak_terpilah",
}


@dataclass
class DatasetStatus:
    counts: dict[str, dict[str, int]]
    category_totals: dict[str, int]
    total: int
    min_per_category: int
    low_items: list[dict]
    warning: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def dataset_root(root: Path | None = None) -> Path:
    return root or project_root() / "dataset"


def ensure_structure(root: Path | None = None) -> Path:
    """Pastikan struktur folder dataset sesuai spesifikasi tersedia."""
    root = dataset_root(root)
    (root / "raw" / "semua_gambar_awal").mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        for category, items in CATEGORY_GROUPS.items():
            category_dir = category.lower().replace("/", "_")
            for item in items:
                folder = root / split / category_dir / item.item_key
                folder.mkdir(parents=True, exist_ok=True)
                (folder / ".gitkeep").touch(exist_ok=True)
    for category, items in CATEGORY_GROUPS.items():
        category_dir = category.lower().replace("/", "_")
        (root / "categorized" / category_dir).mkdir(parents=True, exist_ok=True)
        for item in items:
            specific_folder = root / "specific" / category_dir / item.item_key
            specific_folder.mkdir(parents=True, exist_ok=True)
            (specific_folder / ".gitkeep").touch(exist_ok=True)
    (root / "unknown").mkdir(parents=True, exist_ok=True)
    (root / "unknown" / ".gitkeep").touch(exist_ok=True)
    migrate_legacy_category_files(root)
    data_yaml = root / "data.yaml"
    data_yaml.write_text(
        """path: dataset
train: train
val: valid
test: test

names:
""" + "\n".join(f"  {index}: {item_key}" for index, item_key in enumerate(ITEM_KEYS)) + "\n",
        encoding="utf-8",
    )
    return root


def migrate_legacy_category_files(root: Path) -> None:
    """Pindahkan gambar dari struktur lama split/kategori ke split/kategori/item_default."""
    for split in SPLITS:
        for legacy_category, default_item_key in LEGACY_CATEGORY_DEFAULTS.items():
            legacy_dir = root / split / legacy_category
            if not legacy_dir.exists() or not legacy_dir.is_dir():
                continue
            target_dir = legacy_dir / default_item_key
            target_dir.mkdir(parents=True, exist_ok=True)
            for path in legacy_dir.iterdir():
                if not path.is_file() or path.name == ".gitkeep" or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                target_path = target_dir / path.name
                if target_path.exists():
                    target_path = target_dir / f"{path.stem}_{uuid.uuid4().hex[:6]}{path.suffix}"
                shutil.move(str(path), str(target_path))


def is_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def iter_images(root: Path | None = None, include_unknown: bool = False) -> Iterable[Path]:
    root = ensure_structure(root)
    for split in SPLITS:
        for item_key in CATEGORIES:
            item = ITEM_BY_KEY[item_key]
            category_dir = item.category.lower().replace("/", "_")
            yield from (root / split / category_dir / item_key).glob("*")
    if include_unknown:
        yield from (root / "unknown").glob("*")


def image_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def existing_hashes(root: Path | None = None) -> set[str]:
    hashes: set[str] = set()
    for path in iter_images(root, include_unknown=True):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            try:
                hashes.add(image_digest(path))
            except OSError:
                continue
    return hashes


def normalize_image(source: Path, destination: Path) -> None:
    """Validasi, resize, dan simpan gambar dalam format JPG seragam."""
    with Image.open(source) as image:
        image.verify()
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((RESIZE_MAX_SIZE, RESIZE_MAX_SIZE), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=88, optimize=True)


def save_uploaded_files(files, category: str, root: Path | None = None, split: str = "train") -> dict:
    """Simpan banyak gambar dataset ke folder kategori dan cegah duplikat."""
    root = ensure_structure(root)
    item_key = category
    if item_key not in ITEM_BY_KEY:
        raise ValueError("Jenis sampah spesifik tidak valid.")
    if split not in SPLITS:
        raise ValueError("Split dataset tidak valid.")

    summary = {"saved": 0, "duplicates": 0, "invalid": 0, "files": []}
    hashes = existing_hashes(root)
    item = ITEM_BY_KEY[item_key]
    category_dir = item.category.lower().replace("/", "_")
    target_dir = root / split / category_dir / item_key
    tmp_dir = root / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        filename = getattr(file, "filename", "") or ""
        if not filename or not is_allowed(filename):
            summary["invalid"] += 1
            continue
        tmp_path = tmp_dir / f"{uuid.uuid4().hex}_{Path(filename).name}"
        file.save(tmp_path)
        try:
            digest = image_digest(tmp_path)
            if digest in hashes:
                summary["duplicates"] += 1
                tmp_path.unlink(missing_ok=True)
                continue
            new_name = f"{item_key}_{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}.jpg"
            target_path = target_dir / new_name
            normalize_image(tmp_path, target_path)
            hashes.add(image_digest(target_path))
            summary["saved"] += 1
            summary["files"].append(target_path)
        except (OSError, UnidentifiedImageError):
            summary["invalid"] += 1
        finally:
            tmp_path.unlink(missing_ok=True)
    return summary


def save_unknown_image(image_path: Path, root: Path | None = None) -> Path:
    """Simpan salinan gambar tidak dikenali agar bisa dikoreksi pengguna."""
    root = ensure_structure(root)
    target = root / "unknown" / f"unknown_{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}.jpg"
    normalize_image(image_path, target)
    return target


def count_images(root: Path | None = None) -> DatasetStatus:
    root = ensure_structure(root)
    counts: dict[str, dict[str, int]] = {}
    category_totals: dict[str, int] = {}
    total = 0
    item_totals: list[int] = []
    low_items: list[dict] = []
    for item_key in CATEGORIES:
        item = ITEM_BY_KEY[item_key]
        category_dir = item.category.lower().replace("/", "_")
        counts[item_key] = {"item_name": item.item_name, "category": item.category}
        item_total = 0
        for split in SPLITS:
            folder = root / split / category_dir / item_key
            amount = sum(1 for path in folder.iterdir() if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS)
            counts[item_key][split] = amount
            item_total += amount
        specific_folder = root / "specific" / category_dir / item_key
        specific_amount = sum(1 for path in specific_folder.iterdir() if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS)
        counts[item_key]["specific"] = specific_amount
        item_total = specific_amount if specific_amount else item_total
        counts[item_key]["total"] = item_total
        category_totals[item.category] = category_totals.get(item.category, 0) + item_total
        item_totals.append(item_total)
        total += item_total
        if item_total < item.min_images_required:
            low_items.append({"item_key": item_key, "item_name": item.item_name, "category": item.category, "total": item_total, "required": item.min_images_required})
    min_count = min(item_totals) if item_totals else 0
    warning = ""
    if min_count < MIN_DEMO_PER_CATEGORY:
        warning = "Beberapa jenis sampah spesifik masih kurang dari 50 gambar."
    return DatasetStatus(counts=counts, category_totals=category_totals, total=total, min_per_category=min_count, low_items=low_items, warning=warning)


def list_preview(root: Path | None = None, limit_per_category: int = 6) -> dict[str, list[Path]]:
    root = ensure_structure(root)
    previews: dict[str, list[Path]] = {}
    for item_key in CATEGORIES:
        item = ITEM_BY_KEY[item_key]
        category_dir = item.category.lower().replace("/", "_")
        images: list[Path] = []
        images.extend(sorted((root / "specific" / category_dir / item_key).glob("*"), key=lambda item: item.stat().st_mtime if item.is_file() else 0, reverse=True))
        for split in SPLITS:
            images.extend(sorted((root / split / category_dir / item_key).glob("*"), key=lambda item: item.stat().st_mtime if item.is_file() else 0, reverse=True))
        previews[item_key] = [path for path in images if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS][:limit_per_category]
    previews["unknown"] = [
        path
        for path in sorted((root / "unknown").glob("*"), key=lambda item: item.stat().st_mtime if item.is_file() else 0, reverse=True)
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ][:limit_per_category]
    return previews


def clean_dataset(root: Path | None = None) -> dict:
    """Hapus gambar rusak dan duplikat dari dataset."""
    root = ensure_structure(root)
    seen: set[str] = set()
    removed_invalid = 0
    removed_duplicates = 0
    for path in list(iter_images(root, include_unknown=True)):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            path.unlink(missing_ok=True)
            removed_invalid += 1
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            digest = image_digest(path)
            if digest in seen:
                path.unlink(missing_ok=True)
                removed_duplicates += 1
            else:
                seen.add(digest)
        except (OSError, UnidentifiedImageError):
            path.unlink(missing_ok=True)
            removed_invalid += 1
    return {"removed_invalid": removed_invalid, "removed_duplicates": removed_duplicates}


def split_dataset(root: Path | None = None, seed: int = 42) -> dict:
    """Bagi dataset per kategori menjadi 70% train, 20% valid, 10% test."""
    root = ensure_structure(root)
    rng = random.Random(seed)
    summary: dict[str, dict[str, int]] = {}
    for category in CATEGORIES:
        item = ITEM_BY_KEY[category]
        category_dir = item.category.lower().replace("/", "_")
        all_images: list[Path] = []
        for split in SPLITS:
            all_images.extend([path for path in (root / split / category_dir / category).iterdir() if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS])
        rng.shuffle(all_images)
        total = len(all_images)
        train_end = int(total * 0.7)
        valid_end = train_end + int(total * 0.2)
        targets = {
            "train": all_images[:train_end],
            "valid": all_images[train_end:valid_end],
            "test": all_images[valid_end:],
        }
        summary[category] = {}
        for split, images in targets.items():
            target_dir = root / split / category_dir / category
            target_dir.mkdir(parents=True, exist_ok=True)
            for path in images:
                target_path = target_dir / path.name
                if path.resolve() != target_path.resolve():
                    if target_path.exists():
                        target_path = target_dir / f"{path.stem}_{uuid.uuid4().hex[:6]}{path.suffix}"
                    shutil.move(str(path), str(target_path))
            summary[category][split] = len(images)
    return summary


def delete_image(split: str, category: str, filename: str, root: Path | None = None, item_key: str | None = None) -> bool:
    root = ensure_structure(root)
    if split == "unknown":
        path = root / "unknown" / Path(filename).name
    else:
        item_key = item_key or category
        if split not in SPLITS or item_key not in ITEM_BY_KEY:
            return False
        item = ITEM_BY_KEY[item_key]
        category_dir = item.category.lower().replace("/", "_")
        path = root / split / category_dir / item_key / Path(filename).name
    if path.exists() and path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
        path.unlink()
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Dataset Manager EcoLens")
    parser.add_argument("--split", action="store_true", help="Split dataset menjadi train/valid/test")
    parser.add_argument("--clean", action="store_true", help="Hapus gambar rusak dan duplikat")
    parser.add_argument("--count", action="store_true", help="Hitung jumlah gambar per kategori")
    args = parser.parse_args()

    root = ensure_structure()
    if args.clean:
        result = clean_dataset(root)
        print(f"Clean selesai: invalid={result['removed_invalid']}, duplikat={result['removed_duplicates']}")
    if args.split:
        result = split_dataset(root)
        print("Split selesai:")
        for category, counts in result.items():
            print(f"- {category}: train={counts['train']}, valid={counts['valid']}, test={counts['test']}")
    if args.count or not (args.clean or args.split):
        status = count_images(root)
        print(f"Total gambar: {status.total}")
        for category, counts in status.counts.items():
            print(f"- {category}: train={counts['train']}, valid={counts['valid']}, test={counts['test']}, total={counts['total']}")
        if status.warning:
            print(status.warning)


if __name__ == "__main__":
    main()
