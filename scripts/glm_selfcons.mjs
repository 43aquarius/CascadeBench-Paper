// v1.8 审稿修复第3点: GLM 参考翻译自一致性 — 对 refreal 150 句人工转写重复生成 4 轮 (r2-r5)
// 协议与 glm_translate_v17b.mjs 批量版逐字一致 (8 句/调用, N||translation, thinking disabled)
// 用法: TIME_BUDGET=400 bun /home/z/my-project/scripts/glm_selfcons.mjs
// 断点续跑; exit 3 = 429 惩罚期 (外部驱动冷却后重跑)
import fs from 'fs';

import { fileURLToPath } from 'url';
import path from 'path';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SDK = path.join(path.dirname(fileURLToPath(import.meta.url)), 'zai-sdk/dist/index.js');
const { default: ZAI } = await import(SDK);

const RES = path.join(ROOT, 'results');
const SRC = path.join(RES, 'glm_tasks.jsonl');      // refreal r1 来源
const OUT = path.join(RES, 'glm_selfcons.jsonl');   // r2-r5 输出 (不污染主数据文件)
const BUDGET = parseFloat(process.env.TIME_BUDGET || '400');
const BATCH = parseInt(process.env.GLMBATCH || '8', 10);
const ROUNDS = [2, 3, 4, 5];
const T0 = Date.now();

// 1. 提取 refreal 基准句 (每句一次, r1)
const base = {};
for (const line of fs.readFileSync(SRC, 'utf8').trim().split('\n')) {
  if (!line) continue;
  try {
    const j = JSON.parse(line);
    if (j.ok && j.key && j.key.startsWith('refreal/') && j.kind === 'reference') {
      const sid = j.key.split('/')[1];
      if (!base[sid]) base[sid] = { sid, src: j.src, src_lang: j.src_lang };
    }
  } catch {}
}
const sids = Object.keys(base).sort();
console.log(`refreal base sentences: ${sids.length}`);

// 2. 断点集
const done = new Set();
if (fs.existsSync(OUT)) {
  for (const line of fs.readFileSync(OUT, 'utf8').trim().split('\n')) {
    if (!line) continue;
    try { const j = JSON.parse(line); if (j.ok && j.key) done.add(j.key); } catch {}
  }
}

// 3. 任务: 4 轮 x 150 句
const tasks = [];
for (const r of ROUNDS) {
  for (const sid of sids) {
    const gk = `sc${r}/${sid}`;
    if (!done.has(gk)) tasks.push({ key: gk, src: base[sid].src, lang: base[sid].src_lang, round: r });
  }
}
console.log(`todo=${tasks.length} (batch=${BATCH} → ~${Math.ceil(tasks.length / BATCH)} calls)`);

const append = (obj) => fs.appendFileSync(OUT, JSON.stringify(obj) + '\n');
const zai = await ZAI.create();

async function translateBatch(batch) {
  const tgt = batch[0].lang === 'zh' ? 'English' : 'Chinese';
  const sname = batch[0].lang === 'zh' ? 'Chinese' : 'English';
  const lines = batch.map((t, i) => `${i + 1}. ${t.src.replace(/\n/g, ' ')}`).join('\n');
  const sys = `You are a professional ${sname}-${tgt} translator. You will receive numbered ${sname} sentences. Translate EACH sentence into ${tgt}. Output EXACTLY one line per input sentence in the format: N||translation — where N is the input number and translation is the ${tgt} translation. Do not merge, skip, or add sentences.`;
  for (let attempt = 0; attempt < 6; attempt++) {
    if (Date.now() - T0 > BUDGET * 1000) return -1;
    try {
      const completion = await zai.chat.completions.create({
        messages: [{ role: 'assistant', content: sys }, { role: 'user', content: lines }],
        thinking: { type: 'disabled' }
      });
      const text = (completion.choices?.[0]?.message?.content || '').trim();
      const got = {};
      for (const ln of text.split('\n')) {
        const m = ln.match(/^\s*(\d+)\s*\|\|\s*(.+)$/);
        if (m) got[parseInt(m[1], 10)] = m[2].trim();
      }
      let n_ok = 0; const missing = [];
      batch.forEach((t, i) => {
        const g = got[i + 1];
        if (g) { append({ key: t.key, ok: true, text: g, src: t.src, src_lang: t.lang, kind: 'selfcons', round: t.round }); n_ok++; }
        else missing.push(t);
      });
      if (missing.length) console.log(`  batch missing ${missing.length}: ${missing.map(m => m.key).slice(0, 3).join(',')}${missing.length > 3 ? '...' : ''}`);
      return n_ok + missing.length;  // missing 留待断点重跑 (不逐句补, 保持纯批量协议)
    } catch (e) {
      const msg = String(e && e.message || e);
      const fatal = /api key|unauthorized|401|403/i.test(msg);
      if (fatal) { console.log('FATAL key error'); process.exit(2); }
      const is429 = /429|too many/i.test(msg);
      if (is429 && attempt >= 1) { console.log('RATE_LIMITED (batch)'); process.exit(3); }
      console.error(`  ERR batch a${attempt}: ${msg.slice(0, 110)}`);
      await new Promise(r => setTimeout(r, is429 ? 30000 : Math.min(4000 * (attempt + 1), 25000)));
    }
  }
  return 0;
}

// 按轮次+语言分组 (同批同语言同轮)
let n_done = 0;
const groups = {};
for (const t of tasks) (groups[`${t.round}/${t.lang}`] ||= []).push(t);
const flat = Object.values(groups).flat();
for (let i = 0; i < flat.length; i += BATCH) {
  if (Date.now() - T0 > BUDGET * 1000) { console.log(`BUDGET STOP after ${n_done}/${flat.length}`); break; }
  const batch = flat.slice(i, i + BATCH);
  const r = await translateBatch(batch);
  if (r < 0) { console.log(`BUDGET STOP (in batch) after ${n_done}/${flat.length}`); break; }
  n_done += r;
  await new Promise(r2 => setTimeout(r2, 1500 + Math.random() * 800));
}
console.log(`DONE ok≈${n_done} elapsed=${((Date.now() - T0) / 1000).toFixed(0)}s`);
