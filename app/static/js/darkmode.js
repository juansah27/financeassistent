// Dark mode toggle functionality
(function() {
    // Initialize dark mode on page load
    function initDarkMode() {
        const darkMode = localStorage.getItem('darkMode') === 'true';
        if (darkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }
    
    // Toggle dark mode
    window.toggleDarkMode = function() {
        const html = document.documentElement;
        const isDark = html.classList.toggle('dark');
        localStorage.setItem('darkMode', isDark);
        
        // Sync with server preference
        fetch('/settings/dark-mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `dark_mode=${isDark}`
        }).catch(() => {
            // Ignore errors if server is not available
        });
        
        return false;
    };
    
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDarkMode);
    } else {
        initDarkMode();
    }
})();

