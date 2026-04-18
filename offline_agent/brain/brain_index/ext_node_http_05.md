# Node.js http (5/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ctions. Server will close
  // once remaining active connections are terminated
  server.closeIdleConnections();
}, 10000);
```

### `server.headersTimeout`

<!-- YAML
added:
 - v11.3.0
 - v10.14.0
changes:
  - version:
    - v19.4.0
    - v18.14.0
    pr-url: https://github.com/nodejs/node/pull/45778
    description: The default is now set to the minimum between 60000 (60 seconds) or `requestTimeout`.
-->

* Type: {number} **Default:** The minimum between [`server.requestTimeout`][] or `60000`.

Limit the amount of time the parser will wait to receive the complete HTTP
headers.

If the timeout expires, the server responds with status 408 without
forwarding the request to the request listener and then closes the connection.

It must be set to a non-zero value (e.g. 120 seconds) to protect against
potential Denial-of-Service attacks in case the server is deployed without a
reverse proxy in front.

### `server.listen()`

Starts the HTTP server listening for connections.
This method is identical to [`server.listen()`][] from [`net.Server`][].

### `server.listening`

<!-- YAML
added: v5.7.0
-->

* Type: {boolean} Indicates whether or not the server is listening for connections.

### `server.maxHeadersCount`

<!-- YAML
added: v0.7.0
-->

* Type: {number} **Default:** `2000`

Limits maximum incoming headers count. If set to 0, no limit will be applied.

### `server.requestTimeout`

<!-- YAML
added: v14.11.0
changes:
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41263
    description: The default request timeout changed
                 from no timeout to 300s (5 minutes).
-->

* Type: {number} **Default:** `300000`

Sets the timeout value in milliseconds for receiving the entire request from
the client.

If the timeout expires, the server responds with status 408 without
forwarding the request to the request listener and then closes the connection.

It must be set to a non-zero value (e.g. 120 seconds) to protect against
potential Denial-of-Service attacks in case the server is deployed without a
reverse proxy in front.

### `server.setTimeout([msecs][, callback])`

<!-- YAML
added: v0.9.12
changes:
  - version: v13.0.0
    pr-url: https://github.com/nodejs/node/pull/27558
    description: The default timeout changed from 120s to 0 (no timeout).
-->

* `msecs` {number} **Default:** 0 (no timeout)
* `callback` {Function}
* Returns: {http.Server}

Sets the timeout value for sockets, and emits a `'timeout'` event on
the Server object, passing the socket as an argument, if a timeout
occurs.

If there is a `'timeout'` event listener on the Server object, then it
will be called with the timed-out socket as an argument.

By default, the Server does not timeout sockets. However, if a callback
is assigned to the Server's `'timeout'` event, timeouts must be handled
explicitly.

### `server.maxRequestsPerSocket`

<!-- YAML
added: v16.10.0
-->

* Type: {number} Requests per socket. **Default:** 0 (no limit)

The maximum number of requests socket can handle
before closing keep alive connection.

A value of `0` will disable the limit.

When the limit is reached it will set the `Connection` header value to `close`,
but will not actually close the connection, subsequent requests sent
after the limit is reached will get `503 Service Unavailable` as a response.

### `server.timeout`

<!-- YAML
added: v0.9.12
changes:
  - version: v13.0.0
    pr-url: https://github.com/nodejs/node/pull/27558
    description: The default timeout changed from 120s to 0 (no timeout).
-->

* Type: {number} Timeout in milliseconds. **Default:** 0 (no timeout)

The number of milliseconds of inactivity before a socket is presumed
to have timed out.

A value of `0` will disable the timeout behavior on incoming connections.

The socket timeout logic is set up on connection, so changing this
value only affects new connections to the server, not any existing connections.

### `server.keepAliveTimeout`

<!-- YAML
added: v8.0.0
-->

* Type: {number} Timeout in milliseconds. **Default:** `5000` (5 seconds).

The number of milliseconds of inactivity a server needs to wait for additional
incoming data, after it has finished writing the last response, before a socket
will be destroyed.

This timeout value is combined with the
[`server.keepAliveTimeoutBuffer`][] option to determine the actual socket
timeout, calculated as:
socketTimeout = keepAliveTimeout + keepAliveTimeoutBuffer
If the server receives new data before the keep-alive timeout has fired, it
will reset the regular inactivity timeout, i.e., [`server.timeout`][].

A value of `0` will disable the keep-alive timeout behavior on incoming
connections.
A value of `0` makes the HTTP server behave similarly to Node.js versions prior
to 8.0.0, which did not have a keep-alive timeout.

The socket timeout logic is set up on connection, so changing this value only
affects new connections to the server, not any existing connections.

### `server.keepAliveTimeoutBuffer`

<!-- YAML
added:
 - v24.6.0
 - v22.19.0
-->

* Type: {number} Timeout in milliseconds. **Default:** `1000` (1 second).

An additional buffer time added to the
[`server.keepAliveTimeout`][] to extend the internal socket timeout.

This buffer helps reduce connection reset (`ECONNRESET`) errors by increasing
the socket timeout slightly beyond the advertised keep-alive timeout.

This option applies only to new incoming connections.

### `server[Symbol.asyncDispose]()`

<!-- YAML
added: v20.4.0
changes:
 - version: v24.2.0
   pr-url: https://github.com/nodejs/node/pull/58467
   description: No longer experimental.
-->

Calls [`server.close()`][] and returns a promise that fulfills when the
server has closed.

## Class: `http.ServerResponse`

<!-- YAML
added: v0.1.17
-->

* Extends: {http.OutgoingMessage}

This object is created internally by an HTTP server, not by the user. It is
passed as the second parameter to the [`'request'`][] event.

### Event: `'close'`

<!-- YAML
added: v0.6.7
-->

Indicates that the response is completed, or its underlying connection was
terminated prematurely (before the response completion).

### Event: `'finish'`

<!-- YAML
added: v0.3.6
-->

Emitted when the response has been sent. More specifically, this event is
emitted when the last segment of the response headers and body have been
handed off to the operating system for transmission over the network. It
does not imply that the client has received anything yet.

### `response.addTrailers(headers)`

<!-- YAML
added: v0.3.0
-->

* `headers` {Object}

This method adds HTTP trailing headers (a header but at the end of the
message) to the response.

Trailers will **only** be emitted if chunked encoding is used for the
response; if it is not (e.g. if the request was HTTP/1.0), they will
be silently discarded.

HTTP requires the `Trailer` header to be sent in order to
emit trailers, with a list of the header fields in its value. E.g.,

```js
response.writeHead(200, { 'Content-Type': 'text/plain',
                          'Trailer': 'Content-MD5' });
response.write(fileData);
response.addTrailers({ 'Content-MD5': '7895bf4b8828b55ceaf47747b4bca667' });
response.end();
```

Attempting to set a header field name or value that contains invalid characters
will result in a [`TypeError`][] being thrown.

### `response.connection`

<!-- YAML
added: v0.3.0
deprecated: v13.0.0
-->

> Stability: 0 - Deprecated. Use [`response.socket`][].

* Type: {stream.Duplex}

See [`response.socket`][].

### `response.cork()`

<!-- YAML
added:
 - v13.2.0
 - v12.16.0
-->

See [`writable.cork()`][].

### `response.end([data[, encoding]][, callback])`

<!-- YAML
added: v0.1.90
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `data` parameter can now be a `Uint8Array`.
  - version: v10.0.0
    pr-url: https://github.com/nodejs/node/pull/18780
    description: This method now returns a reference to `ServerResponse`.
-->

* `data` {string|Buffer|Uint8Array}
* `encoding` {string}
* `callback` {Function}
* Returns: {this}

This method signals to the server that all of the response headers and body
have been sent; that server should consider this message complete.
The method, `response.end()`, MUST be called on each response.

If `data` is specified, it is similar in effect to calling
[`response.write(data, encoding)`][] followed by `response.end(callback)`.

If `callback` is specified, it will be called when the response stream
is finished.

### `response.finished`

<!-- YAML
added: v0.0.2
deprecated:
 - v13.4.0
 - v12.16.0
-->

> Stability: 0 - Deprecated. Use [`response.writableEnded`][].

* Type: {boolean}

The `response.finished` property will be `true` if [`response.end()`][]
has been called.

### `response.flushHeaders()`

<!-- YAML
added: v1.6.0
-->

Flushes the response headers. See also: [`request.flushHeaders()`][].

### `response.getHeader(name)`

<!-- YAML
added: v0.4.0
-->

* `name` {string}
* Returns: {number | string | string\[] | undefined}

Reads out a header that's already been queued but not sent to the client.
The name is case-insensitive. The type of the return value depends
on the arguments provided to [`response.setHeader()`][].

```js
response.setHeader('Content-Type', 'text/html');
response.setHeader('Content-Length', Buffer.byteLength(body));
response.setHeader('Set-Cookie', ['type=ninja', 'language=javascript']);
const contentType = response.getHeader('content-type');
// contentType is 'text/html'
const contentLength = response.getHeader('Content-Length');
// contentLength is of type number
const setCookie = response.getHeader('set-cookie');
// setCookie is of type string[]
```

### `response.getHeaderNames()`

<!-- YAML
added: v7.7.0
-->

* Returns: {string\[]}

Returns an array containing the unique names of the current outgoing headers.
All header names are lowercase.

```js
response.setHeader('Foo', 'bar');
response.setHeader('Set-Cookie', ['foo=bar', 'bar=baz']);

const headerNames = response.getHeaderNames();
// headerNames === ['foo', 'set-cookie']
```

### `response.getHeaders()`

<!-- YAML
added: v7.7.0
-->

* Returns: {Object}

Returns a shallow copy of the current outgoing headers. Since a shallow copy
is used, array values may be mutated without additional calls to various
header-related http module methods. The keys of the returned object are the
header names and the values are the respective header values. All header names
are lowercase.

The object returned by the `response.getHeaders()` method _does not_
prototypically inherit from the JavaScript `Object`. This means that typical
`Object` methods such as `obj.toString()`, `obj.hasOwnProperty()`, and others
are not defined and _will not work_.

```js
response.setHeader('Foo', 'bar');
response.setHeader('Set-Cookie', ['foo=bar', 'bar=baz']);

const headers = response.getHeaders();
// headers === { foo: 'bar', 'set-cookie': ['foo=bar', 'bar=baz'] }
```

### `response.hasHeader(name)`

<!-- YAML
added: v7.7.0
-->

* `name` {string}
* Returns: {boolean}

Returns `true` if the header identified by `name` is currently set in the
outgoing headers. The header name matching is case-insensitive.

```js
const hasContentType = response.hasHeader('content-type');
```

### `response.headersSent`

<!-- YAML
added: v0.9.3
-->

* Type: {boolean}

Boolean (read-only). True if headers were sent, false otherwise.

### `response.removeHeader(name)`

<!-- YAML
added: v0.4.0
-->

* `name` {string}

Removes a header that's queued for implicit sending.

```js
response.removeHeader('Content-Encoding');
```

### `response.req`

<!-- YAML
added: v15.7.0
-->

* Type: {http.IncomingMessage}

A reference to the original HTTP `request` object.

### `response.sendDate`

<!-- YAML
added: v0.7.5
-->

* Type: {boolean}

When true, the Date header will be automatically generated and sent in
the response if it is not already present in the headers. Defaults to true.

This should only be disabled for testing; the Date header is required in
most HTTP responses (see [RFC 9110 Section 6.6.1][] for details).

### `response.setHeader(name, value)`

<!-- YAML
added: v0.4.0
-->

* `name` {string}
* `value` {number | string | string\[]}
* Returns: {http.ServerResponse}

Returns the response object.

Sets a single header value for implicit headers. If this header already exists
in the to-be-sent headers, its value will be replaced. Use an array of strings
here to send multiple headers with the same name. Non-string values will be
stored without modification. Therefore, [`response.getHeader()`][] may return
non-string values. However, the non-string values will be converted to strings
for network transmission. The same response object is returned to the caller,
to enable call chaining.

```js
response.setHeader('Content-Type', 'text/html');
```

or

```js
response.setHeader('Set-Cookie', ['type=ninja', 'language=javascript']);
```

Attempting to set a header field name or value that contains invalid characters
will result in a [`TypeError`][] being thrown.

When headers have been set with [`response.setHeader()`][], they will be merged
with any headers passed to [`response.writeHead()`][], with the headers passed
to [`response.writeHead()`][] given precedence.

```js
// Returns content-type = text/plain
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.setHeader('X-Foo', 'bar');
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('ok');
});
```

If [`response.writeHead()`][] method is called and this method has not been
called, it will directly write the supplied header values onto the network
channel without caching internally, and the [`response.getHeader()`][] on the
header will not yield the expected result. If progressive population of headers
is desired with potential future retrieval and modification, use
[`response.setHeader()`][] instead of [`response.writeHead()`][].

### `response.setTimeout(msecs[, callback])`
