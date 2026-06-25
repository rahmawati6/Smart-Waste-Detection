from __future__ import annotations

import shutil
import os
from pathlib import Path

from dataset_manager import CATEGORIES, count_images, ensure_structure


def prepare_classification_view(project_root: Path, dataset_dir: Path) -> Path:
    """Buat salinan sementara train/val/test untuk format YOLO classification."""
    view_dir = project_root / ".cache" / "yolo_cls_dataset"
    if view_dir.exists():
        shutil.rmtree(view_dir)
    split_map = {"train": "train", "valid": "val", "test": "test"}
    for source_split, target_split in split_map.items():
        for category in CATEGORIES:
            source_dir = dataset_dir / source_split / category
            target_dir = view_dir / target_split / category
            target_dir.mkdir(parents=True, exist_ok=True)
            for image_path in source_dir.glob("*"):
                if image_path.is_file() and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    shutil.copy2(image_path, target_dir / image_path.name)
    return view_dir


def train_yolo() -> Path:
    """Latih model YOLO custom dari dataset EcoLens.

    Struktur dataset yang diminta user berbentuk folder per kategori, sehingga
    training memakai mode classification YOLO (`yolov8n-cls.pt`). File hasil
    terbaik tetap disalin sebagai `models/yolov8_waste.pt` agar otomatis dipakai
    aplikasi saat analisis gambar.
    """
    project_root = Path(__file__).resolve().parents[1]
    dataset_dir = ensure_structure(project_root / "dataset")
    yolo_yaml = project_root / "dataset_yolo" / "data.yaml"
    has_yolo_images = any((project_root / "dataset_yolo" / "images" / split).glob("*.jpg") for split in ["train", "valid", "test"])
    data_yaml = yolo_yaml if yolo_yaml.exists() and has_yolo_images else dataset_dir / "data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError("dataset/data.yaml atau dataset_yolo/data.yaml belum tersedia.")

    status = count_images(dataset_dir)
    if status.total == 0:
        raise RuntimeError("Dataset masih kosong. Upload gambar di halaman Dataset Sampah sebelum training.")
    if status.min_per_category < 50:
        print("PERINGATAN: Dataset masih sedikit, hasil analisis mungkin belum akurat.")
        print("Minimal demo yang disarankan adalah 50 gambar per kategori.")

    cache_dir = project_root / ".cache" / "ultralytics"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(cache_dir))
    os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(cache_dir))

    from ultralytics import YOLO

    if yolo_yaml.exists() and has_yolo_images:
        model = YOLO(str(project_root / "models" / "yolov8n.pt") if (project_root / "models" / "yolov8n.pt").exists() else "yolov8n.pt")
        results = model.train(
            data=str(yolo_yaml),
            epochs=25,
            imgsz=640,
            project=str(project_root / "models" / "training_runs"),
            name="ecolens_yolo_detection",
            exist_ok=True,
        )
    else:
        model = YOLO("yolov8n-cls.pt")
        cls_dataset = prepare_classification_view(project_root, dataset_dir)
        results = model.train(
            data=str(cls_dataset),
            epochs=25,
            imgsz=640,
            project=str(project_root / "models" / "training_runs"),
            name="ecolens_yolo_classification",
            exist_ok=True,
        )

    best_model = Path(results.save_dir) / "weights" / "best.pt"
    target = project_root / "models" / "yolov8_waste.pt"
    if not best_model.exists():
        raise FileNotFoundError("Training selesai, tetapi best.pt tidak ditemukan.")
    shutil.copy2(best_model, target)
    print(f"Model custom tersimpan: {target}")
    return target


if __name__ == "__main__":
    train_yolo()
