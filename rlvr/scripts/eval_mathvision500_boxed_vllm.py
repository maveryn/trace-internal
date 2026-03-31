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

MODEL = 'Qwen/Qwen2.5-VL-3B-Instruct'
DATA = 'mydata/mathvision_test_500.parquet'
TEMPLATE = 'examples/format_prompt/math.jinja'


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


def build_messages(prompt_text, has_image):
    if not has_image:
        return [{'role': 'user', 'content': prompt_text}]

    content_list = []
    for i, segment in enumerate(prompt_text.split('<image>')):
        if i > 0:
            content_list.append({'type': 'image'})
        if segment:
            content_list.append({'type': 'text', 'text': segment})
    return [{'role': 'user', 'content': content_list}]


def main():
    df = pd.read_parquet(DATA)
    template = Template(Path(TEMPLATE).read_text(encoding='utf-8').strip())
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=False)

    inputs = []
    for _, row in df.iterrows():
        problem = str(row['problem']).strip()
        prompt = template.render(content=problem, format_prompt_variant='boxed_only')
        images = normalize_images(row.get('images', None))
        messages = build_messages(prompt, has_image=len(images) > 0)
        text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        mm_data = {'image': images} if images else {}
        inputs.append({'prompt': text, 'multi_modal_data': mm_data})

    llm = LLM(
        model=MODEL,
        trust_remote_code=False,
        seed=1,
        tensor_parallel_size=1,
        gpu_memory_utilization=0.9,
        disable_log_stats=True,
        mm_processor_cache_gb=0,
        max_num_seqs=512,
        limit_mm_per_prompt={'image': 1},
    )

    sp = SamplingParams(temperature=0.6, top_p=0.95, n=1, max_tokens=1024)
    outputs = llm.generate(inputs, sampling_params=sp, use_tqdm=True)

    hits = 0.0
    extracted = 0
    rows = []
    for i, out in enumerate(outputs):
        response = out.outputs[0].text if out.outputs else ''
        gt = df.iloc[i]['answer']
        score, is_extracted, extracted_answer, extracted_method = strict_score_response(response, gt)
        if is_extracted:
            extracted += 1
            hits += float(score)
        rows.append(
            {
                'index': i,
                'score': score,
                'extracted': int(is_extracted),
                'extracted_answer': extracted_answer,
                'extracted_method': extracted_method,
                'answer': str(gt),
                'prediction': response,
            }
        )

    acc_extracted = 100.0 * hits / extracted if extracted else 0.0
    acc_total = 100.0 * hits / len(rows) if rows else 0.0
    out_dir = Path('mydata/prism_eval')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tsv = out_dir / 'mathvision500_qwen25vl3b_boxed_reward.tsv'
    pd.DataFrame(rows).to_csv(out_tsv, sep='\t', index=False)

    print(f'total\t{len(rows)}')
    print(f'extracted\t{extracted}')
    print(f'hit\t{hits:.4f}')
    print(f'acc_on_extracted\t{acc_extracted:.4f}')
    print(f'acc_on_total\t{acc_total:.4f}')
    print(f'file\t{out_tsv}')


if __name__ == '__main__':
    main()
