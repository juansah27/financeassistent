/**
 * Toast Notification System
 * Modern toast notifications with auto-dismiss and animations
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.querySelector('.toast-container')) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.querySelector('.toast-container');
        }
    }

    show(message, title = '', type = 'info', duration = 5000) {
        const toast = this.createToast(message, title, type);
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => this.dismiss(toast), duration);
        }

        return toast;
    }

    createToast(message, title, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const iconMap = {
            success: `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`,
            error: `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`,
            warning: `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>`,
            info: `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`
        };

        toast.innerHTML = `
      <div style="color: var(--${type}); flex-shrink: 0;">
        ${iconMap[type] || iconMap.info}
      </div>
      <div style="flex: 1;">
        ${title ? `<h4>${title}</h4>` : ''}
        <p>${message}</p>
      </div>
      <button class="toast-close" aria-label="Close">×</button>
    `;

        // Close button handler
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.dismiss(toast));

        // Swipe to dismiss (mobile)
        let startX = 0;
        toast.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });

        toast.addEventListener('touchmove', (e) => {
            const deltaX = e.touches[0].clientX - startX;
            if (deltaX > 50) {
                this.dismiss(toast);
            }
        });

        return toast;
    }

    dismiss(toast) {
        toast.style.animation = 'slideUp 0.3s ease-out reverse';
        toast.style.opacity = '0';

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300);
    }

    success(message, title = 'Berhasil!') {
        return this.show(message, title, 'success');
    }

    error(message, title = 'Error!') {
        return this.show(message, title, 'error');
    }

    warning(message, title = 'Perhatian!') {
        return this.show(message, title, 'warning');
    }

    info(message, title = '') {
        return this.show(message, title, 'info');
    }
}

// Global toast instance
window.toast = new ToastManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ToastManager;
}
