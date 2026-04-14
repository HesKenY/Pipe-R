/* grader — scores a drill response against the rubric.

   rubric is a list of checks. each check is one of:
     { type: 'contains',   needle: 'halo2.dll', weight: 1 }
     { type: 'regex',      pattern: '0x[0-9a-f]{8,}', flags: 'i', weight: 2 }
     { type: 'min_length', value: 400, weight: 1 }
     { type: 'max_length', value: 8000, weight: 1 }
     { type: 'bullet_count_min', value: 5, weight: 1 }
     { type: 'section_header', header: '## offsets', weight: 2 }
     { type: 'json_valid',  weight: 3 }
     { type: 'must_not_contain', needle: "I'm sorry", weight: 3 }

   returns { score, maxScore, percent, passed, checks: [ {check, passed, note} ] }

   passing is score/max >= drill.passingPercent (default 0.6). */

function countBullets(text) {
  let n = 0;
  for (const line of (text || '').split('\n')) {
    if (/^\s*[-*]\s+\S/.test(line)) n += 1;
  }
  return n;
}

function runCheck(check, text) {
  switch (check.type) {
    case 'contains':
      return {
        passed: String(text).toLowerCase().includes(String(check.needle).toLowerCase()),
        note: `contains "${check.needle}"`,
      };
    case 'must_not_contain':
      return {
        passed: !String(text).toLowerCase().includes(String(check.needle).toLowerCase()),
        note: `absent "${check.needle}"`,
      };
    case 'regex':
      try {
        const re = new RegExp(check.pattern, check.flags || '');
        return { passed: re.test(text), note: `matches /${check.pattern}/${check.flags || ''}` };
      } catch (e) {
        return { passed: false, note: `bad regex: ${e.message}` };
      }
    case 'min_length':
      return {
        passed: (text || '').length >= check.value,
        note: `length >= ${check.value} (got ${(text || '').length})`,
      };
    case 'max_length':
      return {
        passed: (text || '').length <= check.value,
        note: `length <= ${check.value} (got ${(text || '').length})`,
      };
    case 'bullet_count_min': {
      const n = countBullets(text);
      return { passed: n >= check.value, note: `bullets >= ${check.value} (got ${n})` };
    }
    case 'section_header':
      return {
        passed: (text || '').toLowerCase().includes(String(check.header).toLowerCase()),
        note: `section header "${check.header}"`,
      };
    case 'json_valid':
      try {
        // Try direct parse, then find first JSON block
        try { JSON.parse(text); return { passed: true, note: 'json parsed' }; }
        catch (e1) {
          const m = (text || '').match(/\{[\s\S]*\}/);
          if (!m) return { passed: false, note: 'no json block' };
          JSON.parse(m[0]);
          return { passed: true, note: 'embedded json parsed' };
        }
      } catch (e) {
        return { passed: false, note: `json invalid: ${e.message}` };
      }
    default:
      return { passed: false, note: `unknown check type ${check.type}` };
  }
}

export function grade(drill, response) {
  const text = response || '';
  const rubric = drill.rubric || [];
  if (!rubric.length) {
    return {
      score: 0, maxScore: 0, percent: 0, passed: false,
      checks: [],
      note: 'no rubric defined',
    };
  }
  const results = [];
  let score = 0;
  let maxScore = 0;
  for (const check of rubric) {
    const w = check.weight || 1;
    maxScore += w;
    const r = runCheck(check, text);
    if (r.passed) score += w;
    results.push({
      type: check.type,
      weight: w,
      passed: r.passed,
      note: r.note,
    });
  }
  const percent = maxScore ? score / maxScore : 0;
  const passingPercent = drill.passingPercent || 0.6;
  return {
    score,
    maxScore,
    percent: Math.round(percent * 1000) / 1000,
    passed: percent >= passingPercent,
    passingPercent,
    checks: results,
  };
}
