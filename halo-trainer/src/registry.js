/* who is enrolled in the classroom.
   trainer = the student we build toward.
   students = do the drills.
   tutor    = observes + re-tunes prompts. */

export const TRAINER = {
  id: 'kenai:v1',
  displayName: 'Ken AI',
  role: 'trainer',
};

export const STUDENTS = [
  {
    id: 'cherp-piper:latest',
    displayName: 'D3c1du3y3 Pathfinder',
    track: 'recon',
    strengths: ['memory mapping', 'file tree walks', 'delta scan design'],
  },
  {
    id: 'qwen2.5-coder:14b',
    displayName: '5c1z0r Patchsmith',
    track: 'implementation',
    strengths: ['ctypes', 'python', 'rust hunters', 'AOB scanning code'],
  },
  {
    id: 'forgeagent:latest',
    displayName: 'R0t0m Relay',
    track: 'integration',
    strengths: ['stitching modules', 'runtime wiring', 'daemon orchestration'],
  },
  {
    id: 'llama3.1:8b',
    displayName: 'P0ryg0n Logdex',
    track: 'observability',
    strengths: ['HUD reading', 'log summarization', 'scoring engagements'],
  },
  {
    id: 'jefferyjefferferson:latest',
    displayName: 'Umbr30n Safeguard',
    track: 'quality',
    strengths: ['verifying writes', 'god-mode confirmation', 'edge cases'],
  },
];

export const TUTOR = {
  id: 'm3w-learning:latest',
  displayName: 'M3w Promptdex',
  role: 'tutor',
};

export function all() {
  return [TRAINER, ...STUDENTS, TUTOR];
}

export function byId(id) {
  return all().find(a => a.id === id) || null;
}

export function studentsForTrack(track) {
  return STUDENTS.filter(s => s.track === track);
}
