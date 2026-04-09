/**
 * CHERP RoleManager
 * 6-tier role hierarchy: apprentice → journeyman → foreman → superintendent → admin → superuser
 */
class RoleManager {
  constructor() {
    this.roles = {
      apprentice:      { level: 1, label: 'Apprentice' },
      journeyman:      { level: 2, label: 'Journeyman' },
      foreman:         { level: 3, label: 'Foreman' },
      superintendent:  { level: 4, label: 'Superintendent' },
      admin:           { level: 5, label: 'Admin' },
      superuser:       { level: 6, label: 'Superuser' }
    };

    this.permissions = {
      'clock.in':             'apprentice',
      'clock.out':            'apprentice',
      'clock.view_own':       'apprentice',
      'clock.view_crew':      'foreman',
      'clock.edit':           'foreman',
      'calc.use':             'apprentice',
      'task.view_own':        'apprentice',
      'task.create':          'foreman',
      'task.assign':          'foreman',
      'task.delete':          'superintendent',
      'msg.send':             'apprentice',
      'msg.broadcast':        'foreman',
      'msg.delete_any':       'admin',
      'doc.view':             'journeyman',
      'doc.upload':           'journeyman',
      'doc.delete':           'foreman',
      'report.view':          'foreman',
      'report.export':        'foreman',
      'report.admin':         'superintendent',
      'log.create':           'foreman',
      'log.view':             'foreman',
      'log.edit_any':         'superintendent',
      'safety.view':          'apprentice',
      'safety.submit':        'apprentice',
      'safety.approve':       'foreman',
      'safety.admin':         'admin',
      'inventory.view':       'journeyman',
      'inventory.edit':       'journeyman',
      'inventory.admin':      'superintendent',
      'mro.create':           'journeyman',
      'mro.approve':          'foreman',
      'mro.admin':            'superintendent',
      'user.manage':          'admin',
      'user.create':          'admin',
      'user.delete':          'superuser',
      'settings.view':        'admin',
      'settings.edit':        'superuser',
      'module.manage':        'superuser',
      'audit.view':           'admin'
    };
  }

  /**
   * Get the numeric level for a role string.
   * Returns 0 if unknown.
   */
  getRoleLevel(role) {
    const r = this.roles[role];
    return r ? r.level : 0;
  }

  /**
   * Get the display label for a role.
   */
  getRoleLabel(role) {
    const r = this.roles[role];
    return r ? r.label : 'Unknown';
  }

  /**
   * Check if a user role has a specific permission.
   * Higher roles inherit all lower-role permissions.
   */
  hasPermission(userRole, permission) {
    const requiredRole = this.permissions[permission];
    if (!requiredRole) {
      // Unknown permission — deny by default
      console.warn(`[Roles] Unknown permission: ${permission}`);
      return false;
    }

    const userLevel = this.getRoleLevel(userRole);
    const requiredLevel = this.getRoleLevel(requiredRole);

    return userLevel >= requiredLevel;
  }

  /**
   * Check if a user role can access a module based on its requiredRole.
   */
  canAccess(userRole, moduleRequiredRole) {
    const userLevel = this.getRoleLevel(userRole);
    const moduleLevel = this.getRoleLevel(moduleRequiredRole);
    return userLevel >= moduleLevel;
  }

  /**
   * Get all permissions available to a given role.
   */
  getPermissionsForRole(role) {
    const userLevel = this.getRoleLevel(role);
    const result = [];
    for (const [perm, requiredRole] of Object.entries(this.permissions)) {
      if (userLevel >= this.getRoleLevel(requiredRole)) {
        result.push(perm);
      }
    }
    return result;
  }

  /**
   * Get all role names in order of ascending level.
   */
  getAllRoles() {
    return Object.entries(this.roles)
      .sort((a, b) => a[1].level - b[1].level)
      .map(([key, val]) => ({ id: key, level: val.level, label: val.label }));
  }

  /**
   * Check if roleA is at least as high as roleB.
   */
  isAtLeast(roleA, roleB) {
    return this.getRoleLevel(roleA) >= this.getRoleLevel(roleB);
  }
}

window.RoleManager = RoleManager;
