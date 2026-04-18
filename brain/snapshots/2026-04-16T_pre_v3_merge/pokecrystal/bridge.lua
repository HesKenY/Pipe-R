-- mGBA TCP bridge for Pokemon Crystal AI agent.
-- Load in mGBA: Tools > Scripting > Load script.
-- Agent connects on 127.0.0.1:8888 and sends newline-delimited commands:
--   ping                 -> pong
--   r8 <hex_addr>        -> <byte as 2-hex>
--   r <hex_addr> <n>     -> <n bytes as hex blob>
--   press <btn> [frames] -> ok     (btn: a|b|select|start|up|down|left|right)
--   release <btn>        -> ok
--   clear                -> ok     (release all held buttons)

local PORT = 8888

local BUTTONS = {
	a = 0, b = 1, select = 2, start = 3,
	right = 4, left = 5, up = 6, down = 7,
}

local server = nil
local clients = {}
local holds = {}  -- [buttonIdx] = framesRemaining

local function log(msg)
	if console and console.log then
		console:log("[pokebridge] " .. msg)
	end
end

local function hex2(n)
	return string.format("%02x", n & 0xFF)
end

local function handleCommand(line)
	line = line:gsub("^%s+", ""):gsub("%s+$", "")
	if #line == 0 then return "\n" end

	local cmd, rest = line:match("^(%S+)%s*(.*)$")
	cmd = (cmd or ""):lower()
	rest = rest or ""

	if cmd == "ping" then
		return "pong\n"

	elseif cmd == "r8" then
		local addr = tonumber(rest, 16)
		if not addr then return "err bad_addr\n" end
		return hex2(emu:read8(addr)) .. "\n"

	elseif cmd == "r" then
		local a, n = rest:match("^(%x+)%s+(%d+)$")
		if not a then return "err bad_range\n" end
		local addr, count = tonumber(a, 16), tonumber(n)
		local parts = {}
		for i = 0, count - 1 do
			parts[#parts + 1] = hex2(emu:read8(addr + i))
		end
		return table.concat(parts) .. "\n"

	elseif cmd == "press" then
		local btn, framesStr = rest:match("^(%S+)%s*(%d*)$")
		local idx = BUTTONS[(btn or ""):lower()]
		if not idx then return "err bad_button\n" end
		local frames = tonumber(framesStr)
		if not frames or frames <= 0 then frames = 6 end
		emu:addKey(idx)
		holds[idx] = frames
		return "ok\n"

	elseif cmd == "release" then
		local idx = BUTTONS[rest:lower()]
		if idx then
			emu:clearKey(idx)
			holds[idx] = nil
		end
		return "ok\n"

	elseif cmd == "clear" then
		for i = 0, 7 do emu:clearKey(i) end
		holds = {}
		return "ok\n"
	end

	return "err unknown_cmd\n"
end

local function dropClient(client)
	for i, c in ipairs(clients) do
		if c == client then table.remove(clients, i) break end
	end
	pcall(function() client:close() end)
end

local function onClientData(client)
	while true do
		local data, err = client:receive(4096)
		if not data or #data == 0 then
			if err and err ~= "again" then dropClient(client) end
			return
		end
		-- buffer and parse by newline
		client._buf = (client._buf or "") .. data
		while true do
			local nl = client._buf:find("\n")
			if not nl then break end
			local line = client._buf:sub(1, nl - 1)
			client._buf = client._buf:sub(nl + 1)
			local reply = handleCommand(line)
			client:send(reply)
		end
	end
end

local function onServerAccept()
	local client = server:accept()
	if not client then return end
	client._buf = ""
	table.insert(clients, client)
	client:add("received", function() onClientData(client) end)
	client:add("error", function() dropClient(client) end)
	log("client connected (" .. #clients .. " total)")
end

local function onFrame()
	for idx, frames in pairs(holds) do
		frames = frames - 1
		if frames <= 0 then
			emu:clearKey(idx)
			holds[idx] = nil
		else
			holds[idx] = frames
		end
	end
end

server = socket.bind(nil, PORT)
if not server then
	log("failed to bind 127.0.0.1:" .. PORT)
	return
end
server:listen()
server:add("received", onServerAccept)
callbacks:add("frame", onFrame)
log("listening on 127.0.0.1:" .. PORT)
