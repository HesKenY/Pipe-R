export function render(container, context) {
  const STORE_KEY = 'revv_messaging';
  const currentUser = context?.user?.name || 'You';

  function getData() {
    const stored = localStorage.getItem(STORE_KEY);
    if (stored) return JSON.parse(stored);
    // Seed sample threads
    const seed = {
      activeThread: 'thread1',
      threads: [
        {
          id: 'thread1', name: 'Job Site Alpha', lastMsg: 'Pipe delivery at 8am',
          messages: [
            { id: 1, sender: 'Mike R.', text: 'Hey, what time is the pipe delivery?', time: '2026-04-07T07:30:00' },
            { id: 2, sender: currentUser, text: 'Should be around 8am. I confirmed with the supplier.', time: '2026-04-07T07:32:00' },
            { id: 3, sender: 'Mike R.', text: 'Perfect, I\'ll have the crew ready at the loading dock.', time: '2026-04-07T07:33:00' }
          ]
        },
        {
          id: 'thread2', name: 'Safety Team', lastMsg: 'JSA updated for Building C',
          messages: [
            { id: 1, sender: 'Sarah K.', text: 'I updated the JSA for Building C. Please review.', time: '2026-04-07T06:00:00' },
            { id: 2, sender: 'Tom B.', text: 'Looks good. Added a note about the scaffolding.', time: '2026-04-07T06:15:00' },
            { id: 3, sender: currentUser, text: 'Approved. Let\'s brief the crew at morning huddle.', time: '2026-04-07T06:20:00' }
          ]
        },
        {
          id: 'thread3', name: 'Foreman Chat', lastMsg: 'OT approved for Friday',
          messages: [
            { id: 1, sender: currentUser, text: 'Need 4 guys for overtime Friday. Who\'s available?', time: '2026-04-06T14:00:00' },
            { id: 2, sender: 'Dave L.', text: 'I can stay. Put me down.', time: '2026-04-06T14:05:00' },
            { id: 3, sender: 'Chris M.', text: 'Same here. Full day or half?', time: '2026-04-06T14:10:00' }
          ]
        }
      ]
    };
    localStorage.setItem(STORE_KEY, JSON.stringify(seed));
    return seed;
  }

  function saveData(d) { localStorage.setItem(STORE_KEY, JSON.stringify(d)); }

  container.innerHTML = `
    <style>
      .msg-wrap { display: flex; height: calc(100vh - 120px); max-width: 960px; margin: 0 auto; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); overflow: hidden; }
      @media (max-width: 640px) { .msg-wrap { flex-direction: column; height: auto; } .msg-sidebar { max-height: 180px; overflow-y: auto; min-width: unset !important; border-right: none !important; border-bottom: 1px solid var(--border, #333); } }
      .msg-sidebar { min-width: 240px; max-width: 240px; background: var(--bg-secondary, #1e1e2e); border-radius: 12px 0 0 12px; border-right: 1px solid var(--border, #333); overflow-y: auto; }
      .msg-sidebar-title { padding: 16px; font-weight: 700; font-size: 1rem; border-bottom: 1px solid var(--border, #333); }
      .msg-thread { padding: 14px 16px; cursor: pointer; border-bottom: 1px solid var(--border, #222); transition: background 0.15s; }
      .msg-thread:hover { background: var(--bg-primary, #12121a); }
      .msg-thread.active { background: var(--accent, #60a5fa); color: #fff; }
      .msg-thread-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
      .msg-thread-preview { font-size: 0.75rem; color: var(--text-secondary, #888); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .msg-thread.active .msg-thread-preview { color: rgba(255,255,255,0.7); }
      .msg-main { flex: 1; display: flex; flex-direction: column; background: var(--bg-secondary, #1e1e2e); border-radius: 0 12px 12px 0; }
      .msg-header { padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border, #333); font-size: 1rem; }
      .msg-body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
      .msg-bubble { max-width: 75%; padding: 10px 14px; border-radius: 16px; font-size: 0.9rem; line-height: 1.4; }
      .msg-bubble.sent { align-self: flex-end; background: var(--accent, #60a5fa); color: #fff; border-bottom-right-radius: 4px; }
      .msg-bubble.received { align-self: flex-start; background: var(--bg-primary, #12121a); border-bottom-left-radius: 4px; }
      .msg-bubble-sender { font-size: 0.7rem; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary, #888); }
      .msg-bubble.sent .msg-bubble-sender { color: rgba(255,255,255,0.7); }
      .msg-bubble-time { font-size: 0.65rem; margin-top: 4px; opacity: 0.6; }
      .msg-input-row { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--border, #333); }
      .msg-input { flex: 1; padding: 12px; border-radius: 24px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; min-height: 48px; box-sizing: border-box; }
      .msg-send-btn { padding: 12px 20px; border: none; border-radius: 24px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
    </style>
    <div class="msg-wrap">
      <div class="msg-sidebar">
        <div class="msg-sidebar-title">Messages</div>
        <div id="msg-thread-list"></div>
      </div>
      <div class="msg-main">
        <div class="msg-header" id="msg-header">Select a thread</div>
        <div class="msg-body" id="msg-body"></div>
        <div class="msg-input-row">
          <input class="msg-input" id="msg-input" placeholder="Type a message...">
          <button class="msg-send-btn" id="msg-send-btn">Send</button>
        </div>
      </div>
    </div>
  `;

  const threadList = container.querySelector('#msg-thread-list');
  const msgHeader = container.querySelector('#msg-header');
  const msgBody = container.querySelector('#msg-body');
  const msgInput = container.querySelector('#msg-input');
  const sendBtn = container.querySelector('#msg-send-btn');

  function fmtTime(iso) {
    return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }

  function renderThreads() {
    const data = getData();
    threadList.innerHTML = data.threads.map(t => `
      <div class="msg-thread ${t.id === data.activeThread ? 'active' : ''}" data-tid="${t.id}">
        <div class="msg-thread-name">${t.name}</div>
        <div class="msg-thread-preview">${t.lastMsg}</div>
      </div>
    `).join('');

    threadList.querySelectorAll('.msg-thread').forEach(el => {
      el.addEventListener('click', () => {
        const data = getData();
        data.activeThread = el.dataset.tid;
        saveData(data);
        renderThreads();
        renderMessages();
      });
    });
  }

  function renderMessages() {
    const data = getData();
    const thread = data.threads.find(t => t.id === data.activeThread);
    if (!thread) { msgBody.innerHTML = ''; msgHeader.textContent = 'Select a thread'; return; }
    msgHeader.textContent = thread.name;
    msgBody.innerHTML = thread.messages.map(m => {
      const isSent = m.sender === currentUser;
      return `
        <div class="msg-bubble ${isSent ? 'sent' : 'received'}">
          <div class="msg-bubble-sender">${m.sender}</div>
          <div>${m.text}</div>
          <div class="msg-bubble-time">${fmtTime(m.time)}</div>
        </div>
      `;
    }).join('');
    msgBody.scrollTop = msgBody.scrollHeight;
  }

  function sendMessage() {
    const text = msgInput.value.trim();
    if (!text) return;
    const data = getData();
    const thread = data.threads.find(t => t.id === data.activeThread);
    if (!thread) return;
    thread.messages.push({
      id: Date.now(),
      sender: currentUser,
      text,
      time: new Date().toISOString()
    });
    thread.lastMsg = text;
    saveData(data);
    msgInput.value = '';
    renderThreads();
    renderMessages();
  }

  sendBtn.addEventListener('click', sendMessage);
  msgInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });

  renderThreads();
  renderMessages();
}

export const meta = { id: 'messaging', name: 'Messaging', icon: '\uD83D\uDCAC', navLabel: 'Messages' };
