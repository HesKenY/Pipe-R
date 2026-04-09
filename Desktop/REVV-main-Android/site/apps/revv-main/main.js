/**
 * REVV Modular PWA â€” Main Entry Point
 * Boot sequence: config â†’ supabase â†’ auth â†’ roles â†’ shell â†’ modules
 */
(async function () {
  'use strict';

  // Global namespace
  window.REVV = {
    config: null,
    modules: null,
    supabase: null,
    auth: null,
    roles: null,
    shell: null,
    loader: null
  };

  try {
    console.log('[REVV] Booting...');

    // â”€â”€ Step 1: Load configs â”€â”€
    const [instanceRes, modulesRes] = await Promise.all([
      fetch('config/instance.json'),
      fetch('modules.config.json')
    ]);

    if (!instanceRes.ok) throw new Error('Failed to load instance config.');
    if (!modulesRes.ok) throw new Error('Failed to load modules config.');

    const instanceConfig = await instanceRes.json();
    const modulesConfig = await modulesRes.json();

    window.REVV.config = instanceConfig;
    window.REVV.modules = modulesConfig;
    console.log('[REVV] Config loaded:', instanceConfig.company_name);

    // Apply brand colors as CSS custom properties
    if (instanceConfig.brand_colors) {
      const root = document.documentElement;
      if (instanceConfig.brand_colors.primary) root.style.setProperty('--accent', instanceConfig.brand_colors.primary);
      if (instanceConfig.brand_colors.secondary) root.style.setProperty('--bg-card', instanceConfig.brand_colors.secondary);
      if (instanceConfig.brand_colors.accent) root.style.setProperty('--info', instanceConfig.brand_colors.accent);
    }

    // â”€â”€ Step 2: Initialize Supabase â”€â”€
    window.REVV.supabase = new SupabaseClient();
    window.REVV.supabase.init(instanceConfig.supabase_url, instanceConfig.supabase_anon_key);
    console.log('[REVV] Supabase ready.');

    // â”€â”€ Step 3: Initialize Auth â”€â”€
    window.REVV.auth = new AuthManager();
    window.REVV.auth.configure(instanceConfig.auth || {});
    console.log('[REVV] Auth ready.');

    // â”€â”€ Step 4: Initialize Roles â”€â”€
    window.REVV.roles = new RoleManager();
    console.log('[REVV] Roles ready.');

    // â”€â”€ Step 5: Initialize UI Shell â”€â”€
    window.REVV.shell = new UIShell();
    window.REVV.shell.init();
    window.REVV.shell.setCompanyName(instanceConfig.company_name);
    console.log('[REVV] Shell ready.');

    // â”€â”€ Step 6: Check existing session â”€â”€
    const existingUser = window.REVV.auth.checkSession();

    if (existingUser) {
      console.log('[REVV] Existing session:', existingUser.username);
      await _enterApp(existingUser, modulesConfig, instanceConfig);
    } else {
      window.REVV.shell.hideSplash();
      window.REVV.shell.showScreen('auth');
      _setupBiometric();
    }

    // â”€â”€ Login form handler â”€â”€
    window.REVV.shell.els.loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      window.REVV.shell.clearAuthError();

      const username = document.getElementById('login-username').value.trim();
      const pin = document.getElementById('login-pin').value.trim();

      if (!username || !pin) {
        window.REVV.shell.showAuthError('Enter both username and PIN.');
        return;
      }

      try {
        window.REVV.shell.showLoading();
        const user = await window.REVV.auth.login(username, pin);
        await _enterApp(user, modulesConfig, instanceConfig);
        window.REVV.shell.hideLoading();
      } catch (err) {
        window.REVV.shell.hideLoading();
        window.REVV.shell.showAuthError(err.message);
      }
    });

    // â”€â”€ Session expired listener â”€â”€
    window.addEventListener('revv:session-expired', () => {
      window.REVV.shell.showScreen('auth');
      window.REVV.shell.showToast('Session expired. Please sign in again.', 'warning');
    });

    console.log('[REVV] Boot complete.');

  } catch (err) {
    console.error('[REVV] Boot failed:', err);
    const splash = document.getElementById('splash-screen');
    if (splash) {
      splash.innerHTML = `
        <div class="splash-content">
          <div class="splash-logo">REVV</div>
          <p style="color:#ef4444;margin-top:1rem;">Failed to start: ${err.message}</p>
          <button onclick="location.reload()" class="btn btn-primary" style="margin-top:1rem;">Retry</button>
        </div>
      `;
    }
  }

  // â”€â”€ Enter the app after auth â”€â”€
  async function _enterApp(user, modulesConfig, instanceConfig) {
    window.REVV.shell.hideSplash();
    window.REVV.shell.showScreen('main');
    window.REVV.shell.setPageTitle('REVV');

    // Load modules
    window.REVV.loader = new ModuleLoader();
    const result = await window.REVV.loader.loadAll(
      modulesConfig.modules,
      instanceConfig.enabled_modules,
      user.role
    );

    // Build nav from loaded modules
    const navIcons = _getNavIcons();
    const navModules = ['timeclock', 'calculator', 'tasklist', 'messaging', 'safety'];
    const navItems = navModules
      .filter(id => window.REVV.loader.isLoaded(id))
      .map(id => {
        const mod = window.REVV.loader.getModuleConfig(id);
        return {
          id: id,
          name: mod ? mod.name : id,
          icon: navIcons[id] || navIcons._default,
          onSelect: () => _showModule(id)
        };
      });

    // Always add a "More" item for extra modules
    navItems.push({
      id: 'more',
      name: 'More',
      icon: navIcons.more,
      onSelect: () => _showMore()
    });

    window.REVV.shell.renderNav(navItems);

    // Show first module
    if (navItems.length > 0) {
      navItems[0].onSelect();
    }

    window.REVV.shell.showToast(`Welcome, ${user.displayName}`, 'success');
  }

  // â”€â”€ Show a module's content â”€â”€
  function _showModule(id) {
    const mod = window.REVV.loader.getModuleConfig(id);
    window.REVV.shell.setPageTitle(mod ? mod.name : id);

    // Check if module has a render function
    const renderFn = window[`revv_${id}_render`];
    if (typeof renderFn === 'function') {
      renderFn(document.getElementById('content-area'));
    } else {
      // Placeholder for modules that don't have their script yet
      window.REVV.shell.setContent(`
        <div class="empty-state">
          <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
          </svg>
          <p><strong>${mod ? mod.name : id}</strong></p>
          <p style="margin-top:0.5rem;">${mod ? mod.description : 'Module not loaded.'}</p>
        </div>
      `);
    }
  }

  // â”€â”€ Show "More" menu with additional modules â”€â”€
  function _showMore() {
    window.REVV.shell.setPageTitle('More');
    const primaryNav = ['timeclock', 'calculator', 'tasklist', 'messaging', 'safety'];
    const extras = window.REVV.loader.getLoadedModules()
      .filter(id => id !== 'core' && !primaryNav.includes(id));

    if (extras.length === 0) {
      window.REVV.shell.setContent(`
        <div class="empty-state">
          <p>No additional modules available.</p>
        </div>
      `);
      return;
    }

    const items = extras.map(id => {
      const mod = window.REVV.loader.getModuleConfig(id);
      return `
        <div class="list-item" data-module="${id}">
          <div class="list-icon">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
          </div>
          <div class="list-content">
            <div class="list-title">${mod ? mod.name : id}</div>
            <div class="list-desc">${mod ? mod.description : ''}</div>
          </div>
        </div>
      `;
    }).join('');

    window.REVV.shell.setContent(`
      <div class="section-header">Additional Modules</div>
      ${items}
    `);

    // Bind clicks
    document.querySelectorAll('.list-item[data-module]').forEach(el => {
      el.addEventListener('click', () => {
        _showModule(el.dataset.module);
      });
    });
  }

  // â”€â”€ Setup biometric button on auth screen â”€â”€
  function _setupBiometric() {
    if (window.REVV.auth.hasBiometric()) {
      window.REVV.shell.els.biometricWrap.classList.remove('hidden');
      window.REVV.shell.els.biometricBtn.addEventListener('click', async () => {
        try {
          window.REVV.shell.showLoading();
          const user = await window.REVV.auth.authenticateWithBiometric();
          const [instanceRes, modulesRes] = await Promise.all([
            fetch('config/instance.json'),
            fetch('modules.config.json')
          ]);
          const instanceConfig = await instanceRes.json();
          const modulesConfig = await modulesRes.json();
          await _enterApp(user, modulesConfig, instanceConfig);
          window.REVV.shell.hideLoading();
        } catch (err) {
          window.REVV.shell.hideLoading();
          window.REVV.shell.showAuthError(err.message);
        }
      });
    }
  }

  // â”€â”€ Nav icon SVGs â”€â”€
  function _getNavIcons() {
    return {
      timeclock: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
      calculator: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 10h8M8 14h3M13 14h3M8 18h3M13 18h3"/></svg>',
      tasklist: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>',
      messaging: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
      safety: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
      more: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>',
      _default: '<svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>'
    };
  }

})();
