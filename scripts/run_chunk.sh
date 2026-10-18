#!/bin/bash
# 分块实验编排器: 在单个Bash调用内并行运行实验进程, 到时自动停止, 断点续跑
# 用法: bash run_chunk.sh <seconds> <tasks...>
# 任务: tts | perturb | para16k | para8k | q31 | q3 | omni | oracle | refmax | cascade | e2e_omni | e2e_lt
SECS=$1; shift
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPTS/../logs"
mkdir -p $LOGS
PIDS=()
for TASK in "$@"; do
  case $TASK in
    tts)       CMD="python3 $SCRIPTS/run_tts.py" ;;
    perturb)   CMD="python3 $SCRIPTS/perturb.py" ;;
    oracle)    CMD="python3 $SCRIPTS/run_mt.py oracle" ;;
    refmax)    CMD="python3 $SCRIPTS/run_mt.py refmax" ;;
    cascade)   CMD="python3 $SCRIPTS/run_mt.py cascade" ;;
    e2e_omni)  CMD="python3 $SCRIPTS/run_mt.py e2e_omni" ;;
    e2e_lt)    CMD="python3 $SCRIPTS/run_mt.py e2e_lt" ;;
    para16k|para8k|q31|q3|omni) CMD="python3 $SCRIPTS/run_asr.py $TASK" ;;
    *) echo "unknown task $TASK"; continue ;;
  esac
  echo "[$(date +%H:%M:%S)] starting $TASK for ${SECS}s"
  timeout $SECS $CMD >> $LOGS/${TASK}.log 2>&1 &
  PIDS+=($!)
done
wait
echo "[$(date +%H:%M:%S)] chunk done"
