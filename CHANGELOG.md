# Changelog

All notable changes to EcoLens are documented in this file.

## [1.0.0] - 2026-06-26

### Added

- Flask web application for AI-assisted waste analysis.
- MySQL database integration for `analysis_results`, `waste_items`, `dataset_images`, and `users`.
- Dashboard with real database-driven statistics, category chart, trend chart, potential chart, and recent activity.
- Specific waste item catalog with 90 common Indonesian waste objects.
- Analysis flow with pending verification before saving to history.
- Upload, camera, dataset, history, report, and about pages.
- Excel and PDF report export.
- Dataset manager for train/valid/test and specific object folders.
- Public dataset download helper.
- Two-stage dataset sorter for raw, categorized, specific, and unknown folders.
- YOLO training helper.
- Professional README, MIT license, contribution guide, environment example, and real screenshots.

### Security

- Secrets and credentials moved to environment variables.
- `.gitignore` excludes local database files, `.env`, virtual environments, dataset images, upload/capture files, model weights, cache, and training outputs.
- SQL queries use parameterized PyMySQL calls.

### Notes

- Large datasets and model weights are intentionally not included in the repository.
- Place custom model weights at `models/yolov8_waste.pt`.
- Use `utils/download_dataset.py` and `utils/sort_dataset.py` to prepare local training data.
