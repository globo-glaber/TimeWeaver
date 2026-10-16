/**
 * TimeWeaver — Client JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {

    // 1. Dark / Light Theme Toggle Handler
    const themeBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeToggleIcon');
    const themeText = document.getElementById('themeToggleText');

    function syncThemeUI() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        if (themeBtn) {
            if (currentTheme === 'dark') {
                if (themeIcon) themeIcon.innerText = '☀️';
                if (themeText) themeText.innerText = 'Світла тема';
            } else {
                if (themeIcon) themeIcon.innerText = '🌙';
                if (themeText) themeText.innerText = 'Темна тема';
            }
        }
    }

    syncThemeUI();

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';

            if (nextTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }

            localStorage.setItem('theme', nextTheme);
            syncThemeUI();
        });
    }

    // 2. Preference Toggle Handler
    const prefBtns = document.querySelectorAll('.pref-btn[data-teacher-id]');
    prefBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();

            const teacherId = btn.getAttribute('data-teacher-id');
            const day = btn.getAttribute('data-day');
            const slotNumber = btn.getAttribute('data-slot');
            let currentStatus = btn.getAttribute('data-status') || 'neutral';

            // Cycle through statuses: neutral -> preferred -> unavailable -> neutral
            let newStatus = 'neutral';
            if (currentStatus === 'neutral') {
                newStatus = 'preferred';
            } else if (currentStatus === 'preferred') {
                newStatus = 'unavailable';
            } else {
                newStatus = 'neutral';
            }

            // Update UI optimistically
            updatePrefBtnUI(btn, newStatus);

            try {
                const response = await fetch('/api/preferences/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        teacher_id: parseInt(teacherId),
                        day: day,
                        slot_number: parseInt(slotNumber),
                        status: newStatus
                    })
                });

                const resData = await response.json();
                if (!resData.success) {
                    updatePrefBtnUI(btn, currentStatus);
                    alert('Помилка збереження побажання');
                }
            } catch (err) {
                console.error(err);
                updatePrefBtnUI(btn, currentStatus);
            }
        });
    });

    function updatePrefBtnUI(btn, status) {
        btn.setAttribute('data-status', status);
        btn.classList.remove('preferred', 'unavailable', 'neutral');
        btn.classList.add(status);

        const statusText = btn.querySelector('.pref-status-text');
        const hiddenInput = btn.parentElement.querySelector('input[type="hidden"]');
        if (hiddenInput) {
            hiddenInput.value = status;
        }

        if (status === 'preferred') {
            if (statusText) statusText.innerText = '🟢 Бажано';
        } else if (status === 'unavailable') {
            if (statusText) statusText.innerText = '🔴 Неможливо';
        } else {
            if (statusText) statusText.innerText = '⚪ Нейтрально';
        }
    }

    // 3. View selector dropdown change trigger
    const filterSelect = document.getElementById('scheduleFilterSelect');
    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => {
            const selectedVal = e.target.value;
            const viewType = filterSelect.getAttribute('data-view-type');
            if (selectedVal) {
                window.location.href = `/?view=${viewType}&id=${selectedVal}`;
            } else {
                window.location.href = `/?view=official`;
            }
        });
    }

    // 4. Auto dismiss alerts after 5s
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});
