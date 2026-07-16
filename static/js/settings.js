/**
 * ScreenMate Settings — dynamic params, per-section save, test connections.
 */
(function () {
    'use strict';
    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;
    var escapeHtml = window.ScreenMate.escapeHtml;

    // ==================================================================
    // 1. Load current settings from API
    // ==================================================================
    async function loadSettings() {
        try {
            var data = await api.get('/api/settings');
            if (!data.success || !data.settings) return;
            var s = data.settings;
            document.querySelectorAll('[name]').forEach(function (el) {
                var key = el.getAttribute('name');
                if (s[key] !== undefined) {
                    var val = s[key];
                    if (val === '***') val = '';
                    if (el.type === 'checkbox') el.checked = (val === true || val === 'true');
                    else el.value = val;
                }
            });
            // Load custom params for each section
            loadCustomParams('vision', s.VISION_CUSTOM_PARAMS);
            loadCustomParams('chat', s.CHAT_CUSTOM_PARAMS);
            loadCustomParams('tts', s.TTS_CUSTOM_PARAMS);
        } catch (err) { console.warn('Load settings failed:', err); }
    }

    function loadCustomParams(section, jsonStr) {
        if (!jsonStr) return;
        try {
            var params = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
            if (!Array.isArray(params)) return;
            params.forEach(function (p) {
                addParamRow(section, p.name || '', p.value || '');
            });
        } catch (_) {}
    }

    // ==================================================================
    // 2. Dynamic Parameter List Component
    // ==================================================================
    function addParamRow(section, name, value) {
        var list = document.querySelector('#params-' + section + ' .param-list');
        if (!list) return;
        var row = document.createElement('div');
        row.className = 'row g-1 mb-1 param-row';
        row.innerHTML =
            '<div class="col-5"><input type="text" class="form-control form-control-sm param-name" ' +
            'placeholder="Parameter Name" value="' + escapeHtml(name || '') + '"></div>' +
            '<div class="col-6"><input type="text" class="form-control form-control-sm param-value" ' +
            'placeholder="Value" value="' + escapeHtml(value || '') + '"></div>' +
            '<div class="col-1"><button type="button" class="btn btn-outline-danger btn-sm w-100 remove-param" ' +
            'title="Remove"><i class="bi bi-x"></i></button></div>';
        row.querySelector('.remove-param').addEventListener('click', function () { row.remove(); });
        list.appendChild(row);
    }

    function getCustomParams(section) {
        var params = [];
        document.querySelectorAll('#params-' + section + ' .param-row').forEach(function (row) {
            var n = row.querySelector('.param-name').value.trim();
            if (n) params.push({ name: n, value: row.querySelector('.param-value').value });
        });
        return params;
    }

    // Wire "add param" buttons
    document.querySelectorAll('.add-param').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var section = btn.closest('.custom-params').dataset.section;
            addParamRow(section, '', '');
        });
    });

    // ==================================================================
    // 3. Per-section Save
    // ==================================================================
    document.querySelectorAll('.section-save').forEach(function (btn) {
        btn.addEventListener('click', async function () {
            var section = btn.dataset.section;
            var card = btn.closest('.card');
            if (!card) return;
            var payload = {};
            // Collect named fields in this card
            card.querySelectorAll('[name]').forEach(function (el) {
                if (el.value && el.value !== '***') payload[el.getAttribute('name')] = el.value;
            });
            // Collect custom params
            var cpKey = ({
                vision: 'VISION_CUSTOM_PARAMS',
                chat: 'CHAT_CUSTOM_PARAMS',
                tts: 'TTS_CUSTOM_PARAMS',
            })[section];
            if (cpKey) payload[cpKey] = JSON.stringify(getCustomParams(section));

            btnLoading(btn, 'Saving...');
            try {
                var data = await api.post('/api/settings', payload);
                toast(data.message || 'Saved.', data.success ? 'success' : 'danger');
            } catch (err) { toast(err.message, 'danger'); }
            finally { btnRestore(btn); }
        });
    });

    // ==================================================================
    // 4. Provider switch — reset params on change
    // ==================================================================
    document.querySelectorAll('[data-provider-select]').forEach(function (sel) {
        sel.addEventListener('change', function () {
            var section = sel.dataset.section;
            // Clear custom params when switching providers
            document.querySelectorAll('#params-' + section + ' .param-row').forEach(function (r) { r.remove(); });
            // Clear API key field too
            var keyEl = document.querySelector('[name="' + section.toUpperCase() + '_API_KEY"]');
            if (keyEl) keyEl.value = '';
        });
    });

    // ==================================================================
    // 5. Test Vision / Test Chat
    // ==================================================================
    function testProvider(type) {
        var provName = document.querySelector('[name="' + type.toUpperCase() + '_PROVIDER"]');
        return async function () {
            var name = provName ? provName.value : 'mock';
            var btn = document.getElementById('btn-test-' + type);
            btnLoading(btn, 'Testing...');
            try {
                // Save current section first so test uses latest settings
                var sectionBtn = document.querySelector('.section-save[data-section="' + type + '"]');
                if (sectionBtn) sectionBtn.click();
                await new Promise(function (r) { setTimeout(r, 300); });
                var data = await api.post('/api/provider/test', { type: type, provider: name });
                toast(data.message, data.success ? 'success' : 'danger',
                      data.success ? (type === 'vision' ? 'Vision OK' : 'Chat OK') : (type === 'vision' ? 'Vision Failed' : 'Chat Failed'));
            } catch (err) { toast(err.message, 'danger'); }
            finally { btnRestore(btn); }
        };
    }
    var btnVision = document.getElementById('btn-test-vision');
    var btnChat = document.getElementById('btn-test-chat');
    if (btnVision) btnVision.addEventListener('click', testProvider('vision'));
    if (btnChat) btnChat.addEventListener('click', testProvider('chat'));

    // ==================================================================
    // 6. Restore Defaults
    // ==================================================================
    var btnReset = document.getElementById('btn-reset-settings');
    if (btnReset) {
        btnReset.addEventListener('click', async function () {
            if (!confirm('Reset all settings to defaults?')) return;
            btnLoading(btnReset, 'Resetting...');
            try {
                var data = await api.post('/api/settings/reset');
                toast(data.message || 'Reset.', data.success ? 'success' : 'info');
                if (data.success) { await loadSettings(); location.reload(); }
            } catch (err) { toast(err.message, 'danger'); }
            finally { btnRestore(btnReset); }
        });
    }

    // ==================================================================
    // 7. Hotkey Controls
    // ==================================================================
    var btnRecord = document.getElementById('btn-record-shortcut');
    var btnEnable = document.getElementById('btn-enable-hotkey');
    var btnDisable = document.getElementById('btn-disable-hotkey');
    var hotkeyDisplay = document.getElementById('hotkey-display');
    var hotkeyStatusText = document.getElementById('hotkey-status-text');
    var isRecording = false;

    loadHotkeyInfo();
    async function loadHotkeyInfo() {
        try {
            var data = await api.get('/api/hotkey/status');
            if (data.success && data.hotkey) {
                if (hotkeyDisplay) hotkeyDisplay.value = data.hotkey.shortcut || 'ctrl+shift+a';
                if (hotkeyStatusText) hotkeyStatusText.textContent = 'Status: ' +
                    (data.hotkey.registered ? 'Active (' + data.hotkey.shortcut + ')' : 'Not registered');
            }
        } catch (_) {}
    }

    if (btnRecord) {
        btnRecord.addEventListener('click', function () {
            if (isRecording) { stopRecording(); return; }
            isRecording = true;
            btnRecord.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Listening...';
            btnRecord.classList.remove('btn-outline-warning'); btnRecord.classList.add('btn-warning');
        });
    }
    document.addEventListener('keydown', function (e) {
        if (!isRecording) return;
        e.preventDefault(); e.stopPropagation();
        var parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        if (e.metaKey) parts.push('win');
        if (['Control','Shift','Alt','Meta'].indexOf(e.key) === -1) {
            var k = e.key.toLowerCase(); if (k === ' ') k = 'space';
            parts.push(k);
            finishRecording(parts.join('+'));
        }
    });
    async function finishRecording(shortcut) {
        stopRecording();
        if (hotkeyDisplay) hotkeyDisplay.value = shortcut;
        try {
            var data = await api.post('/api/hotkey/change', { shortcut: shortcut });
            toast(data.message, data.success ? 'success' : 'danger');
            await loadHotkeyInfo();
        } catch (err) { toast(err.message, 'danger'); }
    }
    function stopRecording() {
        isRecording = false;
        if (btnRecord) { btnRecord.innerHTML = '<i class="bi bi-record-circle me-1"></i> Record Shortcut'; btnRecord.classList.remove('btn-warning'); btnRecord.classList.add('btn-outline-warning'); }
    }
    if (btnEnable) btnEnable.addEventListener('click', async function () { btnLoading(btnEnable, 'Enabling...'); try { var d = await api.post('/api/hotkey/start'); toast(d.message, d.success ? 'success' : 'warning'); loadHotkeyInfo(); } catch (_) {} finally { btnRestore(btnEnable); } });
    if (btnDisable) btnDisable.addEventListener('click', async function () { btnLoading(btnDisable, 'Disabling...'); try { var d = await api.post('/api/hotkey/stop'); toast(d.message, d.success ? 'success' : 'info'); loadHotkeyInfo(); } catch (_) {} finally { btnRestore(btnDisable); } });

    // Init
    loadSettings();
})();
