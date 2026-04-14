/* shared ollama spawner for halo-trainer.

   bypasses the orchestrator — drills go directly to the
   model with a minimal SYSTEM-free prompt so the response
   stays focused on the curriculum instead of drifting into
   the agent's generic role persona. */

import { spawnSync } from 'node:child_process';

function stripAnsi(s) {
  return String(s || '')
    .replace(/\u001b\[\??[0-9;]*[a-zA-Z]/g, '')
    .replace(/\u001b\][^\u0007]*\u0007/g, '');
}

export function askModel(model, prompt, opts = {}) {
  const started = Date.now();
  const res = spawnSync('ollama', ['run', model], {
    input: prompt,
    encoding: 'utf8',
    timeout: opts.timeoutMs || 120000,
    maxBuffer: 8 * 1024 * 1024,
    windowsHide: true,
  });
  const elapsed = Date.now() - started;
  if (res.status !== 0) {
    return {
      ok: false,
      elapsed,
      error: 'exit ' + res.status,
      stderr: (res.stderr || '').slice(0, 400),
      text: '',
    };
  }
  return {
    ok: true,
    elapsed,
    text: stripAnsi(res.stdout || '').trim(),
  };
}
