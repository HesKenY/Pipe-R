# Node.js http (1/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
# HTTP

<!--introduced_in=v0.10.0-->

> Stability: 2 - Stable

<!-- source_link=lib/http.js -->

This module, containing both a client and server, can be imported via
`require('node:http')` (CommonJS) or `import * as http from 'node:http'` (ES module).

The HTTP interfaces in Node.js are designed to support many features
of the protocol which have been traditionally difficult to use.
In particular, large, possibly chunk-encoded, messages. The interface is
careful to never buffer entire requests or responses, so the
user is able to stream data.

HTTP message headers are represented by an object like this:

```json
{ "content-length": "123",
  "content-type": "text/plain",
  "connection": "keep-alive",
  "host": "example.com",
  "accept": "*/*" }
```

Keys are lowercased. Values are not modified.

In order to support the full spectrum of possible HTTP applications, the Node.js
HTTP API is very low-level. It deals with stream handling and message
parsing only. It parses a message into headers and body but it does not
parse the actual headers or the body.

See [`message.headers`][] for details on how duplicate headers are handled.

The raw headers as they were received are retained in the `rawHeaders`
property, which is an array of `[key, value, key2, value2, ...]`. For
example, the previous message header object might have a `rawHeaders`
list like the following:

<!-- eslint-disable @stylistic/js/semi -->

```js
[ 'ConTent-Length', '123456',
  'content-LENGTH', '123',
  'content-type', 'text/plain',
  'CONNECTION', 'keep-alive',
  'Host', 'example.com',
  'accepT', '*/*' ]
```

## Class: `http.Agent`

<!-- YAML
added: v0.3.4
-->

An `Agent` is responsible for managing connection persistence
and reuse for HTTP clients. It maintains a queue of pending requests
for a given host and port, reusing a single socket connection for each
until the queue is empty, at which time the socket is either destroyed
or put into a pool where it is kept to be used again for requests to the
same host and port. Whether it is destroyed or pooled depends on the
`keepAlive` [option](#new-agentoptions).

Pooled connections have TCP Keep-Alive enabled for them, but servers may
still close idle connections, in which case they will be removed from the
pool and a new connection will be made when a new HTTP request is made for
that host and port. Servers may also refuse to allow multiple requests
over the same connection, in which case the connection will have to be
remade for every request and cannot be pooled. The `Agent` will still make
the requests to that server, but each one will occur over a new connection.

When a connection is closed by the client or the server, it is removed
from the pool. Any unused sockets in the pool will be unrefed so as not
to keep the Node.js process running when there are no outstanding requests.
(see [`socket.unref()`][]).

It is good practice, to [`destroy()`][] an `Agent` instance when it is no
longer in use, because unused sockets consume OS resources.

Sockets are removed from an agent when the socket emits either
a `'close'` event or an `'agentRemove'` event. When intending to keep one
HTTP request open for a long time without keeping it in the agent, something
like the following may be done:

```js
http.get(options, (res) => {
  // Do stuff
}).on('socket', (socket) => {
  socket.emit('agentRemove');
});
```

An agent may also be used for an individual request. By providing
`{agent: false}` as an option to the `http.get()` or `http.request()`
functions, a one-time use `Agent` with default options will be used
for the client connection.

`agent:false`:

```js
http.get({
  hostname: 'localhost',
  port: 80,
  path: '/',
  agent: false,  // Create a new agent just for this one request
}, (res) => {
  // Do stuff with response
});
```

### `new Agent([options])`

<!-- YAML
added: v0.3.4
changes:
  - version:
    - v24.7.0
    - v22.20.0
    pr-url: https://github.com/nodejs/node/pull/59315
    description: Add support for `agentKeepAliveTimeoutBuffer`.
  - version:
    - v24.5.0
    - v22.21.0
    pr-url: https://github.com/nodejs/node/pull/58980
    description: Add support for `proxyEnv`.
  - version:
    - v24.5.0
    - v22.21.0
    pr-url: https://github.com/nodejs/node/pull/58980
    description: Add support for `defaultPort` and `protocol`.
  - version:
      - v15.6.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/36685
    description: Change the default scheduling from 'fifo' to 'lifo'.
  - version:
    - v14.5.0
    - v12.19.0
    pr-url: https://github.com/nodejs/node/pull/33617
    description: Add `maxTotalSockets` option to agent constructor.
  - version:
      - v14.5.0
      - v12.20.0
    pr-url: https://github.com/nodejs/node/pull/33278
    description: Add `scheduling` option to specify the free socket
                 scheduling strategy.
-->

* `options` {Object} Set of configurable options to set on the agent.
  Can have the following fields:
  * `keepAlive` {boolean} Keep sockets around even when there are no
    outstanding requests, so they can be used for future requests without
    having to reestablish a TCP connection. Not to be confused with the
    `keep-alive` value of the `Connection` header. The `Connection: keep-alive`
    header is always sent when using an agent except when the `Connection`
    header is explicitly specified or when the `keepAlive` and `maxSockets`
    options are respectively set to `false` and `Infinity`, in which case
    `Connection: close` will be used. **Default:** `false`.
  * `keepAliveMsecs` {number} When using the `keepAlive` option, specifies
    the [initial delay][]
    for TCP Keep-Alive packets. Ignored when the
    `keepAlive` option is `false` or `undefined`. **Default:** `1000`.
  * `agentKeepAliveTimeoutBuffer` {number} Milliseconds to subtract from
    the server-provided `keep-alive: timeout=...` hint when determining socket
    expiration time. This buffer helps ensure the agent closes the socket
    slightly before the server does, reducing the chance of sending a request
    on a socket that’s about to be closed by the server.
    **Default:** `1000`.
  * `maxSockets` {number} Maximum number of sockets to allow per host.
    If the same host opens multiple concurrent connections, each request
    will use new socket until the `maxSockets` value is reached.
    If the host attempts to open more connections than `maxSockets`,
    the additional requests will enter into a pending request queue, and
    will enter active connection state when an existing connection terminates.
    This makes sure there are at most `maxSockets` active connections at
    any point in time, from a given host.
    **Default:** `Infinity`.
  * `maxTotalSockets` {number} Maximum number of sockets allowed for
    all hosts in total. Each request will use a new socket
    until the maximum is reached.
    **Default:** `Infinity`.
  * `maxFreeSockets` {number} Maximum number of sockets per host to leave open
    in a free state. Only relevant if `keepAlive` is set to `true`.
    **Default:** `256`.
  * `scheduling` {string} Scheduling strategy to apply when picking
    the next free socket to use. It can be `'fifo'` or `'lifo'`.
    The main difference between the two scheduling strategies is that `'lifo'`
    selects the most recently used socket, while `'fifo'` selects
    the least recently used socket.
    In case of a low rate of request per second, the `'lifo'` scheduling
    will lower the risk of picking a socket that might have been closed
    by the server due to inactivity.
    In case of a high rate of request per second,
    the `'fifo'` scheduling will maximize the number of open sockets,
    while the `'lifo'` scheduling will keep it as low as possible.
    **Default:** `'lifo'`.
  * `timeout` {number} Socket timeout in milliseconds.
    This will set the timeout when the socket is created.
  * `proxyEnv` {Object|undefined} Environment variables for proxy configuration.
    See [Built-in Proxy Support][] for details. **Default:** `undefined`
    * `HTTP_PROXY` {string|undefined} URL for the proxy server that HTTP requests should use.
      If undefined, no proxy is used for HTTP requests.
    * `HTTPS_PROXY` {string|undefined} URL for the proxy server that HTTPS requests should use.
      If undefined, no proxy is used for HTTPS requests.
    * `NO_PROXY` {string|undefined} Patterns specifying the endpoints
      that should not be routed through a proxy.
    * `http_proxy` {string|undefined} Same as `HTTP_PROXY`. If both are set, `http_proxy` takes precedence.
    * `https_proxy` {string|undefined} Same as `HTTPS_PROXY`. If both are set, `https_proxy` takes precedence.
    * `no_proxy` {string|undefined} Same as `NO_PROXY`. If both are set, `no_proxy` takes precedence.
  * `defaultPort` {number} Default port to use when the port is not specified
    in requests. **Default:** `80`.
  * `protocol` {string} The protocol to use for the agent. **Default:** `'http:'`.

`options` in [`socket.connect()`][] are also supported.

To configure any of them, a custom [`http.Agent`][] instance must be created.

```mjs
import { Agent, request } from 'node:http';
const keepAliveAgent = new Agent({ keepAlive: true });
options.agent = keepAliveAgent;
request(options, onResponseCallback);
```

```cjs
const http = require('node:http');
const keepAliveAgent = new http.Agent({ keepAlive: true });
options.agent = keepAliveAgent;
http.request(options, onResponseCallback);
```

### `agent.createConnection(options[, callback])`

<!-- YAML
added: v0.11.4
-->

* `options` {Object} Options containing connection details. Check
  [`net.createConnection()`][] for the format of the options. For custom agents,
  this object is passed to the custom `createConnection` function.
* `callback` {Function} (Optional, primarily for custom agents) A function to be
  called by a custom `createConnection` implementation when the socket is
  created, especially for asynchronous operations.
  * `err` {Error | null} An error object if socket creation failed.
  * `socket` {stream.Duplex} The created socket.
* Returns: {stream.Duplex} The created socket. This is returned by the default
  implementation or by a custom synchronous `createConnection` implementation.
  If a custom `createConnection` uses the `callback` for asynchronous
  operation, this return value might not be the primary way to obtain the socket.

Produces a socket/stream to be used for HTTP requests.

By default, this function behaves identically to [`net.createConnection()`][],
synchronously returning the created socket. The optional `callback` parameter in the
signature is **not** used by this default implementation.

However, custom agents may override this method to provide greater flexibility,
for example, to create sockets asynchronously. When overriding `createConnection`:

1. **Synchronous socket creation**: The overriding method can return the
   socket/stream directly.
2. **Asynchronous socket creation**: The overriding method can accept the `callback`
   and pass the created socket/stream to it (e.g., `callback(null, newSocket)`).
   If an error occurs during socket creation, it should be passed as the first
   argument to the `callback` (e.g., `callback(err)`).

The agent will call the provided `createConnection` function with `options` and
this internal `callback`. The `callback` provided by the agent has a signature
of `(err, stream)`.

### `agent.keepSocketAlive(socket)`

<!-- YAML
added: v8.1.0
-->

* `socket` {stream.Duplex}

Called when `socket` is detached from a request and could be persisted by the
`Agent`. Default behavior is to:

```js
socket.setKeepAlive(true, this.keepAliveMsecs);
socket.unref();
return true;
```

This method can be overridden by a particular `Agent` subclass. If this
method returns a falsy value, the socket will be destroyed instead of persisting
it for use with the next request.

The `socket` argument can be an instance of {net.Socket}, a subclass of
{stream.Duplex}.

### `agent.reuseSocket(socket, request)`

<!-- YAML
added: v8.1.0
-->

* `socket` {stream.Duplex}
* `request` {http.ClientRequest}

Called when `socket` is attached to `request` after being persisted because of
the keep-alive options. Default behavior is to:

```js
socket.ref();
```

This method can be overridden by a particular `Agent` subclass.

The `socket` argument can be an instance of {net.Socket}, a subclass of
{stream.Duplex}.

### `agent.destroy()`

<!-- YAML
added: v0.11.4
-->

Destroy any sockets that are currently in use by the agent.

It is usually not necessary to do this. However, if using an
agent with `keepAlive` enabled, then it is best to explicitly shut down
the agent when it is no longer needed. Otherwise,
sockets might stay open for quite a long time before the server
terminates them.

### `agent.freeSockets`

<!-- YAML
added: v0.11.4
changes:
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/36409
    description: The property now has a `null` prototype.
-->

* Type: {Object}

An object which contains arrays of sockets currently awaiting use by
the agent when `keepAlive` is enabled. Do not modify.

Sockets in the `freeSockets` list will be automatically destroyed and
removed from the array on `'timeout'`.

### `agent.getName([options])`

<!-- YAML
added: v0.11.4
changes:
  - version:
    - v17.7.0
    - v16.15.0
    pr-url: https://github.com/nodejs/node/pull/41906
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
