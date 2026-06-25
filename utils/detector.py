from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from utils.waste_catalog import ITEM_BY_KEY, default_item_for_category, get_item, normalize_label

try:
    import cv2
except Exception:  # pragma: no cover - aplikasi tetap bisa jalan tanpa OpenCV saat import.
    cv2 = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


YOLO_LABEL_MAP = {
    "botol_air_mineral": "botol_air_mineral",
    "botol plastik": "botol_plastik",
    "botol_plastik": "botol_plastik",
    "gelas plastik": "gelas_plastik",
    "gelas_plastik": "gelas_plastik",
    "kaleng minuman": "kaleng_minuman",
    "kaleng_minuman": "kaleng_minuman",
    "kaleng cat": "kaleng_cat",
    "kaleng_cat": "kaleng_cat",
    "kardus": "kardus",
    "koran": "koran",
    "botol kaca": "botol_kaca",
    "botol_kaca": "botol_kaca",
    "botol sirup": "botol_sirup",
    "botol_sirup": "botol_sirup",
    "kulit pisang": "kulit_pisang",
    "kulit_pisang": "kulit_pisang",
    "kulit jeruk": "kulit_jeruk",
    "kulit_jeruk": "kulit_jeruk",
    "daun kering": "daun_kering",
    "daun_kering": "daun_kering",
    "ban bekas": "ban_bekas",
    "ban_bekas": "ban_bekas",
    "sepatu bekas": "sepatu_bekas",
    "sepatu_bekas": "sepatu_bekas",
    "charger rusak": "charger_rusak",
    "charger_rusak": "charger_rusak",
    "kabel usb": "kabel_usb",
    "kabel_usb": "kabel_usb",
    "remote tv": "remote_tv",
    "remote_tv": "remote_tv",
    "styrofoam": "styrofoam",
    "kemasan mi instan": "kemasan_mi_instan",
    "kemasan_mi_instan": "kemasan_mi_instan",
    "tutup botol": "tutup_botol_plastik",
    "plastik kresek": "plastik_kresek",
    "bungkus snack": "bungkus_snack",
    "plastik": "Plastik",
    "plastic": "Plastik",
    "kertas": "Kertas",
    "paper": "Kertas",
    "logam": "Logam",
    "metal": "Logam",
    "kaca": "Kaca",
    "glass": "Kaca",
    "karet_kain": "Karet/Kain",
    "karet": "Karet/Kain",
    "kain": "Karet/Kain",
    "organik": "Organik",
    "organic": "Organik",
    "elektronik": "Elektronik",
    "electronic": "Elektronik",
    "campuran": "Campuran",
    "mixed": "Campuran",
    "bottle": "botol_plastik",
    "cup": "gelas_plastik",
    "plastic": "Plastik",
    "bag": "plastik_kresek",
    "book": "buku_bekas",
    "newspaper": "koran",
    "paper": "Kertas",
    "cardboard": "kardus",
    "can": "kaleng_minuman",
    "knife": "besi_tua",
    "fork": "garpu_logam",
    "spoon": "sendok_logam",
    "metal": "Logam",
    "wine glass": "gelas_kaca",
    "glass": "gelas_kaca",
    "vase": "vas_kaca",
    "tire": "ban_bekas",
    "shoe": "sepatu_bekas",
    "sneaker": "sepatu_bekas",
    "clothes": "baju_bekas",
    "banana": "kulit_pisang",
    "apple": "buah_busuk",
    "orange": "kulit_jeruk",
    "broccoli": "sayuran_busuk",
    "carrot": "sayuran_busuk",
    "laptop": "pcb",
    "cell phone": "handphone_rusak",
    "keyboard": "keyboard_rusak",
    "mouse": "mouse_rusak",
    "remote": "remote_tv",
}

FILENAME_HINTS = {
    **{key: key for key in ITEM_BY_KEY},
    "botol": "botol_plastik",
    "plastik": "botol_plastik",
    "plastic": "botol_plastik",
    "kertas": "kertas_hvs",
    "paper": "kertas_hvs",
    "kardus": "kardus",
    "logam": "kaleng_minuman",
    "metal": "kaleng_minuman",
    "kaleng": "kaleng_minuman",
    "kaca": "botol_kaca",
    "glass": "botol_kaca",
    "organik": "sisa_makanan",
    "organic": "sisa_makanan",
    "elektronik": "kabel_usb",
    "electronic": "kabel_usb",
    "ban": "ban_bekas",
    "kain": "baju_bekas",
}


class WasteDetector:
    """Wrapper deteksi sampah.

    Prioritas:
    1. Gunakan YOLO custom `models/yolov8_waste.pt` jika tersedia.
    2. Jika belum ada, coba YOLOv8 pretrained sebagai basis.
    3. Jika YOLO/OpenCV belum siap, gunakan analisis visual ringan agar demo tetap berjalan.
    """

    def __init__(self, model_path: Path):
        self.model = None
        self.model_name = "Analisis visual fallback"
        try:
            cache_dir = model_path.parent.parent / ".cache" / "matplotlib"
            ultralytics_dir = model_path.parent.parent / ".cache" / "ultralytics"
            cache_dir.mkdir(parents=True, exist_ok=True)
            ultralytics_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
            os.environ.setdefault("YOLO_CONFIG_DIR", str(ultralytics_dir))
            os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(ultralytics_dir))
            from ultralytics import YOLO

            if model_path.exists() and model_path.stat().st_size > 0:
                self.model = YOLO(str(model_path))
                self.model_name = model_path.name
            elif (model_path.parent / "yolov8n.pt").exists():
                self.model = YOLO(str(model_path.parent / "yolov8n.pt"))
                self.model_name = "YOLOv8 pretrained lokal"
            else:
                self.model = YOLO("yolov8n.pt")
                self.model_name = "YOLOv8 pretrained"
        except Exception:
            self.model = None

    def analyze(self, image_path: Path) -> dict:
        image = self._read_image(image_path)
        yolo_label, yolo_confidence = self._run_yolo(image_path)
        item = self._map_label(yolo_label) if yolo_label else None
        needs_more_data = False
        if not item:
            filename_item = self._item_from_filename(image_path)
            if filename_item:
                item = filename_item
            else:
                item, heuristic_confidence, needs_more_data = self._heuristic_item(image)
                if not yolo_confidence:
                    yolo_confidence = heuristic_confidence

        condition = self._condition_from_image(image)
        item = item or default_item_for_category("Campuran")
        return {
            "item_key": item.item_key,
            "item_name": item.item_name,
            "category": item.category,
            "detected_label": yolo_label or ("Perlu data tambahan" if needs_more_data else f"{self.model_name}: visual heuristic"),
            "confidence": round(float(yolo_confidence or 0.62), 2),
            "condition": condition,
            "needs_more_data": needs_more_data,
        }

    def _read_image(self, image_path: Path) -> np.ndarray:
        if cv2 is not None:
            image = cv2.imread(str(image_path))
            if image is not None:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if Image is None:
            raise RuntimeError("Pillow/OpenCV tidak tersedia untuk membaca gambar.")
        return np.array(Image.open(image_path).convert("RGB"))

    def _run_yolo(self, image_path: Path) -> tuple[str | None, float | None]:
        if self.model is None:
            return None, None
        try:
            results = self.model(str(image_path), verbose=False)
            best_label, best_conf = None, 0.0
            for result in results:
                names = result.names
                probs = getattr(result, "probs", None)
                if probs is not None and getattr(probs, "top1", None) is not None:
                    conf = float(probs.top1conf)
                    if conf > best_conf:
                        best_conf = conf
                        best_label = names[int(probs.top1)]
                for box in getattr(result, "boxes", []):
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        best_conf = conf
                        best_label = names[int(box.cls[0])]
            return best_label, best_conf
        except Exception:
            return None, None

    def _map_label(self, label: str | None):
        if not label:
            return None
        normalized = label.lower().strip()
        direct = get_item(normalize_label(normalized), normalized)
        if direct:
            return direct
        for key, value in YOLO_LABEL_MAP.items():
            if key in normalized:
                return get_item(value) or default_item_for_category(value)
        return None

    def _item_from_filename(self, image_path: Path):
        name = image_path.name.lower()
        for key, value in FILENAME_HINTS.items():
            if key in name:
                return get_item(value) or default_item_for_category(value)
        return None

    def _heuristic_item(self, image: np.ndarray):
        sample = image.reshape(-1, 3).astype(np.float32)
        brightness = sample.mean()
        channel_std = sample.std(axis=1).mean()
        green_ratio = np.mean((sample[:, 1] > sample[:, 0] * 1.08) & (sample[:, 1] > sample[:, 2] * 1.08))
        gray_ratio = np.mean(np.max(sample, axis=1) - np.min(sample, axis=1) < 18)
        bright_ratio = np.mean(np.mean(sample, axis=1) > 205)

        if green_ratio > 0.28:
            return ITEM_BY_KEY["daun_kering"], 0.58, False
        if gray_ratio > 0.45 and brightness > 90:
            return ITEM_BY_KEY["kaleng_minuman"], 0.56, False
        if bright_ratio > 0.55 and channel_std < 34:
            return ITEM_BY_KEY["kertas_hvs"], 0.55, False
        if gray_ratio > 0.35 and brightness > 150:
            return ITEM_BY_KEY["botol_kaca"], 0.52, False
        if channel_std > 42:
            return ITEM_BY_KEY["botol_plastik"], 0.54, False
        return ITEM_BY_KEY["sampah_tidak_terpilah"], 0.35, True

    def _condition_from_image(self, image: np.ndarray) -> str:
        gray = np.mean(image, axis=2).astype(np.uint8)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        dark_ratio = float(np.mean(gray < 45))

        if cv2 is not None:
            edges = cv2.Canny(gray, 70, 150)
            edge_density = float(np.mean(edges > 0))
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        else:
            gy, gx = np.gradient(gray.astype(float))
            edge_density = float(np.mean(np.sqrt(gx * gx + gy * gy) > 35))
            blur_score = contrast * contrast

        # Aturan sederhana berbasis visual: terlalu gelap/kotor, sangat blur, atau tepi terlalu padat
        # biasanya menandakan sampah basah, pecah, bercampur, atau kondisi rusak.
        if brightness < 45 or dark_ratio > 0.48 or (edge_density > 0.24 and contrast > 68):
            return "Sangat rusak"
        if brightness < 70 or blur_score < 35 or edge_density > 0.17:
            return "Rusak"
        if brightness < 105 or contrast > 62:
            return "Sedang"
        return "Baik"
