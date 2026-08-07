# wVictory — Bootstrap Wajib untuk AI Agent

Direktori ini adalah **spec generator**, bukan aplikasi jadi. Kode aplikasi (PHP 8.2+ / Slim 4 / Eloquent / Twig / Tailwind) di-generate **ke dalam direktori ini** dengan mengikuti spec di bawah. Kalau `app/`, `routes/`, atau `resources/` belum ada, berarti proyek masih kosong — jalankan `onboarding_protocol` lebih dulu (tanyakan Starter Skeleton vs modul langsung), jangan asal menulis file.

---

## 🚨 1. Baca ini di awal SETIAP task — tanpa kecuali

| Urutan | File | Isi |
|---|---|---|
| 1 | `mini_framework.json` | Engine spec: identity rules, `execution_pipeline` (10 langkah), `canonical_snippets` (kode literal), `verified_gotchas` (bug yang sudah terbukti), `design_system` |
| 2 | `starter_boilerplate_blueprint.json` | Struktur direktori + fitur wajib starter (Auth, Profile, Dashboard, RBAC, `bin/setup.php`) |
| 3 | `rules/ui_templates.md` | Markup Twig yang sudah jadi (base layout, navbar, sidebar, tabel, form) |
| 4 | `PROJECT_BRAIN.json` | State proyek saat ini: modul yang sudah selesai, migrasi terakhir, isu terbuka |

**Jangan menulis satu baris kode pun sebelum keempatnya dibaca.** Spec ini ditulis untuk model kecil/lokal: setiap aturan di dalamnya ada karena sebuah bug nyata pernah terjadi, bukan karena preferensi gaya.

---

## 🚨 2. Pipeline eksekusi

Setiap permintaan fitur/modul WAJIB mengikuti **10-Step Mandatory Execution Pipeline** di `mini_framework.json` → `execution_pipeline.steps`, berurutan:

`migration_sql` → `rbac_permission_seeder` → `eloquent_model` → `form_requests` → `service_layer` → `di_container_wiring` → `controller_layer` → `routes_and_middleware` → `view_templates` → `sidebar_navigation`

Melewati satu langkah (paling sering: seeder permission dan registrasi menu) menghasilkan modul yang tidak bisa diakses siapa pun.

---

## 🚨 3. Aturan keras yang tidak boleh dilanggar

- **SLIM 4, BUKAN LARAVEL.** Dilarang memakai Facade (`View::`, `DB::`, `Validator::`) atau `Illuminate\Http\Request`. Controller selalu memakai `Psr\Http\Message\ServerRequestInterface` / `ResponseInterface`.
- **SALIN VERBATIM, JANGAN TULIS DARI INGATAN.** File yang ada di `canonical_snippets` (`composer.json`, `public/index.php`, semua Middleware, pagination, field schema, menu registry) disalin apa adanya. Menulis ulang dari ingatan adalah penyebab langsung sebagian besar entri di `verified_gotchas`.
- **CONSTRUCTOR & CALL-SITE SATU PAKET.** Kelas yang di-`new` manual (semua middleware di `routes/web.php`) — definisi kelas dan baris `new X(...)`-nya harus diambil dari entri snippet yang sama, dalam satu langkah.
- **NO_EXTERNAL_FETCH.** Dilarang `curl`/`wget`/download apa pun saat generasi. Semua aset frontend sudah tersedia lokal di `public/assets/vendor/`, referensi desain di `reference/`. Kalau ada yang terasa kurang, laporkan — jangan mengunduh.
- **HOOK PROTECTION.** `app/Hooks/{Model}Hooks.php` dibuat **sekali seumur hidup**. Kalau filenya sudah ada, jangan disentuh, jangan ditimpa, jangan di-regenerate — kecuali user secara eksplisit minta mengedit file hooks itu. Logika bisnis manusia tinggal di sana.
- **OWASP TOP 10.** Validasi data scope, CSRF, strict type casting, SoftDeletes, tanpa CDN. Lihat `owasp_top_ten_compliance`.
- **NO_PLACEHOLDERS.** Tidak ada `// TODO`, tidak ada fungsi kosong. Semua kode harus langsung jalan.

---

## 🧠 4. Brain Evolve — wajib di akhir task

Setiap kali sebuah modul, perbaikan bug, atau perubahan penting selesai, **update `PROJECT_BRAIN.json` secara proaktif** (`current_state.last_feature`, `current_state.last_migration`, `current_state.last_updated`, `modules_completed`, `known_issues_log`).

**Jangan pernah menunggu user mengingatkan.** Ini bagian dari definisi "task selesai", bukan tugas tambahan. Gunakan skema yang sudah ada di file itu — jangan mengarang struktur baru.

---

## 5. Kalau menemukan bug nyata saat runtime

Pola kerja repo ini: bug yang terbukti terjadi dikodifikasi kembali ke spec supaya tidak terulang. Tambahkan entri baru ke `mini_framework.json` → `verified_gotchas` (jelaskan gejala, akar masalah, dan perbaikannya), dan kalau perlu perbaiki `canonical_snippets` terkait — bukan hanya menambal file hasil generate.
