/**
 * CHERP AuthManager
 * PIN-based authentication with SHA-256 hashing, lockout, session timeout, and biometrics.
 */
class AuthManager {
  constructor() {
    this.user = null;
    this.sessionKey = 'cherp_session';
    this.lockoutKey = 'cherp_lockout';
    this.failKey = 'cherp_fail_count';
    this.maxAttempts = 5;
    this.sessionTimeoutHours = 12;
    this.pinLength = 4;
    this._sessionTimer = null;
  }

  /** Apply settings from instance config */
  configure(authConfig) {
    if (authConfig.pin_length) this.pinLength = authConfig.pin_length;
    if (authConfig.lockout_attempts) this.maxAttempts = authConfig.lockout_attempts;
    if (authConfig.session_timeout_hours) this.sessionTimeoutHours = authConfig.session_timeout_hours;
  }

  /** Hash a PIN with SHA-256 */
  async hashPin(pin) {
    const encoder = new TextEncoder();
    const data = encoder.encode(pin);
    const buffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(buffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /** Attempt login with username and PIN */
  async login(username, pin) {
    if (this.isLockedOut()) {
      const remaining = this.getLockoutRemaining();
      throw new Error(`Account locked. Try again in ${remaining} minutes.`);
    }

    const hashedPin = await this.hashPin(pin);

    const { data, error } = await window.CHERP.supabase.SB()
      .from('user_profiles')
      .select('id, username, display_name, role, pin_hash, is_active')
      .eq('username', username.toLowerCase().trim())
      .eq('pin_hash', hashedPin)
      .single();

    if (error || !data) {
      this._recordFailedAttempt();
      throw new Error('Invalid username or PIN.');
    }

    if (!data.is_active) {
      throw new Error('Account is deactivated. Contact your foreman.');
    }

    // Successful login
    this._clearFailedAttempts();
    this.user = {
      id: data.id,
      username: data.username,
      displayName: data.display_name,
      role: data.role
    };

    const session = {
      user: this.user,
      created: Date.now(),
      expires: Date.now() + (this.sessionTimeoutHours * 60 * 60 * 1000)
    };

    localStorage.setItem(this.sessionKey, JSON.stringify(session));
    this._startSessionTimer();
    await this._logSession('login');

    return this.user;
  }

  /** Log out and clear session */
  async logout() {
    await this._logSession('logout');
    this.user = null;
    localStorage.removeItem(this.sessionKey);
    this._clearSessionTimer();
  }

  /** Check for an existing valid session */
  checkSession() {
    const raw = localStorage.getItem(this.sessionKey);
    if (!raw) return null;

    try {
      const session = JSON.parse(raw);
      if (Date.now() > session.expires) {
        localStorage.removeItem(this.sessionKey);
        return null;
      }
      this.user = session.user;
      this._startSessionTimer();
      return this.user;
    } catch (e) {
      localStorage.removeItem(this.sessionKey);
      return null;
    }
  }

  /** Enroll WebAuthn biometrics for faster login */
  async enrollBiometric() {
    if (!window.PublicKeyCredential) {
      throw new Error('Biometrics not supported on this device.');
    }

    const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    if (!available) {
      throw new Error('No biometric authenticator available.');
    }

    if (!this.user) {
      throw new Error('Must be logged in to enroll biometrics.');
    }

    const challenge = crypto.getRandomValues(new Uint8Array(32));
    const userId = new TextEncoder().encode(this.user.id);

    const credential = await navigator.credentials.create({
      publicKey: {
        challenge: challenge,
        rp: { name: 'CHERP', id: location.hostname },
        user: {
          id: userId,
          name: this.user.username,
          displayName: this.user.displayName
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 },
          { type: 'public-key', alg: -257 }
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'required'
        },
        timeout: 60000
      }
    });

    if (credential) {
      const credentialId = btoa(String.fromCharCode(...new Uint8Array(credential.rawId)));
      localStorage.setItem('cherp_biometric_cred', credentialId);
      localStorage.setItem('cherp_biometric_user', this.user.username);
      return true;
    }

    throw new Error('Biometric enrollment cancelled.');
  }

  /** Check if biometrics are enrolled */
  hasBiometric() {
    return !!localStorage.getItem('cherp_biometric_cred') && !!window.PublicKeyCredential;
  }

  /** Authenticate with biometrics */
  async authenticateWithBiometric() {
    if (!this.hasBiometric()) {
      throw new Error('No biometric credential enrolled.');
    }

    const credentialId = localStorage.getItem('cherp_biometric_cred');
    const rawId = Uint8Array.from(atob(credentialId), c => c.charCodeAt(0));
    const challenge = crypto.getRandomValues(new Uint8Array(32));

    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: challenge,
        allowCredentials: [{
          type: 'public-key',
          id: rawId
        }],
        userVerification: 'required',
        timeout: 60000
      }
    });

    if (assertion) {
      const username = localStorage.getItem('cherp_biometric_user');
      const { data, error } = await window.CHERP.supabase.SB()
        .from('user_profiles')
        .select('id, username, display_name, role, is_active')
        .eq('username', username)
        .single();

      if (error || !data || !data.is_active) {
        throw new Error('Biometric user not found or deactivated.');
      }

      this.user = {
        id: data.id,
        username: data.username,
        displayName: data.display_name,
        role: data.role
      };

      const session = {
        user: this.user,
        created: Date.now(),
        expires: Date.now() + (this.sessionTimeoutHours * 60 * 60 * 1000)
      };

      localStorage.setItem(this.sessionKey, JSON.stringify(session));
      this._startSessionTimer();
      await this._logSession('biometric_login');
      return this.user;
    }

    throw new Error('Biometric authentication cancelled.');
  }

  /** Check if currently locked out */
  isLockedOut() {
    const lockout = localStorage.getItem(this.lockoutKey);
    if (!lockout) return false;
    const lockoutTime = parseInt(lockout, 10);
    if (Date.now() > lockoutTime) {
      localStorage.removeItem(this.lockoutKey);
      localStorage.removeItem(this.failKey);
      return false;
    }
    return true;
  }

  /** Get remaining lockout time in minutes */
  getLockoutRemaining() {
    const lockout = localStorage.getItem(this.lockoutKey);
    if (!lockout) return 0;
    const ms = parseInt(lockout, 10) - Date.now();
    return Math.max(1, Math.ceil(ms / 60000));
  }

  /** Record a failed login attempt, trigger lockout if max reached */
  _recordFailedAttempt() {
    let count = parseInt(localStorage.getItem(this.failKey) || '0', 10) + 1;
    localStorage.setItem(this.failKey, count.toString());

    if (count >= this.maxAttempts) {
      // Lock out for 15 minutes
      const lockoutUntil = Date.now() + (15 * 60 * 1000);
      localStorage.setItem(this.lockoutKey, lockoutUntil.toString());
    }
  }

  /** Clear failed attempt counter */
  _clearFailedAttempts() {
    localStorage.removeItem(this.failKey);
    localStorage.removeItem(this.lockoutKey);
  }

  /** Start session expiry timer */
  _startSessionTimer() {
    this._clearSessionTimer();
    const raw = localStorage.getItem(this.sessionKey);
    if (!raw) return;

    const session = JSON.parse(raw);
    const remaining = session.expires - Date.now();

    if (remaining <= 0) {
      this.logout();
      return;
    }

    this._sessionTimer = setTimeout(() => {
      this.user = null;
      localStorage.removeItem(this.sessionKey);
      window.dispatchEvent(new CustomEvent('cherp:session-expired'));
    }, Math.min(remaining, 2147483647)); // Max setTimeout value
  }

  /** Clear session timer */
  _clearSessionTimer() {
    if (this._sessionTimer) {
      clearTimeout(this._sessionTimer);
      this._sessionTimer = null;
    }
  }

  /** Log a session event to audit_log */
  async _logSession(action) {
    if (!this.user) return;
    try {
      await window.CHERP.supabase.SB()
        .from('audit_log')
        .insert({
          user_id: this.user.id,
          action: action,
          details: { username: this.user.username, timestamp: new Date().toISOString() }
        });
    } catch (e) {
      console.warn('[Auth] Failed to write audit log:', e.message);
    }
  }

  /** Get current user or null */
  getUser() {
    return this.user;
  }

  /** Check if user is authenticated */
  isAuthenticated() {
    return !!this.user;
  }
}

window.AuthManager = AuthManager;
