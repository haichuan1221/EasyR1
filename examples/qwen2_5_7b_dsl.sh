#!/bin/bash
set -x

export VLLM_ATTENTION_BACKEND=XFORMERS
export VLLM_USE_V1=0

MODEL_PATH=/data/models/saves/qwen2.5-7b/lora/sft_nl2sql_20250317_merge  # replace it with cold start model


python3 -m verl.trainer.main \
    config=examples/dsl_config.yaml \
    worker.actor.model.model_path="${MODEL_PATH}" \
    trainer.n_gpus_per_node=4