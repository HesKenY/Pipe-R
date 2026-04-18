# Node.js http (7/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
YAML
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

<!-- YAML
added: v0.1.5
changes:
  - version:
    - v19.5.0
    - v18.14.0
    pr-url: https://github.com/nodejs/node/pull/45982
    description: >-
     The `joinDuplicateHeaders` option in the `http.request()`
     and `http.createServer()` functions ensures that duplicate
     headers are not discarded, but rather combined using a
     comma separator, in accordance with RFC 9110 Section 5.3.
  - version: v15.1.0
    pr-url: https://github.com/nodejs/node/pull/35281
    description: >-
      `message.headers` is now lazily computed using an accessor property
      on the prototype and is no longer enumerable.
-->

* Type: {Object}

The request/response headers object.

Key-value pairs of header names and values. Header names are lower-cased.

```js
// Prints something like:
//
// { 'user-agent': 'curl/7.22.0',
//   host: '127.0.0.1:8000',
//   accept: '*/*' }
console.log(request.headers);
```

Duplicates in raw headers are handled in the following ways, depending on the
header name:

* Duplicates of `age`, `authorization`, `content-length`, `content-type`,
  `etag`, `expires`, `from`, `host`, `if-modified-since`, `if-unmodified-since`,
  `last-modified`, `location`, `max-forwards`, `proxy-authorization`, `referer`,
  `retry-after`, `server`, or `user-agent` are discarded.
  To allow duplicate values of the headers listed above to be joined,
  use the option `joinDuplicateHeaders` in [`http.request()`][]
  and [`http.createServer()`][]. See RFC 9110 Section 5.3 for more
  information.
* `set-cookie` is always an array. Duplicates are added to the array.
* For duplicate `cookie` headers, the values are joined together with `; `.
* For all other headers, the values are joined together with `, `.

### `message.headersDistinct`

<!-- YAML
added:
  - v18.3.0
  - v16.17.0
-->

* Type: {Object}

Similar to [`message.headers`][], but there is no join logic and the values are
always arrays of strings, even for headers received just once.

```js
// Prints something like:
//
// { 'user-agent': ['curl/7.22.0'],
//   host: ['127.0.0.1:8000'],
//   accept: ['*/*'] }
console.log(request.headersDistinct);
```

### `message.httpVersion`

<!-- YAML
added: v0.1.1
-->

* Type: {string}

In case of server request, the HTTP version sent by the client. In the case of
client response, the HTTP version of the connected-to server.
Probably either `'1.1'` or `'1.0'`.

Also `message.httpVersionMajor` is the first integer and
`message.httpVersionMinor` is the second.

### `message.method`

<!-- YAML
added: v0.1.1
-->

* Type: {string}

**Only valid for request obtained from [`http.Server`][].**

The request method as a string. Read only. Examples: `'GET'`, `'DELETE'`.

### `message.rawHeaders`

<!-- YAML
added: v0.11.6
-->

* Type: {string\[]}

The raw request/response headers list exactly as they were received.

The keys and values are in the same list. It is _not_ a
list of tuples. So, the even-numbered offsets are key values, and the
odd-numbered offsets are the associated values.

Header names are not lowercased, and duplicates are not merged.

```js
// Prints something like:
//
// [ 'user-agent',
//   'this is invalid because there can be only one',
//   'User-Agent',
//   'curl/7.22.0',
//   'Host',
//   '127.0.0.1:8000',
//   'ACCEPT',
//   '*/*' ]
console.log(request.rawHeaders);
```

### `message.rawTrailers`

<!-- YAML
added: v0.11.6
-->

* Type: {string\[]}

The raw request/response trailer keys and values exactly as they were
received. Only populated at the `'end'` event.

### `message.setTimeout(msecs[, callback])`

<!-- YAML
added: v0.5.9
-->

* `msecs` {number}
* `callback` {Function}
* Returns: {http.IncomingMessage}

Calls `message.socket.setTimeout(msecs, callback)`.

### `message.signal`

<!-- YAML
added: REPLACEME
-->

* Type: {AbortSignal}

An {AbortSignal} that is aborted when the underlying socket closes or the
request is destroyed. The signal is created lazily on first access — no
{AbortController} is allocated for requests that never use this property.

This is useful for cancelling downstream asynchronous work such as database
queries or `fetch` calls when a client disconnects mid-request.

```mjs
import http from 'node:http';

http.createServer(async (req, res) => {
  try {
    const data = await fetch('https://example.com/api', { signal: req.signal });
    res.end(JSON.stringify(await data.json()));
  } catch (err) {
    if (err.name === 'AbortError') return;
    res.statusCode = 500;
    res.end('Internal Server Error');
  }
}).listen(3000);
```

```cjs
const http = require('node:http');

http.createServer(async (req, res) => {
  try {
    const data = await fetch('https://example.com/api', { signal: req.signal });
    res.end(JSON.stringify(await data.json()));
  } catch (err) {
    if (err.name === 'AbortError') return;
    res.statusCode = 500;
    res.end('Internal Server Error');
  }
}).listen(3000);
```

### `message.socket`

<!-- YAML
added: v0.3.0
-->

* Type: {stream.Duplex}

The [`net.Socket`][] object associated with the connection.

With HTTPS support, use [`request.socket.getPeerCertificate()`][] to obtain the
client's authentication details.

This property is guaranteed to be an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specified a socket
type other than {net.Socket} or internally nulled.

### `message.statusCode`

<!-- YAML
added: v0.1.1
-->

* Type: {number}

**Only valid for response obtained from [`http.ClientRequest`][].**

The 3-digit HTTP response status code. E.G. `404`.

### `message.statusMessage`

<!-- YAML
added: v0.11.10
-->

* Type: {string}

**Only valid for response obtained from [`http.ClientRequest`][].**

The HTTP response status message (reason phrase). E.G. `OK` or `Internal Server
Error`.

### `message.trailers`

<!-- YAML
added: v0.3.0
-->

* Type: {Object}

The request/response trailers object. Only populated at the `'end'` event.

### `message.trailersDistinct`

<!-- YAML
added:
  - v18.3.0
  - v16.17.0
-->

* Type: {Object}

Similar to [`message.trailers`][], but there is no join logic and the values are
always arrays of strings, even for headers received just once.
Only populated at the `'end'` event.

### `message.url`

<!-- YAML
added: v0.1.90
-->

* Type: {string}

**Only valid for request obtained from [`http.Server`][].**

Request URL string. This contains only the URL that is present in the actual
HTTP request. Take the following request:

```http
GET /status?name=ryan HTTP/1.1
Accept: text/plain
```

To parse the URL into its parts:

```js
new URL(`http://${process.env.HOST ?? 'localhost'}${request.url}`);
```

When `request.url` is `'/status?name=ryan'` and `process.env.HOST` is undefined:

```console
$ node
> new URL(`http://${process.env.HOST ?? 'localhost'}${request.url}`);
URL {
  href: 'http://localhost/status?name=ryan',
  origin: 'http://localhost',
  protocol: 'http:',
  username: '',
  password: '',
  host: 'localhost',
  hostname: 'localhost',
  port: '',
  pathname: '/status',
  search: '?name=ryan',
  searchParams: URLSearchParams { 'name' => 'ryan' },
  hash: ''
}
```

Ensure that you set `process.env.HOST` to the server's host name, or consider
replacing this part entirely. If using `req.headers.host`, ensure proper
validation is used, as clients may specify a custom `Host` header.

## Class: `http.OutgoingMessage`

<!-- YAML
added: v0.1.17
-->

* Extends: {Stream}

This class serves as the parent class of [`http.ClientRequest`][]
and [`http.ServerResponse`][]. It is an abstract outgoing message from
the perspective of the participants of an HTTP transaction.

### Event: `'drain'`

<!-- YAML
added: v0.3.6
-->

Emitted when the buffer of the message is free again.

### Event: `'finish'`

<!-- YAML
added: v0.1.17
-->

Emitted when the transmission is finished successfully.

### Event: `'prefinish'`

<!-- YAML
added: v0.11.6
-->

Emitted after `outgoingMessage.end()` is called.
When the event is emitted, all data has been processed but not necessarily
completely flushed.

### `outgoingMessage.addTrailers(headers)`

<!-- YAML
added: v0.3.0
-->

* `headers` {Object}

Adds HTTP trailers (headers but at the end of the message) to the message.

Trailers will **only** be emitted if the message is chunked encoded. If not,
the trailers will be silently discarded.

HTTP requires the `Trailer` header to be sent to emit trailers,
with a list of header field names in its value, e.g.

```js
message.writeHead(200, { 'Content-Type': 'text/plain',
                         'Trailer': 'Content-MD5' });
message.write(fileData);
message.addTrailers({ 'Content-MD5': '7895bf4b8828b55ceaf47747b4bca667' });
message.end();
```

Attempting to set a header field name or value that contains invalid characters
will result in a `TypeError` being thrown.

### `outgoingMessage.appendHeader(name, value)`

<!-- YAML
added:
  - v18.3.0
  - v16.17.0
-->

* `name` {string} Header name
* `value` {string|string\[]} Header value
* Returns: {this}

Append a single header value to the header object.

If the value is an array, this is equivalent to calling this method multiple
times.

If there were no previous values for the header, this is equivalent to calling
[`outgoingMessage.setHeader(name, value)`][].

Depending of the value of `options.uniqueHeaders` when the client request or the
server were created, this will end up in the header being sent multiple times or
a single time with values joined using `; `.

### `outgoingMessage.connection`

<!-- YAML
added: v0.3.0
deprecated:
  - v15.12.0
  - v14.17.1
-->

> Stability: 0 - Deprecated: Use [`outgoingMessage.socket`][] instead.

Alias of [`outgoingMessage.socket`][].

### `outgoingMessage.cork()`

<!-- YAML
added:
  - v13.2.0
  - v12.16.0
-->

See [`writable.cork()`][].

### `outgoingMessage.destroy([error])`

<!-- YAML
added: v0.3.0
-->

* `error` {Error} Optional, an error to emit with `error` event
* Returns: {this}

Destroys the message. Once a socket is associated with the message
and is connected, that socket will be destroyed as well.

### `outgoingMessage.end(chunk[, encoding][, callback])`

<!-- YAML
added: v0.1.90
changes:
  - version: v15.0.0
    pr-url: https://github.com/nodejs/node/pull/33155
    description: The `chunk` parameter can now be a `Uint8Array`.
  - version: v0.11.6
    description: add `callback` argument.
-->

* `chunk` {string|Buffer|Uint8Array}
* `encoding` {string} Optional, **Default**: `utf8`
* `callback` {Function} Optional
* Returns: {this}

Finishes the outgoing message. If any parts of the body are unsent, it will
flush them to the underlying system. If the message is chunked, it will
send the terminating chunk `0\r\n\r\n`, and send the trailers (if any).

If `chunk` is specified, it is equivalent to calling
`outgoingMessage.write(chunk, encoding)`, followed by
`outgoingMessage.end(callback)`.

If `callback` is provided, it will be called when the message is finished
(equivalent to a listener of the `'finish'` event).

### `outgoingMessage.flushHeaders()`

<!-- YAML
added: v1.6.0
-->

Flushes the message headers.

For efficiency reason, Node.js normally buffers the message headers
until `outgoingMessage.end()` is called or the first chunk of message data
is written. It then tries to pack the headers and data into a single TCP
packet.

It is usually desired (it saves a TCP round-trip), but not when the first
data is not sent until possibly much later. `outgoingMessage.flushHeaders()`
bypasses the optimization and kickstarts the message.

### `outgoingMessage.getHeader(name)`

<!-- YAML
added: v0.4.0
-->

* `name` {string} Name of header
* Returns: {number | string | string\[] | undefined}

Gets the value of the HTTP header with the given name. If that header is not
set, the returned value will be `undefined`.

### `outgoingMessage.getHeaderNames()`

<!-- YAML
added: v7.7.0
-->

* Returns: {string\[]}

Returns an array containing the unique names of the current outgoing headers.
All names are lowercase.

### `outgoingMessage.getHeaders()`

<!-- YAML
added: v7.7.0
-->

* Returns: {Object}

Returns a shallow copy of the current outgoing headers. Since a shallow
copy is used, array values may be mutated without additional calls to
various header-related HTTP module methods. The keys of the returned
object are the header names and the values are the respective header
values. All header names are lowercase.

The object returned by the `outgoingMessage.getHeaders()` method does
not prototypically inherit from the JavaScript `Object`. This means that
typical `Object` methods such as `obj.toString()`, `obj.hasOwnProperty()`,
and others are not defined and will not work.

```js
outgoingMessage.setHeader('Foo', 'bar');
outgoingMessage.setHeader('Set-Cookie', ['foo=bar', 'bar=baz']);

const headers = outgoingMessage.getHeaders();
// headers === { foo: 'bar', 'set-cookie': ['foo=bar', 'bar=baz'] }
```

### `outgoingMessage.hasHeader(name)`

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
