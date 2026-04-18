# Node.js http (4/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
entire data was flushed successfully to the kernel
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

Emitted each time a request with an HTTP `Expect: 100-continue` is received.
If this event is not listened for, the server will automatically respond
with a `100 Continue` as appropriate.

Handling this event involves calling [`response.writeContinue()`][] if the
client should continue to send the request body, or generating an appropriate
HTTP response (e.g. 400 Bad Request) if the client should not continue to send
the request body.

When this event is emitted and handled, the [`'request'`][] event will
not be emitted.

### Event: `'checkExpectation'`

<!-- YAML
added: v5.5.0
-->

* `request` {http.IncomingMessage}
* `response` {http.ServerResponse}

Emitted each time a request with an HTTP `Expect` header is received, where the
value is not `100-continue`. If this event is not listened for, the server will
automatically respond with a `417 Expectation Failed` as appropriate.

When this event is emitted and handled, the [`'request'`][] event will
not be emitted.

### Event: `'clientError'`

<!-- YAML
added: v0.1.94
changes:
  - version: v12.0.0
    pr-url: https://github.com/nodejs/node/pull/25605
    description: The default behavior will return a 431 Request Header
                 Fields Too Large if a HPE_HEADER_OVERFLOW error occurs.
  - version: v9.4.0
    pr-url: https://github.com/nodejs/node/pull/17672
    description: The `rawPacket` is the current buffer that just parsed. Adding
                 this buffer to the error object of `'clientError'` event is to
                 make it possible that developers can log the broken packet.
  - version: v6.0.0
    pr-url: https://github.com/nodejs/node/pull/4557
    description: The default action of calling `.destroy()` on the `socket`
                 will no longer take place if there are listeners attached
                 for `'clientError'`.
-->

* `exception` {Error}
* `socket` {stream.Duplex}

If a client connection emits an `'error'` event, it will be forwarded here.
Listener of this event is responsible for closing/destroying the underlying
socket. For example, one may wish to more gracefully close the socket with a
custom HTTP response instead of abruptly severing the connection. The socket
**must be closed or destroyed** before the listener ends.

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

Default behavior is to try close the socket with a HTTP '400 Bad Request',
or a HTTP '431 Request Header Fields Too Large' in the case of a
[`HPE_HEADER_OVERFLOW`][] error. If the socket is not writable or headers
of the current attached [`http.ServerResponse`][] has been sent, it is
immediately destroyed.

`socket` is the [`net.Socket`][] object that the error originated from.

```mjs
import http from 'node:http';

const server = http.createServer((req, res) => {
  res.end();
});
server.on('clientError', (err, socket) => {
  socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
});
server.listen(8000);
```

```cjs
const http = require('node:http');

const server = http.createServer((req, res) => {
  res.end();
});
server.on('clientError', (err, socket) => {
  socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
});
server.listen(8000);
```

When the `'clientError'` event occurs, there is no `request` or `response`
object, so any HTTP response sent, including response headers and payload,
_must_ be written directly to the `socket` object. Care must be taken to
ensure the response is a properly formatted HTTP response message.

`err` is an instance of `Error` with two extra columns:

* `bytesParsed`: the bytes count of request packet that Node.js may have parsed
  correctly;
* `rawPacket`: the raw packet of current request.

In some cases, the client has already received the response and/or the socket
has already been destroyed, like in case of `ECONNRESET` errors. Before
trying to send data to the socket, it is better to check that it is still
writable.

```js
server.on('clientError', (err, socket) => {
  if (err.code === 'ECONNRESET' || !socket.writable) {
    return;
  }

socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
});
```

### Event: `'close'`

<!-- YAML
added: v0.1.4
-->

Emitted when the server closes.

### Event: `'connect'`

<!-- YAML
added: v0.7.0
-->

* `request` {http.IncomingMessage} Arguments for the HTTP request, as it is in
  the [`'request'`][] event
* `socket` {stream.Duplex} Network socket between the server and client
* `head` {Buffer} The first packet of the tunneling stream (may be empty)

Emitted each time a client requests an HTTP `CONNECT` method. If this event is
not listened for, then clients requesting a `CONNECT` method will have their
connections closed.

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

After this event is emitted, the request's socket will not have a `'data'`
event listener, meaning it will need to be bound in order to handle data
sent to the server on that socket.

### Event: `'connection'`

<!-- YAML
added: v0.1.0
-->

* `socket` {stream.Duplex}

This event is emitted when a new TCP stream is established. `socket` is
typically an object of type [`net.Socket`][]. Usually users will not want to
access this event. In particular, the socket will not emit `'readable'` events
because of how the protocol parser attaches to the socket. The `socket` can
also be accessed at `request.socket`.

This event can also be explicitly emitted by users to inject connections
into the HTTP server. In that case, any [`Duplex`][] stream can be passed.

If `socket.setTimeout()` is called here, the timeout will be replaced with
`server.keepAliveTimeout` when the socket has served a request (if
`server.keepAliveTimeout` is non-zero).

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

### Event: `'dropRequest'`

<!-- YAML
added:
  - v18.7.0
  - v16.17.0
-->

* `request` {http.IncomingMessage} Arguments for the HTTP request, as it is in
  the [`'request'`][] event
* `socket` {stream.Duplex} Network socket between the server and client

When the number of requests on a socket reaches the threshold of
`server.maxRequestsPerSocket`, the server will drop new requests
and emit `'dropRequest'` event instead, then send `503` to client.

### Event: `'request'`

<!-- YAML
added: v0.1.0
-->

* `request` {http.IncomingMessage}
* `response` {http.ServerResponse}

Emitted each time there is a request. There may be multiple requests
per connection (in the case of HTTP Keep-Alive connections).

### Event: `'upgrade'`

<!-- YAML
added: v0.1.94
changes:
  - version: REPLACEME
    pr-url: https://github.com/nodejs/node/pull/60016
    description: Request bodies are no longer exposed raw (unparsed) on the
                 socket argument. Instead, if a body is received, the stream
                 argument will be a duplex that emits socket content only
                 after the request body, while the parsed request body data
                 will be emitted from the request, just as in normal server
                 `'request'` events.
  - version:
     - v24.9.0
     - v22.21.0
    pr-url: https://github.com/nodejs/node/pull/59824
    description: Whether this event is fired can now be controlled by the
                 `shouldUpgradeCallback` and sockets will be destroyed
                 if upgraded while no event handler is listening.
  - version: v10.0.0
    pr-url: https://github.com/nodejs/node/pull/19981
    description: Not listening to this event no longer causes the socket
                 to be destroyed if a client sends an Upgrade header.
-->

* `request` {http.IncomingMessage} Arguments for the HTTP request, as it is in
  the [`'request'`][] event
* `stream` {stream.Duplex} The upgraded stream between the server and client
* `head` {Buffer} The first packet of the upgraded stream (may be empty)

Emitted each time a client's HTTP upgrade request is accepted. By default
all HTTP upgrade requests are ignored (i.e. only regular `'request'` events
are emitted, sticking with the normal HTTP request/response flow) unless you
listen to this event, in which case they are all accepted (i.e. the `'upgrade'`
event is emitted instead, and future communication must handled directly
through the raw stream). You can control this more precisely by using the
server `shouldUpgradeCallback` option.

Listening to this event is optional and clients cannot insist on a protocol
change.

If an upgrade is accepted by `shouldUpgradeCallback` but no event handler
is registered then the socket will be destroyed, resulting in an immediate
connection closure for the client.

In the uncommon case that the incoming request has a body, this body will be
parsed as normal, separate to the upgrade stream, and the raw stream data will
only begin after it has completed. To ensure that reading from the stream isn't
blocked by waiting for the request body to be read, any reads on the stream
will start the request body flowing automatically. If you want to read the
request body, ensure that you do so (i.e. you attach `'data'` listeners)
before starting to read from the upgraded stream.

The stream argument will typically be the {net.Socket} instance used by the
request, but in some cases (such as with a request body) it may be a duplex
stream. If required, you can access the raw connection underlying the request
via [`request.socket`][], which is guaranteed to be an instance of {net.Socket}
unless the user specified another socket type.

### `server.close([callback])`

<!-- YAML
added: v0.1.90
changes:
  - version:
      - v19.0.0
    pr-url: https://github.com/nodejs/node/pull/43522
    description: The method closes idle connections before returning.

-->

* `callback` {Function}

Stops the server from accepting new connections and closes all connections
connected to this server which are not sending a request or waiting for
a response.
See [`net.Server.close()`][].

```js
const http = require('node:http');

const server = http.createServer({ keepAliveTimeout: 60000 }, (req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
// Close the server after 10 seconds
setTimeout(() => {
  server.close(() => {
    console.log('server on port 8000 closed successfully');
  });
}, 10000);
```

### `server.closeAllConnections()`

<!-- YAML
added: v18.2.0
-->

Closes all established HTTP(S) connections connected to this server, including
active connections connected to this server which are sending a request or
waiting for a response. This does _not_ destroy sockets upgraded to a different
protocol, such as WebSocket or HTTP/2.

> This is a forceful way of closing all connections and should be used with
> caution. Whenever using this in conjunction with `server.close`, calling this
> _after_ `server.close` is recommended as to avoid race conditions where new
> connections are created between a call to this and a call to `server.close`.

```js
const http = require('node:http');

const server = http.createServer({ keepAliveTimeout: 60000 }, (req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
// Close the server after 10 seconds
setTimeout(() => {
  server.close(() => {
    console.log('server on port 8000 closed successfully');
  });
  // Closes all connections, ensuring the server closes successfully
  server.closeAllConnections();
}, 10000);
```

### `server.closeIdleConnections()`

<!-- YAML
added: v18.2.0
-->

Closes all connections connected to this server which are not sending a request
or waiting for a response.

> Starting with Node.js 19.0.0, there's no need for calling this method in
> conjunction with `server.close` to reap `keep-alive` connections. Using it
> won't cause any harm though, and it can be useful to ensure backwards
> compatibility for libraries and applications that need to support versions
> older than 19.0.0. Whenever using this in conjunction with `server.close`,
> calling this _after_ `server.close` is recommended as to avoid race
> conditions where new connections are created between a call to this and a
> call to `server.close`.

```js
const http = require('node:http');

const server = http.createServer({ keepAliveTimeout: 60000 }, (req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
// Close the server after 10 seconds
setTimeout(() => {
  server.close(() => {
    console.log('server on port 8000 closed successfully');
  });
  // Closes idle connections, such as keep-alive connections. Server will close
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
