// v1.8 审稿修复第3点补充: Table 6 温和条件格子 (revr/rb5/rb10) 的 GLM 候选翻译重渲 2 轮
// 目的: 直接测量格子级生成噪声, 检验 Rev 49.7 < +10/+5 (55.7/55.9) 的凹陷是噪声还是条件效应
// 协议与 glm_translate_v17b.mjs 逐字一致 (8 句/调用, N||translation, thinking disabled)
// 用法: TIME_BUDGET=380 bun /home/z/my-project/scripts/glm_mtre2.mjs
// 断点续跑; exit 3 = 429 惩罚期
import fs from 'fs';

import { fileURLToPath } from 'url';
import path from 'path';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SDK = path.join(path.dirname(fileURLToPath(import.meta.url)), 'zai-sdk/dist/index.js');
const { default: ZAI } = await import(SDK);

const RES = path.join(ROOT, 'results');
const Q31 = path.join(RES, 'd3_asr_q31.jsonl');
const OUT = path.join(RES, 'glm_mtre2.jsonl');
const BUDGET = parseFloat(process.env.TIME_BUDGET || '380');
const BATCH = parseInt(process.env.GLMBATCH || '8', 10);
const T0 = Date.now();

// 优先级顺序: revr 两轮最先 (核心问题格), 再 rb5, 再 rb10
const PLAN = [
  { cond: 'revr', round: 2 }, { cond: 'revr', round: 3 },
  { cond: 'rb5', round: 2 }, { cond: 'rb5', round: 3 },
  { cond: 'rb10', round: 2 }, { cond: 'rb10', round: 3 },
];

// q31 权威转写清单 (同 v17 协议: 最后一条 ok 生效, 空文本不调 GLM)
const q31 = {};
for (const line of fs.readFileSync(Q31, 'utf8').trim().split('\n')) {
  if (!line) continue;
  try {
    const j = JSON.parse(line);
    const k = j.key;
    if (!k || !k.includes('/') || k.startsWith('mt') || k.startsWith('ref')) continue;
    const cond = k.split('/')[0];
    if (!['revr', 'rb5', 'rb10'].includes(cond)) continue;
    if (j.ok) q31[k] = (j.text || '');
  } catch {}
}

const D3C = {};
for (const line of fs.readFileSync(path.join(ROOT, 'corpus/d3_corpus.jsonl'), 'utf8').trim().split('\n')) {
  const j = JSON.parse(line); D3C[j.id] = j.lang;
}

// 断点集
const done = new Set();
if (fs.existsSync(OUT)) {
  for (const line of fs.readFileSync(OUT, 'utf8').trim().split('\n')) {
    if (!line) continue;
    try { const j = JSON.parse(line); if (j.ok && j.key) done.add(j.key); } catch {}
  }
}

// 任务: 按计划顺序
const tasks = [];
for (const { cond, round } of PLAN) {
  for (const [k, txt] of Object.entries(q31)) {
    const c = k.split('/')[0];
    if (c !== cond || !txt) continue;
    const sid = k.split('/')[1];
    const gk = `mtre2/${round}/${cond}/${sid}`;
    if (!done.has(gk)) tasks.push({ key: gk, src: txt, cond, sid, lang: D3C[sid], round });
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
        if (g) { append({ key: t.key, ok: true, text: g, src: t.src, src_lang: t.lang, kind: 'mtre2', round: t.round, cond: t.cond }); n_ok++; }
        else missing.push(t.key);
      });
      if (missing.length) console.log(`  batch missing ${missing.length}: ${missing.slice(0, 3).join(',')}${missing.length > 3 ? '...' : ''}`);
      return n_ok + missing.length;
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

// 分组: 轮次+条件+语言 (同批同语言同轮同条件)
let n_done = 0;
const groups = {};
for (const t of tasks) (groups[`${t.round}/${t.cond}/${t.lang}`] ||= []).push(t);
// 按 PLAN 优先级排序组
const order = [];
for (const { cond, round } of PLAN) for (const lang of ['zh', 'en']) order.push(`${round}/${cond}/${lang}`);
const flat = [];
for (const g of order) if (groups[g]) flat.push(...groups[g]);
for (let i = 0; i < flat.length; i += BATCH) {
  if (Date.now() - T0 > BUDGET * 1000) { console.log(`BUDGET STOP after ${n_done}/${flat.length}`); break; }
  const batch = flat.slice(i, i + BATCH);
  const r = await translateBatch(batch);
  if (r < 0) { console.log(`BUDGET STOP (in batch) after ${n_done}/${flat.length}`); break; }
  n_done += r;
  await new Promise(r2 => setTimeout(r2, 1500 + Math.random() * 800));
}
console.log(`DONE ok≈${n_done} elapsed=${((Date.now() - T0) / 1000).toFixed(0)}s`);
