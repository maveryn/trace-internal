"""FastAPI server for browsing TRACE task-review artifacts."""

from __future__ import annotations

from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict
from urllib.parse import parse_qs, quote, unquote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image as PILImage

from trace.core.review_overlays import render_evidence_overlay, resolve_overlay_evidence

from .artifact_index import build_review_index, load_sample_payload
from .feedback import FeedbackStore
from .models import ReviewIndex, SampleRecord, TaskAuditRecord
from .resource_index import build_resource_index


class ReviewAppState:
    """Mutable app state shared by routes."""

    def __init__(self, *, review_root: Path, repo_root: Path, feedback_db: Path) -> None:
        self.review_root = Path(review_root).resolve()
        self.repo_root = Path(repo_root).resolve()
        self.feedback = FeedbackStore(feedback_db)
        self._lock = threading.RLock()
        self._index = build_review_index(self.review_root, repo_root=self.repo_root)
        self._review_mtime_snapshot_ns = _max_review_file_mtime_ns(self.review_root)
        self._stale_cache = False
        self._stale_cache_until_ns = 0
        self._stale_check_interval_ns = 2_000_000_000

    def index(self) -> ReviewIndex:
        with self._lock:
            return self._index

    def reload(self) -> ReviewIndex:
        fresh = build_review_index(self.review_root, repo_root=self.repo_root)
        fresh_mtime = _max_review_file_mtime_ns(self.review_root)
        with self._lock:
            self._index = fresh
            self._review_mtime_snapshot_ns = fresh_mtime
            self._stale_cache = False
            self._stale_cache_until_ns = 0
            return self._index

    def review_artifacts_stale(self) -> bool:
        now = time.monotonic_ns()
        with self._lock:
            if now < self._stale_cache_until_ns:
                return self._stale_cache
            snapshot = self._review_mtime_snapshot_ns
            interval = self._stale_check_interval_ns
        stale = _max_review_file_mtime_ns(self.review_root) > snapshot
        with self._lock:
            self._stale_cache = stale
            self._stale_cache_until_ns = now + interval
        return stale


def create_app(
    *,
    review_root: Path | str = "review/task-reviews",
    repo_root: Path | str | None = None,
    feedback_db: Path | str | None = None,
    token: str | None = None,
    base_url: str = "",
) -> FastAPI:
    """Create the task-review web app."""

    resolved_review_root = Path(review_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root(resolved_review_root)
    resolved_base_url = _normalize_base_url(base_url)
    resolved_feedback_db = (
        Path(feedback_db).resolve()
        if feedback_db is not None
        else resolved_repo_root / "review" / "feedback" / "review_feedback.sqlite"
    )
    state = ReviewAppState(
        review_root=resolved_review_root,
        repo_root=resolved_repo_root,
        feedback_db=resolved_feedback_db,
    )

    package_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(package_dir / "templates"))
    templates.env.filters["pretty_json"] = _pretty_json
    templates.env.filters["rate"] = _format_rate
    templates.env.filters["excerpt"] = _excerpt
    templates.env.filters["urlquote"] = lambda value: quote(str(value), safe="")
    templates.env.globals["app_path"] = lambda path="": _app_path(resolved_base_url, str(path))
    templates.env.globals["static_version"] = _static_version(package_dir / "static")

    # Do not set FastAPI.root_path here. Jupyter Server Proxy strips the
    # external /proxy/<port> prefix before forwarding requests, while templates
    # still need to emit that prefix for browser-facing links.
    app = FastAPI(title="TRACE Task Review")
    app.state.review = state
    app.state.auth_token = str(token or "").strip()
    app.state.base_url = resolved_base_url
    app.mount("/static", StaticFiles(directory=str(package_dir / "static")), name="static")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Any) -> Response:
        if _request_is_public(request) or not app.state.auth_token:
            return await call_next(request)
        if _request_has_token(request, app.state.auth_token):
            return await call_next(request)
        if request.url.path.startswith("/api"):
            return JSONResponse({"detail": "authentication required"}, status_code=401)
        return RedirectResponse(
            _app_path(resolved_base_url, f"/login?next={quote(str(request.url.path), safe='/')}"),
            status_code=303,
        )

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: str = "/") -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "next": _safe_next(next), "has_token": bool(app.state.auth_token), "error": ""},
        )

    @app.post("/login")
    async def login_submit(request: Request) -> Response:
        form = await _request_data(request)
        submitted = str(form.get("token", "")).strip()
        next_url = _safe_next(str(form.get("next", "/")))
        if not app.state.auth_token or submitted == app.state.auth_token:
            response = RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
            if app.state.auth_token:
                response.set_cookie("trace_review_token", submitted, httponly=True, samesite="lax")
            return response
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "next": next_url, "has_token": True, "error": "Invalid token."},
            status_code=401,
        )

    @app.post("/logout")
    async def logout() -> RedirectResponse:
        response = RedirectResponse(_app_path(resolved_base_url, "/login"), status_code=303)
        response.delete_cookie("trace_review_token")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index_page(request: Request) -> HTMLResponse:
        index = state.index()
        return templates.TemplateResponse(request, "index.html", _context(request, index=index, title="Domains"))

    @app.get("/feedback", response_class=HTMLResponse)
    async def feedback_page(request: Request) -> HTMLResponse:
        index = state.index()
        queue = _build_feedback_work_queue(index=index, feedback=state.feedback)
        return templates.TemplateResponse(
            request,
            "feedback.html",
            _context(
                request,
                index=index,
                title="Feedback Work Queue",
                work_queue=queue["groups"],
                work_queue_summary=queue["summary"],
            ),
        )

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request, q: str = "") -> HTMLResponse:
        index = state.index()
        query = str(q).strip().lower()
        task_results = []
        sample_results = []
        if query:
            for task in index.tasks.values():
                haystack = " ".join([task.domain, task.scene_id, task.task_id, " ".join(task.query_counts)])
                if query in haystack.lower():
                    task_results.append(task)
            for sample in index.samples.values():
                haystack = " ".join(
                    [
                        sample.domain,
                        sample.scene_id,
                        sample.task_id,
                        sample.query_id,
                        sample.prompt,
                        sample.answer_label,
                    ]
                )
                if query in haystack.lower():
                    sample_results.append(sample)
                if len(sample_results) >= 200:
                    break
        return templates.TemplateResponse(
            request,
            "search.html",
            _context(
                request,
                index=index,
                title="Search",
                q=q,
                task_results=task_results[:200],
                sample_results=sample_results[:200],
            ),
        )

    @app.get("/api/search-suggest")
    async def api_search_suggest(q: str = "") -> Dict[str, Any]:
        return {"results": _search_suggestions(state.index(), q, base_url=resolved_base_url)}

    @app.get("/resources", response_class=HTMLResponse)
    async def resources_page(request: Request) -> HTMLResponse:
        index = state.index()
        resources = build_resource_index(state.review_root)
        return templates.TemplateResponse(
            request,
            "resources.html",
            _context(
                request,
                index=index,
                title="Resources",
                resources=resources,
                resource_root_display=_display_path(resources.assets_root, repo_root=state.repo_root),
            ),
        )

    @app.get("/resources/media/{asset_id}")
    async def resource_media(asset_id: str) -> FileResponse:
        resources = build_resource_index(state.review_root)
        asset = resources.assets.get(asset_id)
        if asset is None or not asset.path.exists():
            raise HTTPException(status_code=404, detail="unknown resource asset")
        return FileResponse(asset.path, headers={"Cache-Control": "no-cache"})

    @app.get("/domains/{domain}", response_class=HTMLResponse)
    async def domain_page(request: Request, domain: str) -> Response:
        if domain == "assets":
            return RedirectResponse(_app_path(resolved_base_url, "/resources"), status_code=303)
        index = state.index()
        domain_record = index.domains.get(domain)
        if domain_record is None:
            raise HTTPException(status_code=404, detail="unknown domain")
        scenes = [index.scenes[ReviewIndex.scene_key(domain, scene_id)] for scene_id in domain_record.scenes]
        return templates.TemplateResponse(
            request,
            "domain.html",
            _context(request, index=index, title=f"Domain: {domain}", domain_record=domain_record, scenes=scenes),
        )

    @app.get("/domains/{domain}/scenes/{scene_id}", response_class=HTMLResponse)
    async def scene_page(request: Request, domain: str, scene_id: str) -> HTMLResponse:
        index = state.index()
        scene = index.scenes.get(ReviewIndex.scene_key(domain, scene_id))
        if scene is None:
            raise HTTPException(status_code=404, detail="unknown scene")
        tasks = [index.tasks[ReviewIndex.task_key(domain, scene_id, task_id)] for task_id in scene.tasks]
        return templates.TemplateResponse(
            request,
            "scene.html",
            _context(request, index=index, title=f"Scene: {scene_id}", scene=scene, tasks=tasks),
        )

    @app.get("/domains/{domain}/scenes/{scene_id}/tasks/{task_id}", response_class=HTMLResponse)
    async def task_page(
        request: Request,
        domain: str,
        scene_id: str,
        task_id: str,
        query_id: str = "",
        view: str = "",
    ) -> HTMLResponse:
        return _task_page_response(
            request=request,
            index=state.index(),
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            query_id=query_id,
            view=view,
            templates=templates,
        )

    @app.get("/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/queries/{query_id}", response_class=HTMLResponse)
    async def query_page(
        request: Request,
        domain: str,
        scene_id: str,
        task_id: str,
        query_id: str,
        view: str = "",
    ) -> HTMLResponse:
        return _task_page_response(
            request=request,
            index=state.index(),
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            query_id=unquote(query_id),
            view=view,
            templates=templates,
        )

    @app.get("/samples/{sample_uid}", response_class=HTMLResponse)
    async def sample_page(request: Request, sample_uid: str) -> HTMLResponse:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        payload = load_sample_payload(index, sample)
        query_samples = index.samples_by_query.get(
            ReviewIndex.query_key(sample.domain, sample.scene_id, sample.task_id, sample.query_id),
            [],
        )
        previous_uid, next_uid = _neighbor_uids(query_samples, sample.uid)
        feedback_records = state.feedback.list_for_sample(sample.uid)
        feedback_ids = [record.id for record in feedback_records]
        return templates.TemplateResponse(
            request,
            "sample.html",
            _context(
                request,
                index=index,
                title=f"Sample: {sample.query_id}",
                sample=sample,
                payload=payload,
                feedback=feedback_records,
                reviewer_comments_by_feedback=state.feedback.comments_by_feedback(feedback_ids),
                agent_notes_by_feedback=state.feedback.notes_by_feedback(record.id for record in feedback_records),
                previous_uid=previous_uid,
                next_uid=next_uid,
            ),
        )

    @app.post("/samples/{sample_uid}/feedback")
    async def sample_feedback_submit(request: Request, sample_uid: str) -> RedirectResponse:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        data = await _request_data(request)
        state.feedback.add_feedback(
            sample=sample,
            comment=str(data.get("comment", "")),
            author=str(data.get("author", "")),
            category=str(data.get("category", "other")),
            severity=str(data.get("severity", "issue")),
        )
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        return RedirectResponse(_app_path(resolved_base_url, f"/samples/{sample_uid}#feedback"), status_code=303)

    @app.get("/feedback/{feedback_id}", response_class=HTMLResponse)
    async def feedback_detail_page(request: Request, feedback_id: str) -> HTMLResponse:
        index = state.index()
        try:
            record = state.feedback.get_feedback(feedback_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        sample = index.samples.get(record.sample_uid) if record.sample_uid else None
        task = index.tasks.get(ReviewIndex.task_key(record.domain, record.scene_id, record.task_id))
        task_path = (
            f"/domains/{_url_segment(record.domain)}"
            f"/scenes/{_url_segment(record.scene_id)}"
            f"/tasks/{_url_segment(record.task_id)}"
        )
        return templates.TemplateResponse(
            request,
            "feedback_detail.html",
            _context(
                request,
                index=index,
                title="Feedback Thread",
                feedback_record=record,
                feedback_comments=state.feedback.list_comments_for_feedback(record.id),
                feedback_notes=state.feedback.list_notes_for_feedback(record.id),
                feedback_sample=sample,
                feedback_task=task,
                feedback_task_path=task_path,
            ),
        )

    @app.post("/feedback/{feedback_id}")
    async def feedback_update_submit(request: Request, feedback_id: str) -> RedirectResponse:
        data = await _request_data(request)
        state.feedback.update_feedback(
            feedback_id,
            comment=data.get("comment"),
            author=data.get("author"),
            category=data.get("category"),
            severity=data.get("severity"),
            status=data.get("status"),
        )
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/feedback/{feedback_id}/comments")
    async def feedback_comment_submit(request: Request, feedback_id: str) -> RedirectResponse:
        data = await _request_data(request)
        try:
            state.feedback.add_feedback_comment(
                feedback_id,
                comment=str(data.get("comment", "")),
                author=str(data.get("author", "")),
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/feedback/{feedback_id}/notes")
    async def feedback_note_submit(request: Request, feedback_id: str) -> RedirectResponse:
        data = await _request_data(request)
        try:
            state.feedback.add_feedback_note(
                feedback_id,
                note=str(data.get("note", "")),
                author=str(data.get("author", "")),
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/audit")
    async def task_audit_submit(request: Request, domain: str, scene_id: str, task_id: str) -> RedirectResponse:
        index = state.index()
        task = index.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="unknown task")
        data = await _request_data(request)
        state.feedback.update_task_audit(
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            prompt_pass=_truthy(data.get("prompt_pass")),
            image_pass=_truthy(data.get("image_pass")),
            evidence_pass=_truthy(data.get("evidence_pass")),
            distribution_pass=_truthy(data.get("distribution_pass")),
            solve_rate_pass=_truthy(data.get("solve_rate_pass")),
            notes=str(data.get("notes", "")),
            updated_by=str(data.get("updated_by", "")),
        )
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/feedback")
    async def task_feedback_submit(request: Request, domain: str, scene_id: str, task_id: str) -> RedirectResponse:
        index = state.index()
        task = index.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="unknown task")
        data = await _request_data(request)
        state.feedback.add_task_feedback(
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            comment=str(data.get("comment", "")),
            author=str(data.get("author", "")),
            category=str(data.get("category", "other")),
            severity=str(data.get("severity", "issue")),
        )
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/api/reload")
    async def api_reload() -> Dict[str, Any]:
        return state.reload().as_summary()

    @app.get("/api/index")
    async def api_index() -> Dict[str, Any]:
        return state.index().as_summary()

    @app.get("/api/samples/{sample_uid}/feedback")
    async def api_sample_feedback(sample_uid: str) -> Dict[str, Any]:
        if sample_uid not in state.index().samples:
            raise HTTPException(status_code=404, detail="unknown sample")
        return {"feedback": [asdict(record) for record in state.feedback.list_for_sample(sample_uid)]}

    @app.get("/api/tasks/{domain}/{scene_id}/{task_id}/audit")
    async def api_get_task_audit(domain: str, scene_id: str, task_id: str) -> Dict[str, Any]:
        index = state.index()
        task = index.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="unknown task")
        audit = _effective_task_audit(
            task,
            state.feedback.get_task_audit(domain=domain, scene_id=scene_id, task_id=task_id),
        )
        effective_audit = _effective_task_audit(task, audit)
        return {
            "audit": asdict(effective_audit),
            "status": _task_status_payload(task=task, audit=effective_audit),
        }

    @app.post("/api/samples/{sample_uid}/feedback")
    async def api_add_sample_feedback(request: Request, sample_uid: str) -> Dict[str, Any]:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        data = await _request_data(request)
        record = state.feedback.add_feedback(
            sample=sample,
            comment=str(data.get("comment", "")),
            author=str(data.get("author", "")),
            category=str(data.get("category", "other")),
            severity=str(data.get("severity", "issue")),
        )
        return {"feedback": asdict(record)}

    @app.patch("/api/tasks/{domain}/{scene_id}/{task_id}/audit")
    async def api_update_task_audit(request: Request, domain: str, scene_id: str, task_id: str) -> Dict[str, Any]:
        index = state.index()
        task = index.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="unknown task")
        data = await _request_data(request)
        existing = _effective_task_audit(
            task,
            state.feedback.get_task_audit(domain=domain, scene_id=scene_id, task_id=task_id),
        )
        audit = state.feedback.update_task_audit(
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            prompt_pass=_truthy(data.get("prompt_pass", existing.prompt_pass)),
            image_pass=_truthy(data.get("image_pass", existing.image_pass)),
            evidence_pass=_truthy(data.get("evidence_pass", existing.evidence_pass)),
            distribution_pass=_truthy(data.get("distribution_pass", existing.distribution_pass)),
            solve_rate_pass=_truthy(data.get("solve_rate_pass", existing.solve_rate_pass)),
            notes=str(data.get("notes", existing.notes)),
            updated_by=str(data.get("updated_by", existing.updated_by)),
        )
        return {
            "audit": asdict(audit),
            "status": _task_status_payload(task=task, audit=audit),
        }

    @app.get("/api/feedback/export.jsonl")
    async def api_export_feedback(include_resolved: bool = True) -> Response:
        body = state.feedback.export_jsonl(include_resolved=include_resolved)
        if body:
            body += "\n"
        return Response(body, media_type="application/x-ndjson")

    @app.patch("/api/feedback/{feedback_id}")
    async def api_update_feedback(request: Request, feedback_id: str) -> Dict[str, Any]:
        data = await _request_data(request)
        try:
            record = state.feedback.update_feedback(
                feedback_id,
                comment=data.get("comment"),
                author=data.get("author"),
                category=data.get("category"),
                severity=data.get("severity"),
                status=data.get("status"),
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        return {"feedback": asdict(record)}

    @app.post("/api/feedback/{feedback_id}/comments")
    async def api_add_feedback_comment(request: Request, feedback_id: str) -> Dict[str, Any]:
        data = await _request_data(request)
        try:
            comment = state.feedback.add_feedback_comment(
                feedback_id,
                comment=str(data.get("comment", "")),
                author=str(data.get("author", "")),
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        return {"comment": asdict(comment)}

    @app.post("/api/feedback/{feedback_id}/notes")
    async def api_add_feedback_note(request: Request, feedback_id: str) -> Dict[str, Any]:
        data = await _request_data(request)
        try:
            note = state.feedback.add_feedback_note(
                feedback_id,
                note=str(data.get("note", "")),
                author=str(data.get("author", "")),
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        return {"note": asdict(note)}

    @app.get("/media/{media_id}")
    async def media(media_id: str) -> FileResponse:
        index = state.index()
        path = index.media.get(media_id)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="unknown media")
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    @app.get("/overlay/{sample_uid}.png")
    async def overlay(sample_uid: str) -> StreamingResponse:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        image_path = index.media.get(sample.media_id)
        if image_path is None or not image_path.exists():
            raise HTTPException(status_code=404, detail="sample image missing")
        payload = load_sample_payload(index, sample)
        evidence_gt = payload.get("evidence_gt", {}) if isinstance(payload, dict) else {}
        trace_payload = payload.get("trace_payload", {}) if isinstance(payload, dict) else {}
        evidence_type = str(evidence_gt.get("type", sample.evidence_type)) if isinstance(evidence_gt, dict) else sample.evidence_type
        evidence_value = evidence_gt.get("value", sample.evidence_value) if isinstance(evidence_gt, dict) else sample.evidence_value
        overlay_type, overlay_value = resolve_overlay_evidence(
            evidence_type=evidence_type,
            evidence_value=evidence_value,
            trace_payload=trace_payload if isinstance(trace_payload, dict) else {},
        )
        with PILImage.open(image_path) as source:
            rendered = render_evidence_overlay(
                source.convert("RGB"),
                evidence_type=str(overlay_type),
                evidence_value=overlay_value,
            )
            buffer = io.BytesIO()
            rendered.save(buffer, format="PNG")
            buffer.seek(0)
        return StreamingResponse(buffer, media_type="image/png")

    return app


def _task_page_response(
    *,
    request: Request,
    index: ReviewIndex,
    domain: str,
    scene_id: str,
    task_id: str,
    query_id: str,
    view: str,
    templates: Jinja2Templates,
) -> HTMLResponse:
    task = index.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="unknown task")
    query_ids = sorted(task.query_counts)
    selected_query_id = str(query_id or "")
    if selected_query_id:
        sample_ids = index.samples_by_query.get(ReviewIndex.query_key(domain, scene_id, task_id, selected_query_id), [])
    else:
        sample_ids = index.samples_by_task.get(ReviewIndex.task_key(domain, scene_id, task_id), [])
    samples = [index.samples[uid] for uid in sample_ids]
    selected_view = "images" if str(view or "").strip().lower() in {"image", "images", "grid"} else "rows"
    feedback = request.app.state.review.feedback
    sample_feedback_by_sample = {sample.uid: feedback.list_for_sample(sample.uid) for sample in samples}
    open_feedback_by_sample = {
        sample.uid: [record for record in sample_feedback_by_sample.get(sample.uid, []) if record.status == "open"]
        for sample in samples
    }
    primary_open_feedback_by_sample = {
        sample_uid: records[0]
        for sample_uid, records in open_feedback_by_sample.items()
        if records
    }
    task_level_feedback = feedback.list_task_feedback(domain=domain, scene_id=scene_id, task_id=task_id)
    task_open_feedback = [record for record in task_level_feedback if record.status == "open"]
    feedback_ids = [
        record.id
        for records in sample_feedback_by_sample.values()
        for record in records
    ] + [record.id for record in task_level_feedback]
    return templates.TemplateResponse(
        request,
        "task.html",
        _context(
            request,
            index=index,
            title=f"Task: {task_id}",
            task=task,
            query_ids=query_ids,
            selected_query_id=selected_query_id,
            selected_view=selected_view,
            samples=samples,
            sample_feedback_by_sample=sample_feedback_by_sample,
            open_feedback_by_sample=open_feedback_by_sample,
            primary_open_feedback_by_sample=primary_open_feedback_by_sample,
            task_level_feedback=task_level_feedback,
            task_open_feedback=task_open_feedback,
            primary_task_open_feedback=task_open_feedback[0] if task_open_feedback else None,
            reviewer_comments_by_feedback=feedback.comments_by_feedback(feedback_ids),
            agent_notes_by_feedback=feedback.notes_by_feedback(feedback_ids),
        ),
    )


def _build_feedback_work_queue(*, index: ReviewIndex, feedback: FeedbackStore) -> Dict[str, Any]:
    open_feedback = feedback.list_open_feedback()
    open_by_task: Dict[str, list[Any]] = {}
    for record in open_feedback:
        key = ReviewIndex.task_key(record.domain, record.scene_id, record.task_id)
        open_by_task.setdefault(key, []).append(record)

    audits = feedback.task_audits_by_task()
    task_entries = []
    summary = {
        "task_count": 0,
        "open_feedback_count": len(open_feedback),
        "manual_missing_count": 0,
        "solve_manual_missing_count": 0,
        "automated_solve_missing_count": 0,
        "automated_solve_not_accepted_count": 0,
    }
    for task_key, task in sorted(index.tasks.items()):
        audit = _effective_task_audit(
            task,
            audits.get(task_key) or TaskAuditRecord.empty(
                domain=task.domain,
                scene_id=task.scene_id,
                task_id=task.task_id,
            ),
        )
        missing_manual = []
        if not audit.prompt_pass:
            missing_manual.append("prompt")
        if not audit.image_pass:
            missing_manual.append("image")
        if not audit.evidence_pass:
            missing_manual.append("evidence")
        if not audit.distribution_pass:
            missing_manual.append("distribution")

        open_records = open_by_task.get(task_key, [])
        flags = []
        if missing_manual:
            summary["manual_missing_count"] += 1
            flags.append({"kind": "manual", "label": "Missing manual audit: " + ", ".join(missing_manual)})
        if not audit.solve_rate_pass:
            summary["solve_manual_missing_count"] += 1
            flags.append({"kind": "manual", "label": "Solve-rate manual checkbox not checked"})
        if not task.solve_stats:
            summary["automated_solve_missing_count"] += 1
            flags.append({"kind": "solve", "label": "Automated solve-rate missing"})
        elif not task.solve_pass:
            summary["automated_solve_not_accepted_count"] += 1
            flags.append({"kind": "solve", "label": "Automated solve-rate not accepted"})
        if open_records:
            flags.append({"kind": "feedback", "label": f"{len(open_records)} open feedback"})
        if not flags:
            continue
        task_entries.append(
            {
                "task": task,
                "audit": audit,
                "flags": flags,
                "open_feedback": open_records,
                "task_path": f"/domains/{_url_segment(task.domain)}/scenes/{_url_segment(task.scene_id)}/tasks/{_url_segment(task.task_id)}",
            }
        )

    summary["task_count"] = len(task_entries)
    groups_by_domain: Dict[str, Dict[str, Any]] = {}
    for entry in task_entries:
        task = entry["task"]
        domain_group = groups_by_domain.setdefault(task.domain, {"domain": task.domain, "scenes": {}})
        scene_group = domain_group["scenes"].setdefault(task.scene_id, {"scene_id": task.scene_id, "tasks": []})
        scene_group["tasks"].append(entry)

    groups = []
    for domain_group in groups_by_domain.values():
        scenes = list(domain_group["scenes"].values())
        groups.append({"domain": domain_group["domain"], "scenes": scenes})
    return {"groups": groups, "summary": summary}


def _context(request: Request, *, index: ReviewIndex, title: str, **extra: Any) -> Dict[str, Any]:
    feedback = request.app.state.review.feedback
    audit_by_task = _effective_audits_by_task(index, feedback.task_audits_by_task())
    task_status_by_task, status_by_scene, status_by_domain = _status_summaries(index, audit_by_task)
    feedback_by_domain = feedback.counts_by_domain()
    context: Dict[str, Any] = {
        "request": request,
        "title": title,
        "index": index,
        "review_root_display": _display_path(index.root, repo_root=index.repo_root),
        "review_index_stale": request.app.state.review.review_artifacts_stale(),
        "feedback_by_domain": feedback_by_domain,
        "feedback_by_scene": feedback.counts_by_scene(),
        "feedback_by_task": feedback.counts_by_task(),
        "feedback_by_sample": feedback.counts_by_sample(),
        "feedback_open_count": sum(int(value.get("open", 0)) for value in feedback_by_domain.values()),
        "audit_by_task": audit_by_task,
        "task_status_by_task": task_status_by_task,
        "status_by_scene": status_by_scene,
        "status_by_domain": status_by_domain,
    }
    context.update(extra)
    return context


def _status_summaries(index: ReviewIndex, audit_by_task: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    task_status: Dict[str, Any] = {}
    scene_status: Dict[str, Any] = {}
    domain_status: Dict[str, Any] = {}
    for task_key, task in index.tasks.items():
        audit = audit_by_task.get(task_key)
        if audit is None:
            audit = _empty_task_audit(task.domain, task.scene_id, task.task_id)
            audit_by_task[task_key] = audit
        payload = _task_status_payload(task=task, audit=audit)
        task_status[task_key] = payload
        scene_entry = scene_status.setdefault(
            ReviewIndex.scene_key(task.domain, task.scene_id),
            {"total": 0, "manual_pass": 0, "solve_pass": 0, "complete": 0},
        )
        domain_entry = domain_status.setdefault(
            task.domain,
            {"total": 0, "manual_pass": 0, "solve_pass": 0, "complete": 0},
        )
        for entry in (scene_entry, domain_entry):
            entry["total"] += 1
            entry["manual_pass"] += int(payload["manual_pass"])
            entry["solve_pass"] += int(payload["solve_pass"])
            entry["complete"] += int(payload["complete"])
    return task_status, scene_status, domain_status


def _effective_audits_by_task(index: ReviewIndex, raw_audits: Dict[str, TaskAuditRecord]) -> Dict[str, TaskAuditRecord]:
    effective: Dict[str, TaskAuditRecord] = dict(raw_audits)
    for task_key, task in index.tasks.items():
        audit = effective.get(task_key) or TaskAuditRecord.empty(
            domain=task.domain,
            scene_id=task.scene_id,
            task_id=task.task_id,
        )
        effective[task_key] = _effective_task_audit(task, audit)
    return effective


def _effective_task_audit(task: Any, audit: TaskAuditRecord) -> TaskAuditRecord:
    """Apply generated-artifact defaults while preserving explicit reviewer overrides."""

    if audit.distribution_pass:
        return audit
    if str(audit.updated_at or "").strip():
        return audit
    if bool(getattr(task, "distribution_pass", False)):
        return replace(audit, distribution_pass=True)
    return audit


def _empty_task_audit(domain: str, scene_id: str, task_id: str) -> TaskAuditRecord:
    return TaskAuditRecord.empty(domain=domain, scene_id=scene_id, task_id=task_id)


def _task_status_payload(*, task: Any, audit: Any) -> Dict[str, Any]:
    manual_pass = bool(getattr(audit, "manual_pass", False))
    solve_pass = bool(getattr(task, "solve_pass", False))
    return {
        "manual_pass": manual_pass,
        "manual_count": int(getattr(audit, "passed_count", 0)),
        "manual_total": int(getattr(audit, "total_count", 4)),
        "solve_pass": solve_pass,
        "complete": manual_pass and solve_pass,
    }


def _search_suggestions(index: ReviewIndex, query: str, *, base_url: str, limit: int = 14) -> list[Dict[str, str]]:
    needle_raw = str(query or "").strip().lower()
    needle_folded = _search_fold(query)
    if len(needle_folded) < 2:
        return []

    candidates: list[tuple[int, int, str, Dict[str, str]]] = []

    for domain in index.domains.values():
        score = _search_score(needle_raw, needle_folded, domain.domain)
        if score is None:
            continue
        path = f"/domains/{_url_segment(domain.domain)}"
        candidates.append(
            (
                score,
                0,
                domain.domain,
                {
                    "type": "domain",
                    "label": domain.domain,
                    "subtitle": f"{len(domain.scenes)} scenes · {domain.task_count} tasks · {domain.sample_count} samples",
                    "url": _app_path(base_url, path),
                },
            )
        )

    for scene in index.scenes.values():
        haystack = " ".join([scene.domain, scene.scene_id, f"{scene.domain}/{scene.scene_id}"])
        score = _search_score(needle_raw, needle_folded, haystack)
        if score is None:
            continue
        path = f"/domains/{_url_segment(scene.domain)}/scenes/{_url_segment(scene.scene_id)}"
        candidates.append(
            (
                score + 10,
                1,
                f"{scene.domain}/{scene.scene_id}",
                {
                    "type": "scene",
                    "label": scene.scene_id,
                    "subtitle": f"{scene.domain} · {scene.task_count} tasks · {scene.sample_count} samples",
                    "url": _app_path(base_url, path),
                },
            )
        )

    for task in index.tasks.values():
        query_ids = " ".join(task.query_counts)
        haystack = " ".join([task.domain, task.scene_id, task.task_id, query_ids])
        score = _search_score(needle_raw, needle_folded, haystack)
        if score is None:
            continue
        path = (
            f"/domains/{_url_segment(task.domain)}"
            f"/scenes/{_url_segment(task.scene_id)}"
            f"/tasks/{_url_segment(task.task_id)}"
        )
        candidates.append(
            (
                score + 20,
                2,
                f"{task.domain}/{task.scene_id}/{task.task_id}",
                {
                    "type": "task",
                    "label": task.task_id,
                    "subtitle": f"{task.domain}/{task.scene_id} · {task.sample_count} samples",
                    "url": _app_path(base_url, path),
                },
            )
        )

        for query_id, count in task.query_counts.items():
            query_haystack = " ".join([task.domain, task.scene_id, task.task_id, query_id])
            query_score = _search_score(needle_raw, needle_folded, query_haystack)
            if query_score is None:
                continue
            query_path = f"{path}/queries/{_url_segment(query_id)}"
            candidates.append(
                (
                    query_score + 30,
                    3,
                    f"{task.domain}/{task.scene_id}/{task.task_id}/{query_id}",
                    {
                        "type": "query",
                        "label": query_id,
                        "subtitle": f"{task.task_id} · {count} samples",
                        "url": _app_path(base_url, query_path),
                    },
                )
            )

    sample_matches = 0
    for sample in index.samples.values():
        haystack = " ".join(
            [
                sample.domain,
                sample.scene_id,
                sample.task_id,
                sample.query_id,
                sample.prompt,
                sample.answer_label,
            ]
        )
        score = _search_score(needle_raw, needle_folded, haystack)
        if score is None:
            continue
        path = f"/samples/{_url_segment(sample.uid)}"
        candidates.append(
            (
                score + 80,
                4,
                sample.uid,
                {
                    "type": "sample",
                    "label": sample.prompt if len(sample.prompt) <= 90 else sample.prompt[:87].rstrip() + "...",
                    "subtitle": f"{sample.domain}/{sample.scene_id} · {sample.query_id} · answer {sample.answer_label}",
                    "url": _app_path(base_url, path),
                },
            )
        )
        sample_matches += 1
        if sample_matches >= 8:
            break

    results: list[Dict[str, str]] = []
    seen_urls: set[str] = set()
    for _, _, _, payload in sorted(candidates, key=lambda item: (item[0], item[1], item[2])):
        if payload["url"] in seen_urls:
            continue
        seen_urls.add(payload["url"])
        results.append(payload)
        if len(results) >= limit:
            break
    return results


def _search_score(needle_raw: str, needle_folded: str, value: str) -> int | None:
    raw = str(value or "").lower()
    folded = _search_fold(value)
    if not raw and not folded:
        return None
    if needle_raw == raw or needle_folded == folded:
        return 0
    if raw.startswith(needle_raw) or folded.startswith(needle_folded):
        return 5
    if needle_raw in raw or needle_folded in folded:
        return 20
    return None


def _search_fold(value: Any) -> str:
    folded = "".join(char.lower() if char.isalnum() else " " for char in str(value or ""))
    return " ".join(folded.split())


def _url_segment(value: Any) -> str:
    return quote(str(value), safe="")


def _static_version(static_dir: Path) -> str:
    mtimes = []
    for filename in ("app.css", "app.js"):
        path = static_dir / filename
        if path.exists():
            mtimes.append(path.stat().st_mtime_ns)
    return str(max(mtimes)) if mtimes else "0"


def _display_path(path: Path | str, *, repo_root: Path | str) -> str:
    resolved_path = Path(path).resolve()
    resolved_repo_root = Path(repo_root).resolve()
    try:
        return str(resolved_path.relative_to(resolved_repo_root))
    except ValueError:
        return str(resolved_path)


def _max_review_file_mtime_ns(root: Path) -> int:
    if not root.exists():
        return 0
    max_mtime = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                max_mtime = max(max_mtime, path.stat().st_mtime_ns)
        except OSError:
            continue
    return max_mtime


def _infer_repo_root(review_root: Path) -> Path:
    if len(review_root.parts) >= 2 and review_root.parts[-2:] == ("review", "task-reviews"):
        return review_root.parents[1]
    return Path.cwd().resolve()


def _normalize_base_url(base_url: str) -> str:
    text = str(base_url or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        text = urlsplit(text).path
    text = "/" + text.strip("/")
    return "" if text == "/" else text


def _app_path(base_url: str, path: str = "") -> str:
    base = _normalize_base_url(base_url)
    suffix = str(path or "")
    if not suffix:
        return base or "/"
    if suffix.startswith("http://") or suffix.startswith("https://"):
        return suffix
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    return f"{base}{suffix}" if base else suffix


def _request_is_public(request: Request) -> bool:
    path = request.url.path
    return path.startswith("/static/") or path == "/login" or path == "/healthz"


def _request_has_token(request: Request, token: str) -> bool:
    cookie = str(request.cookies.get("trace_review_token", ""))
    auth = str(request.headers.get("authorization", ""))
    bearer = auth[len("Bearer ") :].strip() if auth.lower().startswith("bearer ") else ""
    query_token = str(request.query_params.get("token", ""))
    return cookie == token or bearer == token or query_token == token


def _safe_next(value: str) -> str:
    text = str(value or "/").strip()
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlsplit(text)
        text = parsed.path or "/"
        if parsed.query:
            text = f"{text}?{parsed.query}"
    if not text.startswith("/") or text.startswith("//"):
        return "/"
    return text


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "checked"}


async def _request_data(request: Request) -> Dict[str, str]:
    content_type = str(request.headers.get("content-type", ""))
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            return {str(key): "" if value is None else str(value) for key, value in payload.items()}
        return {}
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {str(key): values[-1] if values else "" for key, values in parsed.items()}


def _neighbor_uids(sample_uids: list[str], current_uid: str) -> tuple[str, str]:
    if current_uid not in sample_uids:
        return "", ""
    index = sample_uids.index(current_uid)
    previous_uid = sample_uids[index - 1] if index > 0 else ""
    next_uid = sample_uids[index + 1] if index + 1 < len(sample_uids) else ""
    return previous_uid, next_uid


def _pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _format_rate(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}"
    except Exception:
        return str(value)


def _excerpt(value: Any, length: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= int(length):
        return text
    return text[: max(0, int(length) - 3)].rstrip() + "..."
