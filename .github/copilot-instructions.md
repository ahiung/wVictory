# wVictory — instruksi wajib

Direktori ini adalah **spec generator**, bukan aplikasi jadi. Kode aplikasi (PHP 8.2+ / Slim 4 / Eloquent / Twig / Tailwind) di-generate **ke dalam direktori ini** mengikuti `mini_framework.json`.

## Langkah pertama, sebelum menulis kode apa pun

**Baca `.claude/skills/wvictory/SKILL.md`.** Itu prosedur lengkapnya — satu-satunya salinan. Sengaja tidak diduplikasi di sini supaya tidak ada dua versi yang saling berbeda. Nama foldernya `.claude/` karena di situ Claude Code memuatnya otomatis; isinya markdown biasa dan tidak bergantung pada tool mana pun.

Untuk task terarah, panggil `/wvictory` di chat.

## Jangan pernah membaca `mini_framework.json` utuh

Ukurannya ~86 KB (~22k token). Ambil per potong:

```bash
python tools/spec.py map          # 10 langkah pipeline + snippet yang dibutuhkan tiap langkah
python tools/spec.py rules        # aturan keras + design token
python tools/spec.py step 7       # satu langkah pipeline, lengkap
python tools/spec.py show <key>   # satu canonical snippet, apa adanya
python tools/spec.py gotcha       # 16 bug yang sudah pernah benar-benar terjadi
```

## Definisi "task selesai"

Belum selesai sampai keduanya dikerjakan, tanpa perlu diingatkan user:

1. `PROJECT_BRAIN.json` di-update (`last_feature`, `last_migration`, `last_updated`, `modules_completed`, `known_issues_log`) memakai skema yang sudah ada.
2. `python eval/run.py` dijalankan dan hijau. Setiap `FAIL` menyebut entri `verified_gotchas` yang bersangkutan — perbaiki **canonical snippet**-nya, bukan cuma file hasil generate.
