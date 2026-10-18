# -*- coding: utf-8 -*-
"""CascadeBench corpus builder: 合并中英语料 → corpus.jsonl + sweep子集 + babble噪声源文本"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_data_zh import ZH_CORPUS
from corpus_data_en import EN_CORPUS

random.seed(42)
OUT = os.path.join(ROOT, "corpus")
os.makedirs(OUT, exist_ok=True)

# 每语言2个TTS音色（pilot阶段可调整）
ZH_VOICES = ["sambert-zhida-v1", "sambert-zhixiao-v1"]
EN_VOICES = ["sambert-brian-v1", "sambert-beth-v1"]

records = []
for lang, CORPUS, voices in [("zh", ZH_CORPUS, ZH_VOICES), ("en", EN_CORPUS, EN_VOICES)]:
    idx_in_lang = 0
    for (domain, length) in sorted(CORPUS.keys()):
        sents = CORPUS[(domain, length)]
        assert len(sents) == 20, f"{lang} {domain}{length}: {len(sents)} != 20"
        for i, text in enumerate(sents):
            voice = voices[idx_in_lang % 2]  # 语言内全局交替 → 每音色平衡
            rec = {
                "id": f"{lang}_{domain}_{length}_{i+1:02d}",
                "lang": lang, "domain": domain, "length": length,
                "text": text, "voice": voice,
            }
            records.append(rec)
            idx_in_lang += 1

# SNR扫描子集: 每 (lang, domain, length) 单元抽6句 → 每语言48句, 共96句
sweep_ids = []
by_cell = {}
for r in records:
    by_cell.setdefault((r["lang"], r["domain"], r["length"]), []).append(r["id"])
for cell, ids in sorted(by_cell.items()):
    picked = random.sample(ids, 6)
    sweep_ids.extend(picked)

with open(f"{OUT}/corpus.jsonl", "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(f"{OUT}/sweep_ids.json", "w") as f:
    json.dump(sweep_ids, f, ensure_ascii=False, indent=1)

# babble噪声源: 用6个未参与测试的音色 × 每语言20句无关短句
ZH_BABBLE_TEXTS = [
    "请把窗户打开通风。", "这个周末天气不错。", "我们需要提前订票。",
    "楼下的超市在打折。", "他的办公室在三楼。", "这本书写得很有意思。",
    "别忘了带充电器。", "晚饭想吃点清淡的。", "会议记录我整理好了。",
    "院子里种了些花草。", "这条裙子颜色好看。", "公交车还有三站到。",
    "咖啡不加糖谢谢。", "电脑重新启动试试。", "外套挂在门后面。",
    "行李箱密码忘了。", "下午有个电话会议。", "图书馆座位挺多的。",
    "雨伞放门口伞架了。", "这集电视剧很精彩。",
]
EN_BABBLE_TEXTS = [
    "Please close the door quietly.",
    "The garden looks lovely today.",
    "I need to charge my laptop.",
    "Let's meet at the usual place.",
    "This tea tastes wonderful.",
    "The printer needs more paper.",
    "She left her keys on the desk.",
    "We should water the plants.",
    "The movie starts in an hour.",
    "He fixed the leaking faucet.",
    "Traffic was terrible this morning.",
    "My favorite color is blue.",
    "The cake smells delicious.",
    "They arrived early yesterday.",
    "I love walking in the park.",
    "The meeting ran long today.",
    "Winter is coming soon.",
    "Her presentation went well.",
    "We ordered pizza tonight.",
    "The cat is sleeping again.",
]
BABBLE_VOICES_ZH = ["sambert-zhiyue-v1", "sambert-zhiying-v1", "sambert-zhiming-v1",
                    "sambert-zhiyan-v1" if False else "sambert-zhinan-v1", "sambert-zhimao-v1", "sambert-zhiqi-v1"]
BABBLE_VOICES_EN = ["sambert-cindy-v1", "sambert-donna-v1", "sambert-hanna-v1",
                    "sambert-clara-v1", "sambert-cally-v1", "sambert-waan-v1"]
babble = []
for i, t in enumerate(ZH_BABBLE_TEXTS):
    babble.append({"id": f"babble_zh_{i+1:02d}", "lang": "zh", "text": t,
                   "voice": BABBLE_VOICES_ZH[i % len(BABBLE_VOICES_ZH)]})
for i, t in enumerate(EN_BABBLE_TEXTS):
    babble.append({"id": f"babble_en_{i+1:02d}", "lang": "en", "text": t,
                   "voice": BABBLE_VOICES_EN[i % len(BABBLE_VOICES_EN)]})
with open(f"{OUT}/babble_sources.jsonl", "w", encoding="utf-8") as f:
    for r in babble:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# 统计
n_zh = sum(1 for r in records if r["lang"] == "zh")
n_en = sum(1 for r in records if r["lang"] == "en")
zh_chars = sum(len(r["text"]) for r in records if r["lang"] == "zh")
en_words = sum(len(r["text"].split()) for r in records if r["lang"] == "en")
print(f"corpus: {len(records)} sentences (zh={n_zh}, en={n_en})")
print(f"  zh chars total={zh_chars}, avg={zh_chars/n_zh:.1f}")
print(f"  en words total={en_words}, avg={en_words/n_en:.1f}")
print(f"  voice balance: " + ", ".join(f"{v}:{sum(1 for r in records if r['voice']==v)}" for v in ZH_VOICES+EN_VOICES))
print(f"sweep subset: {len(sweep_ids)} sentences")
print(f"babble sources: {len(babble)}")
# 长度分布检查
for lang in ["zh","en"]:
    for L in ["S","M","L"]:
        sel = [r for r in records if r["lang"]==lang and r["length"]==L]
        if lang=="zh":
            lens = [len(r["text"].rstrip("。？！")) for r in sel]
            print(f"  {lang}-{L}: char len min={min(lens)} max={max(lens)} mean={sum(lens)/len(lens):.1f}")
        else:
            lens = [len(r["text"].split()) for r in sel]
            print(f"  {lang}-{L}: word len min={min(lens)} max={max(lens)} mean={sum(lens)/len(lens):.1f}")
