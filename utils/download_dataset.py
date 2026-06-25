from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

try:
    from dataset_manager import CATEGORIES, clean_dataset, ensure_structure, split_dataset
except ImportError:
    from utils.dataset_manager import CATEGORIES, clean_dataset, ensure_structure, split_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "dataset"
YOLO_DIR = PROJECT_ROOT / "dataset_yolo"
DOWNLOAD_DIR = DATASET_DIR / "_downloads"
TMP_DIR = DATASET_DIR / ".tmp_download"
RESIZE_MAX_SIZE = 640
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

TRASHNET_URL = "https://huggingface.co/datasets/garythung/trashnet/resolve/main/dataset-resized.zip"
TACO_ANNOTATIONS_URL = "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"

KAGGLE_DATASETS = [
    "asdasdasasdas/garbage-classification",
    "mostafaabla/garbage-classification",
    "sumn2u/garbage-classification-v2",
]

CLASS_TO_CATEGORY = {
    "plastik": "plastik",
    "plastic": "plastik",
    "plastic bottle": "plastik",
    "plastic bag": "plastik",
    "bottle": "plastik",
    "styrofoam": "plastik",
    "paper": "kertas",
    "cardboard": "kertas",
    "carton": "kertas",
    "newspaper": "kertas",
    "magazine": "kertas",
    "kertas": "kertas",
    "logam": "logam",
    "metal": "logam",
    "can": "logam",
    "aluminium": "logam",
    "aluminum": "logam",
    "tin can": "logam",
    "kaca": "kaca",
    "glass": "kaca",
    "glass bottle": "kaca",
    "karet": "karet_kain",
    "kain": "karet_kain",
    "karet_kain": "karet_kain",
    "rubber": "karet_kain",
    "textile": "karet_kain",
    "clothes": "karet_kain",
    "clothing": "karet_kain",
    "shoe": "karet_kain",
    "shoes": "karet_kain",
    "organik": "organik",
    "organic": "organik",
    "biological": "organik",
    "food": "organik",
    "food waste": "organik",
    "vegetation": "organik",
    "leaf": "organik",
    "leaves": "organik",
    "elektronik": "elektronik",
    "electronic": "elektronik",
    "electronics": "elektronik",
    "battery": "elektronik",
    "charger": "elektronik",
    "cable": "elektronik",
    "mobile phone": "elektronik",
    "cell phone": "elektronik",
    "campuran": "campuran",
    "mixed": "campuran",
    "trash": "campuran",
    "garbage": "campuran",
    "waste": "campuran",
    "other": "campuran",
    "bottle cap": "plastik",
    "bottle caps": "plastik",
    "plastic utensils": "plastik",
    "plastic container": "plastik",
    "food wrappers": "plastik",
    "wrapper": "plastik",
    "lid": "plastik",
    "straw": "plastik",
    "straws": "plastik",
    "paper bag": "kertas",
    "paper packaging": "kertas",
    "drink can": "logam",
    "pop tab": "logam",
    "broken glass": "kaca",
    "glass jar": "kaca",
    "unlabeled litter": "campuran",
}

YOLO_CLASS_INDEX = {category: index for index, category in enumerate(CATEGORIES)}


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def normalize_label(label: str) -> str:
    return label.lower().strip().replace("-", " ").replace("_", " ")


def map_category(label: str | None) -> str | None:
    if not label:
        return None
    normalized = normalize_label(label)
    if normalized in CLASS_TO_CATEGORY:
        return CLASS_TO_CATEGORY[normalized]
    for key, category in CLASS_TO_CATEGORY.items():
        if key in normalized:
            return category
    return None


def write_yolo_data_yaml() -> None:
    names = "\n".join(f"  {idx}: {name}" for idx, name in enumerate(CATEGORIES))
    (YOLO_DIR / "data.yaml").write_text(
        f"""path: {YOLO_DIR.as_posix()}
train: images/train
val: images/valid
test: images/test

names:
{names}
""",
        encoding="utf-8",
    )


def ensure_dirs() -> None:
    ensure_structure(DATASET_DIR)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    for split in ["train", "valid", "test"]:
        (YOLO_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (YOLO_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)
    write_yolo_data_yaml()


def download_file(url: str, destination: Path, retries: int = 3, timeout: int = 60) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Sudah ada, skip download: {destination.name}")
        return True

    for attempt in range(1, retries + 1):
        try:
            print(f"Download: {url}")
            request = urllib.request.Request(url, headers={"User-Agent": "EcoLensDatasetDownloader/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                total = int(response.headers.get("Content-Length", 0))
                progress = tqdm(total=total, unit="B", unit_scale=True, desc=destination.name) if tqdm else None
                with destination.open("wb") as file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        file.write(chunk)
                        if progress:
                            progress.update(len(chunk))
                if progress:
                    progress.close()
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            print(f"Gagal download percobaan {attempt}/{retries}: {exc}")
            destination.unlink(missing_ok=True)
            time.sleep(2 * attempt)
    return False


def safe_extract_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            resolved = (target_dir / member.filename).resolve()
            if not str(resolved).startswith(str(target_dir.resolve())):
                raise RuntimeError(f"ZIP tidak aman, path keluar folder: {member.filename}")
        archive.extractall(target_dir)


def file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def existing_hashes() -> set[str]:
    hashes: set[str] = set()
    for split in ["train", "valid", "test"]:
        for category in CATEGORIES:
            for image_path in (DATASET_DIR / split / category).glob("*"):
                if image_path.is_file() and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    try:
                        hashes.add(file_hash(image_path))
                    except OSError:
                        continue
    return hashes


def normalize_image(source: Path, destination: Path) -> bool:
    try:
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((RESIZE_MAX_SIZE, RESIZE_MAX_SIZE), Image.Resampling.LANCZOS)
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, "JPEG", quality=88, optimize=True)
        return True
    except (OSError, UnidentifiedImageError):
        return False


def image_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def import_image(source: Path, category: str, source_name: str, hashes: set[str]) -> bool:
    if category not in CATEGORIES:
        return False
    try:
        digest = file_hash(source)
    except OSError:
        return False
    if digest in hashes:
        return False

    safe_stem = "".join(ch if ch.isalnum() else "_" for ch in source.stem)[:70]
    filename = f"{source_name}_{category}_{safe_stem}_{digest[:10]}.jpg"
    destination = DATASET_DIR / "train" / category / filename
    if not normalize_image(source, destination):
        return False
    hashes.add(file_hash(destination))
    return True


def import_folder_by_labels(root: Path, source_name: str, hashes: set[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for image_path in image_files(root):
        labels = [part.name for part in image_path.parents if part != root.parent]
        labels.append(image_path.stem)
        category = next((mapped for label in labels if (mapped := map_category(label))), None)
        if category and import_image(image_path, category, source_name, hashes):
            counts[category] += 1
    return dict(counts)


def download_trashnet(hashes: set[str]) -> dict[str, int]:
    print_header("TrashNet")
    zip_path = DOWNLOAD_DIR / "trashnet_dataset_resized.zip"
    extract_dir = DOWNLOAD_DIR / "trashnet"
    if download_file(TRASHNET_URL, zip_path):
        if not extract_dir.exists():
            print("Extract TrashNet ZIP...")
            safe_extract_zip(zip_path, extract_dir)
        counts = import_folder_by_labels(extract_dir, "trashnet", hashes)
        print(f"TrashNet imported: {counts}")
        return counts
    print("TrashNet gagal diunduh. Sumber dilewati.")
    return {}


def taco_image_url(image_info: dict) -> str | None:
    for key in ["flickr_url", "coco_url", "url"]:
        if image_info.get(key):
            return image_info[key]
    return None


def download_taco(hashes: set[str], max_images: int = 0) -> dict[str, int]:
    print_header("TACO Dataset")
    annotations_path = DOWNLOAD_DIR / "taco_annotations.json"
    if not download_file(TACO_ANNOTATIONS_URL, annotations_path):
        print("TACO annotations gagal diunduh. Sumber dilewati.")
        return {}

    data = json.loads(annotations_path.read_text(encoding="utf-8"))
    categories_by_id = {category["id"]: category for category in data.get("categories", [])}
    annotations_by_image: dict[int, list[dict]] = defaultdict(list)
    for annotation in data.get("annotations", []):
        annotations_by_image[annotation.get("image_id")].append(annotation)

    counts: dict[str, int] = defaultdict(int)
    images = data.get("images", [])
    if max_images > 0:
        images = images[:max_images]

    progress = tqdm(images, desc="TACO images") if tqdm else images
    for image_info in progress:
        image_id = image_info.get("id")
        candidates = []
        for annotation in annotations_by_image.get(image_id, []):
            category_info = categories_by_id.get(annotation.get("category_id"), {})
            candidates.extend([category_info.get("name"), category_info.get("supercategory")])
        mapped = [category for value in candidates if (category := map_category(value))]
        category = Counter(mapped).most_common(1)[0][0] if mapped else "campuran"
        url = taco_image_url(image_info)
        if not url:
            continue
        tmp_image = TMP_DIR / f"taco_{image_id}.jpg"
        if download_file(url, tmp_image, retries=2, timeout=30):
            if import_image(tmp_image, category, "taco", hashes):
                counts[category] += 1
            tmp_image.unlink(missing_ok=True)
    print(f"TACO imported: {dict(counts)}")
    return dict(counts)


def kaggle_credentials_available() -> bool:
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return kaggle_json.exists() or (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"))


def print_kaggle_guide() -> None:
    print(
        """
Kaggle dataset memerlukan akun/API token.
Langkah konfigurasi:
1. Login ke https://www.kaggle.com
2. Buka Account -> API -> Create New Token
3. Simpan file kaggle.json ke:
   C:\\Users\\<username>\\.kaggle\\kaggle.json
4. Jalankan lagi:
   python utils/download_dataset.py --sources kaggle
"""
    )


def download_kaggle(hashes: set[str]) -> dict[str, int]:
    print_header("Kaggle Garbage Classification")
    if importlib.util.find_spec("kaggle") is None:
        print("Paket kaggle belum tersedia. Jalankan: pip install kaggle")
        print_kaggle_guide()
        return {}
    if not kaggle_credentials_available():
        print("kaggle.json / KAGGLE_USERNAME+KAGGLE_KEY belum ditemukan.")
        print_kaggle_guide()
        return {}

    total_counts: dict[str, int] = defaultdict(int)
    kaggle_root = DOWNLOAD_DIR / "kaggle"
    kaggle_root.mkdir(parents=True, exist_ok=True)
    for slug in KAGGLE_DATASETS:
        target_dir = kaggle_root / slug.replace("/", "__")
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"Download Kaggle: {slug}")
        command = [
            sys.executable,
            "-m",
            "kaggle",
            "datasets",
            "download",
            "-d",
            slug,
            "-p",
            str(target_dir),
            "--unzip",
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"Kaggle gagal untuk {slug}: {exc}")
            continue
        counts = import_folder_by_labels(target_dir, "kaggle", hashes)
        for category, amount in counts.items():
            total_counts[category] += amount
    print(f"Kaggle imported: {dict(total_counts)}")
    return dict(total_counts)


def download_open_images(hashes: set[str], max_samples: int = 400) -> dict[str, int]:
    print_header("Open Images Dataset")
    if importlib.util.find_spec("fiftyone") is None:
        print(
            "Open Images subset paling aman diunduh via FiftyOne. Paket ini belum terpasang.\n"
            "Jika ingin mengaktifkan Open Images, jalankan:\n"
            "  pip install fiftyone\n"
            "Lalu:\n"
            "  python utils/download_dataset.py --sources openimages --max-open-images 1000"
        )
        return {}

    import fiftyone.zoo as foz  # type: ignore

    class_map = {
        "Bottle": "plastik",
        "Plastic bag": "plastik",
        "Tin can": "logam",
        "Wine glass": "kaca",
        "Book": "kertas",
        "Mobile phone": "elektronik",
        "Clothing": "karet_kain",
        "Food": "organik",
    }
    dataset = foz.load_zoo_dataset(
        "open-images-v6",
        split="validation",
        label_types=["detections"],
        classes=list(class_map),
        max_samples=max_samples,
    )
    counts: dict[str, int] = defaultdict(int)
    progress = tqdm(dataset, desc="Open Images") if tqdm else dataset
    for sample in progress:
        detections = getattr(sample, "detections", None)
        labels = [det.label for det in getattr(detections, "detections", [])] if detections else []
        category = next((class_map[label] for label in labels if label in class_map), None)
        if category and import_image(Path(sample.filepath), category, "openimages", hashes):
            counts[category] += 1
    print(f"Open Images imported: {dict(counts)}")
    return dict(counts)


def clear_yolo_dataset() -> None:
    for folder in [YOLO_DIR / "images", YOLO_DIR / "labels"]:
        if folder.exists():
            shutil.rmtree(folder)
    for split in ["train", "valid", "test"]:
        (YOLO_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (YOLO_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)
    write_yolo_data_yaml()


def build_yolo_dataset_from_classification() -> dict[str, int]:
    """Bangun YOLO detection format dari folder kategori.

    Dataset klasifikasi seperti TrashNet/Kaggle tidak memiliki bounding box.
    Agar tetap bisa dipakai YOLO detection, script membuat weak-label full-image
    box: class x_center y_center width height = 0.5 0.5 1 1.
    """
    print_header("Build dataset_yolo")
    clear_yolo_dataset()
    counts: dict[str, int] = defaultdict(int)
    for split in ["train", "valid", "test"]:
        for category in CATEGORIES:
            class_id = YOLO_CLASS_INDEX[category]
            for image_path in (DATASET_DIR / split / category).glob("*.jpg"):
                digest = file_hash(image_path)[:10]
                filename = f"{category}_{digest}_{image_path.name}"
                target_image = YOLO_DIR / "images" / split / filename
                target_label = YOLO_DIR / "labels" / split / f"{Path(filename).stem}.txt"
                shutil.copy2(image_path, target_image)
                target_label.write_text(f"{class_id} 0.5 0.5 1.0 1.0\n", encoding="utf-8")
                counts[split] += 1
    print(f"YOLO dataset ready: {dict(counts)}")
    return dict(counts)


def parse_sources(value: str) -> list[str]:
    aliases = {
        "trashnet": "trashnet",
        "taco": "taco",
        "kaggle": "kaggle",
        "openimages": "openimages",
        "open_images": "openimages",
        "all": "all",
    }
    requested = [aliases.get(item.strip().lower(), item.strip().lower()) for item in value.split(",") if item.strip()]
    if "all" in requested:
        return ["trashnet", "taco", "kaggle", "openimages"]
    return requested


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto download dataset publik untuk EcoLens")
    parser.add_argument(
        "--sources",
        default="all",
        help="Sumber: all, trashnet, taco, kaggle, openimages. Bisa digabung: trashnet,taco",
    )
    parser.add_argument("--max-taco", type=int, default=0, help="Batasi jumlah image TACO. 0 = semua.")
    parser.add_argument("--max-open-images", type=int, default=400, help="Batas sampel Open Images via FiftyOne.")
    parser.add_argument("--seed", type=int, default=42, help="Seed split dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Tampilkan rencana tanpa download.")
    args = parser.parse_args()

    sources = parse_sources(args.sources)
    ensure_dirs()

    print_header("EcoLens Auto Dataset Downloader")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Sources: {', '.join(sources)}")
    print(f"Output klasifikasi: {DATASET_DIR}")
    print(f"Output YOLO: {YOLO_DIR}")

    if args.dry_run:
        print("Dry run selesai. Tidak ada file yang diunduh.")
        return

    hashes = existing_hashes()
    summary: dict[str, dict[str, int]] = {}

    if "trashnet" in sources:
        summary["trashnet"] = download_trashnet(hashes)
    if "taco" in sources:
        summary["taco"] = download_taco(hashes, max_images=args.max_taco)
    if "kaggle" in sources:
        summary["kaggle"] = download_kaggle(hashes)
    if "openimages" in sources:
        summary["openimages"] = download_open_images(hashes, max_samples=args.max_open_images)

    print_header("Clean, split, dan build YOLO")
    clean_result = clean_dataset(DATASET_DIR)
    print(f"Clean: invalid={clean_result['removed_invalid']}, duplikat={clean_result['removed_duplicates']}")
    split_summary = split_dataset(DATASET_DIR, seed=args.seed)
    for category, counts in split_summary.items():
        print(f"{category}: train={counts['train']}, valid={counts['valid']}, test={counts['test']}")
    yolo_summary = build_yolo_dataset_from_classification()

    print_header("Selesai")
    print("Ringkasan import:", summary)
    print("YOLO summary:", yolo_summary)
    print("Dataset siap digunakan.")
    print("Training:")
    print("  python utils/train_yolo.py")


if __name__ == "__main__":
    main()
