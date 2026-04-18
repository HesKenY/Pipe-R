# Node.js http (6/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ok');
});
```

If [`response.writeHead()`][] method is called and this method has not been
called, it will directly write the supplied header values onto the network
channel without caching internally, and the [`response.getHeader()`][] on the
header will not yield the expected result. If progressive population of headers
is desired with potential future retrieval and modification, use
[`response.setHeader()`][] instead of [`response.writeHead()`][].

### `response.setTimeout(msecs[, callback])`

<!-- YAML
added: v0.9.12
-->

* `msecs` {number}
* `callback` {Function}
* Returns: {http.ServerResponse}

Sets the Socket's timeout value to `msecs`. If a callback is
provided, then it is added as a listener on the `'timeout'` event on
the response object.

If no `'timeout'` listener is added to the request, the response, or
the server, then sockets are destroyed when they time out. If a handler is
assigned to the request, the response, or the server's `'timeout'` events,
timed out sockets must be handled explicitly.

### `response.socket`

<!-- YAML
added: v0.3.0
-->

* Type: {stream.Duplex}

Reference to the underlying socket. Usually users will not want to access
this property. In particular, the socket will not emit `'readable'` events
because of how the protocol parser attaches to the socket. After
`response.end()`, the property is nulled.

```mjs
import http from 'node:http';
const server = http.createServer((req, res) => {
  const ip = res.socket.remoteAddress;
  const port = res.socket.remotePort;
  res.end(`Your IP address is ${ip} and your source port is ${port}.`);
}).listen(3000);
```

```cjs
const http = require('node:http');
const server = http.createServer((req, res) => {
  const ip = res.socket.remoteAddress;
  const port = res.socket.remotePort;
  res.end(`Your IP address is ${ip} and your source port is ${port}.`);
}).listen(3000);
```

This property is guaranteed to be an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specified a socket
type other than {net.Socket}.

### `response.statusCode`

<!-- YAML
added: v0.4.0
-->

* Type: {number} **Default:** `200`

When using implicit headers (not calling [`response.writeHead()`][] explicitly),
this property controls the status code that will be sent to the client when
the headers get flushed.

```js
response.statusCode = 404;
```

After response header was sent to the client, this property indicates the
status code which was sent out.

### `response.statusMessage`

<!-- YAML
added: v0.11.8
-->

* Type: {string}

When using implicit headers (not calling [`response.writeHead()`][] explicitly),
this property controls the status message that will be sent to the client when
the headers get flushed. If this is left as `undefined` then the standard
message for the status code will be used.

```js
response.statusMessage = 'Not found';
```

After response header was sent to the client, this property indicates the
status message which was sent out.

### `response.strictContentLength`

<!-- YAML
added:
  - v18.10.0
  - v16.18.0
-->

* Type: {boolean} **Default:** `false`

If set to `true`, Node.js will check whether the `Content-Length`
header value and the size of the body, in bytes, are equal.
Mismatching the `Content-Length` header value will result
in an `Error` being thrown, identified by `code:` [`'ERR_HTTP_CONTENT_LENGTH_MISMATCH'`][].

### `response.uncork()`

<!-- YAML
added:
 - v13.2.0
 - v12.16.0
-->

See [`writable.uncork()`][].

### `response.writableEnded`

<!-- YAML
added: v12.9.0
-->

* Type: {boolean}

Is `true` after [`response.end()`][] has been called. This property
does not indicate whether the data has been flushed, for this use
[`response.writableFinished`][] instead.

### `response.writableFinished`

<!-- YAML
added: v12.7.0
-->

* Type: {boolean}

Is `true` if all data has been flushed to the underlying system, immediately
before the [`'finish'`][] event is emitted.

### `response.write(chunk[, encoding][, callback])`

<!-- YAML
added: v0.1.29
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `chunk` parameter can now be a `Uint8Array`.
-->

* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string} **Default:** `'utf8'`
* `callback` {Function}
* Returns: {boolean}

If this method is called and [`response.writeHead()`][] has not been called,
it will switch to implicit header mode and flush the implicit headers.

This sends a chunk of the response body. This method may
be called multiple times to provide successive parts of the body.

If `rejectNonStandardBodyWrites` is set to true in `createServer`
then writing to the body is not allowed when the request method or response
status do not support content. If an attempt is made to write to the body for a
HEAD request or as part of a `204` or `304`response, a synchronous `Error`
with the code `ERR_HTTP_BODY_NOT_ALLOWED` is thrown.

`chunk` can be a string or a buffer. If `chunk` is a string,
the second parameter specifies how to encode it into a byte stream.
`callback` will be called when this chunk of data is flushed.

This is the raw HTTP body and has nothing to do with higher-level multi-part
body encodings that may be used.

The first time [`response.write()`][] is called, it will send the buffered
header information and the first chunk of the body to the client. The second
time [`response.write()`][] is called, Node.js assumes data will be streamed,
and sends the new data separately. That is, the response is buffered up to the
first chunk of the body.

Returns `true` if the entire data was flushed successfully to the kernel
buffer. Returns `false` if all or part of the data was queued in user memory.
`'drain'` will be emitted when the buffer is free again.

### `response.writeContinue()`

<!-- YAML
added: v0.3.0
-->

Sends an HTTP/1.1 100 Continue message to the client, indicating that
the request body should be sent. See the [`'checkContinue'`][] event on
`Server`.

### `response.writeEarlyHints(hints[, callback])`

<!-- YAML
added: v18.11.0
changes:
  - version: v18.11.0
    pr-url: https://github.com/nodejs/node/pull/44820
    description: Allow passing hints as an object.
-->

* `hints` {Object}
* `callback` {Function}

Sends an HTTP/1.1 103 Early Hints message to the client with a Link header,
indicating that the user agent can preload/preconnect the linked resources.
The `hints` is an object containing the values of headers to be sent with
early hints message. The optional `callback` argument will be called when
the response message has been written.

**Example**

```js
const earlyHintsLink = '</styles.css>; rel=preload; as=style';
response.writeEarlyHints({
  'link': earlyHintsLink,
});

const earlyHintsLinks = [
  '</styles.css>; rel=preload; as=style',
  '</scripts.js>; rel=preload; as=script',
];
response.writeEarlyHints({
  'link': earlyHintsLinks,
  'x-trace-id': 'id for diagnostics',
});

const earlyHintsCallback = () => console.log('early hints message sent');
response.writeEarlyHints({
  'link': earlyHintsLinks,
}, earlyHintsCallback);
```

### `response.writeHead(statusCode[, statusMessage][, headers])`

<!-- YAML
added: v0.1.30
changes:
  - version: v14.14.0
    pr-url: https://github.com/nodejs/node/pull/35274
    description: Allow passing headers as an array.
  - version:
     - v11.10.0
     - v10.17.0
    pr-url: https://github.com/nodejs/node/pull/25974
    description: Return `this` from `writeHead()` to allow chaining with
                 `end()`.
  - version:
    - v5.11.0
    - v4.4.5
    pr-url: https://github.com/nodejs/node/pull/6291
    description: A `RangeError` is thrown if `statusCode` is not a number in
                 the range `[100, 999]`.
-->

* `statusCode` {number}
* `statusMessage` {string}
* `headers` {Object|Array}
* Returns: {http.ServerResponse}

Sends a response header to the request. The status code is a 3-digit HTTP
status code, like `404`. The last argument, `headers`, are the response headers.
Optionally one can give a human-readable `statusMessage` as the second
argument.

`headers` may be an `Array` where the keys and values are in the same list.
It is _not_ a list of tuples. So, the even-numbered offsets are key values,
and the odd-numbered offsets are the associated values. The array is in the same
format as `request.rawHeaders`.

Returns a reference to the `ServerResponse`, so that calls can be chained.

```js
const body = 'hello world';
response
  .writeHead(200, {
    'Content-Length': Buffer.byteLength(body),
    'Content-Type': 'text/plain',
  })
  .end(body);
```

This method must only be called once on a message and it must
be called before [`response.end()`][] is called.

If [`response.write()`][] or [`response.end()`][] are called before calling
this, the implicit/mutable headers will be calculated and call this function.

When headers have been set with [`response.setHeader()`][], they will be merged
with any headers passed to [`response.writeHead()`][], with the headers passed
to [`response.writeHead()`][] given precedence.

If this method is called and [`response.setHeader()`][] has not been called,
it will directly write the supplied header values onto the network channel
without caching internally, and the [`response.getHeader()`][] on the header
will not yield the expected result. If progressive population of headers is
desired with potential future retrieval and modification, use
[`response.setHeader()`][] instead.

```js
// Returns content-type = text/plain
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.setHeader('X-Foo', 'bar');
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('ok');
});
```

`Content-Length` is read in bytes, not characters. Use
[`Buffer.byteLength()`][] to determine the length of the body in bytes. Node.js
will check whether `Content-Length` and the length of the body which has
been transmitted are equal or not.

Attempting to set a header field name or value that contains invalid characters
will result in a [`TypeError`][] being thrown.

### `response.writeProcessing()`

<!-- YAML
added: v10.0.0
-->

Sends a HTTP/1.1 102 Processing message to the client, indicating that
the request body should be sent.

## Class: `http.IncomingMessage`

<!-- YAML
added: v0.1.17
changes:
  - version: v15.5.0
    pr-url: https://github.com/nodejs/node/pull/33035
    description: The `destroyed` value returns `true` after the incoming data
                 is consumed.
  - version:
     - v13.1.0
     - v12.16.0
    pr-url: https://github.com/nodejs/node/pull/30135
    description: The `readableHighWaterMark` value mirrors that of the socket.
-->

* Extends: {stream.Readable}

An `IncomingMessage` object is created by [`http.Server`][] or
[`http.ClientRequest`][] and passed as the first argument to the [`'request'`][]
and [`'response'`][] event respectively. It may be used to access response
status, headers, and data.

Different from its `socket` value which is a subclass of {stream.Duplex}, the
`IncomingMessage` itself extends {stream.Readable} and is created separately to
parse and emit the incoming HTTP headers and payload, as the underlying socket
may be reused multiple times in case of keep-alive.

### Event: `'aborted'`

<!-- YAML
added: v0.3.8
deprecated:
  - v17.0.0
  - v16.12.0
-->

> Stability: 0 - Deprecated. Listen for `'close'` event instead.

Emitted when the request has been aborted.

### Event: `'close'`

<!-- YAML
added: v0.4.2
changes:
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/33035
    description: The close event is now emitted when the request has been completed and not when the
                 underlying socket is closed.
-->

Emitted when the request has been completed.

### `message.aborted`

<!-- YAML
added: v10.1.0
deprecated:
  - v17.0.0
  - v16.12.0
-->

> Stability: 0 - Deprecated. Check `message.destroyed` from {stream.Readable}.

* Type: {boolean}

The `message.aborted` property will be `true` if the request has
been aborted.

### `message.complete`

<!-- YAML
added: v0.3.0
-->

* Type: {boolean}

The `message.complete` property will be `true` if a complete HTTP message has
been received and successfully parsed.

This property is particularly useful as a means of determining if a client or
server fully transmitted a message before a connection was terminated:

```js
const req = http.request({
  host: '127.0.0.1',
  port: 8080,
  method: 'POST',
}, (res) => {
  res.resume();
  res.on('end', () => {
    if (!res.complete)
      console.error(
        'The connection was terminated while the message was still being sent');
  });
});
```

### `message.connection`

<!-- YAML
added: v0.1.90
deprecated: v16.0.0
 -->

> Stability: 0 - Deprecated. Use [`message.socket`][].

Alias for [`message.socket`][].

### `message.destroy([error])`

<!-- YAML
added: v0.3.0
changes:
  - version:
    - v14.5.0
    - v12.19.0
    pr-url: https://github.com/nodejs/node/pull/32789
    description: The function returns `this` for consistency with other Readable
                 streams.
-->

* `error` {Error}
* Returns: {this}

Calls `destroy()` on the socket that received the `IncomingMessage`. If `error`
is provided, an `'error'` event is emitted on the socket and `error` is passed
as an argument to any listeners on the event.

### `message.headers`
