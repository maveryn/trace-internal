from __future__ import annotations

import ast
import math
import os
import os.path as osp
import re
import shutil
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pandas as pd
import portalocker

from vlmeval.smp import (LMUDataRoot, download_file, dump, get_intermediate_file_path,
                         load, md5, toliststr)
from vlmeval.utils import track_progress_rich

from .image_base import ImageBaseDataset
from .utils import DEBUG_MESSAGE, build_judge


MIRAGE_CATEGORIES = (
    'Algebraic',
    'Arithmetic',
    'Geometry',
    'Logical',
    'Scientific',
    'Spatial',
    'Statistical',
)

_VALID_QUESTION_TYPES = {'multi_choice', 'free_form', 'approx'}
_FAIL_MARKER = 'Failed to obtain answer'
QWEN3_JUDGE_MODEL = 'Qwen/Qwen3-32B'
QWEN3_JUDGE_API_MODEL = 'qwen3-32b-judge'


def _cell_text(value: Any) -> str:
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _question_type(line: Any) -> str:
    question_type = _cell_text(line.get('question_type')).lower()
    if question_type in _VALID_QUESTION_TYPES:
        return question_type
    answer_type = _cell_text(line.get('answer_type')).lower()
    if answer_type in _VALID_QUESTION_TYPES:
        return answer_type
    return 'free_form'


def _strip_image_placeholders(prompt: Any) -> str:
    text = _cell_text(prompt)
    text = re.sub(r'<image\d*>', '', text, flags=re.I)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _last_braced_content(text: str, marker: str) -> str | None:
    start = text.rfind(marker)
    if start < 0:
        return None
    pos = start + len(marker)
    depth = 1
    chars = []
    while pos < len(text):
        char = text[pos]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return ''.join(chars).strip()
        chars.append(char)
        pos += 1
    return None


def _explicit_answer(text: Any) -> str | None:
    text = _cell_text(text)
    if not text:
        return None

    tagged = re.findall(r'<answer\b[^>]*>(.*?)</answer>', text, flags=re.I | re.S)
    if tagged:
        return tagged[-1].strip()

    boxed = _last_braced_content(text, r'\boxed{')
    if boxed:
        return boxed

    patterns = (
        r'(?:final\s+answer|answer)\s*(?:is|=|:|：)\s*(.+)',
        r'(?:therefore|thus|hence)\s*,?\s*(?:the\s+answer\s+is\s*)?(.+)',
    )
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.I)
        if matches:
            return matches[-1].strip().splitlines()[0].strip()

    # Treat a single token or a compact numeric/list expression as answer-only.
    # Short natural-language sentences still need the extraction judge; taking
    # the whole sentence can introduce intermediate numbers and false misses.
    if text.count('\n') <= 1 and (
        len(text.split()) == 1
        or re.fullmatch(r'[\[\](){}$+\-.,:/\\\d\s]+', text)
    ):
        return text
    return None


def _extract_mcq_letter(text: Any) -> str | None:
    text = _cell_text(text)
    if not text:
        return None
    candidates = [_explicit_answer(text), text]
    patterns = (
        r'^\s*[\(\[]?([A-O])[\)\].,:;]?\s*$',
        r'(?i)\b(?:final\s+answer|answer|option|choice)\b\s*(?:is|=|:|：)?\s*[\(\[]?([A-O])\b',
    )
    for candidate in candidates:
        if not candidate:
            continue
        for pattern in patterns:
            match = re.search(pattern, candidate, flags=0 if pattern.startswith('(?i)') else re.I)
            if match:
                return match.group(1).upper()
    return None


def _prefetch_answer(line: Any) -> str | None:
    prediction = _cell_text(line.get('prediction'))
    if _question_type(line) == 'multi_choice':
        return _extract_mcq_letter(prediction)
    return _explicit_answer(prediction)


def _answer_extraction_prompt(line: Any) -> str:
    kind = _question_type(line)
    question = _strip_image_placeholders(line.get('prompt') or line.get('question'))
    prediction = _cell_text(line.get('prediction'))
    if kind == 'multi_choice':
        instruction = (
            'Extract the option selected in the model response. Return only its single '
            'uppercase option letter (A, B, C, ...), or unclear if no option is selected.'
        )
    else:
        instruction = (
            'Extract the final answer from the model response. Return only the answer itself '
            '(a number, list, expression, or short phrase), or unclear if no answer is present.'
        )
    return f'{instruction}\n\nQuestion:\n{question}\n\nModel response:\n{prediction}\n\nExtracted answer:'


def mirage_auxeval(model: Any, line: Any) -> dict[str, str]:
    prefetched = _prefetch_answer(line)
    if prefetched:
        return {
            'parsed_answer': prefetched,
            'judge_output': '',
            'judge_log': 'Prefetch succeeded; judge not invoked.',
        }
    if model is None:
        return {
            'parsed_answer': '',
            'judge_output': '',
            'judge_log': 'No explicit answer found and no extraction judge was configured.',
        }

    prompt = _answer_extraction_prompt(line)
    logs = []
    last_judge_output = ''
    for attempt in range(3):
        try:
            response = model.generate(prompt, temperature=attempt * 0.2)
        except Exception as exc:
            logs.append(f'Attempt {attempt + 1}: judge raised {type(exc).__name__}.')
            continue
        response_text = _cell_text(response)
        last_judge_output = response_text
        if _FAIL_MARKER in response_text:
            logs.append(f'Attempt {attempt + 1}: judge request failed.')
            continue
        parsed = (
            _extract_mcq_letter(response_text)
            if _question_type(line) == 'multi_choice'
            else (_explicit_answer(response_text) or response_text)
        )
        if parsed and parsed.lower() != 'unclear':
            logs.append(f'Attempt {attempt + 1}: extraction succeeded.')
            return {
                'parsed_answer': parsed,
                'judge_output': response_text,
                'judge_log': ' '.join(logs),
            }
        logs.append(f'Attempt {attempt + 1}: judge returned no answer.')
    return {
        'parsed_answer': '',
        'judge_output': last_judge_output,
        'judge_log': ' '.join(logs),
    }


def _numeric_value(value: Any) -> float | None:
    text = _cell_text(value).replace(',', '').replace('−', '-')
    if not text:
        return None
    numbers = re.findall(r'(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', text)
    if len(numbers) != 1:
        return None
    try:
        return float(numbers[0])
    except ValueError:
        return None


def _literal_value(value: Any) -> Any:
    text = _cell_text(value)
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None
    if isinstance(parsed, (list, tuple)):
        return list(parsed)
    return None


def _normalize_answer_text(value: Any) -> str:
    text = _cell_text(value).lower().replace('−', '-')
    text = re.sub(r'</?answer\b[^>]*>', '', text, flags=re.I)
    text = text.replace(r'\left', '').replace(r'\right', '').replace(r'\dfrac', r'\frac')
    text = text.strip().strip('$').strip()
    text = re.sub(r'^\s*(?:answer\s*(?:is|=|:)|=)\s*', '', text, flags=re.I)
    text = re.sub(r'\s+', '', text)
    return text.strip(' .,:;!')


def mirage_answers_match(parsed: Any, answer: Any, question_type: str) -> bool:
    if question_type == 'multi_choice':
        pred_letter = _extract_mcq_letter(parsed)
        answer_letter = _extract_mcq_letter(answer)
        return pred_letter is not None and pred_letter == answer_letter

    pred_literal = _literal_value(parsed)
    answer_literal = _literal_value(answer)
    if pred_literal is not None and answer_literal is not None:
        return pred_literal == answer_literal

    pred_number = _numeric_value(parsed)
    answer_number = _numeric_value(answer)
    if pred_number is not None and answer_number is not None:
        if question_type == 'approx':
            if pred_number == answer_number:
                return True
            denominator = max(abs(pred_number), abs(answer_number))
            return denominator > 0 and abs(pred_number - answer_number) / denominator <= 0.05
        return math.isclose(pred_number, answer_number, rel_tol=0.0, abs_tol=1e-9)

    return bool(_normalize_answer_text(parsed)) and _normalize_answer_text(parsed) == _normalize_answer_text(answer)


def mirage_acc(result_file: str) -> pd.DataFrame:
    data = load(result_file)
    hits = []
    for _, line in data.iterrows():
        hits.append(
            int(
                mirage_answers_match(
                    line.get('parsed_answer'),
                    line.get('answer'),
                    _question_type(line),
                )
            )
        )
    data['hit'] = hits
    dump(data, result_file)

    rows = []
    groups = [('Overall', data)]
    if 'normalized_classification' in data:
        for category in MIRAGE_CATEGORIES:
            groups.append((category, data[data['normalized_classification'] == category]))
        extras = sorted(set(data['normalized_classification'].dropna().astype(str)) - set(MIRAGE_CATEGORIES))
        groups.extend((category, data[data['normalized_classification'] == category]) for category in extras)

    for name, group in groups:
        total = int(len(group))
        correct = int(group['hit'].sum()) if total else 0
        rows.append(
            {
                'split': name,
                'total': total,
                'correct': correct,
                'accuracy': (100.0 * correct / total) if total else None,
            }
        )
    return pd.DataFrame(rows)


class MIRAGE(ImageBaseDataset):
    """MIRAGE multimodal reasoning-chain hallucination benchmark."""

    TYPE = 'VQA'
    DATASET_URL = {
        'MIRAGE': 'https://huggingface.co/datasets/DongSky/mirage/resolve/main/mirage.tsv',
    }
    DATASET_MD5 = {'MIRAGE': 'eb008699c714c29b1356f81906ff7e6f'}
    IMAGE_ARCHIVE_URL = (
        'https://huggingface.co/datasets/DongSky/mirage/resolve/main/mirage_images.zip'
    )
    IMAGE_ARCHIVE_MD5 = 'db2715770f876f7cf8e5c2d5a86d2cce'
    DEFAULT_JUDGE = QWEN3_JUDGE_API_MODEL

    def _expected_image_paths(self, image_values: Any) -> list[Path]:
        root = Path(self.img_root)
        return [root / _cell_text(value) for value in image_values]

    def _download_image_archive(self, archive: Path) -> None:
        if archive.exists() and md5(str(archive)) == self.IMAGE_ARCHIVE_MD5:
            return
        if archive.exists():
            archive.unlink()
        tmp = archive.with_name(f'{archive.name}.tmp.{os.getpid()}')
        try:
            download_file(self.IMAGE_ARCHIVE_URL, str(tmp))
            if md5(str(tmp)) != self.IMAGE_ARCHIVE_MD5:
                raise RuntimeError(f'MIRAGE image archive checksum mismatch: {tmp}')
            tmp.replace(archive)
        finally:
            if tmp.exists():
                tmp.unlink()

    def _extract_image_archive(self, archive: Path) -> None:
        root = Path(self.img_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.is_dir() or member.filename.startswith('__MACOSX/'):
                    continue
                target = (root / member.filename).resolve()
                if not target.is_relative_to(root):
                    raise RuntimeError(f'Unsafe path in MIRAGE image archive: {member.filename}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open('wb') as destination:
                    shutil.copyfileobj(source, destination)

    def _ensure_images(self, image_values: Any) -> list[Path]:
        expected = self._expected_image_paths(image_values)
        if expected and all(path.is_file() for path in expected):
            return expected

        data_root = Path(LMUDataRoot())
        archive = data_root / 'MIRAGE_images.zip'
        lock_path = data_root / 'MIRAGE_images.lock'
        with portalocker.Lock(str(lock_path), 'w', timeout=600):
            if not expected or not all(path.is_file() for path in expected):
                self._download_image_archive(archive)
                self._extract_image_archive(archive)

        missing = [str(path) for path in expected if not path.is_file()]
        if missing:
            preview = ', '.join(missing[:3])
            raise FileNotFoundError(f'MIRAGE image extraction is incomplete; missing {len(missing)} files: {preview}')
        return expected

    def load_data(self, dataset: str) -> pd.DataFrame:
        data = self.prepare_tsv(self.DATASET_URL[dataset], self.DATASET_MD5[dataset]).copy()
        if 'index' not in data:
            data.insert(0, 'index', range(len(data)))
        if 'image' not in data:
            raise ValueError('MIRAGE metadata must contain the released `image` column.')

        image_paths = self._ensure_images(data['image'].tolist())
        data['image_path'] = [str(path) for path in image_paths]
        data.drop(columns=['image'], inplace=True)

        if 'prompt' not in data:
            raise ValueError('MIRAGE metadata must contain the released `prompt` column.')
        if 'question' not in data:
            data['question'] = data['prompt']
        else:
            data['question'] = data['question'].where(~data['question'].isna(), data['prompt'])
        return data

    def build_prompt(self, line: Any) -> list[dict[str, str]]:
        if isinstance(line, int):
            line = self.data.iloc[line]
        image_paths = toliststr(line['image_path'])
        messages = [dict(type='image', value=path) for path in image_paths]
        messages.append(dict(type='text', value=_strip_image_placeholders(line['prompt'])))
        return messages

    @classmethod
    def report_primary_metric(cls, metrics: dict[str, Any] | None) -> dict[str, float | int]:
        if isinstance(metrics, dict) and 'split=Overall|accuracy' in metrics:
            return {'Overall Accuracy': metrics['split=Overall|accuracy']}
        return super().report_primary_metric(metrics)

    def evaluate(self, eval_file: str, **judge_kwargs: Any) -> pd.DataFrame:
        judge_kwargs = dict(judge_kwargs)
        judge_name = judge_kwargs.pop('model', self.DEFAULT_JUDGE)
        if isinstance(judge_name, list):
            judge_name = judge_name[0]
        judge_name = str(judge_name)
        nproc = int(judge_kwargs.pop('nproc', 4))
        safe_judge_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', judge_name)
        storage = get_intermediate_file_path(eval_file, f'_{safe_judge_name}')
        tmp_file = get_intermediate_file_path(eval_file, f'_{safe_judge_name}', 'pkl')

        if not osp.exists(storage):
            data = load(eval_file)
            required = {'index', 'answer', 'prediction'}
            missing = required - set(data.columns)
            if missing:
                raise ValueError(f'MIRAGE evaluation file is missing columns: {sorted(missing)}')

            judge = None
            if judge_name.lower() not in {'exact_matching', 'none'}:
                judge = build_judge(model=judge_name, max_tokens=128, **judge_kwargs)
                assert judge.working(), 'MIRAGE evaluation requires a working extraction judge\n' + DEBUG_MESSAGE

            lines = [data.iloc[i] for i in range(len(data))]
            indices = [line['index'] for line in lines]
            answers = load(tmp_file) if osp.exists(tmp_file) else {}
            pending_lines = [line for line, index in zip(lines, indices) if index not in answers]
            pending_indices = [index for index in indices if index not in answers]
            if pending_indices:
                results = track_progress_rich(
                    mirage_auxeval,
                    [(judge, line) for line in pending_lines],
                    nproc=nproc,
                    chunksize=max(1, nproc),
                    keys=pending_indices,
                    save=tmp_file,
                )
                answers = load(tmp_file)
                for index, result in zip(pending_indices, results):
                    assert index in answers and answers[index] == result

            data['parsed_answer'] = [answers[index]['parsed_answer'] for index in indices]
            data['judge_output'] = [answers[index].get('judge_output', '') for index in indices]
            data['judge_log'] = [answers[index]['judge_log'] for index in indices]
            if judge_name.lower() in {'exact_matching', 'none'}:
                judge_api_model = judge_name
                judge_model = judge_name
            else:
                judge_api_model = os.environ.get('LOCAL_LLM') or judge_name
                judge_model = (
                    QWEN3_JUDGE_MODEL
                    if (
                        judge_api_model == QWEN3_JUDGE_API_MODEL
                        or judge_name == QWEN3_JUDGE_API_MODEL
                    )
                    else judge_name
                )
            data['judge_model'] = judge_model
            data['judge_api_model'] = judge_api_model
            dump(data, storage)

        score = mirage_acc(storage)
        score_path = get_intermediate_file_path(storage, '_score', 'csv')
        dump(score, score_path)
        return score
