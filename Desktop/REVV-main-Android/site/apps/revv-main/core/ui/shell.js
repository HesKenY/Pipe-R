/**
 * CHERP UIShell
 * Top bar, bottom nav, toasts, modals, loading overlay.
 */
class UIShell {
  constructor() {
    this.currentNav = null;
    this.navItems = [];
    this._toastTimeout = 3500;
  }

  /** Initialize the shell after DOM is ready */
  init() {
    this.els = {
      splash: document.getElementById('splash-screen'),
      authScreen: document.getElementById('auth-screen'),
      mainScreen: document.getElementById('main-screen'),
      pageTitle: document.getElementById('page-title'),
      contentArea: document.getElementById('content-area'),
      bottomNav: document.getElementById('bottom-nav'),
      modalOverlay: document.getElementById('modal-overlay'),
      toastContainer: document.getElementById('toast-container'),
      loadingOverlay: document.getElementById('loading-overlay'),
      notifBadge: document.getElementById('notif-badge'),
      loginForm: document.getElementById('login-form'),
      authError: document.getElementById('auth-error'),
      authCompany: document.getElementById('auth-company-name'),
      biometricWrap: document.getElementById('biometric-btn-wrap'),
      biometricBtn: document.getElementById('biometric-btn'),
      btnUserMenu: document.getElementById('btn-user-menu'),
      btnNotifications: document.getElementById('btn-notifications')
    };

    // Close modal on overlay click
    this.els.modalOverlay.addEventListener('click', (e) => {
      if (e.target === this.els.modalOverlay) this.closeModal();
    });

    // User menu
    this.els.btnUserMenu.addEventListener('click', () => this._showUserMenu());

    console.log('[Shell] Initialized.');
  }

  /** Show a specific screen */
  showScreen(name) {
    this.els.splash.classList.add('hidden');
    this.els.authScreen.classList.add('hidden');
    this.els.mainScreen.classList.add('hidden');

    if (name === 'auth') {
      this.els.authScreen.classList.remove('hidden');
    } else if (name === 'main') {
      this.els.mainScreen.classList.remove('hidden');
    }
  }

  /** Hide the splash screen */
  hideSplash() {
    this.els.splash.classList.add('hidden');
  }

  /** Set the company name on the auth screen */
  setCompanyName(name) {
    this.els.authCompany.textContent = name;
  }

  /** Set the page title in the top bar */
  setPageTitle(title) {
    this.els.pageTitle.textContent = title;
  }

  /** Render the content area with HTML */
  setContent(html) {
    this.els.contentArea.innerHTML = html;
  }

  /** Render the bottom navigation from module definitions */
  renderNav(items) {
    this.navItems = items;
    this.els.bottomNav.innerHTML = '';

    items.forEach(item => {
      const btn = document.createElement('button');
      btn.className = 'nav-item' + (item.id === this.currentNav ? ' active' : '');
      btn.setAttribute('aria-label', item.name);
      btn.innerHTML = `
        ${item.icon}
        <span>${item.name}</span>
      `;
      btn.addEventListener('click', () => {
        this._setActiveNav(item.id);
        if (item.onSelect) item.onSelect();
      });
      this.els.bottomNav.appendChild(btn);
    });
  }

  /** Set active nav item */
  _setActiveNav(id) {
    this.currentNav = id;
    const buttons = this.els.bottomNav.querySelectorAll('.nav-item');
    buttons.forEach((btn, i) => {
      btn.classList.toggle('active', this.navItems[i].id === id);
    });
  }

  /** Navigate to a specific module by ID */
  navigateTo(moduleId) {
    const item = this.navItems.find(n => n.id === moduleId);
    if (item) {
      this._setActiveNav(moduleId);
      if (item.onSelect) item.onSelect();
    }
  }

  /** Show a toast notification */
  showToast(message, type = 'info', duration) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
      success: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>',
      error: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
      warning: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>',
      info: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>'
    };

    toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
    this.els.toastContainer.appendChild(toast);

    const timeout = duration || this._toastTimeout;
    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 200);
    }, timeout);
  }

  /** Show a modal dialog */
  showModal(options = {}) {
    const { title = '', body = '', footer = '', onClose } = options;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-header">
        <div class="modal-title">${title}</div>
        <button class="modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
    `;

    this.els.modalOverlay.innerHTML = '';
    this.els.modalOverlay.appendChild(modal);
    this.els.modalOverlay.classList.remove('hidden');

    modal.querySelector('.modal-close').addEventListener('click', () => {
      this.closeModal();
      if (onClose) onClose();
    });

    return modal;
  }

  /** Show a confirm dialog, returns a Promise<boolean> */
  confirm(title, message) {
    return new Promise(resolve => {
      const modal = this.showModal({
        title: title,
        body: `<p>${message}</p>`,
        footer: `
          <button class="btn btn-secondary" data-action="cancel">Cancel</button>
          <button class="btn btn-primary" data-action="confirm">Confirm</button>
        `
      });

      modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
        this.closeModal();
        resolve(false);
      });

      modal.querySelector('[data-action="confirm"]').addEventListener('click', () => {
        this.closeModal();
        resolve(true);
      });
    });
  }

  /** Close the modal */
  closeModal() {
    this.els.modalOverlay.classList.add('hidden');
    this.els.modalOverlay.innerHTML = '';
  }

  /** Show full-screen loading spinner */
  showLoading() {
    this.els.loadingOverlay.classList.remove('hidden');
  }

  /** Hide full-screen loading spinner */
  hideLoading() {
    this.els.loadingOverlay.classList.add('hidden');
  }

  /** Update notification badge count */
  setNotificationCount(count) {
    if (count > 0) {
      this.els.notifBadge.textContent = count > 99 ? '99+' : count;
      this.els.notifBadge.classList.remove('hidden');
    } else {
      this.els.notifBadge.classList.add('hidden');
    }
  }

  /** Show auth error message */
  showAuthError(msg) {
    this.els.authError.textContent = msg;
    this.els.authError.classList.remove('hidden');
  }

  /** Clear auth error */
  clearAuthError() {
    this.els.authError.classList.add('hidden');
    this.els.authError.textContent = '';
  }

  /** Show user menu dropdown */
  _showUserMenu() {
    const user = window.CHERP.auth.getUser();
    if (!user) return;

    const role = window.CHERP.roles.getRoleLabel(user.role);

    this.showModal({
      title: user.displayName,
      body: `
        <p style="color:var(--text-muted);margin-bottom:1rem;">${role} &middot; @${user.username}</p>
        <div style="display:flex;flex-direction:column;gap:0.5rem;">
          <button class="btn btn-secondary btn-block" id="menu-biometric">Enroll Biometrics</button>
          <button class="btn btn-danger btn-block" id="menu-logout">Sign Out</button>
        </div>
      `
    });

    document.getElementById('menu-biometric').addEventListener('click', async () => {
      try {
        await window.CHERP.auth.enrollBiometric();
        this.closeModal();
        this.showToast('Biometric enrolled.', 'success');
      } catch (e) {
        this.showToast(e.message, 'error');
      }
    });

    document.getElementById('menu-logout').addEventListener('click', async () => {
      this.closeModal();
      await window.CHERP.auth.logout();
      this.showScreen('auth');
      this.showToast('Signed out.', 'info');
    });
  }
}

window.UIShell = UIShell;
