/**
 * Modal Management System
 * Modern modal dialogs with animations and accessibility
 */

class ModalManager {
    constructor() {
        this.activeModal = null;
        this.init();
    }

    init() {
        // Handle ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModal) {
                this.close();
            }
        });
    }

    open(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`Modal with id "${modalId}" not found`);
            return;
        }

        this.activeModal = modal;
        modal.style.display = 'flex';

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        // Focus trap
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (firstElement) {
            firstElement.focus();
        }

        // Trap focus inside modal
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement.focus();
                        e.preventDefault();
                    }
                }
            }
        });

        // Click outside to close
        const overlay = modal.querySelector('.modal-overlay') || modal;
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.close();
            }
        });

        // Close button
        const closeBtn = modal.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
    }

    close() {
        if (!this.activeModal) return;

        const modal = this.activeModal;
        modal.style.opacity = '0';

        setTimeout(() => {
            modal.style.display = 'none';
            modal.style.opacity = '1';
            document.body.style.overflow = '';
            this.activeModal = null;
        }, 200);
    }

    confirm(options = {}) {
        const {
            title = 'Konfirmasi',
            message = 'Apakah Anda yakin?',
            confirmText = 'Ya',
            cancelText = 'Batal',
            onConfirm = () => { },
            onCancel = () => { }
        } = options;

        return new Promise((resolve) => {
            // Create modal element
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
        <div class="modal">
          <div class="modal-header">
            <h2>${title}</h2>
            <button class="modal-close" aria-label="Close">×</button>
          </div>
          <div class="modal-body">
            <p>${message}</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost modal-cancel">${cancelText}</button>
            <button class="btn btn-primary modal-confirm">${confirmText}</button>
          </div>
        </div>
      `;

            document.body.appendChild(modal);

            // Show modal
            setTimeout(() => {
                modal.style.display = 'flex';
            }, 10);

            // Handle confirm
            const confirmBtn = modal.querySelector('.modal-confirm');
            confirmBtn.addEventListener('click', () => {
                onConfirm();
                resolve(true);
                this.closeElement(modal);
            });

            // Handle cancel
            const cancelBtn = modal.querySelector('.modal-cancel');
            const closeBtn = modal.querySelector('.modal-close');

            const handleCancel = () => {
                onCancel();
                resolve(false);
                this.closeElement(modal);
            };

            cancelBtn.addEventListener('click', handleCancel);
            closeBtn.addEventListener('click', handleCancel);

            // ESC to cancel
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    handleCancel();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);

            // Click outside to cancel
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    handleCancel();
                }
            });
        });
    }

    closeElement(element) {
        element.style.opacity = '0';
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 200);
    }
}

// Global modal instance
window.modal = new ModalManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModalManager;
}
