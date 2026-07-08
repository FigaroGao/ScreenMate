/**
 * ScreenMate Settings — auto-load, save, reset, test connection.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;

    var form = document.getElementById('settings-form');
    var btnTest = document.getElementById('btn-test-connection');
    var btnSave = document.getElementById('btn-save-settings');
    var btnReset = document.getElementById('btn-reset-settings');

    // ==================================================================
    // 1. Load current settings on page open
    // ==================================================================
    async function loadSettings() {
        try {
            var data = await api.get('/api/settings');
            if (!data.success || !data.settings) return;

            var s = data.settings;
            // Fill each form field by name if it exists in the response
            var fields = form.querySelectorAll('[name]');
            fields.forEach(function (el) {
                var key = el.getAttribute('name');
                if (s[key] !== undefined) {
                    var val = s[key];
                    // Don't fill masked API key placeholders
                    if (val === '***') val = '';
                    if (el.type === 'checkbox') {
                        el.checked = (val === true || val === 'true');
                    } else {
                        el.value = val;
                    }
                }
            });
        } catch (err) {
            console.warn('Failed to load settings:', err);
        }
    }

    loadSettings();

    // ==================================================================
    // 2. Test Connection (real for vision providers)
    // ==================================================================
    if (btnTest) {
        btnTest.addEventListener('click', async function () {
            var provSelect = document.getElementById('vision-provider-select');
            var provName = provSelect ? provSelect.value : 'mock';

            btnLoading(btnTest, 'Testing...');
            try {
                var data = await api.post('/api/provider/test', {
                    type: 'vision',
                    provider: provName,
                });
                if (data.success) {
                    toast(data.message, 'success', 'Connection OK');
                } else {
                    toast(data.message, 'danger', 'Connection Failed');
                }
            } catch (err) {
                toast(err.message, 'danger', 'Connection Error');
            } finally {
                btnRestore(btnTest);
            }
        });
    }

    // ==================================================================
    // 3. Save Settings
    // ==================================================================
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            // Build payload from all named fields
            var formData = new FormData(form);
            var payload = {};
            formData.forEach(function (val, key) {
                // Skip masked placeholder values
                if (val === '***') return;
                payload[key] = val;
            });

            btnLoading(btnSave, 'Saving...');
            try {
                var data = await api.post('/api/settings', payload);
                toast(data.message || 'Settings saved.', data.success ? 'success' : 'danger');
                // Do NOT reload from API — it returns masked "***" for keys.
                // Form values stay as-is since save succeeded.
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnSave);
            }
        });
    }

    // ==================================================================
    // 4. Restore Defaults
    // ==================================================================
    if (btnReset) {
        btnReset.addEventListener('click', async function () {
            if (!confirm('Reset all settings to defaults? This cannot be undone.')) return;
            btnLoading(btnReset, 'Resetting...');
            try {
                var data = await api.post('/api/settings/reset');
                toast(data.message || 'Settings reset.', data.success ? 'success' : 'info');
                if (data.success) {
                    await loadSettings();
                }
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnReset);
            }
        });
    }
})();
