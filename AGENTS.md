# wVictory — Bootstrap Wajib untuk AI Agent

Direktori ini adalah **spec generator**, bukan aplikasi jadi. Kode aplikasi (PHP 8.2+ / Slim 4 / Eloquent / Twig / Tailwind) di-generate **ke dalam direktori ini** mengikuti `mini_framework.json`.

---

## 🚨 Langkah pertama, sebelum apa pun

**Baca `.claude/skills/wvictory/SKILL.md` sekarang.** File itu adalah prosedur lengkapnya — satu-satunya salinan, sengaja tidak diduplikasi di sini supaya tidak ada dua versi yang saling berbeda.

- **Claude Code** memuatnya otomatis sebagai skill (`wvictory`); tetap boleh dibaca langsung sebagai file.
- **Agent lain** (Antigravity, Gemini CLI, model lokal): baca sebagai file markdown biasa. Isinya tidak bergantung pada mekanisme skill apa pun.

---

## 🚨 Jangan pernah membaca `mini_framework.json` utuh

Ukurannya ~86 KB (~22k token). Membacanya penuh setiap task adalah cara tercepat kehilangan bagian yang justru relevan. Ambil per potong:

```bash
python tools/spec.py map          # 10 langkah pipeline + snippet yang dibutuhkan tiap langkah
python tools/spec.py rules        # aturan keras + design token
python tools/spec.py step 7       # satu langkah pipeline, lengkap
python tools/spec.py show <key>   # satu canonical snippet, apa adanya
python tools/spec.py gotcha       # 16 bug yang sudah pernah benar-benar terjadi
python tools/spec.py grep <teks>  # cari potongan mana yang menyebut sesuatu
```

Referensi lain: `rules/ui_templates.md` (markup Twig siap pakai), `PROJECT_BRAIN.json` (state proyek saat ini), `starter_boilerplate_blueprint.json` (struktur starter).

---

## 🚨 Definisi "task selesai"

Sebuah task belum selesai sampai keduanya dikerjakan — tanpa perlu diingatkan user:

1. **`PROJECT_BRAIN.json` di-update** (`current_state.last_feature`, `last_migration`, `last_updated`, `modules_completed`, `known_issues_log`). Pakai skema yang sudah ada, jangan mengarang struktur baru.
2. **Regression suite dijalankan:**

```bash
python eval/run.py
```

Setiap `FAIL` berarti bug yang spec-nya sudah tahu — pesannya menyebut entri `verified_gotchas` yang bersangkutan. Perbaiki **canonical snippet**-nya, bukan cuma file hasil generate.

---

## Kalau menemukan bug runtime yang baru

Pola kerja repo ini: bug yang terbukti terjadi dikodifikasi balik ke spec supaya tidak terulang.

1. Perbaiki `canonical_snippets` yang jadi sumbernya (bukan hanya file hasil generate).
2. Tambahkan entri ke `mini_framework.json` → `verified_gotchas`: gejala, akar masalah, perbaikan.
3. Kalau bisa dijadikan assertion, tambahkan check di `eval/run.py` dengan `gotcha="<key>"` supaya `python eval/run.py --coverage` tetap 16/16 dan bug itu tidak bisa kembali diam-diam.
