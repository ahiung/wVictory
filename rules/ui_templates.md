# Base UI Templates

Panduan *layout* ini **WAJIB** digunakan oleh AI saat melakukan *scaffolding* tampilan aplikasi untuk memastikan konsistensi UI. UI ini didesain menggunakan **Tailwind CSS**.

## 1. Base Layout (`base.twig`)
Layout utama terdiri dari Navbar lebar penuh di paling atas, dan area konten di bawahnya yang terbagi menjadi Sidebar (kiri) dan Main Content (kanan).

```html
<body class="bg-gray-50 font-sans text-gray-900 antialiased">
    <div class="flex flex-col h-screen overflow-hidden">
        <!-- Top Navbar -->
        {% include 'partials/navbar.twig' %}
        
        <!-- Bottom Layout: Sidebar & Content -->
        <div class="flex flex-1 overflow-hidden">
            <!-- Sidebar -->
            {% include 'partials/sidebar.twig' %}
            
            <!-- Main Content -->
            <div class="flex-1 overflow-y-auto">
                <main class="p-4 md:p-6 lg:p-8">
                    {% block content %}{% endblock %}
                </main>
            </div>
        </div>
    </div>
</body>
```

## 2. Navbar (`navbar.twig`)
Navbar berisi Logo di kiri dan Avatar Inisial (menggunakan *filter* Twig `initials`) di kanan. Aksen utama menggunakan `green-800`.

```html
<header class="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-10 relative">
    <!-- Left: Logo -->
    <div class="flex items-center gap-3">
        <div class="bg-green-800 text-white rounded p-1.5 flex items-center justify-center h-8 w-8">
            <!-- SVG Logo -->
        </div>
        <h1 class="text-xl font-bold text-gray-800">{{ app_name }}</h1>
    </div>

    <!-- Right: Profile / Avatar -->
    <div class="flex items-center gap-4">
        <div class="relative group cursor-pointer">
            <!-- Initials Avatar -->
            <div class="w-9 h-9 rounded-full bg-green-800 text-white flex items-center justify-center text-sm font-semibold">
                {{ auth_user.name|initials }}
            </div>
            <!-- Dropdown content goes here (hidden by default, shown on group-hover) -->
        </div>
    </div>
</header>
```

## 3. Sidebar (`sidebar.twig`) — GENERIC RENDERER, JANGAN DIEDIT PER MODUL
Referensi struktur: **Flowbite Admin Dashboard** (github.com/themesberg/flowbite-admin-dashboard) — lihat `mini_framework.json` → `design_system`. Warna brand tetap `green-800` kita, bukan skema abu-abu default mereka.

Sidebar **BUKAN** file yang diedit setiap ada modul baru. Ia adalah renderer generik yang loop atas Twig global `menu` (dibangun oleh `App\Support\MenuBuilder` dari `app/menu.php`, di-inject di `AuthMiddleware`). Menu *accordion* (seperti Sistem Otorisasi) otomatis muncul kalau item punya `children`, memakai mekanisme collapse **native Flowbite** (`data-collapse-toggle`, dari `flowbite.min.js` yang sudah dimuat) — **BUKAN** `<details>`/`<summary>` HTML5 (pola versi sebelumnya, sudah usang).

**Untuk menambah link nav modul baru: tambahkan SATU entri array di `app/menu.php` (lihat `mini_framework.json` → `canonical_snippets.menu_registry_pattern.menu_php_template`). JANGAN PERNAH edit HTML di `sidebar.twig` untuk ini** — satu-satunya bagian `sidebar.twig` yang boleh disentuh modul baru adalah menambah key baru ke dict `icons` di baris atas, kalau butuh ikon yang belum ada.

```html
<style>
    /* Flowbite hanya toggle class "hidden" + aria-expanded, rotasi chevron ditangani CSS murni di sini */
    [data-collapse-toggle][aria-expanded="true"] .chevron { transform: rotate(180deg); }
</style>
{% set icons = {
    'dashboard': '<svg ...>...</svg>',
    'shield': '<svg ...>...</svg>'
} %}
<aside class="w-64 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0 flex flex-col pt-4 pb-10">
    <nav class="flex-1 px-3 space-y-1.5">
        {% for item in menu %}
            {% if item.children is defined and item.children|length > 0 %}
            <button type="button" class="flex items-center justify-between w-full px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-green-800 rounded-lg" data-collapse-toggle="menu-{{ item.id }}" aria-controls="menu-{{ item.id }}" aria-expanded="false">
                <span class="flex items-center gap-3">
                    {% if item.icon and icons[item.icon] is defined %}{{ icons[item.icon]|raw }}{% endif %}
                    <span>{{ item.label }}</span>
                </span>
                <svg class="chevron w-4 h-4 text-gray-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <ul id="menu-{{ item.id }}" class="hidden mt-1 space-y-1">
                {% for child in item.children %}
                <li><a href="{{ child.route }}" class="flex items-center gap-3 pl-11 pr-3 py-2 text-sm font-medium text-gray-600 hover:text-green-800 hover:bg-gray-50 rounded-lg">{{ child.label }}</a></li>
                {% endfor %}
            </ul>
            {% else %}
            <a href="{{ item.route }}" class="flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50 hover:text-green-800">
                {% if item.icon and icons[item.icon] is defined %}{{ icons[item.icon]|raw }}{% endif %}
                <span>{{ item.label }}</span>
            </a>
            {% endif %}
        {% endfor %}
    </nav>
</aside>
```

## 4. Dashboard Cards
Format standar untuk *card* di dalam halaman konten. Gunakan `rounded-2xl`, `bg-white`, dan `shadow-sm`.

### 4.1 Welcome Card (Full Width)
Digunakan di bagian atas *dashboard*.
```html
<div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
    <div class="flex items-center gap-4">
        <!-- Box Ikon Akses (w-12 h-12 bg-green-50) -->
        <div class="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center flex-shrink-0">...</div>
        <div>
            <h2 class="text-xl font-bold text-gray-900">Dashboard Utama</h2>
            <p class="text-sm text-gray-500 mt-1">Deskripsi singkat</p>
        </div>
    </div>
    <!-- Kotak Info Tambahan (misal: Lokasi) -->
    <div class="border border-gray-200 rounded-xl px-5 py-4 flex items-center gap-4">
        <!-- SVG Icon -->
        <div>
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Label</p>
            <p class="text-sm font-semibold text-gray-900">Nilai</p>
        </div>
    </div>
</div>
```

### 4.2 Statistic Cards (Grid)
Digunakan untuk metrik KPI berupa grid berjajar.
```html
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex items-center justify-between">
        <div>
            <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Hak Akses / Roles</p>
            <h3 class="text-3xl font-extrabold text-gray-900">2</h3>
        </div>
        <!-- Ikon Akses -->
        <div class="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-green-700">...</svg>
        </div>
    </div>
</div>
```

## 5. CRUD List / Data Table Template
Digunakan untuk halaman indeks/tabel data pada setiap modul CRUD (seperti Master Data, Daftar Transaksi, dsb). Elemen *hardcoded* harus diganti dengan sintaks Twig (misal `{{ items.currentPage }}`).

```html
<div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
    <!-- Header Modul & Tombol Aksi -->
    <div class="p-6 border-b border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h2 class="text-xl font-bold text-gray-900">{{ module_title }}</h2>
            <p class="text-sm text-gray-500 mt-1">{{ module_description }}</p>
        </div>
        <div class="flex items-center gap-3">
            <button type="button" class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                <svg class="w-4 h-4">...</svg> Export CSV
            </button>
            <a href="/{{ module_route }}/create" class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-lg hover:bg-green-50 hover:text-green-800 transition-colors shadow-sm">
                <svg class="w-4 h-4">...</svg> Tambah {{ entity_name }}
            </a>
        </div>
    </div>

    <!-- Filter & Pencarian -->
    <div class="p-4 border-b border-gray-200 bg-gray-50 flex flex-col md:flex-row gap-4">
        <form method="GET" class="flex items-center gap-2 w-full md:max-w-md">
            <input type="text" name="search" placeholder="Cari data..." value="{{ search }}" class="w-full bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-green-500 focus:border-green-500 p-2.5">
            <button type="submit" class="p-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                <svg class="w-4 h-4">...</svg>
            </button>
        </form>
    </div>

    <!-- Tabel Data -->
    <div class="overflow-x-auto">
        <table class="w-full text-sm text-left text-gray-600">
            <thead class="text-[11px] text-gray-400 uppercase bg-gray-50">
                <tr>
                    <th scope="col" class="px-6 py-4 font-bold">No.</th>
                    <th scope="col" class="px-6 py-4 font-bold">Kolom 1</th>
                    <th scope="col" class="px-6 py-4 font-bold">Kolom 2</th>
                    <th scope="col" class="px-6 py-4 font-bold">Status</th>
                    <th scope="col" class="px-6 py-4 font-bold text-center">Aksi</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                <!-- Baris Data Berulang -->
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="px-6 py-4">1</td>
                    <td class="px-6 py-4 font-medium text-gray-900">Data 1</td>
                    <td class="px-6 py-4">Data 2</td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded-md">Aktif</span>
                    </td>
                    <td class="px-6 py-4">
                        <div class="flex items-center justify-center gap-3">
                            <a href="#" class="text-gray-400 hover:text-green-700" title="Detail"><svg class="w-4 h-4">...</svg></a>
                            <a href="#" class="text-gray-400 hover:text-blue-600" title="Edit"><svg class="w-4 h-4">...</svg></a>
                            <!-- JANGAN pakai onsubmit="confirm(...)" native — requirement step 9 (sweetalert_confirm_delete) wajib pakai SweetAlert2 via app.js. Kelas js-confirm-delete di-intercept otomatis oleh app.js. -->
                            <form action="#" method="POST" class="inline js-confirm-delete" data-confirm-title="Hapus data?" data-confirm-text="Data yang dihapus tidak dapat dikembalikan.">
                                <input type="hidden" name="{{ csrf.keys.name }}" value="{{ csrf.name }}">
                                <input type="hidden" name="{{ csrf.keys.value }}" value="{{ csrf.value }}">
                                <button type="submit" class="text-gray-400 hover:text-red-600" title="Hapus"><svg class="w-4 h-4">...</svg></button>
                            </form>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Pagination Footer -->
    <div class="p-4 border-t border-gray-200 flex items-center justify-between">
        <p class="text-sm text-gray-500">Halaman <span class="font-bold text-gray-900">1</span> dari <span class="font-bold text-gray-900">10</span> (<span class="font-bold text-gray-900">150</span> Record)</p>
        <div class="flex items-center gap-1">
            <a href="#" class="px-3 py-1.5 text-sm text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50">Sebelumnya</a>
            <a href="#" class="px-3 py-1.5 text-sm font-medium text-white bg-green-800 rounded-md">1</a>
            <a href="#" class="px-3 py-1.5 text-sm text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50">2</a>
            <a href="#" class="px-3 py-1.5 text-sm text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50">Berikutnya</a>
        </div>
    </div>
</div>
```

## 6. Form Input & Komponen Interaktif
Sistem basis kita otomatis menginisialisasi pustaka UI modern dengan hanya menyematkan kelas CSS:

- **Tanggal (Flatpickr)**: Tambahkan kelas `datepicker` pada input.
  `<input type="text" name="tgl_lahir" class="datepicker w-full rounded-lg border-gray-300 ...">`
- **Dropdown Pencarian (Choices.js)**: Tambahkan kelas `data-choices` pada tag `<select>`. **JANGAN** pakai nama kelas `select2` — library asli di sini adalah **Choices.js** (`new Choices(el)`), BUKAN jQuery Select2 (`$(...).select2()`). Kedua API tidak kompatibel.
  `<select name="kategori_id" class="data-choices"><option>...</option></select>`
- **Loading Overlay**: Otomatis muncul (membekukan layar) setiap kali formulir di-*submit* (`<form method="POST">`). Jika Anda ingin membuat form pencarian GET (misal di halaman index) yang TIDAK perlu memunculkan loading bar saat di-enter, tambahkan atribut `data-no-loader` pada tag form:
  `<form method="GET" data-no-loader>`

## 7. Form Add/Edit Generik — Field Schema Pattern

**WAJIB** dipakai untuk SEMUA form Add/Edit dan kolom tabel List di modul CRUD manapun (bukan cuma POS — pola ini generik, dipakai berulang di project apapun, persis seperti `field.xml` PHPMaker). Template lengkap ada di `mini_framework.json` → `canonical_snippets.field_schema_pattern`. Ringkasnya:

1. Setiap modul punya **satu file schema** — `app/FieldSchemas/{ModelName}FieldSchema.php` — array kecil berisi definisi tiap field: `name`, `label`, `type` (`text|textarea|number|date|select|checkbox|password` — cuma 7 ini, jangan bikin type baru), `rules` (string Rakit, **tanpa** rule `string` — lihat `verified_gotchas`), `options` (isi untuk `select`), `show_in` (kombinasi `list`/`add`/`edit`).
2. File ini **satu-satunya sumber kebenaran** — dipakai ulang oleh 3 tempat:
   - `{Action}{ModelName}Request::validate()` — rules Rakit di-derive dari schema, bukan ditulis manual.
   - Form Add/Edit — loop schema lewat macro `partials/_form_field.twig` (dibuat sekali, dipakai semua modul).
   - Kolom tabel List — loop schema yang sama untuk `<th>`/`<td>`.
3. **JANGAN PERNAH** menulis `<input>` atau `<td>` manual untuk field yang sudah ada di schema — cukup tambah/ubah entri array-nya. Ini mencegah AI menulis ulang markup form dari nol setiap modul baru, dan menjamin validasi tidak pernah "lupa sinkron" dengan form-nya.

Beda dengan `app/Hooks/{ModelName}Hooks.php` (dibuat sekali, tidak boleh diubah lagi) — file schema ini **memang dimaksudkan untuk diedit ulang** setiap kali field model berubah (tambah/hapus/ganti nama kolom).

## 8. Form Manajemen RBAC (Role / Permission / User)

Template lengkap: `mini_framework.json` → `canonical_snippets.rbac_management_forms_pattern`. Tiga form berbeda, dua di antaranya cukup pakai pola Field Schema (section 7) apa adanya, satu butuh pola khusus:

1. **Kelola Role** — modul CRUD biasa, pakai Field Schema pattern langsung (`RoleFieldSchema.php`: field `name` + `slug`). Tidak ada yang spesial.
2. **Kelola User** — modul CRUD biasa juga (`UserFieldSchema.php`: `name`, `username`, `role_id` bertipe `select`), **KECUALI** field `password`: type-nya `password` (baru, ke-7), dan `show_in` cuma `['add']` — sengaja **tidak muncul** di form Edit. Alasan: admin yang edit akun orang lain tidak boleh melihat/menyetel password mentah orang itu.
3. **Assign Permission ke Role** — **BUKAN** pakai Field Schema (ini bukan form input teks biasa, tapi grid checkbox dikelompokkan per `module`). Halaman tersendiri (`roles/permissions.twig`), checkbox per permission, dikelompokkan pakai kolom `module` yang sudah ada di tabel `permissions`. Simpan pakai `$role->permissions()->sync($ids)` — satu baris, tidak perlu logic diff/hapus manual.

**Reset password (bukan edit form)**: karena form Edit User tidak punya field password, ganti password oleh admin dilakukan lewat **aksi terpisah** ("Reset Password" per baris user) — generate password acak + `must_change_password = true`, pola yang **sama persis** dengan superadmin awal di `bin/setup.php`. Konsisten, tidak menambah pola keamanan baru.
