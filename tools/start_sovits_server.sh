#!/bin/bash
# 启动 GPT-SoVITS-CPUFast API 服务（脱离终端运行）
SOVITS_DIR="/home/amedal/hermes-agent-workdir/ai-dubbing/tools/GPT-SoVITS-CPUFast"
PYTHON="/home/amedal/hermes-agent-workdir/ai-dubbing/venv-sovits/bin/python"
LOG="/home/amedal/hermes-agent-workdir/ai-dubbing/workdir/sovits/server.log"
cd "$SOVITS_DIR"
exec "$PYTHON" api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml > "$LOG" 2>&1
