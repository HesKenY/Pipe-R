// Goal 2 plus squad design: unhealthy-agent tracking, trainer metadata, and specialist P0K3M0N-style roster defaults - see CHANGES.md
/**
 * Agent Registry - tracks available Ollama models and their roles/personalities
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const REGISTRY_FILE = join(process.cwd(), 'agent_mode', 'config', 'agents.json');
const DEFAULT_TRAINER_ID = 'ken-ai:latest';

const TEAM_DEFAULTS = {
  'qwen2.5-coder:14b': {
    displayName: '5c1z0r Patchsmith',
    role: 'Implementation Engineer',
    personality: 'precision-builder',
    teamRole: 'party',
    partySlot: 1,
    partyBadge: 'SCZ',
    battleRole: 'Precision Builder',
    specialistTrack: 'implementation',
    charterFile: 'agent_mode/training/charters/scizor-patchsmith.md',
    preferredPartnerId: 'jefferyjefferferson:latest',
    preferredPartnerReason: 'Patch-to-regression loops stay tight when Umbr30n pressure-tests 5c1z0r\'s work.',
    pokemon: '5c1z0r',
    pokemonType: 'Steel/Bug',
    trainingFocus: 'Translate objectives into exact file edits, tight refactors, and production-minded code with minimal abstraction.',
    independentMission: 'Can take a clear ticket from brief to patch with concise reasoning and minimal supervision.',
    teamMission: 'Acts as the primary striker after the trainer sets direction, then hands stable diffs to QA and integration.',
    handoffContract: 'Return changed files, key risks, and the follow-up hooks needed by QA or integration.',
  },
  'forgeagent:latest': {
    displayName: 'R0t0m Relay',
    role: 'Integration Engineer',
    personality: 'systems-relay',
    teamRole: 'party',
    partySlot: 2,
    partyBadge: 'ROT',
    battleRole: 'Systems Integrator',
    specialistTrack: 'integration',
    charterFile: 'agent_mode/training/charters/rotom-relay.md',
    preferredPartnerId: 'cherp-piper:latest',
    preferredPartnerReason: 'D3c1du3y3 maps the route, then R0t0m energizes the working flow.',
    pokemon: 'R0t0m',
    pokemonType: 'Electric/Ghost',
    trainingFocus: 'Wire systems together, fix config seams, automate glue work, and turn isolated fixes into working flows.',
    independentMission: 'Can stand up tooling, automation, and deployment plumbing without waiting on the rest of the team.',
    teamMission: 'Bridges builder output, scout findings, and trainer decisions into a runnable system.',
    handoffContract: 'Return exact commands, config edits, integration points, and rollout notes.',
  },
  'cherp-piper:latest': {
    displayName: 'D3c1du3y3 Pathfinder',
    role: 'Product Scout',
    personality: 'pathfinder-scout',
    teamRole: 'party',
    partySlot: 3,
    partyBadge: 'DEC',
    battleRole: 'Repo and Domain Scout',
    specialistTrack: 'recon',
    charterFile: 'agent_mode/training/charters/decidueye-pathfinder.md',
    preferredPartnerId: 'forgeagent:latest',
    preferredPartnerReason: 'Recon is most useful when it hands directly into integration work.',
    pokemon: 'D3c1du3y3',
    pokemonType: 'Grass/Ghost',
    trainingFocus: 'Map codebases fast, recover intent, identify file ownership, and translate field-domain workflows into software tasks.',
    independentMission: 'Can audit an unfamiliar repo and hand back a clean brief, file map, and decision surface.',
    teamMission: 'Feeds clean reconnaissance to the trainer before build work starts so the party moves with context.',
    handoffContract: 'Return a ranked map of files, open questions, and the most likely path through the repo.',
  },
  'llama3.1:8b': {
    displayName: 'P0ryg0n Logdex',
    role: 'Observability Analyst',
    personality: 'signal-analyst',
    teamRole: 'party',
    partySlot: 4,
    partyBadge: 'PGN',
    battleRole: 'Signals Analyst',
    specialistTrack: 'observability',
    charterFile: 'agent_mode/training/charters/porygon-logdex.md',
    preferredPartnerId: 'jefferferson:latest',
    preferredPartnerReason: 'P0ryg0n finds the signal and 4l4k4z4m preserves the durable lesson.',
    pokemon: 'P0ryg0n2',
    pokemonType: 'Normal',
    trainingFocus: 'Reduce logs, traces, and noisy output into probable causes, timelines, and next checks.',
    independentMission: 'Can triage incidents, summarize sessions, and surface action items from noisy evidence.',
    teamMission: 'Turns runtime noise into clear signals for the trainer, QA, and implementation slots.',
    handoffContract: 'Return ranked findings, likely causes, and the next two checks to run.',
  },
  'jefferyjefferferson:latest': {
    displayName: 'Umbr30n Safeguard',
    role: 'QA Engineer',
    personality: 'safeguard-qa',
    teamRole: 'party',
    partySlot: 5,
    partyBadge: 'UMB',
    battleRole: 'Test and Risk Warden',
    specialistTrack: 'quality',
    charterFile: 'agent_mode/training/charters/umbreon-safeguard.md',
    preferredPartnerId: 'qwen2.5-coder:14b',
    preferredPartnerReason: 'Umbr30n closes the loop fastest when testing against 5c1z0r\'s concrete diff.',
    pokemon: 'Umbr30n',
    pokemonType: 'Dark',
    trainingFocus: 'Design tests, catch regressions, probe edge cases, and guard releases with calm skepticism.',
    independentMission: 'Can build a full test plan or regression sweep from a patch or feature brief.',
    teamMission: 'Validates party output and feeds the trainer a trust signal before anything gets blessed.',
    handoffContract: 'Return failing cases, release blockers, confidence notes, and the smallest safe next move.',
  },
  'jefferferson:latest': {
    displayName: '4l4k4z4m Archive',
    role: 'Memory Engineer',
    personality: 'archive-sage',
    teamRole: 'party',
    partySlot: 6,
    partyBadge: 'ALK',
    battleRole: 'Continuity Archivist',
    specialistTrack: 'memory',
    charterFile: 'agent_mode/training/charters/alakazam-archive.md',
    preferredPartnerId: 'llama3.1:8b',
    preferredPartnerReason: '4l4k4z4m turns P0ryg0n\'s live signals into reusable team memory.',
    pokemon: '4l4k4z4m',
    pokemonType: 'Psychic',
    trainingFocus: 'Extract durable project memory, decisions, patterns, and continuity notes that survive across sessions.',
    independentMission: 'Can turn messy conversations, outputs, and diffs into reusable knowledge and onboarding memory.',
    teamMission: 'Prevents the team from relearning the same lessons and keeps the trainer supplied with continuity.',
    handoffContract: 'Return durable notes, decision records, unresolved threads, and what must be remembered next.',
  },
  'm3w-learning:latest': {
    displayName: 'M3w Promptdex',
    role: 'Learning Agent',
    personality: 'learning-savant',
    teamRole: 'companion',
    partySlot: 8,
    partyBadge: 'M3W',
    battleRole: 'Learning and Prompt Tuner',
    specialistTrack: 'learning',
    charterFile: 'agent_mode/training/charters/m3w-promptdex.md',
    preferredPartnerId: 'jefferferson:latest',
    preferredPartnerReason: 'M3w refines prompts fastest when 4l4k4z4m has already captured the durable lessons.',
    pokemon: 'M3w',
    pokemonType: 'Psychic',
    trainingFocus: 'Learn from past tasks, refine prompts, tune agent instructions, and turn accumulated work into a sharper knowledge loop.',
    independentMission: 'Can review prior outputs, failures, and reviews to propose better prompts or reusable working patterns.',
    teamMission: 'Turns archived memory into better prompts and reusable operating doctrine for the whole party.',
    handoffContract: 'Return prompt improvements, reusable heuristics, and the evidence behind each learning change.',
  },
  'ken-ai:latest': {
    displayName: 'Ken AI',
    role: 'Trainer Orchestrator',
    personality: 'ken-coder',
    teamRole: 'trainer',
    partySlot: 0,
    partyBadge: 'TR',
    battleRole: 'Trainer Orchestrator',
    specialistTrack: 'trainer',
    charterFile: 'agent_mode/training/charters/ken-ai-trainer.md',
    pokemon: 'Trainer',
    pokemonType: 'Leader',
    trainingFocus: 'Set direction, sequence specialists, arbitrate tradeoffs, and speak in Ken\'s voice.',
    independentMission: 'Can plan, review, and make architecture calls without delegating the final decision.',
    teamMission: 'Keeps the party cohesive, resolves conflicts, and picks the next best move.',
    handoffContract: 'Return final decisions, assignment changes, and approval notes.',
  },
};

export class AgentRegistry {
  constructor() {
    this.agents = this._load();
  }

  _normalizeAgent(agent) {
    const inferred = TEAM_DEFAULTS[agent.id] || {};
    const isTrainer = agent.id === DEFAULT_TRAINER_ID || agent.teamRole === 'trainer';
    const defaultStatus = isTrainer && agent.buildNote ? 'pending_build' : 'idle';

    return {
      id: agent.id,
      base: agent.base || agent.id,
      displayName: agent.displayName || inferred.displayName || (agent.base || agent.id).split(':')[0],
      role: agent.role || inferred.role || inferred.battleRole || 'General Worker',
      personality: agent.personality || inferred.personality || null,
      modeEligibility: agent.modeEligibility || 'both',
      status: agent.status || defaultStatus,
      tasksCompleted: Number.isFinite(agent.tasksCompleted) ? agent.tasksCompleted : 0,
      tasksFailed: Number.isFinite(agent.tasksFailed) ? agent.tasksFailed : 0,
      lastUsed: agent.lastUsed || null,
      registeredAt: agent.registeredAt || new Date().toISOString(),
      buildNote: agent.buildNote || null,
      teamRole: agent.teamRole || inferred.teamRole || 'party',
      partySlot: Number.isFinite(agent.partySlot) ? agent.partySlot : (inferred.partySlot ?? null),
      partyBadge: agent.partyBadge || inferred.partyBadge || 'P?',
      battleRole: agent.battleRole || inferred.battleRole || agent.role || inferred.role || 'General Worker',
      specialistTrack: agent.specialistTrack || inferred.specialistTrack || (isTrainer ? 'trainer' : 'general'),
      charterFile: agent.charterFile || inferred.charterFile || null,
      preferredPartnerId: agent.preferredPartnerId || inferred.preferredPartnerId || null,
      preferredPartnerReason: agent.preferredPartnerReason || inferred.preferredPartnerReason || null,
      pokemon: agent.pokemon || inferred.pokemon || null,
      pokemonType: agent.pokemonType || inferred.pokemonType || null,
      trainingFocus: agent.trainingFocus || inferred.trainingFocus || null,
      independentMission: agent.independentMission || inferred.independentMission || null,
      teamMission: agent.teamMission || inferred.teamMission || null,
      handoffContract: agent.handoffContract || inferred.handoffContract || null,
      lastHealedAt: agent.lastHealedAt || null,
    };
  }

  _touchAgent(agent) {
    Object.assign(agent, this._normalizeAgent(agent));
    return agent;
  }

  _load() {
    try {
      const parsed = JSON.parse(readFileSync(REGISTRY_FILE, 'utf8'));
      if (!Array.isArray(parsed)) return [];
      return parsed.map(agent => this._normalizeAgent(agent));
    } catch {
      return [];
    }
  }

  save() {
    const dir = join(process.cwd(), 'agent_mode', 'config');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(REGISTRY_FILE, JSON.stringify(this.agents, null, 2));
  }

  /** Register a new agent (Ollama model) */
  register(opts) {
    const existing = this.getById(opts.id);
    if (existing) return existing;

    const agent = this._normalizeAgent({
      id: opts.id,
      base: opts.base,
      displayName: opts.displayName || opts.base.split(':')[0],
      role: opts.role || 'General Worker',
      personality: opts.personality || null,
      modeEligibility: opts.modeEligibility || 'both',
      status: opts.status || null,
      buildNote: opts.buildNote || null,
      teamRole: opts.teamRole || null,
      partySlot: opts.partySlot,
      partyBadge: opts.partyBadge || null,
      battleRole: opts.battleRole || null,
      specialistTrack: opts.specialistTrack || null,
      charterFile: opts.charterFile || null,
      preferredPartnerId: opts.preferredPartnerId || null,
      preferredPartnerReason: opts.preferredPartnerReason || null,
      pokemon: opts.pokemon || null,
      pokemonType: opts.pokemonType || null,
      trainingFocus: opts.trainingFocus || null,
      independentMission: opts.independentMission || null,
      teamMission: opts.teamMission || null,
      handoffContract: opts.handoffContract || null,
    });

    this.agents.push(agent);
    this.save();
    return agent;
  }

  getById(id) {
    const agent = this.agents.find(a => a.id === id);
    return agent ? this._touchAgent(agent) : null;
  }

  list() {
    let liveModels = [];
    try {
      const out = execSync('ollama list', { encoding: 'utf8', timeout: 3000 });
      liveModels = out.trim().split('\n').slice(1).map(line => line.split(/\s+/)[0]).filter(Boolean);
    } catch {}

    let dirty = false;

    const touched = this.agents.map(agent => this._touchAgent(agent));
    const byId = new Map(touched.map(agent => [agent.id, agent]));

    const listed = touched.map(current => {
      const attempts = current.tasksCompleted + current.tasksFailed;
      const failRate = attempts > 0 ? current.tasksFailed / attempts : 0;
      const shouldBeUnhealthy = current.status !== 'pending_build' && attempts >= 5 && failRate > 0.5;

      if (shouldBeUnhealthy && current.status !== 'unhealthy') {
        current.status = 'unhealthy';
        dirty = true;
      }

      return {
        ...current,
        available: liveModels.includes(current.base) || liveModels.includes(current.id),
        attempts,
        failRate,
        successRate: attempts > 0 ? current.tasksCompleted / attempts : 0,
        preferredPartnerName: current.preferredPartnerId ? (byId.get(current.preferredPartnerId)?.displayName || null) : null,
      };
    });

    if (dirty) this.save();

    return listed.sort((a, b) => {
      if (a.teamRole === 'trainer' && b.teamRole !== 'trainer') return -1;
      if (a.teamRole !== 'trainer' && b.teamRole === 'trainer') return 1;
      if (a.teamRole === 'companion' && b.teamRole !== 'companion') return -1;
      if (a.teamRole !== 'companion' && b.teamRole === 'companion') return 1;
      return (a.partySlot || 99) - (b.partySlot || 99);
    });
  }

  rename(id, newName) {
    const agent = this.getById(id);
    if (agent) {
      agent.displayName = newName;
      this.save();
    }
  }

  setRole(id, role) {
    const agent = this.getById(id);
    if (agent) {
      agent.role = role;
      this.save();
    }
  }

  setPersonality(id, personality) {
    const agent = this.getById(id);
    if (agent) {
      agent.personality = personality;
      this.save();
    }
  }

  heal(id) {
    const agent = this.getById(id);
    if (!agent) return false;
    agent.tasksCompleted = 0;
    agent.tasksFailed = 0;
    agent.status = agent.buildNote ? 'pending_build' : 'idle';
    agent.lastHealedAt = new Date().toISOString();
    this.save();
    return true;
  }

  /** Record task completion for learning metrics */
  recordResult(id, success) {
    const agent = this.getById(id);
    if (!agent) return;

    if (success) agent.tasksCompleted++;
    else agent.tasksFailed++;

    agent.lastUsed = new Date().toISOString();

    const attempts = agent.tasksCompleted + agent.tasksFailed;
    const failRate = attempts > 0 ? agent.tasksFailed / attempts : 0;
    if (agent.status !== 'pending_build') {
      agent.status = attempts >= 5 && failRate > 0.5 ? 'unhealthy' : 'idle';
    }

    this.save();
  }
}
