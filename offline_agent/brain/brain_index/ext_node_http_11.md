# Node.js http (11/11)
source: https://github.com/nodejs/node/blob/main/doc/api/http.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
es.statusCode}`);
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

[Built-in Proxy Support]: #built-in-proxy-support
[RFC 8187]: https://www.rfc-editor.org/rfc/rfc8187.txt
[RFC 9110 Section 6.6.1]: https://www.rfc-editor.org/rfc/rfc9110#section-6.6.1
[`'ERR_HTTP_CONTENT_LENGTH_MISMATCH'`]: errors.md#err_http_content_length_mismatch
[`'checkContinue'`]: #event-checkcontinue
[`'finish'`]: #event-finish
[`'request'`]: #event-request
[`'response'`]: #event-response
[`'upgrade'`]: #event-upgrade
[`--insecure-http-parser`]: cli.md#--insecure-http-parser
[`--max-http-header-size`]: cli.md#--max-http-header-sizesize
[`Agent`]: #class-httpagent
[`Buffer.byteLength()`]: buffer.md#static-method-bufferbytelengthstring-encoding
[`Duplex`]: stream.md#class-streamduplex
[`HPE_HEADER_OVERFLOW`]: errors.md#hpe_header_overflow
[`Headers`]: globals.md#class-headers
[`TypeError`]: errors.md#class-typeerror
[`URL`]: url.md#the-whatwg-url-api
[`agent.createConnection()`]: #agentcreateconnectionoptions-callback
[`agent.getName()`]: #agentgetnameoptions
[`destroy()`]: #agentdestroy
[`dns.lookup()`]: dns.md#dnslookuphostname-options-callback
[`dns.lookup()` hints]: dns.md#supported-getaddrinfo-flags
[`getHeader(name)`]: #requestgetheadername
[`http.Agent`]: #class-httpagent
[`http.ClientRequest`]: #class-httpclientrequest
[`http.IncomingMessage`]: #class-httpincomingmessage
[`http.ServerResponse`]: #class-httpserverresponse
[`http.Server`]: #class-httpserver
[`http.createServer()`]: #httpcreateserveroptions-requestlistener
[`http.get()`]: #httpgetoptions-callback
[`http.globalAgent`]: #httpglobalagent
[`http.request()`]: #httprequestoptions-callback
[`http.setGlobalProxyFromEnv()`]: #httpsetglobalproxyfromenvproxyenv
[`message.headers`]: #messageheaders
[`message.rawHeaders`]: #messagerawheaders
[`message.socket`]: #messagesocket
[`message.trailers`]: #messagetrailers
[`net.Server.close()`]: net.md#serverclosecallback
[`net.Server`]: net.md#class-netserver
[`net.Socket`]: net.md#class-netsocket
[`net.createConnection()`]: net.md#netcreateconnectionoptions-connectlistener
[`new URL()`]: url.md#new-urlinput-base
[`outgoingMessage.setHeader(name, value)`]: #outgoingmessagesetheadername-value
[`outgoingMessage.setHeaders()`]: #outgoingmessagesetheadersheaders
[`outgoingMessage.socket`]: #outgoingmessagesocket
[`removeHeader(name)`]: #requestremoveheadername
[`request.destroy()`]: #requestdestroyerror
[`request.destroyed`]: #requestdestroyed
[`request.end()`]: #requestenddata-encoding-callback
[`request.flushHeaders()`]: #requestflushheaders
[`request.getHeader()`]: #requestgetheadername
[`request.setHeader()`]: #requestsetheadername-value
[`request.setTimeout()`]: #requestsettimeouttimeout-callback
[`request.socket.getPeerCertificate()`]: tls.md#tlssocketgetpeercertificatedetailed
[`request.socket`]: #requestsocket
[`request.writableEnded`]: #requestwritableended
[`request.writableFinished`]: #requestwritablefinished
[`request.write(data, encoding)`]: #requestwritechunk-encoding-callback
[`response.end()`]: #responseenddata-encoding-callback
[`response.getHeader()`]: #responsegetheadername
[`response.setHeader()`]: #responsesetheadername-value
[`response.socket`]: #responsesocket
[`response.strictContentLength`]: #responsestrictcontentlength
[`response.writableEnded`]: #responsewritableended
[`response.writableFinished`]: #responsewritablefinished
[`response.write()`]: #responsewritechunk-encoding-callback
[`response.write(data, encoding)`]: #responsewritechunk-encoding-callback
[`response.writeContinue()`]: #responsewritecontinue
[`response.writeHead()`]: #responsewriteheadstatuscode-statusmessage-headers
[`server.close()`]: #serverclosecallback
[`server.headersTimeout`]: #serverheaderstimeout
[`server.keepAliveTimeoutBuffer`]: #serverkeepalivetimeoutbuffer
[`server.keepAliveTimeout`]: #serverkeepalivetimeout
[`server.listen()`]: net.md#serverlisten
[`server.requestTimeout`]: #serverrequesttimeout
[`server.timeout`]: #servertimeout
[`setHeader(name, value)`]: #requestsetheadername-value
[`socket.connect()`]: net.md#socketconnectoptions-connectlistener
[`socket.setKeepAlive()`]: net.md#socketsetkeepaliveenable-initialdelay
[`socket.setNoDelay()`]: net.md#socketsetnodelaynodelay
[`socket.setTimeout()`]: net.md#socketsettimeouttimeout-callback
[`socket.unref()`]: net.md#socketunref
[`stream.getDefaultHighWaterMark()`]: stream.md#streamgetdefaulthighwatermarkobjectmode
[`url.parse()`]: url.md#urlparseurlstring-parsequerystring-slashesdenotehost
[`writable.cork()`]: stream.md#writablecork
[`writable.destroy()`]: stream.md#writabledestroyerror
[`writable.destroyed`]: stream.md#writabledestroyed
[`writable.uncork()`]: stream.md#writableuncork
[`writable.write()`]: stream.md#writablewritechunk-encoding-callback
[initial delay]: net.md#socketsetkeepaliveenable-initialdelay
