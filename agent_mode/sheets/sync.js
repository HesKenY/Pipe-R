/**
 * CHERP ↔ Google Sheets Sync Engine
 * Push: Supabase → Sheets | Pull: Sheets → Supabase
 * Zero dependencies — Node.js built-in https only
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { getToken } = require('./auth');
const { TABS, getTab, getEditableTabs, getHeaders, getKeys, buildFormatRequests } = require('./schema');

const SHEETS_DIR = path.dirname(__filename);
const CONFIG_PATH = path.join(SHEETS_DIR, 'config.json');

// Supabase credentials — same ones CHERP uses
const SUPABASE_URL = 'https://nptmzihtujgkmqougkzd.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY || '';

// ─── Config Management ──────────────────────────────────────────

function loadConfig() {
  if (fs.existsSync(CONFIG_PATH)) {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  }
  return { crews: {}, lastSync: null, syncInterval: 900000 }; // 15 min default
}

function saveConfig(config) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
}

// ─── HTTPS Helpers ───────────────────────────────────────────────

function httpsRequest(method, url, headers = {}, body = null) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const opts = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method,
      headers: { ...headers }
    };
    if (body) {
      const payload = typeof body === 'string' ? body : JSON.stringify(body);
      opts.headers['Content-Length'] = Buffer.byteLength(payload);
    }
    const req = https.request(opts, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data });
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(typeof body === 'string' ? body : JSON.stringify(body));
    req.end();
  });
}

async function sheetsApi(method, path, body = null) {
  const token = await getToken();
  const url = `https://sheets.googleapis.com/v4/spreadsheets${path}`;
  return httpsRequest(method, url, {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }, body);
}

async function driveApi(method, path, body = null) {
  const token = await getToken();
  const url = `https://www.googleapis.com/drive/v3${path}`;
  return httpsRequest(method, url, {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }, body);
}

function supabaseGet(table, query = '') {
  const url = `${SUPABASE_URL}/rest/v1/${table}?${query}`;
  return httpsRequest('GET', url, {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json'
  });
}

function supabasePatch(table, matchColumn, matchValue, data) {
  const url = `${SUPABASE_URL}/rest/v1/${table}?${matchColumn}=eq.${encodeURIComponent(matchValue)}`;
  return httpsRequest('PATCH', url, {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
  }, data);
}

// ─── Sheet Creation ──────────────────────────────────────────────

/**
 * Create a new Google Spreadsheet for a crew.
 * Sets up all tabs with headers, formatting, and validation.
 * @param {string} teamCode - The crew's team_code
 * @param {string} crewName - Display name for the spreadsheet title
 * @returns {string} spreadsheetId
 */
async function createCrewSheet(teamCode, crewName) {
  const title = `CHERP — ${crewName || teamCode}`;

  // Create spreadsheet with all tabs
  const createBody = {
    properties: { title },
    sheets: TABS.map((tab, i) => ({
      properties: {
        sheetId: i,
        title: tab.name,
        index: i
      }
    }))
  };

  const { status, data } = await sheetsApi('POST', '', createBody);
  if (status !== 200) {
    throw new Error(`Failed to create spreadsheet: ${JSON.stringify(data)}`);
  }

  const spreadsheetId = data.spreadsheetId;

  // Write headers to each tab
  const headerData = TABS.map(tab => ({
    range: `'${tab.name}'!A1`,
    values: [getHeaders(tab.name)]
  }));

  await sheetsApi('POST', `/${spreadsheetId}/values:batchUpdate`, {
    valueInputOption: 'RAW',
    data: headerData
  });

  // Apply formatting (colors, widths, freeze, validation, protection)
  const formatRequests = [];
  TABS.forEach((tab, i) => {
    formatRequests.push(...buildFormatRequests(tab, i));
  });

  await sheetsApi('POST', `/${spreadsheetId}:batchUpdate`, {
    requests: formatRequests
  });

  // Save to config
  const config = loadConfig();
  config.crews[teamCode] = {
    spreadsheetId,
    crewName: crewName || teamCode,
    createdAt: new Date().toISOString(),
    lastPush: null,
    lastPull: null
  };
  saveConfig(config);

  return spreadsheetId;
}

// ─── Push Sync (Supabase → Sheets) ──────────────────────────────

/**
 * Push data from Supabase to Google Sheets for a crew.
 * Replaces all data in each tab (preserving headers).
 */
async function pushSync(teamCode) {
  const config = loadConfig();
  const crew = config.crews[teamCode];
  if (!crew) throw new Error(`No sheet configured for crew: ${teamCode}`);

  const spreadsheetId = crew.spreadsheetId;
  const results = { tabs: {}, errors: [] };

  for (const tab of TABS) {
    try {
      // Build Supabase query
      let query = 'select=*';
      if (tab.teamFilter) {
        query += `&${tab.teamFilter}=eq.${encodeURIComponent(teamCode)}`;
      }
      if (tab.sortBy) {
        query += `&order=${tab.sortBy}.${tab.sortDesc ? 'desc' : 'asc'}`;
      }

      // Special case: certifications join through user_profiles
      let rows;
      if (tab.name === 'Certifications') {
        // Get user IDs for this crew first
        const usersResp = await supabaseGet('user_profiles', `select=id&team_code=eq.${encodeURIComponent(teamCode)}`);
        if (usersResp.status === 200 && usersResp.data.length > 0) {
          const userIds = usersResp.data.map(u => u.id);
          const certQuery = `select=*&user_id=in.(${userIds.join(',')})`;
          const certResp = await supabaseGet('worker_certifications', certQuery);
          rows = certResp.status === 200 ? certResp.data : [];
        } else {
          rows = [];
        }
      } else {
        const resp = await supabaseGet(tab.table, query);
        rows = resp.status === 200 ? resp.data : [];
      }

      // Map rows to sheet values using column keys
      const keys = getKeys(tab.name);
      const values = rows.map(row =>
        keys.map(key => {
          const val = row[key];
          if (val === null || val === undefined) return '';
          if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
          if (typeof val === 'object') return JSON.stringify(val);
          return String(val);
        })
      );

      // Clear existing data (rows 2+) and write new data
      const range = `'${tab.name}'!A2:${String.fromCharCode(64 + keys.length)}`;

      // Clear old data
      await sheetsApi('POST', `/${spreadsheetId}/values/${encodeURIComponent(range)}:clear`);

      // Write new data
      if (values.length > 0) {
        await sheetsApi('PUT',
          `/${spreadsheetId}/values/${encodeURIComponent(`'${tab.name}'!A2`)}?valueInputOption=RAW`,
          { values }
        );
      }

      results.tabs[tab.name] = { rows: values.length, ok: true };
    } catch (e) {
      results.tabs[tab.name] = { rows: 0, ok: false, error: e.message };
      results.errors.push(`${tab.name}: ${e.message}`);
    }
  }

  // Update config
  crew.lastPush = new Date().toISOString();
  saveConfig(config);

  return results;
}

/**
 * Push sync all configured crews.
 */
async function pushSyncAll() {
  const config = loadConfig();
  const results = {};
  for (const teamCode of Object.keys(config.crews)) {
    try {
      results[teamCode] = await pushSync(teamCode);
    } catch (e) {
      results[teamCode] = { error: e.message };
    }
  }
  return results;
}

// ─── Pull Sync (Sheets → Supabase) ──────────────────────────────

/**
 * Pull edits from Google Sheets back into Supabase.
 * Only processes editable tabs. Diffs against current Supabase state.
 */
async function pullSync(teamCode) {
  const config = loadConfig();
  const crew = config.crews[teamCode];
  if (!crew) throw new Error(`No sheet configured for crew: ${teamCode}`);

  const spreadsheetId = crew.spreadsheetId;
  const editableTabs = getEditableTabs();
  const results = { tabs: {}, changes: 0, errors: [] };

  for (const tab of editableTabs) {
    try {
      const keys = getKeys(tab.name);
      const idKey = tab.idColumn;

      // Read sheet data
      const range = `'${tab.name}'!A2:${String.fromCharCode(64 + keys.length)}`;
      const sheetResp = await sheetsApi('GET',
        `/${spreadsheetId}/values/${encodeURIComponent(range)}`
      );
      const sheetRows = (sheetResp.data && sheetResp.data.values) || [];

      // Read current Supabase data
      let query = `select=*`;
      if (tab.teamFilter) {
        query += `&${tab.teamFilter}=eq.${encodeURIComponent(teamCode)}`;
      }
      const dbResp = await supabaseGet(tab.table, query);
      const dbRows = dbResp.status === 200 ? dbResp.data : [];

      // Index DB rows by ID
      const dbIndex = {};
      dbRows.forEach(row => { dbIndex[String(row[idKey])] = row; });

      let tabChanges = 0;

      // Compare each sheet row against DB
      for (const sheetRow of sheetRows) {
        if (!sheetRow || sheetRow.length === 0) continue;

        // Map sheet values back to keyed object
        const obj = {};
        keys.forEach((key, i) => {
          const val = sheetRow[i] || '';
          if (val === 'TRUE') obj[key] = true;
          else if (val === 'FALSE') obj[key] = false;
          else if (val === '') obj[key] = null;
          else obj[key] = val;
        });

        const rowId = obj[idKey];
        if (!rowId) continue;

        const dbRow = dbIndex[String(rowId)];
        if (!dbRow) continue; // Don't create new rows from sheets — safety measure

        // Diff: find changed fields (skip id and non-editable metadata)
        const skipKeys = new Set([idKey, 'created_at', 'team_code']);
        const patch = {};
        let changed = false;

        for (const key of keys) {
          if (skipKeys.has(key)) continue;
          const sheetVal = obj[key];
          const dbVal = dbRow[key];

          // Normalize for comparison
          const normSheet = sheetVal === null ? '' : String(sheetVal);
          const normDb = (dbVal === null || dbVal === undefined) ? '' : String(dbVal);

          if (normSheet !== normDb) {
            patch[key] = sheetVal;
            changed = true;
          }
        }

        if (changed) {
          await supabasePatch(tab.table, idKey, rowId, patch);
          tabChanges++;
        }
      }

      results.tabs[tab.name] = { checked: sheetRows.length, changed: tabChanges, ok: true };
      results.changes += tabChanges;
    } catch (e) {
      results.tabs[tab.name] = { checked: 0, changed: 0, ok: false, error: e.message };
      results.errors.push(`${tab.name}: ${e.message}`);
    }
  }

  // Update config
  crew.lastPull = new Date().toISOString();
  saveConfig(config);

  return results;
}

// ─── Status & Utilities ──────────────────────────────────────────

/** Get sync status for all crews */
function getSyncStatus() {
  const config = loadConfig();
  const status = {};
  for (const [code, crew] of Object.entries(config.crews)) {
    status[code] = {
      crewName: crew.crewName,
      spreadsheetId: crew.spreadsheetId,
      lastPush: crew.lastPush,
      lastPull: crew.lastPull,
      url: `https://docs.google.com/spreadsheets/d/${crew.spreadsheetId}`
    };
  }
  return status;
}

/** Get the spreadsheet URL for a crew */
function getSheetUrl(teamCode) {
  const config = loadConfig();
  const crew = config.crews[teamCode];
  return crew ? `https://docs.google.com/spreadsheets/d/${crew.spreadsheetId}` : null;
}

/** List all configured crew codes */
function getConfiguredCrews() {
  const config = loadConfig();
  return Object.keys(config.crews);
}

/** Set the Supabase service key at runtime */
function setSupabaseKey(key) {
  // Store in module scope for this process
  module.exports._supabaseKey = key;
}

module.exports = {
  createCrewSheet,
  pushSync,
  pushSyncAll,
  pullSync,
  getSyncStatus,
  getSheetUrl,
  getConfiguredCrews,
  setSupabaseKey,
  loadConfig,
  saveConfig
};
