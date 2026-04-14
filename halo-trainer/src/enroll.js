/* enroll — health-check every student model.

   fires a trivial prompt at each student (name yourself +
   echo a short phrase). confirms the model exists, is
   loadable, and responds. prints a roll call.

   use this before a long drill pass so you don't waste 10
   minutes running drills against a broken model. */

import { askModel } from '../tools/ollama.js';
import { STUDENTS, TRAINER, TUTOR } from './registry.js';

const HEALTH_PROMPT =
  'echo this exact line and nothing else: "ready for drills"';

export async function enrollAll() {
  const roster = [TRAINER, ...STUDENTS, TUTOR];
  const results = [];
  for (const a of roster) {
    const r = askModel(a.id, HEALTH_PROMPT, { timeoutMs: 45000 });
    const ok = r.ok && r.text && /ready for drills/i.test(r.text);
    results.push({
      id: a.id,
      role: a.role || a.track || '',
      ok,
      elapsedMs: r.elapsed,
      snippet: (r.text || '').slice(0, 60).replace(/\n/g, ' '),
      error: r.error || null,
    });
    const mark = ok ? '✓' : '✗';
    console.log(`${mark} ${a.id.padEnd(32)} ${(r.elapsed/1000).toFixed(1).padStart(6)}s  ${(r.text||'').slice(0,60).replace(/\n/g,' ')}`);
  }
  const ready = results.filter(r => r.ok).length;
  console.log(`\nroll call: ${ready}/${results.length} ready`);
  return results;
}

const _entry = process.argv[1] || '';
if (import.meta.url.endsWith('/enroll.js') && _entry.endsWith('enroll.js')) {
  enrollAll().catch(e => { console.error(e); process.exit(1); });
}
