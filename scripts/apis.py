# -*- coding: utf-8 -*-
"""CascadeBench 核心API库: 统一封装全部模型调用(重试/退避/延迟/错误处理)"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, time, base64, os, random
import requests
import dashscope
from dashscope import SpeechSynthesizer, MultiModalConversation
from dashscope.audio.asr import Recognition, RecognitionCallback

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
if not API_KEY:
    _keyfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apikey.txt")
    API_KEY = open(_keyfile).read().strip() if os.path.exists(_keyfile) else ""
if not API_KEY:
    raise SystemExit("Set DASHSCOPE_API_KEY or create apikey.txt at the repository root.")
dashscope.api_key = API_KEY
EP = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
GEN_EP = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
HDRS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "X-DashScope-SSE": "disable"}

class RateLimitError(Exception): pass
class ApiError(Exception): pass
class NonRetriableError(ApiError): pass  # 参数/鉴权错误, 不重试

_NON_RETRIABLE = ("InvalidParameter", "InvalidApiKey", "Unauthorized", "Unsupported", "NotFound", "model_not_exist")

def _backoff(attempt, base=1.5):
    time.sleep(min(base ** attempt + random.random()*0.5, 45))

def _retry_call(fn, max_retry=6):
    """通用重试: 限流/超时/连接断开退避重试; 参数错误直接抛出"""
    last = None
    for attempt in range(max_retry):
        try:
            return fn()
        except NonRetriableError:
            raise
        except (RateLimitError, requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                json.JSONDecodeError, ConnectionError, OSError) as e:
            last = e; _backoff(attempt)
        except ApiError as e:
            msg = str(e)
            if any(p in msg for p in _NON_RETRIABLE):
                raise
            last = e; _backoff(attempt)
    raise last or ApiError("max retries")

# ---------------- TTS: Sambert ----------------
def tts_sambert(model, text):
    """返回wav bytes(16k mono)"""
    def _c():
        r = SpeechSynthesizer.call(model=model, text=text)
        data = r.get_audio_data() if r else None
        if data and len(data) > 1000:
            return data
        resp = r.get_response() if r else None
        raise ApiError(f"TTS fail: {str(resp)[:200]}")
    return _retry_call(_c)

# ---------------- ASR: Paraformer (websocket流式) ----------------
class _RecCB(RecognitionCallback):
    def __init__(self):
        super().__init__(); self.final_sentences=[]; self.err=None; self.first_evt_t=None
    def on_open(self): pass
    def on_complete(self): pass
    def on_error(self, r): self.err=str(r)[:250]
    def on_event(self, r):
        if self.first_evt_t is None: self.first_evt_t = time.time()
        try:
            s = r.get_sentence()
            if s and s.get("sentence_end"):
                self.final_sentences.append(s.get("text",""))
        except Exception: pass
    def on_close(self): pass

def asr_paraformer(model, wav_path, sample_rate=16000, chunk_bytes=6400, inter=0.01):
    """流式识别本地wav, 只返回sentence_end=True的句子拼接"""
    def _c():
        cb = _RecCB()
        rec = Recognition(model=model, format='wav', sample_rate=sample_rate, callback=cb)
        t0 = time.time()
        rec.start()
        with open(wav_path,'rb') as f:
            while True:
                chunk = f.read(chunk_bytes)
                if not chunk: break
                rec.send_audio_frame(chunk)
                if inter: time.sleep(inter)
        rec.stop()
        dt = time.time()-t0
        if cb.err and not cb.final_sentences:
            if "Throttling" in str(cb.err): raise RateLimitError(cb.err)
            raise ApiError(cb.err)
        return {"text": "".join(cb.final_sentences), "latency_s": round(dt,2),
                "n_sent": len(cb.final_sentences), "err": cb.err}
    return _retry_call(_c)

# ---------------- ASR: qwen-audio-3.1 (input_audio格式) ----------------
def _b64_wav(path):
    with open(path,'rb') as f:
        return "data:audio/wav;base64,"+base64.b64encode(f.read()).decode()

def asr_q31(wav_path, model="qwen-audio-3.1-asr-flash", sample_rate=16000):
    def _c():
        body = {"model": model,
                "input": {"messages": [{"role": "user", "content": [
                    {"type": "input_audio", "input_audio": {"data": _b64_wav(wav_path)}}]}]},
                "parameters": {"format": "wav", "sample_rate": str(sample_rate)}}
        r = requests.post(EP, headers=HDRS, json=body, timeout=90)
        j = r.json()
        if r.status_code == 200 and "output" in j:
            txt = j.get("output",{}).get("text","") or ""
            usage = j.get("usage",{})
            return {"text": txt, "latency_s": None, "usage": usage}
        code = j.get("code",""); msg = j.get("message","")
        if "Throttling" in msg or "rate" in msg.lower(): raise RateLimitError(msg)
        raise ApiError(f"{code}: {msg[:200]}")
    return _retry_call(_c)

# ---------------- ASR: qwen3-asr-flash (audio uri格式) ----------------
def asr_q3(wav_path, model="qwen3-asr-flash"):
    def _c():
        messages = [{"role":"user","content":[{"audio": _b64_wav(wav_path)}]}]
        r = MultiModalConversation.call(model=model, messages=messages, timeout=90)
        if r.status_code == 200:
            txt = ""
            try: txt = r.output.choices[0].message.content[0].get("text","")
            except Exception: txt = ""
            usage = dict(r.usage) if r.usage else {}
            return {"text": txt, "latency_s": None, "usage": usage}
        msg = str(r.message if hasattr(r,'message') else r)[:200]
        if "Throttling" in msg or "rate" in msg.lower(): raise RateLimitError(msg)
        raise ApiError(msg)
    return _retry_call(_c)

# ---------------- MT: qwen-mt-uni ----------------
def mt_uni(text, source_lang, target_lang):
    def _c():
        body = {"model": "qwen-mt-uni",
                "input": {"source_texts": text, "source_lang": source_lang, "target_lang": target_lang}}
        r = requests.post(EP, headers=HDRS, json=body, timeout=90)
        j = r.json()
        if r.status_code == 200:
            try: txt = j["output"]["Data"]["TranslatedTexts"]
            except Exception: txt = ""
            usage = j.get("usage",{})
            if txt: return {"text": txt, "usage": usage}
            raise ApiError("empty translation: "+str(j)[:150])
        code = j.get("code",""); msg = j.get("message","")
        if "Throttling" in msg or "rate" in msg.lower(): raise RateLimitError(msg)
        raise ApiError(f"{code}: {msg[:200]}")
    return _retry_call(_c)

# ---------------- LLM文本生成: qwen3.8-max (参考译文用) ----------------
def gen_text(model, prompt, system=None, max_tokens=512, temperature=0.3):
    def _c():
        msgs = []
        if system: msgs.append({"role":"system","content":system})
        msgs.append({"role":"user","content":prompt})
        r = requests.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            timeout=120, json={"model": model, "messages": msgs,
                               "temperature": temperature, "max_tokens": max_tokens})
        j = r.json()
        if r.status_code == 200 and j.get("choices"):
            txt = j["choices"][0].get("message",{}).get("content","") or ""
            if txt:
                return {"text": txt, "usage": j.get("usage",{})}
            raise ApiError("empty gen: "+str(j)[:150])
        code = j.get("code",""); msg = j.get("message","") or str(j)[:200]
        if "Throttling" in str(msg) or "rate" in str(msg).lower(): raise RateLimitError(str(msg))
        raise ApiError(f"{code}: {str(msg)[:200]}")
    return _retry_call(_c)

# ---------------- Omni: 音频理解(ASR/E2E翻译) ----------------
def omni_audio(wav_path, prompt, model="qwen3.8-omni-flash"):
    def _c():
        messages = [{"role":"user","content":[{"audio": _b64_wav(wav_path)},{"text": prompt}]}]
        r = MultiModalConversation.call(model=model, messages=messages, timeout=120)
        if r.status_code == 200:
            txt = ""
            try: txt = r.output.choices[0].message.content[0].get("text","")
            except Exception: txt = ""
            usage = dict(r.usage) if r.usage else {}
            if txt: return {"text": txt, "usage": usage}
            raise ApiError("empty omni output")
        msg = str(r.message if hasattr(r,'message') else r)[:200]
        if "Throttling" in msg or "rate" in msg.lower(): raise RateLimitError(msg)
        raise ApiError(msg)
    return _retry_call(_c)

# ---------------- LiveTranslate: websocket E2E语音翻译 ----------------
def livetranslate(wav_path, target_lang="en", timeout=60):
    """输入16k wav, 返回 {source: 原文转写, translation: 译文, latency_s}"""
    import websocket as wslib
    def _c():
        url = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3.8-livetranslate-flash-realtime"
        result = {"source": "", "translation": "", "err": None, "latency_s": None}
        ws = wslib.create_connection(url, header={"Authorization": f"Bearer {API_KEY}"}, timeout=timeout)
        t0 = time.time()
        try:
            # 1. 等session.created
            while True:
                ev = json.loads(ws.recv())
                if ev.get("type") == "session.created": break
                if ev.get("type") == "error": raise ApiError(str(ev)[:200])
            # 2. 配置
            ws.send(json.dumps({"type": "session.update", "session":
                {"output_modalities": ["text"], "voice": "Tina", "translation": {"language": target_lang}}}))
            while True:
                ev = json.loads(ws.recv())
                t = ev.get("type")
                if t == "session.updated": break
                if t == "error": raise ApiError(str(ev)[:200])
            # 3. 读取wav PCM数据(跳过44字节头)并发送
            with open(wav_path,'rb') as f: raw = f.read()
            pcm = raw[44:] if raw[:4] == b'RIFF' else raw
            step = 16000  # 0.5s chunk of 16k16bit = 32000 bytes; 用32000
            step = 32000
            for i in range(0, len(pcm), step):
                ws.send(json.dumps({"type": "input_audio_buffer.append",
                                    "audio": base64.b64encode(pcm[i:i+step]).decode()}))
                time.sleep(0.05)
            # 4. 结束输入
            ws.send(json.dumps({"type": "session.finish"}))
            # 5. 收集结果
            while True:
                ev = json.loads(ws.recv())
                t = ev.get("type")
                if t == "conversation.item.input_audio_transcription.delta":
                    result["source"] += ev.get("delta","")
                elif t == "conversation.item.input_audio_transcription.completed":
                    result["source"] = ev.get("transcript", result["source"])
                elif t in ("response.text.delta", "response.audio_transcript.delta"):
                    result["translation"] += ev.get("delta","")
                elif t in ("response.text.done", "response.audio_transcript.done"):
                    if ev.get("text"): result["translation"] = ev["text"]
                elif t == "response.done":
                    pass
                elif t == "session.finished":
                    break
                elif t == "error":
                    raise ApiError(str(ev)[:200])
            result["latency_s"] = round(time.time()-t0, 2)
            return result
        finally:
            try: ws.close()
            except Exception: pass
    return _retry_call(_c)

# ---------------- 工具: JSONL断点日志 ----------------
def load_done(path):
    """只统计成功的key (失败项需要重试)"""
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    j = json.loads(line)
                    if j.get("ok") and j.get("key"):
                        done.add(j["key"])
                except Exception: pass
    return done

def append_jsonl(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
