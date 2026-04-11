/**
 * Google OAuth2 Authentication for Sheets Sync
 * Zero dependencies — uses Node.js built-in https/http/fs
 *
 * Flow:
 *   1. First run: opens browser for OAuth consent, catches callback on :9999
 *   2. Subsequent runs: loads refresh token from token.json, auto-refreshes
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SHEETS_DIR = path.dirname(__filename);
const TOKEN_PATH = path.join(SHEETS_DIR, 'token.json');
const CREDS_PATH = path.join(SHEETS_DIR, 'credentials.json');
const SCOPES = [
  'https://www.googleapis.com/auth/spreadsheets',
  'https://www.googleapis.com/auth/drive.file'
];
const REDIRECT_PORT = 9999;
const REDIRECT_URI = `http://localhost:${REDIRECT_PORT}`;

/** Load OAuth client credentials */
function loadCredentials() {
  // Check local copy first, then Desktop fallback
  let credPath = CREDS_PATH;
  if (!fs.existsSync(credPath)) {
    const desktopPath = 'C:/Users/Ken/Desktop/client_secret_294359454385-u6n51uhkub2d5dkm75e0406gl7dhtaf2.apps.googleusercontent.com.json';
    if (fs.existsSync(desktopPath)) {
      // Copy to sheets dir for future use
      fs.copyFileSync(desktopPath, credPath);
    } else {
      throw new Error('No Google credentials found. Place credentials.json in agent_mode/sheets/');
    }
  }
  const raw = JSON.parse(fs.readFileSync(credPath, 'utf8'));
  const creds = raw.installed || raw.web;
  return {
    clientId: creds.client_id,
    clientSecret: creds.client_secret
  };
}

/** HTTPS POST helper — returns parsed JSON */
function httpsPost(hostname, path, params) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams(params).toString();
    const req = https.request({
      hostname, path, method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { reject(new Error(`Bad response: ${data}`)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

/** Exchange authorization code for tokens */
async function exchangeCode(code, clientId, clientSecret) {
  return httpsPost('oauth2.googleapis.com', '/token', {
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: REDIRECT_URI,
    grant_type: 'authorization_code'
  });
}

/** Refresh an expired access token */
async function refreshAccessToken(refreshToken, clientId, clientSecret) {
  return httpsPost('oauth2.googleapis.com', '/token', {
    refresh_token: refreshToken,
    client_id: clientId,
    client_secret: clientSecret,
    grant_type: 'refresh_token'
  });
}

/**
 * One-time interactive auth flow.
 * Opens browser → user consents → callback catches code → exchanges for tokens.
 * Returns the token object and saves to disk.
 */
function authorizeInteractive() {
  return new Promise((resolve, reject) => {
    const { clientId, clientSecret } = loadCredentials();
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
      `&response_type=code&scope=${encodeURIComponent(SCOPES.join(' '))}` +
      `&access_type=offline&prompt=consent`;

    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url, `http://localhost:${REDIRECT_PORT}`);
      const code = url.searchParams.get('code');
      const error = url.searchParams.get('error');

      if (error) {
        res.writeHead(400, { 'Content-Type': 'text/html' });
        res.end(`<h2>Authorization failed: ${error}</h2><p>Close this tab and try again.</p>`);
        server.close();
        reject(new Error(`OAuth denied: ${error}`));
        return;
      }

      if (code) {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`<h2 style="color:green">&#10003; CHERP Sheets connected!</h2><p>You can close this tab.</p>`);
        server.close();

        try {
          const tokens = await exchangeCode(code, clientId, clientSecret);
          if (tokens.error) {
            reject(new Error(`Token exchange failed: ${tokens.error_description || tokens.error}`));
            return;
          }
          tokens.obtained_at = Date.now();
          fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2));
          resolve(tokens);
        } catch (e) {
          reject(e);
        }
      }
    });

    server.listen(REDIRECT_PORT, () => {
      console.log(`OAuth callback listening on port ${REDIRECT_PORT}`);
      // Open browser on Windows
      try {
        execSync(`start "" "${authUrl}"`, { shell: 'cmd.exe', stdio: 'ignore' });
      } catch {
        console.log(`Open this URL in your browser:\n${authUrl}`);
      }
    });

    // Timeout after 2 minutes
    setTimeout(() => {
      server.close();
      reject(new Error('OAuth timed out — no response in 2 minutes'));
    }, 120000);
  });
}

/**
 * Get a valid access token.
 * - If token.json exists and is fresh, returns it.
 * - If expired, refreshes it.
 * - If no token exists, runs interactive auth.
 *
 * @returns {Promise<string>} A valid access_token
 */
async function getToken() {
  const { clientId, clientSecret } = loadCredentials();

  if (fs.existsSync(TOKEN_PATH)) {
    const tokens = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
    const expiresAt = (tokens.obtained_at || 0) + ((tokens.expires_in || 3600) * 1000);

    // Still valid (with 5-min buffer)
    if (Date.now() < expiresAt - 300000) {
      return tokens.access_token;
    }

    // Expired but has refresh token
    if (tokens.refresh_token) {
      const refreshed = await refreshAccessToken(tokens.refresh_token, clientId, clientSecret);
      if (refreshed.error) {
        throw new Error(`Token refresh failed: ${refreshed.error_description || refreshed.error}`);
      }
      // Preserve refresh_token (Google doesn't always return it on refresh)
      refreshed.refresh_token = refreshed.refresh_token || tokens.refresh_token;
      refreshed.obtained_at = Date.now();
      fs.writeFileSync(TOKEN_PATH, JSON.stringify(refreshed, null, 2));
      return refreshed.access_token;
    }
  }

  // No token — need interactive auth
  const tokens = await authorizeInteractive();
  return tokens.access_token;
}

/** Check if we have a stored token (without refreshing) */
function hasToken() {
  return fs.existsSync(TOKEN_PATH);
}

module.exports = { getToken, hasToken, authorizeInteractive, loadCredentials, TOKEN_PATH };
