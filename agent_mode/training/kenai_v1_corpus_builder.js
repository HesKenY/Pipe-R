#!/usr/bin/env node
// kenai_v1_corpus_builder.js
// Converts kenai_v1_corpus.txt → kenai_v1_corpus.jsonl (fine-tune format)
//
// JSONL format per line:
//   { "system": "...", "user": "...", "assistant": "...", "category": "..." }
//
// Run: node agent_mode/training/kenai_v1_corpus_builder.js

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const CORPUS_TXT  = join(__dirname, 'kenai_v1_corpus.txt');
const CORPUS_JSONL = join(__dirname, 'kenai_v1_corpus.jsonl');

const SYSTEM_PROMPT = `You are Ken — a plumber and construction-industry veteran who builds software by directing AI agents. You run CHERP (construction crew management at cherp.live), Pipe-R (a Node.js command center), and Bird's Nest (a multi-tenant backend manager).

You answer the way Ken answers: lowercase, 3-10 words per message, direct, no pleasantries, no analogies, no "as an AI" disclaimers. The answer comes before the reason. If you're guessing, you say so. You don't invent features. You don't suggest npm packages for Pipe-R.`;

const raw = readFileSync(CORPUS_TXT, 'utf8');
const lines = raw.split('\n');

const pairs = [];

for (const line of lines) {
  const trimmed = line.trim();
  // skip comments and blanks
  if (!trimmed || trimmed.startsWith('#')) continue;

  const parts = trimmed.split('|');
  if (parts.length < 3) continue;

  const category = parts[0].trim();
  const question = parts[1].trim();
  // Answer may contain pipes — rejoin
  const answer = parts.slice(2).join('|').trim();

  if (!category || !question || !answer) continue;

  pairs.push({
    system: SYSTEM_PROMPT,
    user: question,
    assistant: answer,
    category,
    source: 'kenai_v1_corpus',
  });
}

const jsonl = pairs.map(p => JSON.stringify(p)).join('\n') + '\n';
writeFileSync(CORPUS_JSONL, jsonl, 'utf8');

console.log(`wrote ${pairs.length} pairs → ${CORPUS_JSONL}`);
