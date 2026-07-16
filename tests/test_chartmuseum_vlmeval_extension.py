from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
for path in (VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from batched_chartmuseum_vllm import (  # noqa: E402
    format_question_prompt,
    make_vl_requests,
)
from vlmeval.dataset.chartmuseum import get_question  # noqa: E402


def test_chartmuseum_extension_uses_exact_official_question_template() -> None:
    question = "What is the value of the final point?"

    assert format_question_prompt(question) == get_question(question)


def test_chartmuseum_legacy_request_preserves_official_image_text_order(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "chart.png"
    Image.new("RGB", (32, 24), "white").save(image_path)

    class Processor:
        messages = None

        def apply_chat_template(self, messages, **_kwargs):
            self.messages = messages
            return "rendered prompt"

    processor = Processor()
    requests = make_vl_requests(
        processor,
        [{"question": "Read the chart.", "image_path": image_path}],
    )

    assert requests[0]["prompt"] == "rendered prompt"
    assert processor.messages[0]["content"] == [
        {"type": "image"},
        {"type": "text", "text": get_question("Read the chart.")},
    ]
    assert requests[0]["multi_modal_data"]["image"][0].size == (32, 24)
