(function () {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

function setTheme(themeName) {
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem('theme', themeName);

    // Update active state of buttons if they exist
    updateThemeButtons(themeName);
}

function updateThemeButtons(activeTheme) {
    const buttons = document.querySelectorAll('.theme-btn');
    buttons.forEach(btn => {
        if (btn.dataset.theme === activeTheme) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Init buttons on load
document.addEventListener('DOMContentLoaded', () => {
    updateThemeButtons(localStorage.getItem('theme') || 'dark');
});

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}
