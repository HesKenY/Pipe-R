export function render(container, context) {
  const STORE_KEY = 'revv_tasklist';
  const getTasks = () => JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
  const saveTasks = (t) => localStorage.setItem(STORE_KEY, JSON.stringify(t));

  const COLUMNS = ['todo', 'inprogress', 'done'];
  const COL_LABELS = { todo: 'To Do', inprogress: 'In Progress', done: 'Done' };
  const COL_COLORS = { todo: '#60a5fa', inprogress: '#f59e0b', done: '#22c55e' };
  const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent'];
  const PRI_COLORS = { Low: '#22c55e', Medium: '#f59e0b', High: '#f97316', Urgent: '#ef4444' };

  container.innerHTML = `
    <style>
      .tk-wrap { max-width: 960px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .tk-add-card { background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
      .tk-add-row { display: flex; gap: 8px; flex-wrap: wrap; }
      .tk-input { padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; min-height: 48px; box-sizing: border-box; }
      .tk-input.title { flex: 2; min-width: 140px; }
      .tk-input.assignee { flex: 1; min-width: 100px; }
      .tk-select { padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; min-height: 48px; }
      .tk-add-btn { padding: 12px 20px; border: none; border-radius: 8px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .tk-board { display: flex; gap: 12px; overflow-x: auto; }
      @media (max-width: 640px) { .tk-board { flex-direction: column; } }
      .tk-col { flex: 1; min-width: 240px; background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 12px; }
      .tk-col-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid var(--border, #333); }
      .tk-col-title { font-weight: 700; font-size: 0.9rem; }
      .tk-col-count { background: var(--bg-primary, #12121a); padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
      .tk-task { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 12px; margin-bottom: 8px; border-left: 3px solid; }
      .tk-task-title { font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; }
      .tk-task-meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: var(--text-secondary, #888); }
      .tk-task-pri { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.7rem; color: #fff; }
      .tk-task-actions { display: flex; gap: 4px; margin-top: 8px; }
      .tk-move-btn { padding: 6px 10px; border: 1px solid var(--border, #333); border-radius: 6px; background: transparent; color: var(--text-secondary, #888); cursor: pointer; font-size: 0.75rem; min-height: 32px; }
      .tk-move-btn:hover { background: var(--bg-secondary, #1e1e2e); color: var(--text-primary, #e0e0e0); }
      .tk-del-btn { padding: 6px 10px; border: 1px solid #ef4444; border-radius: 6px; background: transparent; color: #ef4444; cursor: pointer; font-size: 0.75rem; min-height: 32px; }
    </style>
    <div class="tk-wrap">
      <div class="tk-add-card">
        <div class="tk-add-row">
          <input class="tk-input title" id="tk-title" placeholder="Task title...">
          <input class="tk-input assignee" id="tk-assignee" placeholder="Assignee">
          <select class="tk-select" id="tk-priority">
            ${PRIORITIES.map(p => `<option value="${p}">${p}</option>`).join('')}
          </select>
          <button class="tk-add-btn" id="tk-add-btn">+ Add Task</button>
        </div>
      </div>
      <div class="tk-board" id="tk-board"></div>
    </div>
  `;

  const board = container.querySelector('#tk-board');

  function renderBoard() {
    const tasks = getTasks();
    board.innerHTML = COLUMNS.map(col => {
      const colTasks = tasks.filter(t => t.status === col);
      return `
        <div class="tk-col">
          <div class="tk-col-header">
            <span class="tk-col-title" style="color:${COL_COLORS[col]}">${COL_LABELS[col]}</span>
            <span class="tk-col-count">${colTasks.length}</span>
          </div>
          ${colTasks.map(t => {
            const colIdx = COLUMNS.indexOf(col);
            const canLeft = colIdx > 0;
            const canRight = colIdx < COLUMNS.length - 1;
            return `
              <div class="tk-task" style="border-left-color:${PRI_COLORS[t.priority] || '#60a5fa'}">
                <div class="tk-task-title">${escHtml(t.title)}</div>
                <div class="tk-task-meta">
                  <span>${escHtml(t.assignee || 'Unassigned')}</span>
                  <span class="tk-task-pri" style="background:${PRI_COLORS[t.priority]}">${t.priority}</span>
                </div>
                <div class="tk-task-actions">
                  ${canLeft ? `<button class="tk-move-btn" data-id="${t.id}" data-dir="left">&larr; ${COL_LABELS[COLUMNS[colIdx - 1]]}</button>` : ''}
                  ${canRight ? `<button class="tk-move-btn" data-id="${t.id}" data-dir="right">${COL_LABELS[COLUMNS[colIdx + 1]]} &rarr;</button>` : ''}
                  <button class="tk-del-btn" data-id="${t.id}" data-action="delete">X</button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }).join('');

    board.querySelectorAll('.tk-move-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tasks = getTasks();
        const task = tasks.find(t => t.id === parseInt(btn.dataset.id));
        if (!task) return;
        const idx = COLUMNS.indexOf(task.status);
        if (btn.dataset.dir === 'left' && idx > 0) task.status = COLUMNS[idx - 1];
        if (btn.dataset.dir === 'right' && idx < COLUMNS.length - 1) task.status = COLUMNS[idx + 1];
        saveTasks(tasks);
        renderBoard();
      });
    });

    board.querySelectorAll('.tk-del-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        let tasks = getTasks();
        tasks = tasks.filter(t => t.id !== parseInt(btn.dataset.id));
        saveTasks(tasks);
        renderBoard();
      });
    });
  }

  function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  container.querySelector('#tk-add-btn').addEventListener('click', () => {
    const title = container.querySelector('#tk-title').value.trim();
    if (!title) return;
    const tasks = getTasks();
    tasks.push({
      id: Date.now(),
      title,
      assignee: container.querySelector('#tk-assignee').value.trim(),
      priority: container.querySelector('#tk-priority').value,
      status: 'todo',
      created: new Date().toISOString()
    });
    saveTasks(tasks);
    container.querySelector('#tk-title').value = '';
    container.querySelector('#tk-assignee').value = '';
    renderBoard();
  });

  renderBoard();
}

export const meta = { id: 'tasklist', name: 'Task Board', icon: '\uD83D\uDCCB', navLabel: 'Tasks' };
