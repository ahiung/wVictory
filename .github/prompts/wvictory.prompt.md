---
mode: agent
description: Generate atau ubah kode wVictory (Slim 4 + Eloquent + Twig) mengikuti 10-step pipeline, canonical snippets, dan regression suite.
---

# wVictory

Baca `.claude/skills/wvictory/SKILL.md` lebih dulu — itu prosedur lengkapnya, satu-satunya salinan. Prompt ini hanya urutan kerjanya.

## 1. Orientasi

```bash
python tools/spec.py map
```

Cek juga `PROJECT_BRAIN.json` untuk tahu apa yang sudah ada. Kalau `app/`, `routes/`, dan `resources/` belum ada, proyek masih kosong — **tanyakan dulu** ke user, jangan asal menulis file:

> Proyek ini masih baru/kosong. Mau inisialisasi Starter Skeleton Boilerplate dulu (Auth, Login, Profile, Base Layout, Sidebar, Navbar), atau langsung buat modul?

## 2. Kerjakan

**Modul baru/berubah** — ikuti 10 langkah dari `spec.py map`, berurutan. Untuk tiap langkah: `python tools/spec.py step <n>`, lalu `show` snippet yang disebutkan, lalu **salin verbatim**. Dua langkah yang paling sering terlewat: langkah 2 (seeder permission) dan langkah 10 (entri menu) — lewat salah satunya, modulnya ada tapi tidak bisa diakses siapa pun.

**Bug di app hasil generate** — perbaiki **canonical snippet**-nya, bukan cuma file hasil generate, kalau tidak generasi berikutnya memunculkannya lagi. Lalu tambahkan entri `verified_gotchas` (gejala, akar masalah, perbaikan), dan kalau bisa dijadikan assertion tambahkan check di `eval/run.py` dengan `gotcha="<key>"`.

## 3. Aturan yang bukan soal selera

Tiap aturan ini ada karena sebuah generasi nyata pernah rusak. Lengkapnya: `python tools/spec.py rules`.

- **Slim 4, bukan Laravel.** Tidak ada `View::` / `DB::` / `Validator::`, tidak ada `Illuminate\Http\Request`, tidak ada `FormRequest`. Controller memakai `ServerRequestInterface` / `ResponseInterface`.
- **Salin verbatim.** Apa pun yang ada di `canonical_snippets` disalin, tidak pernah diketik ulang dari ingatan.
- **Constructor dan call-site satu paket.** Kelas yang di-`new` manual (semua middleware di `routes/web.php`) — ambil kelas *dan* baris instansiasinya dari snippet yang sama, di langkah yang sama.
- **Dilarang fetch eksternal.** Tidak ada curl/wget/download saat generasi. Aset frontend sudah ada di `public/assets/vendor/`. Kalau terasa ada yang kurang, laporkan — jangan mengunduh.
- **Hooks ditulis sekali.** Kalau `app/Hooks/{Model}Hooks.php` sudah ada, jangan disentuh sama sekali, kecuali user eksplisit minta mengedit file itu.
- **Tanpa placeholder.** Tidak ada `// TODO`, tidak ada method kosong.
- **Dark mode mati.** Jangan keluarkan class `dark:`.

## 4. Tutup task

```bash
python eval/run.py
```

Update `PROJECT_BRAIN.json` (`last_feature`, `last_migration`, `last_updated`, `modules_completed`, `known_issues_log`) memakai skema yang sudah ada. Keduanya bagian dari "selesai", bukan tugas tambahan.
