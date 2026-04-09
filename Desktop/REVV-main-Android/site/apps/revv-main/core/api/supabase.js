/**
 * CHERP SupabaseClient
 * Wraps @supabase/supabase-js with error handling and admin access.
 */
class SupabaseClient {
  constructor() {
    this._client = null;
    this._adminClient = null;
    this._url = null;
    this._anonKey = null;
  }

  /**
   * Initialize the Supabase client from instance config.
   */
  init(url, anonKey) {
    if (!url || !anonKey) {
      throw new Error('Supabase URL and anon key are required.');
    }

    this._url = url;
    this._anonKey = anonKey;

    this._client = supabase.createClient(url, anonKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
        detectSessionInUrl: false
      },
      global: {
        headers: {
          'x-cherp-client': 'modular-pwa'
        }
      }
    });

    console.log('[Supabase] Client initialized:', url);
    return this._client;
  }

  /**
   * Get the standard Supabase client (anon key, RLS enforced).
   */
  SB() {
    if (!this._client) {
      throw new Error('Supabase client not initialized. Call init() first.');
    }
    return this._client;
  }

  /**
   * Get an admin-level Supabase client (service role key).
   * Only available if a service role key is provided — never expose in production client.
   * Falls back to the standard client if no admin key set.
   */
  SB_Admin() {
    if (this._adminClient) return this._adminClient;
    console.warn('[Supabase] No admin client configured — using standard client. Set service_role_key for admin operations.');
    return this.SB();
  }

  /**
   * Set up admin client with service role key.
   * This should only be used in controlled server-side or build contexts.
   */
  initAdmin(serviceRoleKey) {
    if (!this._url) {
      throw new Error('Must call init() before initAdmin().');
    }

    this._adminClient = supabase.createClient(this._url, serviceRoleKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
        detectSessionInUrl: false
      }
    });

    console.log('[Supabase] Admin client initialized.');
    return this._adminClient;
  }

  /**
   * Execute a query with standardized error handling.
   * Returns { data, error, ok }.
   */
  async query(fn) {
    try {
      const { data, error } = await fn(this.SB());

      if (error) {
        console.error('[Supabase] Query error:', error.message);
        return { data: null, error: error.message, ok: false };
      }

      return { data, error: null, ok: true };
    } catch (e) {
      console.error('[Supabase] Exception:', e.message);
      return { data: null, error: e.message, ok: false };
    }
  }

  /**
   * Fetch a single row or null.
   */
  async fetchOne(table, matchObj, select = '*') {
    const { data, error } = await this.SB()
      .from(table)
      .select(select)
      .match(matchObj)
      .single();

    if (error) {
      if (error.code === 'PGRST116') return { data: null, error: null, ok: true }; // No rows
      return { data: null, error: error.message, ok: false };
    }

    return { data, error: null, ok: true };
  }

  /**
   * Insert a row and return it.
   */
  async insert(table, row) {
    const { data, error } = await this.SB()
      .from(table)
      .insert(row)
      .select()
      .single();

    if (error) return { data: null, error: error.message, ok: false };
    return { data, error: null, ok: true };
  }

  /**
   * Update rows matching a condition.
   */
  async update(table, matchObj, updates) {
    const { data, error } = await this.SB()
      .from(table)
      .update(updates)
      .match(matchObj)
      .select();

    if (error) return { data: null, error: error.message, ok: false };
    return { data, error: null, ok: true };
  }

  /**
   * Delete rows matching a condition.
   */
  async remove(table, matchObj) {
    const { data, error } = await this.SB()
      .from(table)
      .delete()
      .match(matchObj);

    if (error) return { data: null, error: error.message, ok: false };
    return { data, error: null, ok: true };
  }

  /**
   * Subscribe to real-time changes on a table.
   */
  subscribe(table, filter, callback) {
    const channel = this.SB()
      .channel(`cherp-${table}-${Date.now()}`)
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: table,
        filter: filter || undefined
      }, payload => {
        callback(payload);
      })
      .subscribe();

    return channel;
  }

  /**
   * Check if we can reach Supabase.
   */
  async healthCheck() {
    try {
      const { data, error } = await this.SB()
        .from('app_settings')
        .select('key')
        .limit(1);
      return !error;
    } catch (e) {
      return false;
    }
  }
}

window.SupabaseClient = SupabaseClient;
