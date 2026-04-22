(function () {
    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'dark');
})();

function setTheme(themeName) {
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem('theme', themeName);
    updateThemeButtons(themeName);
}

function updateThemeButtons(activeTheme) {
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === activeTheme);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    updateThemeButtons(localStorage.getItem('theme') || 'dark');
});

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'light' ? 'dark' : 'light');
}
