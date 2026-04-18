#!/usr/bin/env node
/**
 * Pull all Gen 1+2 Pokemon (#1-251) and all Gen 1+2 moves from PokeAPI.
 * Saves raw JSON to C:\Users\Ken\Desktop\Codex\corpora\pokecrystal\raw\
 *
 * Polite: 200ms delay between requests, retries on transient errors.
 *
 * Run:
 *   node agent_mode/pokecrystal/fetch_pokeapi.js
 *
 * Re-runs are idempotent — skips files already on disk.
 */

const fs = require('fs');
const path = require('path');

const RAW_DIR = process.env.POKE_RAW_DIR
  || 'C:/Users/Ken/Desktop/Codex/corpora/pokecrystal/raw';

const POKEMON_DIR = path.join(RAW_DIR, 'pokemon');
const SPECIES_DIR = path.join(RAW_DIR, 'species');
const MOVE_DIR    = path.join(RAW_DIR, 'move');
const PROGRESS    = path.join(RAW_DIR, '_progress.json');

const POKEMON_RANGE = [1, 251];   // Gen 1+2
// Gen 2 ends around move id 251 in PokeAPI ordering. Pull through 267 for safety.
const MOVE_RANGE    = [1, 267];

const DELAY_MS = 200;
const MAX_RETRIES = 4;

for (const d of [RAW_DIR, POKEMON_DIR, SPECIES_DIR, MOVE_DIR]) {
  fs.mkdirSync(d, { recursive: true });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchJson(url) {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const r = await fetch(url, { headers: { 'User-Agent': 'KenAI-PokeCorpus/1.0' } });
      if (r.status === 404) return null;
      if (!r.ok) throw new Error(`http ${r.status}`);
      return await r.json();
    } catch (e) {
      if (attempt === MAX_RETRIES) throw e;
      console.error(`  retry ${attempt} for ${url}: ${e.message}`);
      await sleep(1000 * attempt);
    }
  }
}

async function pullOne(kind, id) {
  const dir = { pokemon: POKEMON_DIR, species: SPECIES_DIR, move: MOVE_DIR }[kind];
  const fp = path.join(dir, `${id}.json`);
  if (fs.existsSync(fp)) return 'cached';
  const url = `https://pokeapi.co/api/v2/${kind}/${id}/`;
  const data = await fetchJson(url);
  if (!data) {
    fs.writeFileSync(fp, JSON.stringify({ _missing: true, id }));
    return 'missing';
  }
  fs.writeFileSync(fp, JSON.stringify(data));
  return 'fetched';
}

async function main() {
  const start = Date.now();
  let counts = { fetched: 0, cached: 0, missing: 0, failed: 0 };

  console.log(`fetching pokemon ${POKEMON_RANGE[0]}..${POKEMON_RANGE[1]}`);
  for (let id = POKEMON_RANGE[0]; id <= POKEMON_RANGE[1]; id++) {
    try {
      const r1 = await pullOne('pokemon', id);
      counts[r1]++;
      const r2 = await pullOne('species', id);
      counts[r2]++;
    } catch (e) {
      console.error(`  pokemon ${id} failed: ${e.message}`);
      counts.failed++;
    }
    if (id % 25 === 0) console.log(`  ...pokemon ${id}/${POKEMON_RANGE[1]}  ${JSON.stringify(counts)}`);
    await sleep(DELAY_MS);
  }

  console.log(`fetching moves ${MOVE_RANGE[0]}..${MOVE_RANGE[1]}`);
  for (let id = MOVE_RANGE[0]; id <= MOVE_RANGE[1]; id++) {
    try {
      const r = await pullOne('move', id);
      counts[r]++;
    } catch (e) {
      console.error(`  move ${id} failed: ${e.message}`);
      counts.failed++;
    }
    if (id % 25 === 0) console.log(`  ...move ${id}/${MOVE_RANGE[1]}  ${JSON.stringify(counts)}`);
    await sleep(DELAY_MS);
  }

  const dur = ((Date.now() - start) / 1000).toFixed(0);
  fs.writeFileSync(PROGRESS, JSON.stringify({ counts, durationSec: Number(dur), finishedAt: new Date().toISOString() }, null, 2));
  console.log(`\ndone in ${dur}s. ${JSON.stringify(counts)}`);
}

main().catch(e => { console.error(e); process.exit(1); });
