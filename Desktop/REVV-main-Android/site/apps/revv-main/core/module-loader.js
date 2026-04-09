/**
 * REVV ModuleLoader
 * Loads module configs, performs topological dependency sort, and dynamically loads module scripts.
 */
class ModuleLoader {
  constructor() {
    this.registry = {};        // All module definitions from modules.config.json
    this.loaded = new Set();   // IDs of successfully loaded modules
    this.failed = new Set();   // IDs of modules that failed to load
    this.enabledModules = [];  // Ordered list after dependency sort
  }

  /**
   * Load all enabled modules based on config and user role.
   * @param {Array} moduleConfigs - Array of module definitions from modules.config.json
   * @param {Array} enabledIds - Array of enabled module IDs from instance config
   * @param {string} userRole - Current user's role
   */
  async loadAll(moduleConfigs, enabledIds, userRole) {
    // Build registry
    moduleConfigs.forEach(mod => {
      this.registry[mod.id] = mod;
    });

    // Filter to enabled modules the user can access
    const roles = window.REVV.roles;
    const candidates = moduleConfigs.filter(mod =>
      enabledIds.includes(mod.id) &&
      mod.enabled !== false &&
      roles.canAccess(userRole, mod.requiredRole)
    );

    // Topological sort by dependencies
    this.enabledModules = this._topologicalSort(candidates);

    console.log('[ModuleLoader] Load order:', this.enabledModules.map(m => m.id).join(' â†’ '));

    // Load each module in order
    for (const mod of this.enabledModules) {
      await this.loadModule(mod);
    }

    console.log(`[ModuleLoader] Loaded ${this.loaded.size}/${this.enabledModules.length} modules.`);
    if (this.failed.size > 0) {
      console.warn('[ModuleLoader] Failed:', [...this.failed].join(', '));
    }

    return { loaded: [...this.loaded], failed: [...this.failed] };
  }

  /**
   * Load a single module: check dependencies, load script, call init.
   */
  async loadModule(mod) {
    if (this.loaded.has(mod.id)) return true;

    // Check dependencies are loaded
    for (const dep of mod.dependencies) {
      if (!this.loaded.has(dep)) {
        console.error(`[ModuleLoader] ${mod.id}: missing dependency "${dep}". Skipping.`);
        this.failed.add(mod.id);
        return false;
      }
    }

    // Skip core â€” it's loaded by the HTML directly
    if (mod.id === 'core') {
      this.loaded.add('core');
      return true;
    }

    try {
      // Try to load the module's main script
      const scriptPath = `modules/${mod.id}/${mod.id}.js`;
      await this._loadScript(scriptPath);

      // Call the module's init function if it exists
      const initFn = window[`revv_${mod.id}_init`];
      if (typeof initFn === 'function') {
        await initFn();
        console.log(`[ModuleLoader] ${mod.id}: initialized.`);
      }

      this.loaded.add(mod.id);
      return true;
    } catch (e) {
      console.warn(`[ModuleLoader] ${mod.id}: failed to load (${e.message}). Module may not exist yet.`);
      // Still mark as loaded so nav items can show a placeholder
      this.loaded.add(mod.id);
      return true;
    }
  }

  /**
   * Dynamically load a script by path.
   */
  _loadScript(src) {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Failed to load: ${src}`));
      document.body.appendChild(script);
    });
  }

  /**
   * Topological sort using Kahn's algorithm.
   * Ensures modules load after their dependencies.
   */
  _topologicalSort(modules) {
    const idSet = new Set(modules.map(m => m.id));
    const graph = new Map();   // id â†’ set of dependency ids (within enabled set)
    const inDegree = new Map();

    // Build adjacency
    modules.forEach(mod => {
      graph.set(mod.id, new Set());
      inDegree.set(mod.id, 0);
    });

    modules.forEach(mod => {
      mod.dependencies.forEach(dep => {
        if (idSet.has(dep)) {
          graph.get(dep).add(mod.id);
          inDegree.set(mod.id, inDegree.get(mod.id) + 1);
        }
      });
    });

    // Kahn's algorithm
    const queue = [];
    inDegree.forEach((deg, id) => {
      if (deg === 0) queue.push(id);
    });

    const sorted = [];
    while (queue.length > 0) {
      const id = queue.shift();
      sorted.push(id);

      graph.get(id).forEach(neighbor => {
        const newDeg = inDegree.get(neighbor) - 1;
        inDegree.set(neighbor, newDeg);
        if (newDeg === 0) queue.push(neighbor);
      });
    }

    // Check for cycles
    if (sorted.length !== modules.length) {
      const missing = modules.filter(m => !sorted.includes(m.id)).map(m => m.id);
      console.error('[ModuleLoader] Circular dependency detected among:', missing.join(', '));
      // Add remaining modules anyway â€” best effort
      missing.forEach(id => sorted.push(id));
    }

    // Map back to module objects
    const byId = {};
    modules.forEach(m => byId[m.id] = m);
    return sorted.map(id => byId[id]);
  }

  /**
   * Check if a module is loaded.
   */
  isLoaded(moduleId) {
    return this.loaded.has(moduleId);
  }

  /**
   * Get a module's config by ID.
   */
  getModuleConfig(moduleId) {
    return this.registry[moduleId] || null;
  }

  /**
   * Get the list of enabled/loaded module IDs.
   */
  getLoadedModules() {
    return [...this.loaded];
  }
}

window.ModuleLoader = ModuleLoader;
