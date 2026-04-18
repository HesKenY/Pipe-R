# Node.js http (8/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
e.hasHeader(name)`

<!-- YAML
added: v7.7.0
-->

* `name` {string}
* Returns: {boolean}

Returns `true` if the header identified by `name` is currently set in the
outgoing headers. The header name is case-insensitive.

```js
const hasContentType = outgoingMessage.hasHeader('content-type');
```

### `outgoingMessage.headersSent`

<!-- YAML
added: v0.9.3
-->

* Type: {boolean}

Read-only. `true` if the headers were sent, otherwise `false`.

### `outgoingMessage.pipe()`

<!-- YAML
added: v9.0.0
-->

Overrides the `stream.pipe()` method inherited from the legacy `Stream` class
which is the parent class of `http.OutgoingMessage`.

Calling this method will throw an `Error` because `outgoingMessage` is a
write-only stream.

### `outgoingMessage.removeHeader(name)`

<!-- YAML
added: v0.4.0
-->

* `name` {string} Header name

Removes a header that is queued for implicit sending.

```js
outgoingMessage.removeHeader('Content-Encoding');
```

### `outgoingMessage.setHeader(name, value)`

<!-- YAML
added: v0.4.0
-->

* `name` {string} Header name
* `value` {number | string | string\[]} Header value
* Returns: {this}

Sets a single header value. If the header already exists in the to-be-sent
headers, its value will be replaced. Use an array of strings to send multiple
headers with the same name.

### `outgoingMessage.setHeaders(headers)`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* `headers` {Headers|Map}
* Returns: {this}

Sets multiple header values for implicit headers.
`headers` must be an instance of [`Headers`][] or `Map`,
if a header already exists in the to-be-sent headers,
its value will be replaced.

```js
const headers = new Headers({ foo: 'bar' });
outgoingMessage.setHeaders(headers);
```

or

```js
const headers = new Map([['foo', 'bar']]);
outgoingMessage.setHeaders(headers);
```

When headers have been set with [`outgoingMessage.setHeaders()`][],
they will be merged with any headers passed to [`response.writeHead()`][],
with the headers passed to [`response.writeHead()`][] given precedence.

```js
// Returns content-type = text/plain
const server = http.createServer((req, res) => {
  const headers = new Headers({ 'Content-Type': 'text/html' });
  res.setHeaders(headers);
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('ok');
});
```

### `outgoingMessage.setTimeout(msecs[, callback])`

<!-- YAML
added: v0.9.12
-->

* `msecs` {number}
* `callback` {Function} Optional function to be called when a timeout
  occurs. Same as binding to the `timeout` event.
* Returns: {this}

Once a socket is associated with the message and is connected,
[`socket.setTimeout()`][] will be called with `msecs` as the first parameter.

### `outgoingMessage.socket`

<!-- YAML
added: v0.3.0
-->

* Type: {stream.Duplex}

Reference to the underlying socket. Usually, users will not want to access
this property.

After calling `outgoingMessage.end()`, this property will be nulled.

### `outgoingMessage.uncork()`

<!-- YAML
added:
  - v13.2.0
  - v12.16.0
-->

See [`writable.uncork()`][]

### `outgoingMessage.writableCorked`

<!-- YAML
added:
  - v13.2.0
  - v12.16.0
-->

* Type: {number}

The number of times `outgoingMessage.cork()` has been called.

### `outgoingMessage.writableEnded`

<!-- YAML
added: v12.9.0
-->

* Type: {boolean}

Is `true` if `outgoingMessage.end()` has been called. This property does
not indicate whether the data has been flushed. For that purpose, use
`message.writableFinished` instead.

### `outgoingMessage.writableFinished`

<!-- YAML
added: v12.7.0
-->

* Type: {boolean}

Is `true` if all data has been flushed to the underlying system.

### `outgoingMessage.writableHighWaterMark`

<!-- YAML
added: v12.9.0
-->

* Type: {number}

The `highWaterMark` of the underlying socket if assigned. Otherwise, the default
buffer level when [`writable.write()`][] starts returning false (`16384`).

### `outgoingMessage.writableLength`

<!-- YAML
added: v12.9.0
-->

* Type: {number}

The number of buffered bytes.

### `outgoingMessage.writableObjectMode`

<!-- YAML
added: v12.9.0
-->

* Type: {boolean}

Always `false`.

### `outgoingMessage.write(chunk[, encoding][, callback])`

<!-- YAML
added: v0.1.29
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `chunk` parameter can now be a `Uint8Array`.
  - version: v0.11.6
    description: The `callback` argument was added.
-->

* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string} **Default**: `utf8`
* `callback` {Function}
* Returns: {boolean}

Sends a chunk of the body. This method can be called multiple times.

The `encoding` argument is only relevant when `chunk` is a string. Defaults to
`'utf8'`.

The `callback` argument is optional and will be called when this chunk of data
is flushed.

Returns `true` if the entire data was flushed successfully to the kernel
buffer. Returns `false` if all or part of the data was queued in the user
memory. The `'drain'` event will be emitted when the buffer is free again.

## `http.METHODS`

<!-- YAML
added: v0.11.8
-->

* Type: {string\[]}

A list of the HTTP methods that are supported by the parser.

## `http.STATUS_CODES`

<!-- YAML
added: v0.1.22
-->

* Type: {Object}

A collection of all the standard HTTP response status codes, and the
short description of each. For example, `http.STATUS_CODES[404] === 'Not
Found'`.

## `http.createServer([options][, requestListener])`

<!-- YAML
added: v0.1.13
changes:
  - version:
      - v25.1.0
      - v24.12.0
    pr-url: https://github.com/nodejs/node/pull/59778
    description: Add optimizeEmptyRequests option.
  - version:
     - v24.9.0
     - v22.21.0
    pr-url: https://github.com/nodejs/node/pull/59824
    description: The `shouldUpgradeCallback` option is now supported.
  - version:
    - v20.1.0
    - v18.17.0
    pr-url: https://github.com/nodejs/node/pull/47405
    description: The `highWaterMark` option is supported now.
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41263
    description: The `requestTimeout`, `headersTimeout`, `keepAliveTimeout`, and
                 `connectionsCheckingInterval` options are supported now.
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/42163
    description: The `noDelay` option now defaults to `true`.
  - version:
    - v17.7.0
    - v16.15.0
    pr-url: https://github.com/nodejs/node/pull/41310
    description: The `noDelay`, `keepAlive` and `keepAliveInitialDelay`
                 options are supported now.
  - version:
     - v13.8.0
     - v12.15.0
     - v10.19.0
    pr-url: https://github.com/nodejs/node/pull/31448
    description: The `insecureHTTPParser` option is supported now.
  - version: v13.3.0
    pr-url: https://github.com/nodejs/node/pull/30570
    description: The `maxHeaderSize` option is supported now.
  - version:
    - v9.6.0
    - v8.12.0
    pr-url: https://github.com/nodejs/node/pull/15752
    description: The `options` argument is supported now.
-->

* `options` {Object}
  * `connectionsCheckingInterval`: Sets the interval value in milliseconds to
    check for request and headers timeout in incomplete requests.
    **Default:** `30000`.
  * `headersTimeout`: Sets the timeout value in milliseconds for receiving
    the complete HTTP headers from the client.
    See [`server.headersTimeout`][] for more information.
    **Default:** `60000`.
  * `highWaterMark` {number} Optionally overrides all `socket`s'
    `readableHighWaterMark` and `writableHighWaterMark`. This affects
    `highWaterMark` property of both `IncomingMessage` and `ServerResponse`.
    **Default:** See [`stream.getDefaultHighWaterMark()`][].
  * `insecureHTTPParser` {boolean} If set to `true`, it will use a HTTP parser
    with leniency flags enabled. Using the insecure parser should be avoided.
    See [`--insecure-http-parser`][] for more information.
    **Default:** `false`.
  * `IncomingMessage` {http.IncomingMessage} Specifies the `IncomingMessage`
    class to be used. Useful for extending the original `IncomingMessage`.
    **Default:** `IncomingMessage`.
  * `joinDuplicateHeaders` {boolean} If set to `true`, this option allows
    joining the field line values of multiple headers in a request with
    a comma (`, `) instead of discarding the duplicates.
    For more information, refer to [`message.headers`][].
    **Default:** `false`.
  * `keepAlive` {boolean} If set to `true`, it enables keep-alive functionality
    on the socket immediately after a new incoming connection is received,
    similarly on what is done in \[`socket.setKeepAlive([enable][, initialDelay])`]\[`socket.setKeepAlive(enable, initialDelay)`].
    **Default:** `false`.
  * `keepAliveInitialDelay` {number} If set to a positive number, it sets the
    initial delay before the first keepalive probe is sent on an idle socket.
    **Default:** `0`.
  * `keepAliveTimeout`: The number of milliseconds of inactivity a server
    needs to wait for additional incoming data, after it has finished writing
    the last response, before a socket will be destroyed.
    See [`server.keepAliveTimeout`][] for more information.
    **Default:** `5000`.
  * `maxHeaderSize` {number} Optionally overrides the value of
    [`--max-http-header-size`][] for requests received by this server, i.e.
    the maximum length of request headers in bytes.
    **Default:** 16384 (16 KiB).
  * `noDelay` {boolean} If set to `true`, it disables the use of Nagle's
    algorithm immediately after a new incoming connection is received.
    **Default:** `true`.
  * `requestTimeout`: Sets the timeout value in milliseconds for receiving
    the entire request from the client.
    See [`server.requestTimeout`][] for more information.
    **Default:** `300000`.
  * `requireHostHeader` {boolean} If set to `true`, it forces the server to
    respond with a 400 (Bad Request) status code to any HTTP/1.1
    request message that lacks a Host header
    (as mandated by the specification).
    **Default:** `true`.
  * `ServerResponse` {http.ServerResponse} Specifies the `ServerResponse` class
    to be used. Useful for extending the original `ServerResponse`. **Default:**
    `ServerResponse`.
  * `shouldUpgradeCallback(request)` {Function} A callback which receives an
    incoming request and returns a boolean, to control which upgrade attempts
    should be accepted. Accepted upgrades will fire an `'upgrade'` event (or
    their sockets will be destroyed, if no listener is registered) while
    rejected upgrades will fire a `'request'` event like any non-upgrade
    request. This options defaults to
    `() => server.listenerCount('upgrade') > 0`.
  * `uniqueHeaders` {Array} A list of response headers that should be sent only
    once. If the header's value is an array, the items will be joined
    using `; `.
  * `rejectNonStandardBodyWrites` {boolean} If set to `true`, an error is thrown
    when writing to an HTTP response which does not have a body.
    **Default:** `false`.
  * `optimizeEmptyRequests` {boolean} If set to `true`, requests without `Content-Length`
    or `Transfer-Encoding` headers (indicating no body) will be initialized with an
    already-ended body stream, so they will never emit any stream events
    (like `'data'` or `'end'`). You can use `req.readableEnded` to detect this case.
    **Default:** `false`.

* `requestListener` {Function}

* Returns: {http.Server}

Returns a new instance of [`http.Server`][].

The `requestListener` is a function which is automatically
added to the [`'request'`][] event.

```mjs
import http from 'node:http';

// Create a local server to receive data from
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
```

```cjs
const http = require('node:http');

// Create a local server to receive data from
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
```

```mjs
import http from 'node:http';

// Create a local server to receive data from
const server = http.createServer();

// Listen to the request event
server.on('request', (request, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
```

```cjs
const http = require('node:http');

// Create a local server to receive data from
const server = http.createServer();

// Listen to the request event
server.on('request', (request, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
```

## `http.get(options[, callback])`

## `http.get(url[, options][, callback])`

<!-- YAML
added: v0.3.6
changes:
  - version: v10.9.0
    pr-url: https://github.com/nodejs/node/pull/21616
    description: The `url` parameter can now be passed along with a separate
                 `options` object.
  - version: v7.5.0
    pr-url: https://github.com/nodejs/node/pull/10638
    description: The `options` parameter can be a WHATWG `URL` object.
-->

* `url` {string | URL}
* `options` {Object} Accepts the same `options` as
  [`http.request()`][], with the method set to GET by default.
* `callback` {Function}
* Returns: {http.ClientRequest}

Since most requests are GET requests without bodies, Node.js provides this
convenience method. The only difference between this method and
[`http.request()`][] is that it sets the method to GET by default and calls `req.end()`
automatically. The callback must take care to consume the response
data for reasons stated in [`http.ClientRequest`][] section.

The `callback` is invoked with a single argument that is an instance of
[`http.IncomingMessage`][].

JSON fetching example:
