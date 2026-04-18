# Node.js http (2/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
.com/nodejs/node/pull/41906
    description: The `options` parameter is now optional.
-->

* `options` {Object} A set of options providing information for name generation
  * `host` {string} A domain name or IP address of the server to issue the
    request to
  * `port` {number} Port of remote server
  * `localAddress` {string} Local interface to bind for network connections
    when issuing the request
  * `family` {integer} Must be 4 or 6 if this doesn't equal `undefined`.
* Returns: {string}

Get a unique name for a set of request options, to determine whether a
connection can be reused. For an HTTP agent, this returns
`host:port:localAddress` or `host:port:localAddress:family`. For an HTTPS agent,
the name includes the CA, cert, ciphers, and other HTTPS/TLS-specific options
that determine socket reusability.

### `agent.maxFreeSockets`

<!-- YAML
added: v0.11.7
-->

* Type: {number}

By default set to 256. For agents with `keepAlive` enabled, this
sets the maximum number of sockets that will be left open in the free
state.

### `agent.maxSockets`

<!-- YAML
added: v0.3.6
-->

* Type: {number}

By default set to `Infinity`. Determines how many concurrent sockets the agent
can have open per origin. Origin is the returned value of [`agent.getName()`][].

### `agent.maxTotalSockets`

<!-- YAML
added:
  - v14.5.0
  - v12.19.0
-->

* Type: {number}

By default set to `Infinity`. Determines how many concurrent sockets the agent
can have open. Unlike `maxSockets`, this parameter applies across all origins.

### `agent.requests`

<!-- YAML
added: v0.5.9
changes:
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/36409
    description: The property now has a `null` prototype.
-->

* Type: {Object}

An object which contains queues of requests that have not yet been assigned to
sockets. Do not modify.

### `agent.sockets`

<!-- YAML
added: v0.3.6
changes:
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/36409
    description: The property now has a `null` prototype.
-->

* Type: {Object}

An object which contains arrays of sockets currently in use by the
agent. Do not modify.

## Class: `http.ClientRequest`

<!-- YAML
added: v0.1.17
-->

* Extends: {http.OutgoingMessage}

This object is created internally and returned from [`http.request()`][]. It
represents an _in-progress_ request whose header has already been queued. The
header is still mutable using the [`setHeader(name, value)`][],
[`getHeader(name)`][], [`removeHeader(name)`][] API. The actual header will
be sent along with the first data chunk or when calling [`request.end()`][].

To get the response, add a listener for [`'response'`][] to the request object.
[`'response'`][] will be emitted from the request object when the response
headers have been received. The [`'response'`][] event is executed with one
argument which is an instance of [`http.IncomingMessage`][].

During the [`'response'`][] event, one can add listeners to the
response object; particularly to listen for the `'data'` event.

If no [`'response'`][] handler is added, then the response will be
entirely discarded. However, if a [`'response'`][] event handler is added,
then the data from the response object **must** be consumed, either by
calling `response.read()` whenever there is a `'readable'` event, or
by adding a `'data'` handler, or by calling the `.resume()` method.
Until the data is consumed, the `'end'` event will not fire. Also, until
the data is read it will consume memory that can eventually lead to a
'process out of memory' error.

For backward compatibility, `res` will only emit `'error'` if there is an
`'error'` listener registered.

Set `Content-Length` header to limit the response body size.
If [`response.strictContentLength`][] is set to `true`, mismatching the
`Content-Length` header value will result in an `Error` being thrown,
identified by `code:` [`'ERR_HTTP_CONTENT_LENGTH_MISMATCH'`][].

`Content-Length` value should be in bytes, not characters. Use
[`Buffer.byteLength()`][] to determine the length of the body in bytes.

### Event: `'abort'`

<!-- YAML
added: v1.4.1
deprecated:
  - v17.0.0
  - v16.12.0
-->

> Stability: 0 - Deprecated. Listen for the `'close'` event instead.

Emitted when the request has been aborted by the client. This event is only
emitted on the first call to `abort()`.

### Event: `'close'`

<!-- YAML
added: v0.5.4
-->

Indicates that the request is completed, or its underlying connection was
terminated prematurely (before the response completion).

### Event: `'connect'`

<!-- YAML
added: v0.7.0
-->

* `response` {http.IncomingMessage}
* `socket` {stream.Duplex}
* `head` {Buffer}

Emitted each time a server responds to a request with a `CONNECT` method. If
this event is not being listened for, clients receiving a `CONNECT` method will
have their connections closed.

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

A client and server pair demonstrating how to listen for the `'connect'` event:

```mjs
import { createServer, request } from 'node:http';
import { connect } from 'node:net';
import { URL } from 'node:url';

// Create an HTTP tunneling proxy
const proxy = createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('okay');
});
proxy.on('connect', (req, clientSocket, head) => {
  // Connect to an origin server
  const { port, hostname } = new URL(`http://${req.url}`);
  const serverSocket = connect(port || 80, hostname, () => {
    clientSocket.write('HTTP/1.1 200 Connection Established\r\n' +
                    'Proxy-agent: Node.js-Proxy\r\n' +
                    '\r\n');
    serverSocket.write(head);
    serverSocket.pipe(clientSocket);
    clientSocket.pipe(serverSocket);
  });
});

// Now that proxy is running
proxy.listen(1337, '127.0.0.1', () => {

// Make a request to a tunneling proxy
  const options = {
    port: 1337,
    host: '127.0.0.1',
    method: 'CONNECT',
    path: 'www.google.com:80',
  };

const req = request(options);
  req.end();

req.on('connect', (res, socket, head) => {
    console.log('got connected!');

// Make a request over an HTTP tunnel
    socket.write('GET / HTTP/1.1\r\n' +
                 'Host: www.google.com:80\r\n' +
                 'Connection: close\r\n' +
                 '\r\n');
    socket.on('data', (chunk) => {
      console.log(chunk.toString());
    });
    socket.on('end', () => {
      proxy.close();
    });
  });
});
```

```cjs
const http = require('node:http');
const net = require('node:net');
const { URL } = require('node:url');

// Create an HTTP tunneling proxy
const proxy = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('okay');
});
proxy.on('connect', (req, clientSocket, head) => {
  // Connect to an origin server
  const { port, hostname } = new URL(`http://${req.url}`);
  const serverSocket = net.connect(port || 80, hostname, () => {
    clientSocket.write('HTTP/1.1 200 Connection Established\r\n' +
                    'Proxy-agent: Node.js-Proxy\r\n' +
                    '\r\n');
    serverSocket.write(head);
    serverSocket.pipe(clientSocket);
    clientSocket.pipe(serverSocket);
  });
});

// Now that proxy is running
proxy.listen(1337, '127.0.0.1', () => {

// Make a request to a tunneling proxy
  const options = {
    port: 1337,
    host: '127.0.0.1',
    method: 'CONNECT',
    path: 'www.google.com:80',
  };

const req = http.request(options);
  req.end();

req.on('connect', (res, socket, head) => {
    console.log('got connected!');

// Make a request over an HTTP tunnel
    socket.write('GET / HTTP/1.1\r\n' +
                 'Host: www.google.com:80\r\n' +
                 'Connection: close\r\n' +
                 '\r\n');
    socket.on('data', (chunk) => {
      console.log(chunk.toString());
    });
    socket.on('end', () => {
      proxy.close();
    });
  });
});
```

### Event: `'continue'`

<!-- YAML
added: v0.3.2
-->

Emitted when the server sends a '100 Continue' HTTP response, usually because
the request contained 'Expect: 100-continue'. This is an instruction that
the client should send the request body.

### Event: `'finish'`

<!-- YAML
added: v0.3.6
-->

Emitted when the request has been sent. More specifically, this event is emitted
when the last segment of the request headers and body have been handed off to
the operating system for transmission over the network. It does not imply that
the server has received anything yet.

### Event: `'information'`

<!-- YAML
added: v10.0.0
-->

* `info` {Object}
  * `httpVersion` {string}
  * `httpVersionMajor` {integer}
  * `httpVersionMinor` {integer}
  * `statusCode` {integer}
  * `statusMessage` {string}
  * `headers` {Object}
  * `rawHeaders` {string\[]}

Emitted when the server sends a 1xx intermediate response (excluding 101
Upgrade). The listeners of this event will receive an object containing the
HTTP version, status code, status message, key-value headers object,
and array with the raw header names followed by their respective values.

```mjs
import { request } from 'node:http';

const options = {
  host: '127.0.0.1',
  port: 8080,
  path: '/length_request',
};

// Make a request
const req = request(options);
req.end();

req.on('information', (info) => {
  console.log(`Got information prior to main response: ${info.statusCode}`);
});
```

```cjs
const http = require('node:http');

const options = {
  host: '127.0.0.1',
  port: 8080,
  path: '/length_request',
};

// Make a request
const req = http.request(options);
req.end();

req.on('information', (info) => {
  console.log(`Got information prior to main response: ${info.statusCode}`);
});
```

101 Upgrade statuses do not fire this event due to their break from the
traditional HTTP request/response chain, such as web sockets, in-place TLS
upgrades, or HTTP 2.0. To be notified of 101 Upgrade notices, listen for the
[`'upgrade'`][] event instead.

### Event: `'response'`

<!-- YAML
added: v0.1.0
-->

* `response` {http.IncomingMessage}

Emitted when a response is received to this request. This event is emitted only
once.

### Event: `'socket'`

<!-- YAML
added: v0.5.3
-->

* `socket` {stream.Duplex}

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

### Event: `'timeout'`

<!-- YAML
added: v0.7.8
-->

Emitted when the underlying socket times out from inactivity. This only notifies
that the socket has been idle. The request must be destroyed manually.

See also: [`request.setTimeout()`][].

### Event: `'upgrade'`

<!-- YAML
added: v0.1.94
-->

* `response` {http.IncomingMessage}
* `stream` {stream.Duplex}
* `head` {Buffer}

Emitted each time a server responds to a request with an upgrade. If this
event is not being listened for and the response status code is 101 Switching
Protocols, clients receiving an upgrade header will have their connections
closed.

This event is guaranteed to be passed an instance of the {net.Socket} class,
a subclass of {stream.Duplex}, unless the user specifies a socket
type other than {net.Socket}.

A client server pair demonstrating how to listen for the `'upgrade'` event.

```mjs
import http from 'node:http';
import process from 'node:process';

// Create an HTTP server
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('okay');
});
server.on('upgrade', (req, stream, head) => {
  stream.write('HTTP/1.1 101 Web Socket Protocol Handshake\r\n' +
               'Upgrade: WebSocket\r\n' +
               'Connection: Upgrade\r\n' +
               '\r\n');

stream.pipe(stream); // echo back
});

// Now that server is running
server.listen(1337, '127.0.0.1', () => {

// make a request
  const options = {
    port: 1337,
    host: '127.0.0.1',
    headers: {
      'Connection': 'Upgrade',
      'Upgrade': 'websocket',
    },
  };

const req = http.request(options);
  req.end();

req.on('upgrade', (res, stream, upgradeHead) => {
    console.log('got upgraded!');
    stream.end();
    process.exit(0);
  });
});
```

```cjs
const http = require('node:http');

// Create an HTTP server
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('okay');
});
server.on('upgrade', (req, stream, head) => {
  stream.write('HTTP/1.1 101 Web Socket Protocol Handshake\r\n' +
               'Upgrade: WebSocket\r\n' +
               'Connection: Upgrade\r\n' +
               '\r\n');

stream.pipe(stream); // echo back
});

// Now that server is running
server.listen(1337, '127.0.0.1', () => {

// make a request
  const options = {
    port: 1337,
    host: '127.0.0.1',
    headers: {
      'Connection': 'Upgrade',
      'Upgrade': 'websocket',
    },
  };

const req = http.request(options);
  req.end();

req.on('upgrade', (res, stream, upgradeHead) => {
    console.log('got upgraded!');
    stream.end();
    process.exit(0);
  });
});
```

### `request.abort()`

<!-- YAML
added: v0.3.8
deprecated:
  - v14.1.0
  - v13.14.0
-->

> Stability: 0 - Deprecated: Use [`request.destroy()`][] instead.

Marks the request as aborting. Calling this will cause remaining data
in the response to be dropped and the socket to be destroyed.

### `request.aborted`

<!-- YAML
added: v0.11.14
deprecated:
  - v17.0.0
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
