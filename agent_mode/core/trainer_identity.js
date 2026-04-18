export const PRIMARY_TRAINER_ID = 'kenai:v4-offline-developer';
export const LEGACY_TRAINER_ID = 'ken-ai:latest';
export const TRAINER_ID_ALIASES = new Set([
  PRIMARY_TRAINER_ID,
  LEGACY_TRAINER_ID,
]);

export const TRAINER_MODEL_FALLBACKS = [
  PRIMARY_TRAINER_ID,
  LEGACY_TRAINER_ID,
  'qwen2.5-coder:14b',
  'llama3.1:8b',
];

export const TRAINER_DISPLAY_NAME = 'Ken V4';
export const TRAINER_LONG_NAME = 'Ken V4 Offline Developer';

export function isTrainerId(id) {
  return TRAINER_ID_ALIASES.has(String(id || ''));
}

export function normalizeTrainerId(id) {
  return isTrainerId(id) ? PRIMARY_TRAINER_ID : id;
}

export function trainerFallbacksFor(agent) {
  if (!agent) return [];
  const choices = [
    agent.base || agent.id,
    ...(Array.isArray(agent.fallbackModels) ? agent.fallbackModels : []),
  ].filter(Boolean);
  if (isTrainerId(agent.id) || choices.some(isTrainerId)) {
    return [...new Set(TRAINER_MODEL_FALLBACKS)];
  }
  return [...new Set(choices)];
}
