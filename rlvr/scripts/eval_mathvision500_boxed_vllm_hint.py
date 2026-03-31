#!/usr/bin/env python3
import math
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from jinja2 import Template
from transformers import AutoProcessor
from vllm import LLM, SamplingParams

RLVR_ROOT = Path(__file__).resolve().parents[1]
if str(RLVR_ROOT) not in sys.path:
    sys.path.append(str(RLVR_ROOT))
from verl.utils.local_strict_eval import strict_score_response

MODEL='Qwen/Qwen2.5-VL-3B-Instruct'
DATA='mydata/mathvision_test_500.parquet'
HINT='Hint: Please answer the question and provide the final answer at the end.\nQuestion: '
SUFFIX='Put your final answer inside \\boxed{...}.'

def process_image_local(image, min_pixels=262144, max_pixels=4194304):
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    elif isinstance(image, str):
        image = Image.open(image)
    elif isinstance(image, dict):
        image = Image.open(BytesIO(image['bytes']))
    elif isinstance(image, bytes):
        image = Image.open(BytesIO(image))
    image.load()
    if max_pixels is not None and (image.width * image.height) > max_pixels:
        resize_factor = math.sqrt(max_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))
    if min_pixels is not None and (image.width * image.height) < min_pixels:
        resize_factor = math.sqrt(min_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return image

def normalize_images(raw_images):
    if raw_images is None:
        return []
    if isinstance(raw_images, np.ndarray):
        raw_images = raw_images.tolist()
    if not isinstance(raw_images, list):
        raw_images = [raw_images]
    return [process_image_local(img) for img in raw_images]

def main():
    df = pd.read_parquet(DATA)
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=False)
    inputs=[]
    for _, row in df.iterrows():
        problem = str(row['problem']).replace('<image>','').strip()
        prompt = f"{HINT}{problem}"
        if SUFFIX not in prompt:
            prompt = f"{prompt}\n{SUFFIX}"
        images = normalize_images(row.get('images', None))
        content=[{'type':'image'},{'type':'text','text':prompt}] if images else [{'type':'text','text':prompt}]
        messages=[{'role':'user','content':content}]
        text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        mm_data = {'image': images} if images else {}
        inputs.append({'prompt': text, 'multi_modal_data': mm_data})

    llm = LLM(model=MODEL, trust_remote_code=False, seed=1, tensor_parallel_size=1,
              gpu_memory_utilization=0.9, disable_log_stats=True,
              mm_processor_cache_gb=0, max_num_seqs=512, limit_mm_per_prompt={'image':1})
    sp = SamplingParams(temperature=0.6, top_p=0.95, top_k=-1, n=1, max_tokens=1024)
    outputs = llm.generate(inputs, sampling_params=sp, use_tqdm=True)

    hits = 0.0
    extracted = 0
    for i,o in enumerate(outputs):
        resp = o.outputs[0].text if o.outputs else ''
        gt = df.iloc[i]['answer']
        score, is_extracted, _, _ = strict_score_response(resp, gt)
        if is_extracted:
            extracted += 1
            hits += float(score)

    total = len(outputs)
    acc_extracted = 100.0 * hits / extracted if extracted else 0.0
    acc_total = 100.0 * hits / total if total else 0.0
    print('total\t', total)
    print('extracted\t', extracted)
    print('hit\t', hits)
    print('acc_on_extracted\t', acc_extracted)
    print('acc_on_total\t', acc_total)

if __name__=='__main__':
    main()
