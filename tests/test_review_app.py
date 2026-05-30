from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time

from PIL import Image

from trace.review_app.artifact_index import build_review_index
from trace.review_app.feedback import FeedbackStore


TASK_ID = "task_pages__workspace__professional_target_label"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _make_review_fixture(tmp_path: Path, *, prompt: str = "What label is on the target control?") -> Path:
    root = tmp_path / "review" / "task-reviews"
    task_dir = root / "pages" / "workspace" / TASK_ID
    image_rel = f"pages/workspace/{TASK_ID}/images/lookup/0000.png"
    data_rel = f"pages/workspace/{TASK_ID}/data/lookup/0000.json"

    image_path = root / image_rel
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 90), (245, 247, 250)).save(image_path)

    _write_json(
        root / "pages" / "workspace" / "scene_review_manifest.json",
        {
            "calibration_baseline": "v0",
            "domain": "pages",
            "scene_id": "workspace",
            "task_count": 1,
            "inspection_count": 1,
            "workbook": "pages/workspace/scene_review.xlsx",
            "tasks": {TASK_ID: {"task_manifest": f"pages/workspace/{TASK_ID}/manifest.json"}},
        },
    )
    _write_json(
        task_dir / "manifest.json",
        {
            "calibration_baseline": "v0",
            "inspection_count": 1,
            "query_ids": {"lookup": 1},
            "task_id": TASK_ID,
            "workbook": f"pages/workspace/{TASK_ID}/{TASK_ID}.xlsx",
        },
    )
    _write_json(
        task_dir / "distribution_review.json",
        {
            "task_id": TASK_ID,
            "domain": "pages",
            "scene_id": "workspace",
            "mode": "single_sample",
            "pass": True,
            "overall": {
                "checks": {
                    "max_answer_frequency": {
                        "observed": 0.25,
                        "pass": True,
                        "threshold": 0.3333333333333333,
                    },
                    "max_five_bin_frequency": {
                        "observed": 0.335,
                        "pass": None,
                        "status": "reported_not_gated_numeric_answers",
                    },
                    "min_unique_answers": {
                        "observed": 5,
                        "pass": True,
                        "threshold": 5,
                    },
                },
                "max_answer_frequency": 0.25,
                "sample_count": 100,
                "unique_answers": 5,
            },
        },
    )
    _write_json(
        root / data_rel,
        {
            "answer_gt": {"type": "option_letter", "value": "G"},
            "domain": "pages",
            "evidence_gt": {"type": "bbox_set", "value": [[10, 10, 40, 40]]},
            "image": {"format": "png", "path": image_rel},
            "instance_seed": 123,
            "prompt": prompt,
            "prompt_variants": {
                "answer_only": prompt + " Answer only.",
                "answer_and_evidence": prompt + " Include evidence.",
            },
            "query_id": "lookup",
            "scene_id": "workspace",
            "task": TASK_ID,
            "trace_payload": {
                "execution_trace": {"query_id": "lookup"},
                "taxonomy": {
                    "public": {
                        "domain": "pages",
                        "scene_id": "workspace",
                        "task_id": TASK_ID,
                        "query_id": "lookup",
                    }
                },
            },
        },
    )
    return root


def _write_accepted_solve_status(root: Path) -> None:
    _write_json(
        root.parent / "calibration_sweep_status.json",
        {
            "config": {"calibration_baseline": "v0"},
            "tasks": {
                TASK_ID: {
                    "domain": "pages",
                    "scene_id": "workspace",
                    "status": "accepted",
                    "models": {
                        "qwen25vl7b": {
                            "status": "accepted",
                            "stats": {
                                "overall": {
                                    "mean_solve_rate": 0.42,
                                    "hard_frac": 0.08,
                                    "easy_frac": 0.12,
                                    "band_frac": 0.80,
                                    "prompt_count": 100,
                                    "rollout_count": 2400,
                                },
                                "prompt_token_stats": {"over_limit_count": 0},
                                "response_token_stats": {"cap_rate": 0.0},
                            },
                        }
                    },
                }
            },
        },
    )


def test_review_index_scans_domain_scene_task_query_samples(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)
    _write_json(
        root / "assets" / "fonts" / "scene_review_manifest.json",
        {"domain": "assets", "scene_id": "fonts", "task_count": 99},
    )
    _write_json(
        root / "scratch_domain" / "scratch_scene" / "scene_review_manifest.json",
        {"domain": "scratch_domain", "scene_id": "scratch_scene", "task_count": 99},
    )

    index = build_review_index(root, repo_root=tmp_path)

    assert sorted(index.domains) == ["pages"]
    assert sorted(index.scenes) == ["pages/workspace"]
    assert sorted(index.tasks) == [f"pages/workspace/{TASK_ID}"]
    assert len(index.samples) == 1
    task = index.tasks[f"pages/workspace/{TASK_ID}"]
    assert task.query_counts == {"lookup": 1}
    assert task.distribution_pass is True
    sample = next(iter(index.samples.values()))
    assert sample.answer_value == "G"
    assert sample.image_exists is True
    assert sample.image_mtime_ns > 0
    assert index.media[sample.media_id].exists()
    assert "assets" not in index.domains
    assert "scratch_domain" not in index.domains
    assert "assets/fonts" not in index.scenes


def test_review_sample_uid_changes_when_sample_content_changes(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path, prompt="First prompt")
    first_uid = next(iter(build_review_index(root, repo_root=tmp_path).samples))

    _make_review_fixture(tmp_path, prompt="Changed prompt")
    second_uid = next(iter(build_review_index(root, repo_root=tmp_path).samples))

    assert first_uid != second_uid


def test_feedback_store_persists_and_updates_records(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)
    sample = next(iter(build_review_index(root, repo_root=tmp_path).samples.values()))
    store = FeedbackStore(tmp_path / "feedback.sqlite")

    created = store.add_feedback(sample=sample, comment="Evidence box is too broad.", category="evidence")
    updated = store.update_feedback(created.id, status="resolved", severity="note")

    assert updated.status == "resolved"
    assert updated.severity == "note"
    assert store.list_for_sample(sample.uid)[0].comment == "Evidence box is too broad."
    assert store.counts_by_task()[f"pages/workspace/{TASK_ID}"]["resolved"] == 1

    task_feedback = store.add_task_feedback(
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
        comment="Needs more font variation across samples.",
    )
    assert task_feedback.sample_uid == ""
    assert store.list_task_feedback(domain="pages", scene_id="workspace", task_id=TASK_ID)[0].comment == (
        "Needs more font variation across samples."
    )
    assert sample.uid in store.counts_by_sample()
    assert "" not in store.counts_by_sample()
    assert store.counts_by_task()[f"pages/workspace/{TASK_ID}"]["total"] == 2
    assert [record.comment for record in store.list_open_feedback()] == ["Needs more font variation across samples."]

    note = store.add_feedback_note(
        created.id,
        note="Narrowed the evidence box and regenerated the review sample.",
        author="agent",
    )
    comment = store.add_feedback_comment(
        created.id,
        comment="Reviewer confirmed the new box is closer, but still slightly tall.",
        author="reviewer",
    )
    assert note.feedback_id == created.id
    assert note.author == "agent"
    assert comment.feedback_id == created.id
    assert comment.author == "reviewer"
    assert store.list_comments_for_feedback(created.id)[0].comment == (
        "Reviewer confirmed the new box is closer, but still slightly tall."
    )
    assert store.list_notes_for_feedback(created.id)[0].note == (
        "Narrowed the evidence box and regenerated the review sample."
    )
    exported = {record["id"]: record for record in store.export_records()}
    assert exported[created.id]["reviewer_comments"][0]["comment"] == (
        "Reviewer confirmed the new box is closer, but still slightly tall."
    )
    assert exported[created.id]["agent_notes"][0]["note"] == "Narrowed the evidence box and regenerated the review sample."


def test_feedback_store_persists_task_audit_status(tmp_path: Path) -> None:
    store = FeedbackStore(tmp_path / "feedback.sqlite")

    default = store.get_task_audit(domain="pages", scene_id="workspace", task_id=TASK_ID)
    assert default.manual_pass is False
    assert default.passed_count == 0

    updated = store.update_task_audit(
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
        prompt_pass=True,
        image_pass=True,
        evidence_pass=True,
        distribution_pass=True,
        solve_rate_pass=True,
        updated_by="reviewer",
    )

    assert updated.manual_pass is True
    assert updated.passed_count == 5
    assert store.task_audits_by_task()[f"pages/workspace/{TASK_ID}"].updated_by == "reviewer"


def test_review_app_requires_token_and_serves_index(tmp_path: Path) -> None:
    fastapi = __import__("pytest").importorskip("fastapi")
    assert fastapi is not None
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    assert client.get("/api/index").status_code == 401
    response = client.get("/api/index", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.json()["sample_count"] == 1

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "TRACE Review" in page.text


def test_review_app_supports_proxy_base_url(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    asset_image = root / "assets" / "fonts" / "readout_pool_v0" / "readout_pool_v0_spritesheet.png"
    asset_image.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (180, 80), (255, 255, 255)).save(asset_image)
    _write_json(
        root / "assets" / "fonts" / "readout_pool_v0" / "readout_pool_v0_spritesheet_manifest.json",
        {"title": "Readout font pool"},
    )
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
        base_url="/proxy/7860",
    )
    client = TestClient(app)

    redirect = client.get("/", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/proxy/7860/login?next=/"

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert 'href="/proxy/7860/domains/pages"' in page.text
    assert 'href="/proxy/7860/static/app.css?v=' in page.text
    assert 'src="/proxy/7860/static/app.js?v=' in page.text
    assert "Review root: review/task-reviews" in page.text
    assert str(root.resolve()) not in page.text
    assert 'class="site-header"' in page.text
    assert 'class="sidebar"' not in page.text
    assert 'data-suggest-url="/proxy/7860/api/search-suggest"' in page.text
    assert 'href="/proxy/7860/resources"' in page.text
    assert 'href="/proxy/7860/feedback"' in page.text
    assert 'class="theme-switch"' in page.text
    assert 'data-theme-choice="dark"' in page.text
    assert 'data-theme-choice="light"' in page.text

    suggestions = client.get("/api/search-suggest?q=workspace", headers={"Authorization": "Bearer secret"})
    assert suggestions.status_code == 200
    results = suggestions.json()["results"]
    assert any(
        result["type"] == "scene" and result["url"] == "/proxy/7860/domains/pages/scenes/workspace"
        for result in results
    )
    assert any(result["type"] == "task" and result["label"] == TASK_ID for result in results)

    task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}",
        headers={"Authorization": "Bearer secret"},
    )
    assert task_page.status_code == 200
    assert 'data-preview-root data-active-view="rows"' in task_page.text
    assert 'data-preview-switch="rows"' in task_page.text
    assert 'data-preview-switch="images"' in task_page.text
    assert 'class="sample-row-list"' in task_page.text
    assert 'class="sample-row"' in task_page.text
    assert 'data-task-feedback-toggle' in task_page.text
    assert 'data-task-feedback-form' in task_page.text
    assert "<h2>Distribution</h2>" in task_page.text
    assert "PASS" in task_page.text
    assert "mode single_sample" in task_page.text
    assert "max_answer_frequency" in task_page.text
    assert "min_unique_answers" in task_page.text
    assert "max_five_bin_frequency" not in task_page.text
    assert "reported_not_gated_numeric_answers" not in task_page.text
    assert "Query Collection" not in task_page.text
    assert "<th>Generated</th>" not in task_page.text
    assert 'name="distribution_pass" value="1" checked' in task_page.text
    assert f"/media/{next(iter(app.state.review.index().samples.values())).media_id}?v=" in task_page.text
    assert "Include evidence." in task_page.text
    assert "answer" in task_page.text
    assert "evidence" in task_page.text

    sample = next(iter(app.state.review.index().samples.values()))
    image_task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        headers={"Authorization": "Bearer secret"},
    )
    assert image_task_page.status_code == 200
    assert 'data-preview-root data-active-view="images"' in image_task_page.text
    assert 'class="image-only-grid"' in image_task_page.text
    assert 'class="image-only-card"' in image_task_page.text
    assert 'class="image-pair-card"' in image_task_page.text
    assert "Original" in image_task_page.text
    assert "Evidence" in image_task_page.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in image_task_page.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in image_task_page.text
    assert 'class="sample-row-list"' in image_task_page.text
    assert f"/domains/pages/scenes/workspace/tasks/{TASK_ID}/queries/lookup?view=images" in image_task_page.text

    task_feedback = client.post(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}/feedback",
        headers={"Authorization": "Bearer secret"},
        data={
            "comment": "Task-level note.",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert task_feedback.status_code == 303
    assert task_feedback.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    task_thread = app.state.review.feedback.list_task_feedback(domain="pages", scene_id="workspace", task_id=TASK_ID)[0]
    assert task_thread.comment == "Task-level note."

    sample_feedback = app.state.review.feedback.add_feedback(
        sample=sample,
        comment="Evidence should be tighter.",
        category="evidence",
    )
    feedback_note = client.post(
        f"/feedback/{sample_feedback.id}/notes",
        headers={"Authorization": "Bearer secret"},
        data={
            "note": "Adjusted evidence projection and regenerated the task review.",
            "author": "agent",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert feedback_note.status_code == 303
    assert feedback_note.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    assert app.state.review.feedback.list_notes_for_feedback(sample_feedback.id)[0].note == (
        "Adjusted evidence projection and regenerated the task review."
    )
    feedback_comment = client.post(
        f"/feedback/{sample_feedback.id}/comments",
        headers={"Authorization": "Bearer secret"},
        data={
            "comment": "Reviewer follow-up should stay on the same thread.",
            "author": "reviewer",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert feedback_comment.status_code == 303
    assert feedback_comment.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    assert app.state.review.feedback.list_comments_for_feedback(sample_feedback.id)[0].comment == (
        "Reviewer follow-up should stay on the same thread."
    )

    image_task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        headers={"Authorization": "Bearer secret"},
    )
    assert "Evidence should be tighter." in image_task_page.text
    assert "Adjusted evidence projection and regenerated the task review." in image_task_page.text
    assert "Reviewer follow-up should stay on the same thread." in image_task_page.text
    assert "Continue task feedback" in image_task_page.text
    assert f'action="/proxy/7860/feedback/{task_thread.id}/comments"' in image_task_page.text
    assert "Continue existing sample feedback" in image_task_page.text
    assert f'action="/proxy/7860/feedback/{sample_feedback.id}/comments"' in image_task_page.text
    assert f'href="/proxy/7860/feedback/{sample_feedback.id}"' in image_task_page.text
    assert "Brief repair note after changing code or artifacts" not in image_task_page.text

    sample_page = client.get(f"/samples/{sample.uid}", headers={"Authorization": "Bearer secret"})
    assert sample_page.status_code == 200
    assert 'class="sample-image-pair"' in sample_page.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in sample_page.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in sample_page.text
    assert "Reviewer follow-up should stay on the same thread." in sample_page.text
    assert "Adjusted evidence projection and regenerated the task review." in sample_page.text
    assert "Brief repair note after changing code or artifacts" not in sample_page.text

    feedback_queue = client.get("/feedback", headers={"Authorization": "Bearer secret"})
    assert feedback_queue.status_code == 200
    assert "Feedback Work Queue" in feedback_queue.text
    assert "Task-level note." in feedback_queue.text
    assert "Evidence should be tighter." in feedback_queue.text
    assert "Missing manual audit: prompt, image, evidence" in feedback_queue.text
    assert "Missing manual audit: prompt, image, evidence, distribution" not in feedback_queue.text
    assert "Solve-rate manual checkbox not checked" in feedback_queue.text
    assert "Automated solve-rate missing" in feedback_queue.text
    assert f'href="/proxy/7860/samples/{sample.uid}"' in feedback_queue.text
    assert f'href="/proxy/7860/feedback/{sample_feedback.id}"' in feedback_queue.text

    feedback_thread = client.get(f"/feedback/{sample_feedback.id}", headers={"Authorization": "Bearer secret"})
    assert feedback_thread.status_code == 200
    assert "Reviewer Feedback" in feedback_thread.text
    assert "Reviewer Follow-Ups" in feedback_thread.text
    assert "Repair Notes" in feedback_thread.text
    assert "Evidence should be tighter." in feedback_thread.text
    assert "Reviewer follow-up should stay on the same thread." in feedback_thread.text
    assert "Adjusted evidence projection and regenerated the task review." in feedback_thread.text
    assert f'href="/proxy/7860/samples/{sample.uid}"' in feedback_thread.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in feedback_thread.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in feedback_thread.text

    resolve = client.post(
        f"/feedback/{sample_feedback.id}",
        headers={"Authorization": "Bearer secret"},
        data={"status": "resolved", "next": "/feedback"},
        follow_redirects=False,
    )
    assert resolve.status_code == 303
    assert resolve.headers["location"] == "/proxy/7860/feedback"
    feedback_queue = client.get("/feedback", headers={"Authorization": "Bearer secret"})
    assert "Task-level note." in feedback_queue.text
    assert "Evidence should be tighter." not in feedback_queue.text

    assets_redirect = client.get("/domains/assets", headers={"Authorization": "Bearer secret"}, follow_redirects=False)
    assert assets_redirect.status_code == 303
    assert assets_redirect.headers["location"] == "/proxy/7860/resources"

    resources_page = client.get("/resources", headers={"Authorization": "Bearer secret"})
    assert resources_page.status_code == 200
    assert "fonts / readout pool v0" in resources_page.text
    assert "readout_pool_v0_spritesheet.png" in resources_page.text
    assert "readout_pool_v0_spritesheet_manifest.json" in resources_page.text
    media_match = re.search(r'href="/proxy/7860/resources/media/([^"]+)"', resources_page.text)
    assert media_match is not None
    resource_media = client.get(f"/resources/media/{media_match.group(1)}", headers={"Authorization": "Bearer secret"})
    assert resource_media.status_code == 200
    assert resource_media.headers["cache-control"] == "no-cache"

    media = client.get(f"/media/{sample.media_id}", headers={"Authorization": "Bearer secret"})
    assert media.status_code == 200
    assert media.headers["cache-control"] == "no-cache"

    static_asset = client.get("/static/app.css")
    assert static_asset.status_code == 200
    assert ":root" in static_asset.text


def test_review_app_shows_and_updates_task_audit_status(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    _write_accepted_solve_status(root)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    domain_page = client.get("/domains/pages", headers={"Authorization": "Bearer secret"})
    assert domain_page.status_code == 200
    assert "Manual 0/1" in domain_page.text
    assert "Solve 1/1" in domain_page.text
    assert "Completed 0/1" in domain_page.text

    update = client.patch(
        f"/api/tasks/pages/workspace/{TASK_ID}/audit",
        headers={"Authorization": "Bearer secret"},
        json={
            "prompt_pass": True,
            "image_pass": True,
            "evidence_pass": True,
            "distribution_pass": True,
            "solve_rate_pass": True,
            "updated_by": "reviewer",
        },
    )
    assert update.status_code == 200
    assert update.json()["status"]["complete"] is True

    domain_page = client.get("/domains/pages", headers={"Authorization": "Bearer secret"})
    assert "Manual 1/1" in domain_page.text
    assert "Solve 1/1" in domain_page.text
    assert "Completed 1/1" in domain_page.text

    scene_page = client.get("/domains/pages/scenes/workspace", headers={"Authorization": "Bearer secret"})
    assert scene_page.status_code == 200
    assert "manual 5/5" in scene_page.text
    assert "completed" in scene_page.text


def test_review_app_warns_when_review_artifacts_are_stale(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "Review artifacts changed." not in page.text

    touched = root / "pages" / "workspace" / TASK_ID / "manifest.json"
    future = time.time() + 5
    os.utime(touched, (future, future))
    app.state.review._stale_cache_until_ns = 0

    stale_page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert "Review artifacts changed." in stale_page.text
    assert "Reload Index before inspecting generated samples." in stale_page.text

    reload_response = client.post("/api/reload", headers={"Authorization": "Bearer secret"})
    assert reload_response.status_code == 200
    fresh_page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert "Review artifacts changed." not in fresh_page.text


def test_review_app_adds_feedback_via_api(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    sample_uid = next(iter(app.state.review.index().samples))
    client = TestClient(app)

    response = client.post(
        f"/api/samples/{sample_uid}/feedback",
        headers={"Authorization": "Bearer secret"},
        json={"comment": "Prompt wording is confusing.", "category": "prompt", "severity": "issue"},
    )

    assert response.status_code == 200
    assert response.json()["feedback"]["category"] == "prompt"
    listed = client.get(f"/api/samples/{sample_uid}/feedback", headers={"Authorization": "Bearer secret"})
    assert listed.json()["feedback"][0]["comment"] == "Prompt wording is confusing."
