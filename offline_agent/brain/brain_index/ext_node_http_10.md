# Node.js http (10/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ponse'`
  * `'data'` any number of times, on the `res` object
* (`req.destroy()` called here)
* `'aborted'` on the `res` object
* `'close'`
* `'error'` on the `res` object with an error with message `'Error: aborted'`
  and code `'ECONNRESET'`, or the error with which `req.destroy()` was called
* `'close'` on the `res` object

If `req.abort()` is called before a socket is assigned, the following
events will be emitted in the following order:

* (`req.abort()` called here)
* `'abort'`
* `'close'`

If `req.abort()` is called before the connection succeeds, the following
events will be emitted in the following order:

* `'socket'`
* (`req.abort()` called here)
* `'abort'`
* `'error'` with an error with message `'Error: socket hang up'` and code
  `'ECONNRESET'`
* `'close'`

If `req.abort()` is called after the response is received, the following
events will be emitted in the following order:

* `'socket'`
* `'response'`
  * `'data'` any number of times, on the `res` object
* (`req.abort()` called here)
* `'abort'`
* `'aborted'` on the `res` object
* `'error'` on the `res` object with an error with message
  `'Error: aborted'` and code `'ECONNRESET'`.
* `'close'`
* `'close'` on the `res` object

Setting the `timeout` option or using the `setTimeout()` function will
not abort the request or do anything besides add a `'timeout'` event.

Passing an `AbortSignal` and then calling `abort()` on the corresponding
`AbortController` will behave the same way as calling `.destroy()` on the
request. Specifically, the `'error'` event will be emitted with an error with
the message `'AbortError: The operation was aborted'`, the code `'ABORT_ERR'`
and the `cause`, if one was provided.

## `http.validateHeaderName(name[, label])`

<!-- YAML
added: v14.3.0
changes:
  - version:
    - v19.5.0
    - v18.14.0
    pr-url: https://github.com/nodejs/node/pull/46143
    description: The `label` parameter is added.
-->

* `name` {string}
* `label` {string} Label for error message. **Default:** `'Header name'`.

Performs the low-level validations on the provided `name` that are done when
`res.setHeader(name, value)` is called.

Passing illegal value as `name` will result in a [`TypeError`][] being thrown,
identified by `code: 'ERR_INVALID_HTTP_TOKEN'`.

It is not necessary to use this method before passing headers to an HTTP request
or response. The HTTP module will automatically validate such headers.

Example:

```mjs
import { validateHeaderName } from 'node:http';

try {
  validateHeaderName('');
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code); // --> 'ERR_INVALID_HTTP_TOKEN'
  console.error(err.message); // --> 'Header name must be a valid HTTP token [""]'
}
```

```cjs
const { validateHeaderName } = require('node:http');

try {
  validateHeaderName('');
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code); // --> 'ERR_INVALID_HTTP_TOKEN'
  console.error(err.message); // --> 'Header name must be a valid HTTP token [""]'
}
```

## `http.validateHeaderValue(name, value)`

<!-- YAML
added: v14.3.0
-->

* `name` {string}
* `value` {any}

Performs the low-level validations on the provided `value` that are done when
`res.setHeader(name, value)` is called.

Passing illegal value as `value` will result in a [`TypeError`][] being thrown.

* Undefined value error is identified by `code: 'ERR_HTTP_INVALID_HEADER_VALUE'`.
* Invalid value character error is identified by `code: 'ERR_INVALID_CHAR'`.

It is not necessary to use this method before passing headers to an HTTP request
or response. The HTTP module will automatically validate such headers.

Examples:

```mjs
import { validateHeaderValue } from 'node:http';

try {
  validateHeaderValue('x-my-header', undefined);
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code === 'ERR_HTTP_INVALID_HEADER_VALUE'); // --> true
  console.error(err.message); // --> 'Invalid value "undefined" for header "x-my-header"'
}

try {
  validateHeaderValue('x-my-header', 'oʊmɪɡə');
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code === 'ERR_INVALID_CHAR'); // --> true
  console.error(err.message); // --> 'Invalid character in header content ["x-my-header"]'
}
```

```cjs
const { validateHeaderValue } = require('node:http');

try {
  validateHeaderValue('x-my-header', undefined);
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code === 'ERR_HTTP_INVALID_HEADER_VALUE'); // --> true
  console.error(err.message); // --> 'Invalid value "undefined" for header "x-my-header"'
}

try {
  validateHeaderValue('x-my-header', 'oʊmɪɡə');
} catch (err) {
  console.error(err instanceof TypeError); // --> true
  console.error(err.code === 'ERR_INVALID_CHAR'); // --> true
  console.error(err.message); // --> 'Invalid character in header content ["x-my-header"]'
}
```

## `http.setMaxIdleHTTPParsers(max)`

<!-- YAML
added:
  - v18.8.0
  - v16.18.0
-->

* `max` {number} **Default:** `1000`.

Set the maximum number of idle HTTP parsers.

## `http.setGlobalProxyFromEnv([proxyEnv])`

<!-- YAML
added:
  - v25.4.0
  - v24.14.0
-->

* `proxyEnv` {Object} An object containing proxy configuration. This accepts the
  same options as the `proxyEnv` option accepted by [`Agent`][]. **Default:**
  `process.env`.
* Returns: {Function} A function that restores the original agent and dispatcher
  settings to the state before this `http.setGlobalProxyFromEnv()` is invoked.

Dynamically resets the global configurations to enable built-in proxy support for
`fetch()` and `http.request()`/`https.request()` at runtime, as an alternative
to using the `--use-env-proxy` flag or `NODE_USE_ENV_PROXY` environment variable.
It can also be used to override settings configured from the environment variables.

As this function resets the global configurations, any previously configured
`http.globalAgent`, `https.globalAgent` or undici global dispatcher would be
overridden after this function is invoked. It's recommended to invoke it before any
requests are made and avoid invoking it in the middle of any requests.

See [Built-in Proxy Support][] for details on proxy URL formats and `NO_PROXY`
syntax.

## Class: `WebSocket`

<!-- YAML
added:
  - v22.5.0
-->

A browser-compatible implementation of {WebSocket}.

## Built-in Proxy Support

<!-- YAML
added:
 - v24.5.0
 - v22.21.0
-->

> Stability: 1.1 - Active development

When Node.js creates the global agent, if the `NODE_USE_ENV_PROXY` environment variable is
set to `1` or `--use-env-proxy` is enabled, the global agent will be constructed
with `proxyEnv: process.env`, enabling proxy support based on the environment variables.

To enable proxy support dynamically and globally, use [`http.setGlobalProxyFromEnv()`][].

Custom agents can also be created with proxy support by passing a
`proxyEnv` option when constructing the agent. The value can be `process.env`
if they just want to inherit the configuration from the environment variables,
or an object with specific setting overriding the environment.

The following properties of the `proxyEnv` are checked to configure proxy
support.

* `HTTP_PROXY` or `http_proxy`: Proxy server URL for HTTP requests. If both are set,
  `http_proxy` takes precedence.
* `HTTPS_PROXY` or `https_proxy`: Proxy server URL for HTTPS requests. If both are set,
  `https_proxy` takes precedence.
* `NO_PROXY` or `no_proxy`: Comma-separated list of hosts to bypass the proxy. If both are set,
  `no_proxy` takes precedence.

If the request is made to a Unix domain socket, the proxy settings will be ignored.

### Proxy URL Format

Proxy URLs can use either HTTP or HTTPS protocols:

* HTTP proxy: `http://proxy.example.com:8080`
* HTTPS proxy: `https://proxy.example.com:8080`
* Proxy with authentication: `http://username:password@proxy.example.com:8080`

### `NO_PROXY` Format

The `NO_PROXY` environment variable supports several formats:

* `*` - Bypass proxy for all hosts
* `example.com` - Exact host name match
* `.example.com` - Domain suffix match (matches `sub.example.com`)
* `*.example.com` - Wildcard domain match
* `192.168.1.100` - Exact IP address match
* `192.168.1.1-192.168.1.100` - IP address range
* `example.com:8080` - Hostname with specific port

Multiple entries should be separated by commas.

### Example

To start a Node.js process with proxy support enabled for all requests sent
through the default global agent, either use the `NODE_USE_ENV_PROXY` environment
variable:

```console
NODE_USE_ENV_PROXY=1 HTTP_PROXY=http://proxy.example.com:8080 NO_PROXY=localhost,127.0.0.1 node client.js
```

Or the `--use-env-proxy` flag.

```console
HTTP_PROXY=http://proxy.example.com:8080 NO_PROXY=localhost,127.0.0.1 node --use-env-proxy client.js
```

To enable proxy support dynamically and globally with `process.env` (the default option of `http.setGlobalProxyFromEnv()`):

```cjs
const http = require('node:http');

// Reads proxy-related environment variables from process.env
const restore = http.setGlobalProxyFromEnv();

// Subsequent requests will use the configured proxies from environment variables
http.get('http://www.example.com', (res) => {
  // This request will be proxied if HTTP_PROXY or http_proxy is set
});

fetch('https://www.example.com', (res) => {
  // This request will be proxied if HTTPS_PROXY or https_proxy is set
});

// To restore the original global agent and dispatcher settings, call the returned function.
// restore();
```

```mjs
import http from 'node:http';

// Reads proxy-related environment variables from process.env
http.setGlobalProxyFromEnv();

// Subsequent requests will use the configured proxies from environment variables
http.get('http://www.example.com', (res) => {
  // This request will be proxied if HTTP_PROXY or http_proxy is set
});

fetch('https://www.example.com', (res) => {
  // This request will be proxied if HTTPS_PROXY or https_proxy is set
});

// To restore the original global agent and dispatcher settings, call the returned function.
// restore();
```

To enable proxy support dynamically and globally with custom settings:

```cjs
const http = require('node:http');

const restore = http.setGlobalProxyFromEnv({
  http_proxy: 'http://proxy.example.com:8080',
  https_proxy: 'https://proxy.example.com:8443',
  no_proxy: 'localhost,127.0.0.1,.internal.example.com',
});

// Subsequent requests will use the configured proxies
http.get('http://www.example.com', (res) => {
  // This request will be proxied through proxy.example.com:8080
});

fetch('https://www.example.com', (res) => {
  // This request will be proxied through proxy.example.com:8443
});
```

```mjs
import http from 'node:http';

http.setGlobalProxyFromEnv({
  http_proxy: 'http://proxy.example.com:8080',
  https_proxy: 'https://proxy.example.com:8443',
  no_proxy: 'localhost,127.0.0.1,.internal.example.com',
});

// Subsequent requests will use the configured proxies
http.get('http://www.example.com', (res) => {
  // This request will be proxied through proxy.example.com:8080
});

fetch('https://www.example.com', (res) => {
  // This request will be proxied through proxy.example.com:8443
});
```

To create a custom agent with built-in proxy support:

```cjs
const http = require('node:http');

// Creating a custom agent with custom proxy support.
const agent = new http.Agent({ proxyEnv: { HTTP_PROXY: 'http://proxy.example.com:8080' } });

http.request({
  hostname: 'www.example.com',
  port: 80,
  path: '/',
  agent,
}, (res) => {
  // This request will be proxied through proxy.example.com:8080 using the HTTP protocol.
  console.log(`STATUS: ${res.statusCode}`);
});
```

Alternatively, the following also works:

```cjs
const http = require('node:http');
// Use lower-cased option name.
const agent1 = new http.Agent({ proxyEnv: { http_proxy: 'http://proxy.example.com:8080' } });
// Use values inherited from the environment variables, if the process is started with
// HTTP_PROXY=http://proxy.example.com:8080 this will use the proxy server specified
// in process.env.HTTP_PROXY.
const agent2 = new http.Agent({ proxyEnv: process.env });
```
