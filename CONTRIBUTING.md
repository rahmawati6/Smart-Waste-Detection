# Contributing to EcoLens

Terima kasih sudah tertarik berkontribusi ke EcoLens.

## Alur Kontribusi

1. Fork repository.
2. Buat branch baru:

   ```powershell
   git checkout -b feature/nama-fitur
   ```

3. Jalankan aplikasi dan test lokal.
4. Pastikan tidak ada dataset besar, model besar, upload pengguna, credential, atau cache yang ikut commit.
5. Buat pull request dengan deskripsi perubahan yang jelas.

## Standar Kode

- Gunakan Python yang mudah dibaca.
- Jangan mengubah route atau schema database tanpa alasan jelas.
- Gunakan parameterized query untuk akses database.
- Validasi file upload.
- Hindari hardcoded secret, password, token, dan path absolut.

## Checklist Pull Request

- [ ] `python -m py_compile app.py utils/*.py` lolos.
- [ ] Login berhasil.
- [ ] Semua route utama dapat dibuka.
- [ ] Dashboard tidak memakai data dummy.
- [ ] Upload/kamera tidak langsung menyimpan sebelum verifikasi.
- [ ] Riwayat dan laporan membaca data dari database.
- [ ] README diperbarui jika ada perubahan fitur.

## File yang Tidak Boleh Di-commit

- `.env`
- `.venv/`
- `dataset/`
- `dataset_yolo/images/`
- `dataset_yolo/labels/`
- `models/*.pt`
- `models/*.h5`
- `static/uploads/`
- `static/captures/`
- `*.db`
- cache Python dan log
