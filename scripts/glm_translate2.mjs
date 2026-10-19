// 升级项b/e: GLM (非Qwen系) 批量翻译 v2 — 每批多句, 大幅减少API调用次数
// 用法: bun glm_translate2.mjs  (断点续跑, TIME_BUDGET 秒数限制)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ZAI_SDK = path.join(path.dirname(fileURLToPath(import.meta.url)), 'zai-sdk/dist/index.js');
const { default: ZAI } = await import(ZAI_SDK);

import { fileURLToPath } from 'url';
import path from 'path';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RES = path.join(ROOT, 'results');
const OUT = `${RES}/glm_tasks.jsonl`;
const BUDGET = parseFloat(process.env.TIME_BUDGET || '500');
const BATCH = parseInt(process.env.GLMBATCH || '8', 10);
const T0 = Date.now();

function buildTasks() {
  const tasks = [];
  const synth = fs.readFileSync(path.join(ROOT, 'corpus', 'corpus.jsonl'), 'utf8').trim().split('\n').map(l => JSON.parse(l));
  for (const r of synth) tasks.push({ key: `refsynth/${r.id}`, src: r.text, src_lang: r.lang, kind: 'reference' });
  const real = fs.readFileSync(path.join(ROOT, 'corpus', 'd3_corpus.jsonl'), 'utf8').trim().split('\n').map(l => JSON.parse(l));
  for (const r of real) tasks.push({ key: `refreal/${r.id}`, src: r.text, src_lang: r.lang, kind: 'reference' });
  const q31real = {};
  for (const line of fs.readFileSync(`${RES}/d3_asr_q31.jsonl`, 'utf8').trim().split('\n')) {
    const j = JSON.parse(line);
    if (j.ok) q31real[j.key] = j.text || '';
  }
  for (const cond of ['clean_r', 'rb0', 'rb5', 'rbm5']) {
    for (const r of real) {
      const k = `${cond}/${r.id}`;
      if (k in q31real) tasks.push({ key: `mtreal/${k}`, src: q31real[k], src_lang: r.lang, kind: 'mt' });
    }
  }
  return tasks;
}

function loadDone() {
  const done = new Set();
  if (fs.existsSync(OUT)) {
    for (const line of fs.readFileSync(OUT, 'utf8').trim().split('\n')) {
      if (!line) continue;
      try { const j = JSON.parse(line); if (j.ok && j.key) done.add(j.key); } catch {}
    }
  }
  return done;
}
function append(obj) { fs.appendFileSync(OUT, JSON.stringify(obj) + '\n'); }

const tasks = buildTasks();
const done = loadDone();
const todo = tasks.filter(t => !done.has(t.key) && t.src && t.src.trim());
console.log(`total=${tasks.length} done=${done.size} todo=${todo.length} (batch=${BATCH})`);

const zai = await ZAI.create();

async function callGLM(messages) {
  return await zai.chat.completions.create({
    messages, thinking: { type: 'disabled' }
  });
}

// 批量翻译一批任务; 返回成功写入数
async function translateBatch(batch) {
  const tgtName = batch[0].src_lang === 'zh' ? 'English' : 'Chinese';
  const srcName = batch[0].src_lang === 'zh' ? 'Chinese' : 'English';
  const lines = batch.map((t, i) => `${i + 1}. ${t.src.replace(/\n/g, ' ')}`).join('\n');
  const sys = `You are a professional ${srcName}-${tgtName} translator. You will receive numbered ${srcName} sentences. Translate EACH sentence into ${tgtName}. Output EXACTLY one line per input sentence in the format: N||translation — where N is the input number and translation is the ${tgtName} translation. Do not merge, skip, or add sentences.`;
  const user = lines;
  for (let attempt = 0; attempt < 6; attempt++) {
    if (Date.now() - T0 > BUDGET * 1000) return -1;
    try {
      const completion = await callGLM([
        { role: 'assistant', content: sys },
        { role: 'user', content: user }
      ]);
      const text = (completion.choices?.[0]?.message?.content || '').trim();
      const got = {};
      for (const ln of text.split('\n')) {
        const m = ln.match(/^\s*(\d+)\s*\|\|\s*(.+)$/);
        if (m) got[parseInt(m[1], 10)] = m[2].trim();
      }
      let n_ok = 0;
      const missing = [];
      batch.forEach((t, i) => {
        const g = got[i + 1];
        if (g) { append({ key: t.key, ok: true, text: g, src: t.src, src_lang: t.src_lang, kind: t.kind }); n_ok++; }
        else missing.push(t);
      });
      if (missing.length && missing.length < batch.length) {
        // 部分成功: 缺的单独补
        for (const t of missing) await translateSingle(t);
      }
      return n_ok;
    } catch (e) {
      const msg = String(e);
      if (msg.includes('429') || msg.toLowerCase().includes('too many')) {
        const wait = Math.min(6000 * Math.pow(1.7, attempt), 45000);
        console.log(`  429 backoff ${Math.round(wait / 1000)}s`);
        await new Promise(r => setTimeout(r, wait));
      } else {
        console.log(`  batch err: ${msg.slice(0, 100)}`);
        await new Promise(r => setTimeout(r, 2000));
      }
    }
  }
  // 批失败 → 逐句
  let n = 0;
  for (const t of batch) { const r = await translateSingle(t); if (r) n++; }
  return n;
}

async function translateSingle(t) {
  const tgt = t.src_lang === 'zh' ? 'English' : 'Chinese';
  const sname = t.src_lang === 'zh' ? 'Chinese' : 'English';
  const prompt = `Translate the following ${sname} sentence into ${tgt}. Output only the translation, nothing else.\n${t.src}`;
  for (let attempt = 0; attempt < 5; attempt++) {
    if (Date.now() - T0 > BUDGET * 1000) return false;
    try {
      const completion = await callGLM([
        { role: 'assistant', content: 'You are a professional translator. Output only the translation with no explanations.' },
        { role: 'user', content: prompt }
      ]);
      const text = (completion.choices?.[0]?.message?.content || '').trim();
      if (text) { append({ key: t.key, ok: true, text, src: t.src, src_lang: t.src_lang, kind: t.kind }); return true; }
    } catch (e) {
      const msg = String(e);
      if (msg.includes('429') || msg.toLowerCase().includes('too many')) {
        await new Promise(r => setTimeout(r, Math.min(5000 * Math.pow(1.7, attempt), 40000)));
      } else { await new Promise(r => setTimeout(r, 2000)); }
    }
  }
  return false;
}

let n_done = 0;
for (let i = 0; i < todo.length; i += BATCH) {
  if (Date.now() - T0 > BUDGET * 1000) { console.log(`BUDGET STOP after ${n_done}`); break; }
  // 批内同语言
  const batch = [];
  for (let j = i; j < Math.min(i + BATCH, todo.length); j++) {
    if (todo[j].src_lang === todo[i].src_lang) batch.push(todo[j]);
  }
  if (!batch.length) continue;
  const r = await translateBatch(batch);
  if (r >= 0) { n_done += r; i += (batch.length - 1); }
  if ((i / BATCH) % 10 === 0) console.log(`  progress ~${i}/${todo.length} (+${n_done} this run)`);
  await new Promise(r2 => setTimeout(r2, 2500 + Math.random() * 1500));
}
console.log(`DONE this-run=${n_done}`);
