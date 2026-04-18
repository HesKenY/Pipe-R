# Node.js http (9/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
http.ClientRequest}

Since most requests are GET requests without bodies, Node.js provides this
convenience method. The only difference between this method and
[`http.request()`][] is that it sets the method to GET by default and calls `req.end()`
automatically. The callback must take care to consume the response
data for reasons stated in [`http.ClientRequest`][] section.

The `callback` is invoked with a single argument that is an instance of
[`http.IncomingMessage`][].

JSON fetching example:

```js
http.get('http://localhost:8000/', (res) => {
  const { statusCode } = res;
  const contentType = res.headers['content-type'];

let error;
  // Any 2xx status code signals a successful response but
  // here we're only checking for 200.
  if (statusCode !== 200) {
    error = new Error('Request Failed.\n' +
                      `Status Code: ${statusCode}`);
  } else if (!/^application\/json/.test(contentType)) {
    error = new Error('Invalid content-type.\n' +
                      `Expected application/json but received ${contentType}`);
  }
  if (error) {
    console.error(error.message);
    // Consume response data to free up memory
    res.resume();
    return;
  }

res.setEncoding('utf8');
  let rawData = '';
  res.on('data', (chunk) => { rawData += chunk; });
  res.on('end', () => {
    try {
      const parsedData = JSON.parse(rawData);
      console.log(parsedData);
    } catch (e) {
      console.error(e.message);
    }
  });
}).on('error', (e) => {
  console.error(`Got error: ${e.message}`);
});

// Create a local server to receive data from
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    data: 'Hello World!',
  }));
});

server.listen(8000);
```

## `http.globalAgent`

<!-- YAML
added: v0.5.9
changes:
  - version:
      - v19.0.0
    pr-url: https://github.com/nodejs/node/pull/43522
    description: The agent now uses HTTP Keep-Alive and a 5 second timeout by
                 default.
-->

* Type: {http.Agent}

Global instance of `Agent` which is used as the default for all HTTP client
requests. Diverges from a default `Agent` configuration by having `keepAlive`
enabled and a `timeout` of 5 seconds.

## `http.maxHeaderSize`

<!-- YAML
added:
 - v11.6.0
 - v10.15.0
-->

* Type: {number}

Read-only property specifying the maximum allowed size of HTTP headers in bytes.
Defaults to 16 KiB. Configurable using the [`--max-http-header-size`][] CLI
option.

This can be overridden for servers and client requests by passing the
`maxHeaderSize` option.

## `http.request(options[, callback])`

## `http.request(url[, options][, callback])`

<!-- YAML
added: v0.3.6
changes:
  - version:
      - v16.7.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/39310
    description: When using a `URL` object parsed username and
                 password will now be properly URI decoded.
  - version:
      - v15.3.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/36048
    description: It is possible to abort a request with an AbortSignal.
  - version:
     - v13.8.0
     - v12.15.0
     - v10.19.0
    pr-url: https://github.com/nodejs/node/pull/31448
    description: The `insecureHTTPParser` option is supported now.
  - version: v13.3.0
    pr-url: https://github.com/nodejs/node/pull/30570
    description: The `maxHeaderSize` option is supported now.
  - version: v10.9.0
    pr-url: https://github.com/nodejs/node/pull/21616
    description: The `url` parameter can now be passed along with a separate
                 `options` object.
  - version: v7.5.0
    pr-url: https://github.com/nodejs/node/pull/10638
    description: The `options` parameter can be a WHATWG `URL` object.
-->

* `url` {string | URL}
* `options` {Object}
  * `agent` {http.Agent | boolean} Controls [`Agent`][] behavior. Possible
    values:
    * `undefined` (default): use [`http.globalAgent`][] for this host and port.
    * `Agent` object: explicitly use the passed in `Agent`.
    * `false`: causes a new `Agent` with default values to be used.
  * `auth` {string} Basic authentication (`'user:password'`) to compute an
    Authorization header.
  * `createConnection` {Function} A function that produces a socket/stream to
    use for the request when the `agent` option is not used. This can be used to
    avoid creating a custom `Agent` class just to override the default
    `createConnection` function. See [`agent.createConnection()`][] for more
    details. Any [`Duplex`][] stream is a valid return value.
  * `defaultPort` {number} Default port for the protocol. **Default:**
    `agent.defaultPort` if an `Agent` is used, else `undefined`.
  * `family` {number} IP address family to use when resolving `host` or
    `hostname`. Valid values are `4` or `6`. When unspecified, both IP v4 and
    v6 will be used.
  * `headers` {Object|Array} An object or an array of strings containing request
    headers. The array is in the same format as [`message.rawHeaders`][].
  * `hints` {number} Optional [`dns.lookup()` hints][].
  * `host` {string} A domain name or IP address of the server to issue the
    request to. **Default:** `'localhost'`.
  * `hostname` {string} Alias for `host`. To support [`url.parse()`][],
    `hostname` will be used if both `host` and `hostname` are specified.
  * `insecureHTTPParser` {boolean} If set to `true`, it will use a HTTP parser
    with leniency flags enabled. Using the insecure parser should be avoided.
    See [`--insecure-http-parser`][] for more information.
    **Default:** `false`
  * `joinDuplicateHeaders` {boolean} It joins the field line values of
    multiple headers in a request with `, ` instead of discarding
    the duplicates. See [`message.headers`][] for more information.
    **Default:** `false`.
  * `localAddress` {string} Local interface to bind for network connections.
  * `localPort` {number} Local port to connect from.
  * `lookup` {Function} Custom lookup function. **Default:** [`dns.lookup()`][].
  * `maxHeaderSize` {number} Optionally overrides the value of
    [`--max-http-header-size`][] (the maximum length of response headers in
    bytes) for responses received from the server.
    **Default:** 16384 (16 KiB).
  * `method` {string} A string specifying the HTTP request method. **Default:**
    `'GET'`.
  * `path` {string} Request path. Should include query string if any.
    E.G. `'/index.html?page=12'`. An exception is thrown when the request path
    contains illegal characters. Currently, only spaces are rejected but that
    may change in the future. **Default:** `'/'`.
  * `port` {number} Port of remote server. **Default:** `defaultPort` if set,
    else `80`.
  * `protocol` {string} Protocol to use. **Default:** `'http:'`.
  * `setDefaultHeaders` {boolean}: Specifies whether or not to automatically add
    default headers such as `Connection`, `Content-Length`, `Transfer-Encoding`,
    and `Host`. If set to `false` then all necessary headers must be added
    manually. Defaults to `true`.
  * `setHost` {boolean}: Specifies whether or not to automatically add the
    `Host` header. If provided, this overrides `setDefaultHeaders`. Defaults to
    `true`.
  * `signal` {AbortSignal}: An AbortSignal that may be used to abort an ongoing
    request.
  * `socketPath` {string} Unix domain socket. Cannot be used if one of `host`
    or `port` is specified, as those specify a TCP Socket.
  * `timeout` {number}: A number specifying the socket timeout in milliseconds.
    This will set the timeout before the socket is connected.
  * `uniqueHeaders` {Array} A list of request headers that should be sent
    only once. If the header's value is an array, the items will be joined
    using `; `.
* `callback` {Function}
* Returns: {http.ClientRequest}

`options` in [`socket.connect()`][] are also supported.

Node.js maintains several connections per server to make HTTP requests.
This function allows one to transparently issue requests.

`url` can be a string or a [`URL`][] object. If `url` is a
string, it is automatically parsed with [`new URL()`][]. If it is a [`URL`][]
object, it will be automatically converted to an ordinary `options` object.

If both `url` and `options` are specified, the objects are merged, with the
`options` properties taking precedence.

The optional `callback` parameter will be added as a one-time listener for
the [`'response'`][] event.

`http.request()` returns an instance of the [`http.ClientRequest`][]
class. The `ClientRequest` instance is a writable stream. If one needs to
upload a file with a POST request, then write to the `ClientRequest` object.

```mjs
import http from 'node:http';
import { Buffer } from 'node:buffer';

const postData = JSON.stringify({
  'msg': 'Hello World!',
});

const options = {
  hostname: 'www.google.com',
  port: 80,
  path: '/upload',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(postData),
  },
};

const req = http.request(options, (res) => {
  console.log(`STATUS: ${res.statusCode}`);
  console.log(`HEADERS: ${JSON.stringify(res.headers)}`);
  res.setEncoding('utf8');
  res.on('data', (chunk) => {
    console.log(`BODY: ${chunk}`);
  });
  res.on('end', () => {
    console.log('No more data in response.');
  });
});

req.on('error', (e) => {
  console.error(`problem with request: ${e.message}`);
});

// Write data to request body
req.write(postData);
req.end();
```

```cjs
const http = require('node:http');

const postData = JSON.stringify({
  'msg': 'Hello World!',
});

const options = {
  hostname: 'www.google.com',
  port: 80,
  path: '/upload',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(postData),
  },
};

const req = http.request(options, (res) => {
  console.log(`STATUS: ${res.statusCode}`);
  console.log(`HEADERS: ${JSON.stringify(res.headers)}`);
  res.setEncoding('utf8');
  res.on('data', (chunk) => {
    console.log(`BODY: ${chunk}`);
  });
  res.on('end', () => {
    console.log('No more data in response.');
  });
});

req.on('error', (e) => {
  console.error(`problem with request: ${e.message}`);
});

// Write data to request body
req.write(postData);
req.end();
```

In the example `req.end()` was called. With `http.request()` one
must always call `req.end()` to signify the end of the request -
even if there is no data being written to the request body.

If any error is encountered during the request (be that with DNS resolution,
TCP level errors, or actual HTTP parse errors) an `'error'` event is emitted
on the returned request object. As with all `'error'` events, if no listeners
are registered the error will be thrown.

There are a few special headers that should be noted.

* Sending a 'Connection: keep-alive' will notify Node.js that the connection to
  the server should be persisted until the next request.

* Sending a 'Content-Length' header will disable the default chunked encoding.

* Sending an 'Expect' header will immediately send the request headers.
  Usually, when sending 'Expect: 100-continue', both a timeout and a listener
  for the `'continue'` event should be set. See RFC 2616 Section 8.2.3 for more
  information.

* Sending an Authorization header will override using the `auth` option
  to compute basic authentication.

Example using a [`URL`][] as `options`:

```js
const options = new URL('http://abc:xyz@example.com');

const req = http.request(options, (res) => {
  // ...
});
```

In a successful request, the following events will be emitted in the following
order:

* `'socket'`
* `'response'`
  * `'data'` any number of times, on the `res` object
    (`'data'` will not be emitted at all if the response body is empty, for
    instance, in most redirects)
  * `'end'` on the `res` object
* `'close'`

In the case of a connection error, the following events will be emitted:

* `'socket'`
* `'error'`
* `'close'`

In the case of a premature connection close before the response is received,
the following events will be emitted in the following order:

* `'socket'`
* `'error'` with an error with message `'Error: socket hang up'` and code
  `'ECONNRESET'`
* `'close'`

In the case of a premature connection close after the response is received,
the following events will be emitted in the following order:

* `'socket'`
* `'response'`
  * `'data'` any number of times, on the `res` object
* (connection closed here)
* `'aborted'` on the `res` object
* `'close'`
* `'error'` on the `res` object with an error with message
  `'Error: aborted'` and code `'ECONNRESET'`
* `'close'` on the `res` object

If `req.destroy()` is called before a socket is assigned, the following
events will be emitted in the following order:

* (`req.destroy()` called here)
* `'error'` with an error with message `'Error: socket hang up'` and code
  `'ECONNRESET'`, or the error with which `req.destroy()` was called
* `'close'`

If `req.destroy()` is called before the connection succeeds, the following
events will be emitted in the following order:

* `'socket'`
* (`req.destroy()` called here)
* `'error'` with an error with message `'Error: socket hang up'` and code
  `'ECONNRESET'`, or the error with which `req.destroy()` was called
* `'close'`

If `req.destroy()` is called after the response is received, the following
events will be emitted in the following order:

* `'socket'`
* `'response'`
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
