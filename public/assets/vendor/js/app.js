/*
 * Mini Framework Engine — global UI glue script.
 * Loaded once from base.twig, AFTER axios.min.js, sweetalert2.all.min.js,
 * choices.min.js and flatpickr.min.js.
 *
 * HTML contract this file expects from base.twig / layouts:
 *   <meta name="csrf-name"  content="{{ csrf.name }}">
 *   <meta name="csrf-value" content="{{ csrf.value }}">
 *   <div id="app-loader" class="hidden fixed inset-0 z-50 ...">...</div>
 *   <button id="sidebar-toggle"> (in navbar.twig, lg:hidden)
 *   <aside id="sidebar"> (sidebar.twig, starts off-screen on mobile via -translate-x-full)
 *   <div id="sidebar-backdrop" class="hidden fixed inset-0 z-20 ... lg:hidden"> (base.twig)
 *
 * Form conventions used across all Twig views:
 *   - <form method="POST"> shows the loader automatically on submit.
 *   - <form method="GET" data-no-loader> never shows the loader.
 *   - <form class="js-confirm-delete" data-confirm-title="..." data-confirm-text="...">
 *     intercepts submit and asks for SweetAlert2 confirmation before posting.
 *   - <input class="datepicker"> is auto-initialized with Flatpickr.
 *   - <select class="data-choices"> is auto-initialized with Choices.js
 *     (NOT the class "select2" — this project does not use jQuery Select2).
 */
(function () {
    'use strict';

    function getMeta(name) {
        var el = document.querySelector('meta[name="' + name + '"]');
        return el ? el.getAttribute('content') : null;
    }

    var CSRF_NAME = getMeta('csrf-name');
    var CSRF_VALUE = getMeta('csrf-value');

    // --- Axios global defaults -------------------------------------------------
    if (window.axios) {
        axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
        if (CSRF_NAME && CSRF_VALUE) {
            axios.defaults.headers.common[CSRF_NAME] = CSRF_VALUE;
        }

        axios.interceptors.request.use(function (config) {
            showLoader();
            return config;
        }, function (error) {
            hideLoader();
            return Promise.reject(error);
        });

        axios.interceptors.response.use(function (response) {
            hideLoader();
            return response;
        }, function (error) {
            hideLoader();
            var message = (error.response && error.response.data && error.response.data.message)
                || 'Terjadi kesalahan. Silakan coba lagi.';
            if (window.Swal) {
                Swal.fire({ icon: 'error', title: 'Gagal', text: message });
            }
            return Promise.reject(error);
        });
    }

    // --- Page loading overlay ---------------------------------------------------
    function showLoader() {
        var loader = document.getElementById('app-loader');
        if (loader) loader.classList.remove('hidden');
    }

    function hideLoader() {
        var loader = document.getElementById('app-loader');
        if (loader) loader.classList.add('hidden');
    }

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.hasAttribute('data-no-loader')) return;
        if (form.classList.contains('js-confirm-delete')) return; // handled separately
        if (form.method && form.method.toUpperCase() === 'GET' && !form.method) return;
        showLoader();
    });

    // --- SweetAlert2 delete confirmation ----------------------------------------
    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (!form.classList.contains('js-confirm-delete')) return;
        if (form.dataset.confirmed === 'true') return; // already confirmed, let it submit

        event.preventDefault();

        if (!window.Swal) {
            form.submit();
            return;
        }

        Swal.fire({
            title: form.dataset.confirmTitle || 'Hapus data?',
            text: form.dataset.confirmText || 'Data yang dihapus tidak dapat dikembalikan.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Ya, hapus',
            cancelButtonText: 'Batal',
            confirmButtonColor: '#166534'
        }).then(function (result) {
            if (result.isConfirmed) {
                form.dataset.confirmed = 'true';
                showLoader();
                form.submit();
            }
        });
    });

    // --- Mobile sidebar toggle ---------------------------------------------------
    function initSidebarToggle() {
        var toggle = document.getElementById('sidebar-toggle');
        var sidebar = document.getElementById('sidebar');
        var backdrop = document.getElementById('sidebar-backdrop');
        if (!toggle || !sidebar) return;

        function openSidebar() {
            sidebar.classList.remove('-translate-x-full');
            if (backdrop) backdrop.classList.remove('hidden');
            toggle.setAttribute('aria-expanded', 'true');
        }

        function closeSidebar() {
            sidebar.classList.add('-translate-x-full');
            if (backdrop) backdrop.classList.add('hidden');
            toggle.setAttribute('aria-expanded', 'false');
        }

        toggle.addEventListener('click', function () {
            if (sidebar.classList.contains('-translate-x-full')) {
                openSidebar();
            } else {
                closeSidebar();
            }
        });

        if (backdrop) backdrop.addEventListener('click', closeSidebar);
    }

    // --- Component auto-init -----------------------------------------------------
    function initComponents() {
        if (window.flatpickr) {
            document.querySelectorAll('.datepicker').forEach(function (el) {
                if (!el._flatpickr) flatpickr(el, { dateFormat: 'Y-m-d', allowInput: true });
            });
        }

        if (window.Choices) {
            document.querySelectorAll('.data-choices').forEach(function (el) {
                if (!el.dataset.choicesInitialized) {
                    new Choices(el, { searchEnabled: true, itemSelectText: '' });
                    el.dataset.choicesInitialized = 'true';
                }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initComponents();
        initSidebarToggle();
    });
})();
