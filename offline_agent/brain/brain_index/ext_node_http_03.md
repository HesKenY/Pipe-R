# Node.js http (3/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
.0
  - v16.12.0
changes:
  - version: v11.0.0
    pr-url: https://github.com/nodejs/node/pull/20230
    description: The `aborted` property is no longer a timestamp number.
-->

> Stability: 0 - Deprecated. Check [`request.destroyed`][] instead.

* Type: {boolean}

The `request.aborted` property will be `true` if the request has
been aborted.

### `request.connection`

<!-- YAML
added: v0.3.0
deprecated: v13.0.0
-->

> Stability: 0 - Deprecated. Use [`request.socket`][].

* Type: {stream.Duplex}

See [`request.socket`][].

### `request.cork()`

<!-- YAML
added:
 - v13.2.0
 - v12.16.0
-->

See [`writable.cork()`][].

### `request.end([data[, encoding]][, callback])`

<!-- YAML
added: v0.1.90
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `data` parameter can now be a `Uint8Array`.
  - version: v10.0.0
    pr-url: https://github.com/nodejs/node/pull/18780
    description: This method now returns a reference to `ClientRequest`.
-->

* `data` {string|Buffer|Uint8Array}
* `encoding` {string}
* `callback` {Function}
* Returns: {this}

Finishes sending the request. If any parts of the body are
unsent, it will flush them to the stream. If the request is
chunked, this will send the terminating `'0\r\n\r\n'`.

If `data` is specified, it is equivalent to calling
[`request.write(data, encoding)`][] followed by `request.end(callback)`.

If `callback` is specified, it will be called when the request stream
is finished.

### `request.destroy([error])`

<!-- YAML
added: v0.3.0
changes:
  - version: v14.5.0
    pr-url: https://github.com/nodejs/node/pull/32789
    description: The function returns `this` for consistency with other Readable
                 streams.
-->

* `error` {Error} Optional, an error to emit with `'error'` event.
* Returns: {this}

Destroy the request. Optionally emit an `'error'` event,
and emit a `'close'` event. Calling this will cause remaining data
in the response to be dropped and the socket to be destroyed.

See [`writable.destroy()`][] for further details.

#### `request.destroyed`

<!-- YAML
added:
  - v14.1.0
  - v13.14.0
-->

* Type: {boolean}

Is `true` after [`request.destroy()`][] has been called.

See [`writable.destroyed`][] for further details.

### `request.finished`

<!-- YAML
added: v0.0.1
deprecated:
 - v13.4.0
 - v12.16.0
-->

> Stability: 0 - Deprecated. Use [`request.writableEnded`][].

* Type: {boolean}

The `request.finished` property will be `true` if [`request.end()`][]
has been called. `request.end()` will automatically be called if the
request was initiated via [`http.get()`][].

### `request.flushHeaders()`

<!-- YAML
added: v1.6.0
-->

Flushes the request headers.

For efficiency reasons, Node.js normally buffers the request headers until
`request.end()` is called or the first chunk of request data is written. It
then tries to pack the request headers and data into a single TCP packet.

That's usually desired (it saves a TCP round-trip), but not when the first
data is not sent until possibly much later. `request.flushHeaders()` bypasses
the optimization and kickstarts the request.

### `request.getHeader(name)`

<!-- YAML
added: v1.6.0
-->

* `name` {string}
* Returns: {any}

Reads out a header on the request. The name is case-insensitive.
The type of the return value depends on the arguments provided to
[`request.setHeader()`][].

```js
request.setHeader('content-type', 'text/html');
request.setHeader('Content-Length', Buffer.byteLength(body));
request.setHeader('Cookie', ['type=ninja', 'language=javascript']);
const contentType = request.getHeader('Content-Type');
// 'contentType' is 'text/html'
const contentLength = request.getHeader('Content-Length');
// 'contentLength' is of type number
const cookie = request.getHeader('Cookie');
// 'cookie' is of type string[]
```

### `request.getHeaderNames()`

<!-- YAML
added: v7.7.0
-->

* Returns: {string\[]}

Returns an array containing the unique names of the current outgoing headers.
All header names are lowercase.

```js
request.setHeader('Foo', 'bar');
request.setHeader('Cookie', ['foo=bar', 'bar=baz']);

const headerNames = request.getHeaderNames();
// headerNames === ['foo', 'cookie']
```

### `request.getHeaders()`

<!-- YAML
added: v7.7.0
-->

* Returns: {Object}

Returns a shallow copy of the current outgoing headers. Since a shallow copy
is used, array values may be mutated without additional calls to various
header-related http module methods. The keys of the returned object are the
header names and the values are the respective header values. All header names
are lowercase.

The object returned by the `request.getHeaders()` method _does not_
prototypically inherit from the JavaScript `Object`. This means that typical
`Object` methods such as `obj.toString()`, `obj.hasOwnProperty()`, and others
are not defined and _will not work_.

```js
request.setHeader('Foo', 'bar');
request.setHeader('Cookie', ['foo=bar', 'bar=baz']);

const headers = request.getHeaders();
// headers === { foo: 'bar', 'cookie': ['foo=bar', 'bar=baz'] }
```

### `request.getRawHeaderNames()`

<!-- YAML
added:
  - v15.13.0
  - v14.17.0
-->

* Returns: {string\[]}

Returns an array containing the unique names of the current outgoing raw
headers. Header names are returned with their exact casing being set.

```js
request.setHeader('Foo', 'bar');
request.setHeader('Set-Cookie', ['foo=bar', 'bar=baz']);

const headerNames = request.getRawHeaderNames();
// headerNames === ['Foo', 'Set-Cookie']
```

### `request.hasHeader(name)`

<!-- YAML
added: v7.7.0
-->

* `name` {string}
* Returns: {boolean}

Returns `true` if the header identified by `name` is currently set in the
outgoing headers. The header name matching is case-insensitive.

```js
const hasContentType = request.hasHeader('content-type');
```

### `request.maxHeadersCount`

* Type: {number} **Default:** `2000`

Limits maximum response headers count. If set to 0, no limit will be applied.

### `request.path`

<!-- YAML
added: v0.4.0
-->

* Type: {string} The request path.

### `request.method`

<!-- YAML
added: v0.1.97
-->

* Type: {string} The request method.

### `request.host`

<!-- YAML
added:
  - v14.5.0
  - v12.19.0
-->

* Type: {string} The request host.

### `request.protocol`

<!-- YAML
added:
  - v14.5.0
  - v12.19.0
-->

* Type: {string} The request protocol.

### `request.removeHeader(name)`

<!-- YAML
added: v1.6.0
-->

* `name` {string}

Removes a header that's already defined into headers object.

```js
request.removeHeader('Content-Type');
```

### `request.reusedSocket`

<!-- YAML
added:
 - v13.0.0
 - v12.16.0
-->

* Type: {boolean} Whether the request is send through a reused socket.

When sending request through a keep-alive enabled agent, the underlying socket
might be reused. But if server closes connection at unfortunate time, client
may run into a 'ECONNRESET' error.

```mjs
import http from 'node:http';
const agent = new http.Agent({ keepAlive: true });

// Server has a 5 seconds keep-alive timeout by default
http
  .createServer((req, res) => {
    res.write('hello\n');
    res.end();
  })
  .listen(3000);

setInterval(() => {
  // Adapting a keep-alive agent
  http.get('http://localhost:3000', { agent }, (res) => {
    res.on('data', (data) => {
      // Do nothing
    });
  });
}, 5000); // Sending request on 5s interval so it's easy to hit idle timeout
```

```cjs
const http = require('node:http');
const agent = new http.Agent({ keepAlive: true });

// Server has a 5 seconds keep-alive timeout by default
http
  .createServer((req, res) => {
    res.write('hello\n');
    res.end();
  })
  .listen(3000);

setInterval(() => {
  // Adapting a keep-alive agent
  http.get('http://localhost:3000', { agent }, (res) => {
    res.on('data', (data) => {
      // Do nothing
    });
  });
}, 5000); // Sending request on 5s interval so it's easy to hit idle timeout
```

By marking a request whether it reused socket or not, we can do
automatic error retry base on it.

```mjs
import http from 'node:http';
const agent = new http.Agent({ keepAlive: true });

function retriableRequest() {
  const req = http
    .get('http://localhost:3000', { agent }, (res) => {
      // ...
    })
    .on('error', (err) => {
      // Check if retry is needed
      if (req.reusedSocket && err.code === 'ECONNRESET') {
        retriableRequest();
      }
    });
}

retriableRequest();
```

```cjs
const http = require('node:http');
const agent = new http.Agent({ keepAlive: true });

function retriableRequest() {
  const req = http
    .get('http://localhost:3000', { agent }, (res) => {
      // ...
    })
    .on('error', (err) => {
      // Check if retry is needed
      if (req.reusedSocket && err.code === 'ECONNRESET') {
        retriableRequest();
      }
    });
}

retriableRequest();
```

### `request.setHeader(name, value)`

<!-- YAML
added: v1.6.0
-->

* `name` {string}
* `value` {any}

Sets a single header value for headers object. If this header already exists in
the to-be-sent headers, its value will be replaced. Use an array of strings
here to send multiple headers with the same name. Non-string values will be
stored without modification. Therefore, [`request.getHeader()`][] may return
non-string values. However, the non-string values will be converted to strings
for network transmission.

```js
request.setHeader('Content-Type', 'application/json');
```

or

```js
request.setHeader('Cookie', ['type=ninja', 'language=javascript']);
```

When the value is a string an exception will be thrown if it contains
characters outside the `latin1` encoding.

If you need to pass UTF-8 characters in the value please encode the value
using the [RFC 8187][] standard.

```js
const filename = 'Rock 🎵.txt';
request.setHeader('Content-Disposition', `attachment; filename*=utf-8''${encodeURIComponent(filename)}`);
```

### `request.setNoDelay([noDelay])`

<!-- YAML
added: v0.5.9
-->

* `noDelay` {boolean}

Once a socket is assigned to this request and is connected
[`socket.setNoDelay()`][] will be called.

### `request.setSocketKeepAlive([enable][, initialDelay])`

<!-- YAML
added: v0.5.9
-->

* `enable` {boolean}
* `initialDelay` {number}

Once a socket is assigned to this request and is connected
[`socket.setKeepAlive()`][] will be called.

### `request.setTimeout(timeout[, callback])`

<!-- YAML
added: v0.5.9
changes:
  - version: v9.0.0
    pr-url: https://github.com/nodejs/node/pull/8895
    description: Consistently set socket timeout only when the socket connects.
-->

* `timeout` {number} Milliseconds before a request times out.
* `callback` {Function} Optional function to be called when a timeout occurs.
  Same as binding to the `'timeout'` event.
* Returns: {http.ClientRequest}

Once a socket is assigned to this request and is connected
[`socket.setTimeout()`][] will be called.

### `request.socket`

<!-- YAML
added: v0.3.0
-->

* Type: {stream.Duplex}

Reference to the underlying socket. Usually users will not want to access
this property. In particular, the socket will not emit `'readable'` events
because of how the protocol parser attaches to the socket.

```mjs
import http from 'node:http';
const options = {
  host: 'www.google.com',
};
const req = http.get(options);
req.end();
req.once('response', (res) => {
  const ip = req.socket.localAddress;
  const port = req.socket.localPort;
  console.log(`Your IP address is ${ip} and your source port is ${port}.`);
  // Consume response object
});
```

```cjs
const http = require('node:http');
const options = {
  host: 'www.google.com',
};
const req = http.get(options);
req.end();
req.once('response', (res) => {
  const ip = req.socket.localAddress;
  const port = req.socket.localPort;
  console.log(`Your IP address is ${ip} and your source port is ${port}.`);
  // Consume response object
});
```

This property is guaranteed to be an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specified a socket
type other than {net.Socket}.

### `request.uncork()`

<!-- YAML
added:
 - v13.2.0
 - v12.16.0
-->

See [`writable.uncork()`][].

### `request.writableEnded`

<!-- YAML
added: v12.9.0
-->

* Type: {boolean}

Is `true` after [`request.end()`][] has been called. This property
does not indicate whether the data has been flushed, for this use
[`request.writableFinished`][] instead.

### `request.writableFinished`

<!-- YAML
added: v12.7.0
-->

* Type: {boolean}

Is `true` if all data has been flushed to the underlying system, immediately
before the [`'finish'`][] event is emitted.

### `request.write(chunk[, encoding][, callback])`

<!-- YAML
added: v0.1.29
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `chunk` parameter can now be a `Uint8Array`.
-->

* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string}
* `callback` {Function}
* Returns: {boolean}

Sends a chunk of the body. This method can be called multiple times. If no
`Content-Length` is set, data will automatically be encoded in HTTP Chunked
transfer encoding, so that server knows when the data ends. The
`Transfer-Encoding: chunked` header is added. Calling [`request.end()`][]
is necessary to finish sending the request.

The `encoding` argument is optional and only applies when `chunk` is a string.
Defaults to `'utf8'`.

The `callback` argument is optional and will be called when this chunk of data
is flushed, but only if the chunk is non-empty.

Returns `true` if the entire data was flushed successfully to the kernel
buffer. Returns `false` if all or part of the data was queued in user memory.
`'drain'` will be emitted when the buffer is free again.

When `write` function is called with empty string or buffer, it does
nothing and waits for more input.

## Class: `http.Server`

<!-- YAML
added: v0.1.17
-->

* Extends: {net.Server}

### Event: `'checkContinue'`

<!-- YAML
added: v0.3.0
-->

* `request` {http.IncomingMessage}
* `response` {http.ServerResponse}
