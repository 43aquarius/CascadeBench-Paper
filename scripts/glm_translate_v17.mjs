// 升级项2 (v1.7): GLM 九条件重译 — 批量版 (BATCH=8, 复用 glm_translate2.mjs 协议)
// 用法: TIME_BUDGET=500 bun scripts/glm_translate_v17.mjs  (仓库根目录)
// 断点续跑; 429 惩罚期中止块 (exit 3) 由 glm_drive.sh 处理
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SDK = path.join(path.dirname(fileURLToPath(import.meta.url)), 'zai-sdk/dist/index.js');
const { default: ZAI } = await import(SDK);

const RES = path.join(ROOT, 'results');
const Q31 = path.join(ROOT, 'results', 'd3_asr_q31.jsonl');
const OUT = path.join(ROOT, 'results', 'glm_tasks.jsonl');
const BUDGET = parseFloat(process.env.TIME_BUDGET || '500');
const BATCH = parseInt(process.env.GLMBATCH || '8', 10);
const T0 = Date.now();

const CONDS9 = ['clean_r', 'revr', 'rb10', 'rb5', 'rb25', 'rb0', 'rbm25', 'rbm5', 'rn0'];

const done = new Set();
for (const line of fs.readFileSync(OUT, 'utf8').trim().split('\n')) {
  if (!line) continue;
  try { const j = JSON.parse(line); if (j.ok && j.key) done.add(j.key); } catch {}
}

const q31 = {};
for (const line of fs.readFileSync(Q31, 'utf8').trim().split('\n')) {
  if (!line) continue;
  try {
    const j = JSON.parse(line);
    const k = j.key;
    if (!k || !k.includes('/') || k.startsWith('mt') || k.startsWith('ref')) continue;
    const cond = k.split('/')[0];
    if (!CONDS9.includes(cond)) continue;
    if (j.ok) q31[k] = (j.text || '');
  } catch {}
}

const D3C = {};
for (const line of fs.readFileSync(path.join(ROOT, 'corpus', 'd3_corpus.jsonl'), 'utf8').trim().split('\n')) {
  const j = JSON.parse(line); D3C[j.id] = j.lang;
}

const tasks = [];
for (const [k, txt] of Object.entries(q31)) {
  const [cond, sid] = k.split('/');
  const gk = `mtreal/${cond}/${sid}`;
  if (done.has(gk) || !txt) continue;
  tasks.push({ key: gk, src: txt, cond, sid, lang: D3C[sid] });
}
console.log(`todo=${tasks.length} (batch=${BATCH} → ~${Math.ceil(tasks.length / BATCH)} calls)`);

const append = (obj) => fs.appendFileSync(OUT, JSON.stringify(obj) + '\n');
const zai = await ZAI.create();

async function callGLM(messages) {
  return zai.chat.completions.create({ messages, thinking: { type: 'disabled' } });
}

async function translateBatch(batch) {
  const tgt = batch[0].lang === 'zh' ? 'English' : 'Chinese';
  const sname = batch[0].lang === 'zh' ? 'Chinese' : 'English';
  const lines = batch.map((t, i) => `${i + 1}. ${t.src.replace(/\n/g, ' ')}`).join('\n');
  const sys = `You are a professional ${sname}-${tgt} translator. You will receive numbered ${sname} sentences. Translate EACH sentence into ${tgt}. Output EXACTLY one line per input sentence in the format: N||translation — where N is the input number and translation is the ${tgt} translation. Do not merge, skip, or add sentences.`;
  for (let attempt = 0; attempt < 6; attempt++) {
    if (Date.now() - T0 > BUDGET * 1000) return -1;
    try {
      const completion = await callGLM([
        { role: 'assistant', content: sys },
        { role: 'user', content: lines }
      ]);
      const text = (completion.choices?.[0]?.message?.content || '').trim();
      const got = {};
      for (const ln of text.split('\n')) {
        const m = ln.match(/^\s*(\d+)\s*\|\|\s*(.+)$/);
        if (m) got[parseInt(m[1], 10)] = m[2].trim();
      }
      let n_ok = 0; const missing = [];
      batch.forEach((t, i) => {
        const g = got[i + 1];
        if (g) { append({ key: t.key, ok: true, text: g, src: t.src, src_lang: t.lang, kind: 'mt' }); n_ok++; }
        else missing.push(t);
      });
      if (missing.length && missing.length < batch.length) {
        for (const t of missing) await translateSingle(t);
      }
      return n_ok + missing.length;
    } catch (e) {
      const msg = String(e && e.message || e);
      const fatal = /api key|unauthorized|401|403/i.test(msg);
      if (fatal) { console.log('FATAL key error'); process.exit(2); }
      const is429 = /429|too many/i.test(msg);
      if (is429 && attempt >= 1) {
        console.log(`RATE_LIMITED (batch) at batch attempt ${attempt}`);
        process.exit(3);
      }
      console.error(`  ERR batch a${attempt}: ${msg.slice(0, 110)}`);
      await new Promise(r => setTimeout(r, is429 ? 30000 : Math.min(4000 * (attempt + 1), 25000)));
    }
  }
  let n = 0;
  for (const t of batch) { if (await translateSingle(t)) n++; }
  return n;
}

async function translateSingle(t) {
  const tgt = t.lang === 'zh' ? 'English' : 'Chinese';
  const sname = t.lang === 'zh' ? 'Chinese' : 'English';
  const prompt = `Translate the following ${sname} sentence into ${tgt}. Output only the translation, nothing else.\n${t.src}`;
  for (let attempt = 0; attempt < 5; attempt++) {
    if (Date.now() - T0 > BUDGET * 1000) return false;
    try {
      const completion = await callGLM([
        { role: 'assistant', content: 'You are a professional translator. Output only the translation with no explanations.' },
        { role: 'user', content: prompt }
      ]);
      const text = (completion.choices?.[0]?.message?.content || '').trim();
      if (text) { append({ key: t.key, ok: true, text, src: t.src, src_lang: t.lang, kind: 'mt' }); return true; }
    } catch (e) {
      const msg = String(e && e.message || e);
      const is429 = /429|too many/i.test(msg);
      if (is429 && attempt >= 1) { console.log('RATE_LIMITED (single)'); process.exit(3); }
      await new Promise(r => setTimeout(r, is429 ? 30000 : Math.min(5000 * (attempt + 1), 30000)));
    }
  }
  return false;
}

let n_done = 0;
// 按条件+语言分组批处理 (同批同语言)
const groups = {};
for (const t of tasks) (groups[t.cond + '/' + t.lang] ||= []).push(t);
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
