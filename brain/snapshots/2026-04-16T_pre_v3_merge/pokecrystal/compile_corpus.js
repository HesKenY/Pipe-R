#!/usr/bin/env node
/**
 * Pokemon Crystal corpus compiler.
 *
 * Reads structured data from agent_mode/pokecrystal/corpus/ and
 * emits instruction/response JSONL pairs for fine-tuning at
 * agent_mode/training/poke-corpus.jsonl.
 *
 * Output format: { "instruction": "...", "input": "", "output": "..." }
 * Compatible with alpaca-style fine-tune (unsloth, axolotl, llamafactory).
 *
 * Run: node agent_mode/pokecrystal/compile_corpus.js
 */

const fs = require('fs');
const path = require('path');

// Corpora live at C:\Users\Ken\Desktop\Codex\corpora\pokecrystal so both
// agent clones (Claude + Codex) point at the same canonical library.
const CORPUS_DIR = process.env.POKE_CORPUS_DIR
  || 'C:/Users/Ken/Desktop/Codex/corpora/pokecrystal';
const RAW_DIR = path.join(CORPUS_DIR, 'raw');
const OUT_PATH = path.join(__dirname, '..', 'training', 'poke-corpus.jsonl');

const pairs = [];

function add(instruction, output, input = '') {
  pairs.push({ instruction, input, output });
}

// ---------- TYPE CHART ----------
function compileTypeChart() {
  const data = JSON.parse(fs.readFileSync(path.join(CORPUS_DIR, 'type_chart.json'), 'utf8'));
  const { types, chart } = data;

  for (const atk of types) {
    const eff = chart[atk] || {};
    const supers = [], resists = [], immunes = [];
    for (const def of types) {
      const m = eff[def] === undefined ? 1 : eff[def];
      if (m === 0) immunes.push(def);
      else if (m === 2) supers.push(def);
      else if (m === 0.5) resists.push(def);
    }
    add(
      `In Pokemon Crystal, what does a ${atk}-type move do against each defender type?`,
      `${atk}-type moves are SUPER EFFECTIVE (2x) against: ${supers.join(', ') || 'none'}. ` +
      `RESISTED (0.5x) by: ${resists.join(', ') || 'none'}. ` +
      `NO EFFECT (0x) on: ${immunes.join(', ') || 'none'}. ` +
      `Neutral against everything else.`
    );

    if (supers.length > 0) {
      add(
        `What types are weak to ${atk} in Pokemon Crystal?`,
        `${supers.join(', ')} all take 2x damage from ${atk}-type moves.`
      );
    }
  }

  // Defender-side queries
  for (const def of types) {
    const weakTo = [], resistedBy = [], immuneTo = [];
    for (const atk of types) {
      const m = (chart[atk] && chart[atk][def] !== undefined) ? chart[atk][def] : 1;
      if (m === 0) immuneTo.push(atk);
      else if (m === 2) weakTo.push(atk);
      else if (m === 0.5) resistedBy.push(atk);
    }
    add(
      `What is a ${def}-type Pokemon weak to in Crystal?`,
      `${def} takes 2x damage from: ${weakTo.join(', ') || 'no types'}. ` +
      `Resists (0.5x): ${resistedBy.join(', ') || 'no types'}. ` +
      `Immune to: ${immuneTo.join(', ') || 'no types'}.`
    );
  }
}

// ---------- GYM LEADERS ----------
function compileGyms() {
  const data = JSON.parse(fs.readFileSync(path.join(CORPUS_DIR, 'gym_leaders.json'), 'utf8'));

  for (const g of data.johto || []) {
    const teamLine = g.team.map(p => `${p.species} L${p.level}${p.key_move ? ` (${p.key_move})` : ''}`).join(', ');
    add(
      `Tell me about ${g.leader}, the ${g.city} gym leader in Pokemon Crystal.`,
      `${g.leader} runs the ${g.city} City gym (${g.type}-type) and gives the ${g.badge} Badge. Team: ${teamLine}. Tip: ${g.tip}`
    );
    add(
      `What's the best counter for ${g.leader} in Crystal?`,
      `${g.leader} uses ${g.type}-type Pokemon. ${g.tip}`
    );
    for (const p of g.team) {
      if (p.warning) {
        add(
          `What should I watch for with ${g.leader}'s ${p.species}?`,
          `${g.leader}'s ${p.species} (L${p.level}): ${p.warning}`
        );
      }
    }
  }

  for (const g of data.kanto || []) {
    add(
      `Tell me about Kanto gym leader ${g.leader} in Pokemon Crystal.`,
      `${g.leader} runs the ${g.city} City gym (${g.type}-type) and gives the ${g.badge} Badge. Headline team: ${(g.headline_team || []).join(', ')}. Tip: ${g.tip}`
    );
  }

  for (const e of data.elite_four || []) {
    add(
      `Who is ${e.name} in the Pokemon Crystal Elite Four?`,
      `${e.name} specializes in ${e.type}. Team typically includes: ${(e.headline_team || []).join(', ')}.${e.tip ? ' ' + e.tip : ''}`
    );
  }

  if (data.red_silver_top) {
    const r = data.red_silver_top;
    const teamLine = r.team.map(p => `${p.species} L${p.level}`).join(', ');
    add(
      `Tell me about the Red battle on Mt. Silver in Pokemon Crystal.`,
      `${r.name} sits at ${r.location}, the post-game superboss. Team: ${teamLine}. ${r.tip}`
    );
  }
}

// ---------- STARTERS ----------
function compileStarters() {
  const data = JSON.parse(fs.readFileSync(path.join(CORPUS_DIR, 'starters.json'), 'utf8'));

  for (const s of data.starters) {
    const evoLine = s.evolves_to.map(e => `${e.species} at L${e.level}`).join(' → ');
    add(
      `Tell me about the starter ${s.name} in Pokemon Crystal.`,
      `${s.name} (#${s.dex}) is a ${s.type}-type starter. Evolutionary line: ${s.name} → ${evoLine}. ` +
      `Stat bias: ${s.stat_bias}. Early movepool: ${s.early_movepool.join(', ')}. ${s.advantage}`
    );
  }

  add(
    `Which starter is easiest in Pokemon Crystal?`,
    `Difficulty ranking, easiest first: ${data.starter_ranking_for_first_run.join(' → ')}. Cyndaquil cleans Bugsy and Jasmine; Totodile crushes the second half of Johto; Chikorita is hard mode and loses to most early gyms.`
  );

  add(
    `What does the rival pick if I take Cyndaquil/Totodile/Chikorita?`,
    data.rival_starter_logic
  );
}

// ---------- STRATEGY MD ----------
function compileStrategy() {
  const md = fs.readFileSync(path.join(CORPUS_DIR, 'strategy.md'), 'utf8');
  const sections = md.split(/\n##\s+/).slice(1); // drop header before first ##

  for (const block of sections) {
    const [titleLine, ...rest] = block.split('\n');
    const title = titleLine.trim().replace(/_/g, ' ');
    const body = rest.join('\n').trim();

    // Each bullet becomes its own QA pair
    const bullets = body.split(/\n-\s+/).filter(b => b.trim()).map(b => b.replace(/^-\s*/, '').trim());

    if (bullets.length > 0) {
      add(
        `What are key tips for ${title} in Pokemon Crystal?`,
        bullets.map(b => `- ${b}`).join('\n')
      );
    }

    for (const bullet of bullets) {
      // Use the bullet itself as a teaching point
      const firstSentence = bullet.split('.')[0].trim();
      if (firstSentence.length > 20 && firstSentence.length < 200) {
        add(
          `Pokemon Crystal tip about ${title}:`,
          bullet
        );
      }
    }
  }
}

// ---------- WRITE ----------
function main() {
  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  compileTypeChart();
  compileGyms();
  compileStarters();
  compileStrategy();

  const lines = pairs.map(p => JSON.stringify(p)).join('\n') + '\n';
  fs.writeFileSync(OUT_PATH, lines);
  console.log(`compiled ${pairs.length} instruction/response pairs`);
  console.log(`wrote ${OUT_PATH}`);
}

main();
