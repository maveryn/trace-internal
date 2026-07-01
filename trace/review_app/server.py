"""FastAPI server for browsing TRACE task-review artifacts."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from functools import lru_cache
import io
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from types import SimpleNamespace
from typing import Any, Dict
from urllib.parse import parse_qs, quote, unquote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image as PILImage

from trace.core.review_overlays import render_annotation_overlay, resolve_overlay_annotation

from .artifact_index import (
    PUBLISH_IN_PROGRESS_ERROR,
    build_review_index,
    build_review_scene_index,
    load_sample_payload,
    merge_review_scene_index,
    preserve_locked_scenes,
)
from .feedback import FeedbackStore
from .illustration_object_review import (
    RENDERER_LABELS as ILLUSTRATION_RENDERER_LABELS,
    VALID_REVIEW_DECISIONS as ILLUSTRATION_OBJECT_REVIEW_DECISIONS,
    filtered_illustration_object_items,
    illustration_object_category_tabs,
    illustration_object_renderer_tabs,
    illustration_object_review_item,
    render_illustration_object_review_image,
)
from .models import ReviewIndex, SampleRecord, TaskAuditRecord
from .resource_index import build_resource_index
from .taxonomy_index import DEFAULT_TAXONOMY_ROUND, build_taxonomy_audit_index
from .locks import review_file_lock_active, scene_publish_lock_path


logger = logging.getLogger(__name__)


class ReviewAppState:
    """Mutable app state shared by routes."""

    def __init__(
        self,
        *,
        review_root: Path,
        repo_root: Path,
        feedback_db: Path,
        enforce_migration_registry: bool = True,
        defer_initial_index: bool = False,
    ) -> None:
        self.review_root = Path(review_root).resolve()
        self.repo_root = Path(repo_root).resolve()
        self.enforce_migration_registry = bool(enforce_migration_registry)
        self.feedback = FeedbackStore(feedback_db)
        self._lock = threading.RLock()
        if defer_initial_index:
            self._index = _loading_review_index(review_root=self.review_root, repo_root=self.repo_root)
            self._review_mtime_snapshot_ns = 0
        else:
            self._index = build_review_index(
                self.review_root,
                repo_root=self.repo_root,
                enforce_migration_registry=self.enforce_migration_registry,
            )
            self._review_mtime_snapshot_ns = _max_review_file_mtime_ns(self.review_root)
        self._stale_cache = False
        self._stale_scene_cache: list[Dict[str, str]] = []
        self._stale_cache_until_ns = 0
        self._stale_check_interval_ns = 2_000_000_000
        self._reload_in_progress = False
        self._reload_status = "idle"
        self._reload_started_at = ""
        self._reload_finished_at = ""
        self._reload_error = ""
        self._reload_generation = 0
        self._reload_scope = "all"
        self._reload_thread: threading.Thread | None = None
        self._pending_reload_all = False
        self._pending_reload_scenes: list[tuple[str, str]] = []
        if defer_initial_index:
            self.request_reload()

    def index(self) -> ReviewIndex:
        with self._lock:
            self._prune_inactive_publish_errors_locked()
            return self._index

    def reload(self) -> ReviewIndex:
        fresh = build_review_index(
            self.review_root,
            repo_root=self.repo_root,
            enforce_migration_registry=self.enforce_migration_registry,
        )
        fresh_mtime = _max_review_file_mtime_ns(self.review_root)
        with self._lock:
            self._index = fresh
            self._review_mtime_snapshot_ns = fresh_mtime
            self._stale_cache = False
            self._stale_scene_cache = []
            self._stale_cache_until_ns = 0
            self._reload_in_progress = False
            self._reload_status = "succeeded"
            self._reload_started_at = self._reload_started_at or _utc_timestamp()
            self._reload_finished_at = _utc_timestamp()
            self._reload_error = ""
            return self._index

    def request_reload(self, *, domain: str = "", scene_id: str = "") -> Dict[str, Any]:
        """Start an index rebuild in the background and keep serving the old index."""

        scope = "all"
        domain_name = str(domain).strip()
        scene_name = str(scene_id).strip()
        if domain_name or scene_name:
            if not domain_name or not scene_name:
                raise ValueError("scene reload requires both domain and scene_id")
            scope = f"scene:{domain_name}/{scene_name}"
        with self._lock:
            if self._reload_in_progress:
                self._queue_reload_locked(domain=domain_name, scene_id=scene_name)
                payload = self._reload_status_payload_locked()
                payload.update({"accepted": True, "already_running": True, "queued": True})
                return payload
            if domain_name and scene_name and review_file_lock_active(
                scene_publish_lock_path(review_root=self.review_root, domain=domain_name, scene_id=scene_name)
            ):
                self._reload_generation += 1
                self._reload_in_progress = False
                self._reload_status = "succeeded"
                self._reload_started_at = _utc_timestamp()
                self._reload_finished_at = self._reload_started_at
                self._reload_error = ""
                self._reload_scope = scope
                self._stale_cache = True
                self._stale_scene_cache = [
                    {"domain": domain_name, "scene_id": scene_name, "key": f"{domain_name}/{scene_name}"}
                ]
                message = (
                    f"{domain_name}/{scene_name}: {PUBLISH_IN_PROGRESS_ERROR}; "
                    "serving previous indexed scene"
                )
                if message not in self._index.errors:
                    self._index.errors.append(message)
                self._stale_cache_until_ns = 0
                payload = self._reload_status_payload_locked()
                payload.update({"accepted": True, "already_running": False, "queued": False})
                return payload

            thread = self._begin_reload_locked(domain=domain_name, scene_id=scene_name, scope=scope)
            payload = self._reload_status_payload_locked()
            payload.update({"accepted": True, "already_running": False, "queued": False})

        thread.start()
        return payload

    def reload_status(self) -> Dict[str, Any]:
        with self._lock:
            self._prune_inactive_publish_errors_locked()
            publish_stale_scenes = _publish_in_progress_scenes(self._index.errors)
            if publish_stale_scenes and not self._reload_in_progress:
                payload = self._reload_status_payload_locked()
                payload["stale"] = True
                payload["stale_scenes"] = publish_stale_scenes
                return payload
            if self._reload_in_progress and self._reload_scope == "all":
                payload = self._reload_status_payload_locked()
                payload["stale"] = self._stale_cache
                payload["stale_scenes"] = []
                return payload
            if self._stale_cache:
                payload = self._reload_status_payload_locked()
                payload["stale"] = True
                payload["stale_scenes"] = list(self._stale_scene_cache)
                return payload
        stale, stale_scenes = self.review_artifacts_stale_summary()
        with self._lock:
            payload = self._reload_status_payload_locked()
            payload["stale"] = stale
            payload["stale_scenes"] = stale_scenes
            return payload

    def _reload_worker(self, generation: int, domain: str = "", scene_id: str = "") -> None:
        try:
            current = self.index()
            if domain and scene_id:
                scene_fresh = build_review_scene_index(
                    self.review_root,
                    domain=domain,
                    scene_id=scene_id,
                    repo_root=self.repo_root,
                    enforce_migration_registry=self.enforce_migration_registry,
                )
                fresh = merge_review_scene_index(current, scene_fresh, domain=domain, scene_id=scene_id)
            else:
                fresh = build_review_index(
                    self.review_root,
                    repo_root=self.repo_root,
                    enforce_migration_registry=self.enforce_migration_registry,
                )
            fresh = preserve_locked_scenes(current, fresh)
            publish_in_progress = any("review artifact publish in progress" in str(error) for error in fresh.errors)
            fresh_mtime = _max_review_file_mtime_ns(self.review_root)
        except Exception as exc:  # pragma: no cover - exercised through route tests.
            thread_to_start: threading.Thread | None = None
            with self._lock:
                if generation != self._reload_generation:
                    return
                self._reload_in_progress = False
                self._reload_status = "failed"
                self._reload_finished_at = _utc_timestamp()
                self._reload_error = str(exc)
                self._stale_cache = True
                self._stale_cache_until_ns = 0
                thread_to_start = self._start_next_queued_reload_locked()
            if thread_to_start is not None:
                thread_to_start.start()
            return

        thread_to_start: threading.Thread | None = None
        with self._lock:
            if generation != self._reload_generation:
                return
            self._index = fresh
            if publish_in_progress:
                self._stale_cache = True
                stale_scenes = _stale_review_scenes(self.review_root, self._review_mtime_snapshot_ns)
                if not stale_scenes and domain and scene_id:
                    stale_scenes = [{"domain": str(domain), "scene_id": str(scene_id), "key": f"{domain}/{scene_id}"}]
                self._stale_scene_cache = stale_scenes
                self._stale_cache_until_ns = time.monotonic_ns() + self._stale_check_interval_ns
            else:
                self._review_mtime_snapshot_ns = fresh_mtime
                self._stale_cache = False
                self._stale_scene_cache = []
                self._stale_cache_until_ns = 0
            self._reload_in_progress = False
            self._reload_status = "succeeded"
            self._reload_finished_at = _utc_timestamp()
            self._reload_error = ""
            thread_to_start = self._start_next_queued_reload_locked()
        if thread_to_start is not None:
            thread_to_start.start()

    def _begin_reload_locked(self, *, domain: str, scene_id: str, scope: str) -> threading.Thread:
        self._reload_generation += 1
        generation = self._reload_generation
        self._reload_in_progress = True
        self._reload_status = "running"
        self._reload_started_at = _utc_timestamp()
        self._reload_finished_at = ""
        self._reload_error = ""
        self._reload_scope = scope
        thread = threading.Thread(
            target=self._reload_worker,
            args=(generation, domain, scene_id),
            name=f"trace-review-index-reload-{generation}",
            daemon=True,
        )
        self._reload_thread = thread
        return thread

    def _queue_reload_locked(self, *, domain: str, scene_id: str) -> None:
        if not domain and not scene_id:
            self._pending_reload_all = True
            self._pending_reload_scenes.clear()
            return
        pair = (str(domain), str(scene_id))
        if self._pending_reload_all or pair in self._pending_reload_scenes:
            return
        self._pending_reload_scenes.append(pair)

    def _start_next_queued_reload_locked(self) -> threading.Thread | None:
        if self._pending_reload_all:
            self._pending_reload_all = False
            self._pending_reload_scenes.clear()
            return self._begin_reload_locked(domain="", scene_id="", scope="all")
        if not self._pending_reload_scenes:
            return None
        domain, scene_id = self._pending_reload_scenes.pop(0)
        return self._begin_reload_locked(domain=domain, scene_id=scene_id, scope=f"scene:{domain}/{scene_id}")

    def _pending_reload_scopes_locked(self) -> list[str]:
        if self._pending_reload_all:
            return ["all"]
        return [f"scene:{domain}/{scene_id}" for domain, scene_id in self._pending_reload_scenes]

    def _reload_status_payload_locked(self) -> Dict[str, Any]:
        return {
            "status": self._reload_status,
            "in_progress": self._reload_in_progress,
            "started_at": self._reload_started_at,
            "finished_at": self._reload_finished_at,
            "error": self._reload_error,
            "generation": self._reload_generation,
            "scope": self._reload_scope,
            "stale": self._stale_cache,
            "queued": bool(self._pending_reload_all or self._pending_reload_scenes),
            "queued_scopes": self._pending_reload_scopes_locked(),
        }

    def review_artifacts_stale(self) -> bool:
        stale, _stale_scenes = self.review_artifacts_stale_summary()
        return stale

    def review_artifacts_stale_summary(self) -> tuple[bool, list[Dict[str, str]]]:
        now = time.monotonic_ns()
        with self._lock:
            if self._stale_cache:
                return self._stale_cache, list(self._stale_scene_cache)
            if now < self._stale_cache_until_ns:
                return self._stale_cache, list(self._stale_scene_cache)
            snapshot = self._review_mtime_snapshot_ns
            interval = self._stale_check_interval_ns
        stale, stale_scenes = _review_stale_summary(self.review_root, snapshot)
        with self._lock:
            self._stale_cache = stale
            self._stale_scene_cache = stale_scenes
            self._stale_cache_until_ns = now + interval
        return stale, list(stale_scenes)

    def _prune_inactive_publish_errors_locked(self) -> None:
        """Drop publish-in-progress errors once their scene lock is released."""

        if not self._index.errors:
            return
        pruned = _filter_active_publish_errors(
            self._index.errors,
            review_root=self.review_root,
        )
        if len(pruned) == len(self._index.errors):
            return
        self._index.errors = pruned


def create_app(
    *,
    review_root: Path | str = "review/task-reviews",
    repo_root: Path | str | None = None,
    feedback_db: Path | str | None = None,
    token: str | None = None,
    base_url: str = "",
    enforce_migration_registry: bool = True,
    defer_initial_index: bool = False,
    allow_full_reload: bool | None = None,
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
    resolved_allow_full_reload = (
        _truthy(os.environ.get("TRACE_REVIEW_ALLOW_FULL_RELOAD"))
        if allow_full_reload is None
        else bool(allow_full_reload)
    )
    state = ReviewAppState(
        review_root=resolved_review_root,
        repo_root=resolved_repo_root,
        feedback_db=resolved_feedback_db,
        enforce_migration_registry=bool(enforce_migration_registry),
        defer_initial_index=bool(defer_initial_index),
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
    app.state.allow_full_reload = bool(resolved_allow_full_reload)
    app.mount("/static", StaticFiles(directory=str(package_dir / "static")), name="static")

    @app.exception_handler(sqlite3.OperationalError)
    async def sqlite_operational_error_handler(request: Request, exc: sqlite3.OperationalError) -> Response:
        message = str(exc)
        if "locked" in message.lower():
            logger.warning("Review feedback database is locked for %s: %s", request.url.path, message)
            return _transient_error_response(request, status_code=503, detail="Review feedback database is busy. Retry shortly.")
        logger.exception("Unhandled SQLite error for %s", request.url.path)
        return _transient_error_response(request, status_code=500, detail="Review feedback database error.")

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled review app error for %s", request.url.path)
        return _transient_error_response(request, status_code=500, detail="Internal review app error.")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Any) -> Response:
        _strip_base_url_from_scope(request.scope, resolved_base_url)
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

    @app.get("/domains")
    @app.get("/domains/")
    async def domains_index_redirect() -> RedirectResponse:
        return RedirectResponse(_app_path(resolved_base_url, "/"), status_code=303)

    @app.get("/feedback")
    async def feedback_page_redirect(request: Request) -> RedirectResponse:
        target = "/issues"
        if request.url.query:
            target = f"{target}?{request.url.query}"
        return RedirectResponse(_app_path(resolved_base_url, target), status_code=303)

    @app.get("/issues", response_class=HTMLResponse)
    async def feedback_page(request: Request, domain: str = "") -> HTMLResponse:
        index = state.index()
        selected_domain = str(domain or "").strip()
        queue = _build_feedback_work_queue(index=index, feedback=state.feedback, domain=selected_domain)
        return templates.TemplateResponse(
            request,
            "feedback.html",
            _context(
                request,
                index=index,
                title="Issue Work Queue",
                work_queue=queue["groups"],
                work_queue_summary=queue["summary"],
                selected_feedback_domain=selected_domain,
                feedback_domain_tabs=_feedback_domain_tabs(
                    index=index,
                    feedback_by_domain=state.feedback.counts_by_domain(),
                    selected_domain=selected_domain,
                ),
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

    @app.get("/three-d/objects", response_class=HTMLResponse)
    async def three_d_objects_page(request: Request, group: str = "", decision: str = "") -> HTMLResponse:
        index = state.index()
        review_state = _build_three_d_object_review_state(
            feedback=state.feedback,
            selected_group=group,
            selected_decision=decision,
        )
        return templates.TemplateResponse(
            request,
            "three_d_objects.html",
            _context(
                request,
                index=index,
                title="3D Object Review",
                three_d_object_review=review_state,
            ),
        )

    @app.get("/three-d/objects/previews/{profile_token}")
    async def three_d_object_preview(profile_token: str) -> Response:
        profile_id = _decode_three_d_profile_token(profile_token)
        if profile_id not in _three_d_object_profile_by_id():
            raise HTTPException(status_code=404, detail="unknown 3D object profile")
        try:
            png = _three_d_object_preview_png(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        return Response(png, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.post("/three-d/objects/reviews/{profile_token}")
    async def three_d_object_review_submit(request: Request, profile_token: str) -> RedirectResponse:
        profile_id = _decode_three_d_profile_token(profile_token)
        profile = _three_d_object_profile_by_id().get(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="unknown 3D object profile")
        data = await _request_data(request)
        review = state.feedback.update_three_d_object_review(
            profile_id=str(profile.profile_id),
            canonical_id=str(profile.canonical_id),
            object_type=str(profile.object_type),
            renderer=str(profile.renderer),
            source_scene=str(profile.source_scene),
            decision=str(data.get("decision", "")),
            notes=str(data.get("notes", "")),
            updated_by=str(data.get("updated_by", "")),
        )
        decision = str(review.decision or "").strip().lower()
        if decision not in {"approve", "remove", "improve"}:
            decision = "unreviewed"
        if _request_wants_json(request):
            return JSONResponse(
                {
                    "ok": True,
                    "decision": decision,
                    "status_label": _three_d_object_status_label(decision),
                    "review": asdict(review),
                }
            )
        default_next = f"/three-d/objects#{_three_d_object_anchor_id(profile.profile_id)}"
        next_url = _safe_next(str(data.get("next", default_next)))
        return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)

    @app.get("/illustration-objects")
    async def illustration_objects_legacy_redirect(request: Request) -> RedirectResponse:
        target = "/illustrations/objects"
        if request.url.query:
            target = f"{target}?{request.url.query}"
        return RedirectResponse(_app_path(resolved_base_url, target), status_code=303)

    @app.get("/illustrations/objects", response_class=HTMLResponse)
    async def illustration_objects_page(request: Request, renderer: str = "", category: str = "", decision: str = "") -> HTMLResponse:
        index = state.index()
        review_state = _build_illustration_object_review_state(
            feedback=state.feedback,
            selected_renderer=renderer,
            selected_category=category,
            selected_decision=decision,
        )
        return templates.TemplateResponse(
            request,
            "illustration_objects.html",
            _context(
                request,
                index=index,
                title="Illustration Object Review",
                illustration_object_review=review_state,
            ),
        )

    @app.get("/illustrations/objects/previews/{item_token}")
    async def illustration_object_preview(item_token: str) -> Response:
        item_id = _decode_illustration_object_token(item_token)
        if illustration_object_review_item(item_id) is None:
            raise HTTPException(status_code=404, detail="unknown illustration object preview")
        png = _illustration_object_preview_png(item_id)
        return Response(png, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.post("/illustrations/objects/reviews/{item_token}")
    async def illustration_object_review_submit(request: Request, item_token: str) -> Response:
        item_id = _decode_illustration_object_token(item_token)
        item = illustration_object_review_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="unknown illustration object preview")
        data = await _request_data(request)
        review = state.feedback.update_illustration_object_review(
            item_id=str(item.item_id),
            renderer_style=str(item.renderer_style),
            category=str(item.category),
            object_type=str(item.object_type),
            label=str(item.display_label),
            decision=str(data.get("decision", "")),
            notes=str(data.get("notes", "")),
            updated_by=str(data.get("updated_by", "")),
        )
        decision = str(review.decision or "").strip().lower()
        if decision not in ILLUSTRATION_OBJECT_REVIEW_DECISIONS:
            decision = "unreviewed"
        if _request_wants_json(request):
            return JSONResponse(
                {
                    "ok": True,
                    "decision": decision,
                    "status_label": _illustration_object_status_label(decision),
                    "review": asdict(review),
                }
            )
        default_next = (
            f"/illustrations/objects?renderer={_url_segment(item.renderer_style)}"
            f"&category={_url_segment(item.category)}#{_illustration_object_anchor_id(item.item_id)}"
        )
        next_url = _safe_next(str(data.get("next", default_next)))
        return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)

    @app.get("/taxonomy")
    async def taxonomy_redirect() -> RedirectResponse:
        return RedirectResponse(
            _app_path(resolved_base_url, f"/taxonomy/{_taxonomy_round_slug(DEFAULT_TAXONOMY_ROUND)}"),
            status_code=303,
        )

    @app.get("/taxonomy/{round_slug}", response_class=HTMLResponse)
    async def taxonomy_page(
        request: Request,
        round_slug: str,
        domain: str = "",
        decision: str = "",
        review: str = "",
        q: str = "",
    ) -> HTMLResponse:
        index = state.index()
        taxonomy = build_taxonomy_audit_index(
            repo_root=state.repo_root,
            review_index=index,
            round_id=round_slug,
        )
        selected_domain = str(domain or "").strip()
        selected_decision = str(decision or "").strip().lower()
        selected_review = str(review or "").strip().lower()
        query = str(q or "").strip().lower()
        review_by_task = state.feedback.taxonomy_decision_reviews_by_task(round_id=taxonomy.round_id)
        open_feedback = state.feedback.list_open_feedback()
        taxonomy_open_issue_counts = _taxonomy_open_issue_counts(open_feedback, taxonomy.round_id)
        taxonomy_open_issues_by_task = _taxonomy_open_issues_by_task(open_feedback, taxonomy.round_id)
        tasks = taxonomy.domain_tasks(selected_domain)
        if selected_decision in {"keep", "split", "rename", "merge", "retire", "blocked_needs_inspection"}:
            tasks = [task for task in tasks if task.decision == selected_decision]
        if selected_review == "approved":
            tasks = [task for task in tasks if _taxonomy_task_approved(task, review_by_task)]
        elif selected_review == "pending":
            tasks = [task for task in tasks if not _taxonomy_task_approved(task, review_by_task)]
        elif selected_review == "open_issues":
            tasks = [task for task in tasks if taxonomy_open_issue_counts.get(task.task_key, 0)]
        if query:
            tasks = [task for task in tasks if _taxonomy_task_matches(task, query)]
        sample_uids = [uid for task in tasks for uid in task.sample_uids[:1]]
        samples_by_uid = {uid: index.samples[uid] for uid in sample_uids if uid in index.samples}
        all_tasks = taxonomy.domain_tasks("")
        return templates.TemplateResponse(
            request,
            "taxonomy.html",
            _context(
                request,
                index=index,
                title="Taxonomy Audit",
                taxonomy=taxonomy,
                taxonomy_round_slug=_taxonomy_round_slug(taxonomy.round_id),
                taxonomy_tasks=tasks,
                taxonomy_review_progress=_taxonomy_review_progress(
                    tasks=all_tasks,
                    review_by_task=review_by_task,
                    open_issue_counts=taxonomy_open_issue_counts,
                ),
                taxonomy_domain_review_progress=_taxonomy_review_progress(
                    tasks=taxonomy.domain_tasks(selected_domain) if selected_domain else all_tasks,
                    review_by_task=review_by_task,
                    open_issue_counts=taxonomy_open_issue_counts,
                ),
                taxonomy_decision_reviews_by_task=review_by_task,
                taxonomy_open_issue_counts=taxonomy_open_issue_counts,
                taxonomy_open_issues_by_task=taxonomy_open_issues_by_task,
                selected_taxonomy_domain=selected_domain,
                selected_taxonomy_decision=selected_decision,
                selected_taxonomy_review=selected_review,
                taxonomy_query=q,
                taxonomy_samples_by_uid=samples_by_uid,
                taxonomy_domain_doc=taxonomy.domain_docs.get(selected_domain, "") if selected_domain else "",
            ),
        )

    @app.get("/taxonomy/{round_slug}/tree", response_class=HTMLResponse)
    async def taxonomy_tree_page(request: Request, round_slug: str, domain: str = "") -> HTMLResponse:
        index = state.index()
        taxonomy = build_taxonomy_audit_index(
            repo_root=state.repo_root,
            review_index=index,
            round_id=round_slug,
        )
        selected_domain = str(domain or "").strip()
        units = taxonomy.domain_units(selected_domain)
        sample_uids = [uid for unit in units for uid in unit.sample_uids[:1]]
        samples_by_uid = {uid: index.samples[uid] for uid in sample_uids if uid in index.samples}
        return templates.TemplateResponse(
            request,
            "taxonomy_tree.html",
            _context(
                request,
                index=index,
                title="Taxonomy Tree",
                taxonomy=taxonomy,
                taxonomy_round_slug=_taxonomy_round_slug(taxonomy.round_id),
                selected_taxonomy_domain=selected_domain,
                taxonomy_tree=_build_taxonomy_tree(units),
                taxonomy_samples_by_uid=samples_by_uid,
            ),
        )

    @app.get("/taxonomy/{round_slug}/domains/{domain}", response_class=HTMLResponse)
    async def taxonomy_domain_page(request: Request, round_slug: str, domain: str) -> RedirectResponse:
        target = f"/taxonomy/{_url_segment(round_slug)}?domain={_url_segment(domain)}"
        return RedirectResponse(_app_path(resolved_base_url, target), status_code=303)

    @app.get("/taxonomy/{round_slug}/domains/{domain}/scenes/{scene_id}/tasks/{task_id}", response_class=HTMLResponse)
    async def taxonomy_task_page(
        request: Request,
        round_slug: str,
        domain: str,
        scene_id: str,
        task_id: str,
    ) -> HTMLResponse:
        index = state.index()
        taxonomy = build_taxonomy_audit_index(
            repo_root=state.repo_root,
            review_index=index,
            round_id=round_slug,
        )
        task = taxonomy.tasks.get(ReviewIndex.task_key(domain, scene_id, task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="unknown taxonomy task")
        samples_by_uid = {
            uid: index.samples[uid]
            for query in task.queries
            for uid in query.sample_uids
            if uid in index.samples
        }
        task_feedback = state.feedback.list_task_feedback(domain=domain, scene_id=scene_id, task_id=task_id)
        taxonomy_feedback = _taxonomy_feedback_records(task_feedback, taxonomy.round_id)
        feedback_ids = [record.id for record in taxonomy_feedback]
        taxonomy_decision_review = state.feedback.get_taxonomy_decision_review(
            round_id=taxonomy.round_id,
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
        )
        review_by_task = state.feedback.taxonomy_decision_reviews_by_task(round_id=taxonomy.round_id)
        domain_tasks = taxonomy.domain_tasks(domain)
        taxonomy_next_pending_task = _next_taxonomy_task(
            tasks=domain_tasks,
            current_task=task,
            review_by_task=review_by_task,
            pending_only=True,
        )
        taxonomy_next_task = _next_taxonomy_task(
            tasks=domain_tasks,
            current_task=task,
            review_by_task=review_by_task,
            pending_only=False,
        )
        return templates.TemplateResponse(
            request,
            "taxonomy_task.html",
            _context(
                request,
                index=index,
                title=f"Taxonomy: {task.current_task_id}",
                taxonomy=taxonomy,
                taxonomy_round_slug=_taxonomy_round_slug(taxonomy.round_id),
                taxonomy_task=task,
                taxonomy_units_by_id=taxonomy.proposed_units,
                taxonomy_samples_by_uid=samples_by_uid,
                taxonomy_feedback=taxonomy_feedback,
                taxonomy_decision_review=taxonomy_decision_review,
                taxonomy_open_issue_count=sum(1 for record in taxonomy_feedback if record.status == "open"),
                taxonomy_next_pending_path=(
                    _taxonomy_task_path(taxonomy.round_id, taxonomy_next_pending_task)
                    if taxonomy_next_pending_task is not None
                    else ""
                ),
                taxonomy_next_task_path=(
                    _taxonomy_task_path(taxonomy.round_id, taxonomy_next_task)
                    if taxonomy_next_task is not None
                    else ""
                ),
                reviewer_comments_by_feedback=state.feedback.comments_by_feedback(feedback_ids),
                agent_notes_by_feedback=state.feedback.notes_by_feedback(feedback_ids),
                feedback_thread_events_by_feedback=state.feedback.thread_events_by_feedback(feedback_ids),
            ),
        )

    @app.post("/taxonomy/{round_slug}/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/decision-review")
    async def taxonomy_task_decision_review(
        request: Request,
        round_slug: str,
        domain: str,
        scene_id: str,
        task_id: str,
    ) -> RedirectResponse:
        data = await _request_data(request)
        round_id = _normalize_taxonomy_round(round_slug)
        action = str(data.get("action", "")).strip().lower()
        if action:
            approved = action in {"approve", "approve_next"}
        else:
            approved = str(data.get("approved", "")).strip().lower() in {"1", "true", "yes", "on"}
        state.feedback.update_taxonomy_decision_review(
            round_id=round_id,
            domain=domain,
            scene_id=scene_id,
            task_id=task_id,
            approved=approved,
            notes=str(data.get("notes", "")),
            updated_by=str(data.get("updated_by", "")),
        )
        default_next = (
            f"/taxonomy/{_taxonomy_round_slug(round_id)}/domains/{_url_segment(domain)}"
            f"/scenes/{_url_segment(scene_id)}/tasks/{_url_segment(task_id)}"
        )
        if action == "approve_next":
            default_next = f"/taxonomy/{_taxonomy_round_slug(round_id)}?domain={_url_segment(domain)}&review=pending"
        next_field = "next_pending" if action == "approve_next" else "next"
        next_value = str(data.get(next_field, "")).strip()
        if not next_value:
            next_value = default_next if action == "approve_next" else str(data.get("next", default_next)).strip()
        next_url = _safe_next(next_value)
        return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)

    @app.post("/taxonomy/{round_slug}/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/issues")
    async def taxonomy_task_feedback(
        request: Request,
        round_slug: str,
        domain: str,
        scene_id: str,
        task_id: str,
    ) -> RedirectResponse:
        data = await _request_data(request)
        round_id = _normalize_taxonomy_round(round_slug)
        query_id = str(data.get("query_id", "")).strip()
        prefix = _taxonomy_feedback_prefix(round_id, query_id=query_id)
        comment = f"{prefix} {str(data.get('comment', '')).strip()}"
        try:
            state.feedback.add_task_feedback(
                domain=domain,
                scene_id=scene_id,
                task_id=task_id,
                comment=comment,
                author=str(data.get("author", "")),
                category=str(data.get("category", "other")),
                severity=str(data.get("severity", "issue")),
            )
            existing_review = state.feedback.get_taxonomy_decision_review(
                round_id=round_id,
                domain=domain,
                scene_id=scene_id,
                task_id=task_id,
            )
            state.feedback.update_taxonomy_decision_review(
                round_id=round_id,
                domain=domain,
                scene_id=scene_id,
                task_id=task_id,
                approved=False,
                notes=existing_review.notes,
                updated_by=str(data.get("author", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        next_mode = str(data.get("next_mode", "")).strip().lower()
        default_next = (
            f"/taxonomy/{_taxonomy_round_slug(round_id)}/domains/{_url_segment(domain)}"
            f"/scenes/{_url_segment(scene_id)}/tasks/{_url_segment(task_id)}"
        )
        if next_mode == "next_pending":
            default_next = f"/taxonomy/{_taxonomy_round_slug(round_id)}?domain={_url_segment(domain)}&review=pending"
        next_field = "next_pending" if next_mode == "next_pending" else "next"
        next_value = str(data.get(next_field, "")).strip()
        if not next_value:
            next_value = default_next if next_mode == "next_pending" else str(data.get("next", default_next)).strip()
        next_url = _safe_next(next_value)
        return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)

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
        scene_feedback = state.feedback.list_scene_feedback(domain=domain, scene_id=scene_id)
        return templates.TemplateResponse(
            request,
            "scene.html",
            _context(
                request,
                index=index,
                title=f"Scene: {scene_id}",
                scene=scene,
                tasks=tasks,
                scene_level_feedback=scene_feedback,
                scene_open_feedback=[record for record in scene_feedback if record.status == "open"],
            ),
        )

    @app.get("/domains/{domain}/scenes/{scene_id}/review", response_class=HTMLResponse)
    async def scene_review_page(request: Request, domain: str, scene_id: str) -> HTMLResponse:
        index = state.index()
        scene = index.scenes.get(ReviewIndex.scene_key(domain, scene_id))
        if scene is None:
            raise HTTPException(status_code=404, detail="unknown scene")
        tasks = [index.tasks[ReviewIndex.task_key(domain, scene_id, task_id)] for task_id in scene.tasks]
        scene_feedback = state.feedback.list_scene_feedback(domain=domain, scene_id=scene_id)
        feedback_ids = [record.id for record in scene_feedback]
        return templates.TemplateResponse(
            request,
            "scene_review.html",
            _context(
                request,
                index=index,
                title=f"Scene Review: {scene_id}",
                scene=scene,
                tasks=tasks,
                scene_review=_build_scene_review_samples(index=index, tasks=tasks, samples_per_query=2),
                scene_level_feedback=scene_feedback,
                scene_open_feedback=[record for record in scene_feedback if record.status == "open"],
                reviewer_comments_by_feedback=state.feedback.comments_by_feedback(feedback_ids),
                agent_notes_by_feedback=state.feedback.notes_by_feedback(feedback_ids),
                feedback_thread_events_by_feedback=state.feedback.thread_events_by_feedback(feedback_ids),
            ),
        )

    @app.post("/domains/{domain}/scenes/{scene_id}/issues")
    @app.post("/domains/{domain}/scenes/{scene_id}/feedback")
    async def scene_feedback_submit(request: Request, domain: str, scene_id: str) -> RedirectResponse:
        index = state.index()
        scene = index.scenes.get(ReviewIndex.scene_key(domain, scene_id))
        if scene is None:
            raise HTTPException(status_code=404, detail="unknown scene")
        data = await _request_data(request)
        try:
            state.feedback.add_scene_feedback(
                domain=domain,
                scene_id=scene_id,
                comment=str(data.get("comment", "")),
                author=str(data.get("author", "")),
                category=str(data.get("category", "other")),
                severity=str(data.get("severity", "issue")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        next_url = _safe_next(str(data.get("next", "")))
        if next_url != "/":
            return RedirectResponse(_app_path(resolved_base_url, next_url), status_code=303)
        return RedirectResponse(
            _app_path(resolved_base_url, f"/domains/{_url_segment(domain)}/scenes/{_url_segment(scene_id)}/review#scene-feedback"),
            status_code=303,
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
        payload = _load_sample_payload_or_503(index, sample)
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
                agent_notes_by_feedback=state.feedback.notes_by_feedback(feedback_ids),
                feedback_thread_events_by_feedback=state.feedback.thread_events_by_feedback(feedback_ids),
                previous_uid=previous_uid,
                next_uid=next_uid,
            ),
        )

    @app.post("/samples/{sample_uid}/issues")
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

    @app.get("/feedback/{feedback_id}")
    async def feedback_detail_redirect(feedback_id: str) -> RedirectResponse:
        return RedirectResponse(_app_path(resolved_base_url, f"/issues/{_url_segment(feedback_id)}"), status_code=303)

    @app.get("/issues/{feedback_id}", response_class=HTMLResponse)
    async def feedback_detail_page(request: Request, feedback_id: str) -> HTMLResponse:
        index = state.index()
        try:
            record = state.feedback.get_feedback(feedback_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown feedback") from None
        sample = index.samples.get(record.sample_uid) if record.sample_uid else None
        task = index.tasks.get(ReviewIndex.task_key(record.domain, record.scene_id, record.task_id))
        task_path = _feedback_task_path(record)
        return templates.TemplateResponse(
            request,
            "feedback_detail.html",
            _context(
                request,
                index=index,
                title="Issue Thread",
                feedback_record=record,
                feedback_comments=state.feedback.list_comments_for_feedback(record.id),
                feedback_notes=state.feedback.list_notes_for_feedback(record.id),
                feedback_thread_events=state.feedback.thread_events_for_feedback(record.id),
                feedback_sample=sample,
                feedback_task=task,
                feedback_task_path=task_path,
                feedback_source_path=_feedback_source_path(record),
            ),
        )

    @app.post("/issues/{feedback_id}")
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

    @app.post("/issues/{feedback_id}/comments")
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

    @app.post("/issues/{feedback_id}/notes")
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
            annotation_pass=_truthy(data.get("annotation_pass")),
            distribution_pass=_truthy(data.get("distribution_pass")),
            code_review_pass=_truthy(data.get("code_review_pass")),
            taxonomy_review_pass=_truthy(data.get("taxonomy_review_pass")),
            solve_rate_pass=_truthy(data.get("solve_rate_pass")),
            notes=str(data.get("notes", "")),
            updated_by=str(data.get("updated_by", "")),
        )
        referer = request.headers.get("referer", "/")
        return RedirectResponse(_safe_next(referer), status_code=303)

    @app.post("/domains/{domain}/scenes/{scene_id}/tasks/{task_id}/issues")
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
        if not bool(app.state.allow_full_reload):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Full index reload is disabled for the shared review app. "
                    "Use POST /api/reload/scene/<domain>/<scene_id> after scene artifact changes. "
                    "Restart the app with TRACE_REVIEW_ALLOW_FULL_RELOAD=1 only for explicit global reload work."
                ),
            )
        return state.request_reload()

    @app.post("/api/reload/scene/{domain}/{scene_id}")
    async def api_reload_scene(domain: str, scene_id: str) -> Dict[str, Any]:
        try:
            return state.request_reload(domain=domain, scene_id=scene_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/reload/status")
    async def api_reload_status() -> Dict[str, Any]:
        return state.reload_status()

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
            annotation_pass=_truthy(data.get("annotation_pass", existing.annotation_pass)),
            distribution_pass=_truthy(data.get("distribution_pass", existing.distribution_pass)),
            code_review_pass=_truthy(data.get("code_review_pass", existing.code_review_pass)),
            taxonomy_review_pass=_truthy(data.get("taxonomy_review_pass", existing.taxonomy_review_pass)),
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

    @app.get("/api/three-d/objects/reviews")
    async def api_three_d_object_reviews() -> Dict[str, Any]:
        review_state = _build_three_d_object_review_state(feedback=state.feedback)
        return {
            "summary": dict(review_state["summary"]),
            "reviews": [asdict(record) for record in state.feedback.three_d_object_reviews_by_profile().values()],
        }

    @app.get("/api/three-d/objects/reviews/export.jsonl")
    async def api_export_three_d_object_reviews() -> Response:
        body = state.feedback.export_three_d_object_reviews_jsonl()
        if body:
            body += "\n"
        return Response(body, media_type="application/x-ndjson")

    @app.get("/api/illustrations/objects/reviews")
    async def api_illustration_object_reviews(renderer: str = "", category: str = "") -> Dict[str, Any]:
        review_state = _build_illustration_object_review_state(
            feedback=state.feedback,
            selected_renderer=renderer,
            selected_category=category,
        )
        return {
            "summary": dict(review_state["summary"]),
            "reviews": [asdict(record) for record in state.feedback.illustration_object_reviews_by_item().values()],
        }

    @app.get("/api/illustrations/objects/reviews/export.jsonl")
    async def api_export_illustration_object_reviews() -> Response:
        body = state.feedback.export_illustration_object_reviews_jsonl()
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
        if path is None:
            raise HTTPException(status_code=404, detail="unknown media")
        if not path.exists():
            raise HTTPException(status_code=503, detail="review media is being regenerated; retry after reload completes")
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    @app.get("/overlay/{sample_uid}.png")
    async def overlay(sample_uid: str) -> StreamingResponse:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        image_path = index.media.get(sample.media_id)
        if image_path is None:
            raise HTTPException(status_code=404, detail="sample image missing")
        if not image_path.exists():
            raise HTTPException(status_code=503, detail="review media is being regenerated; retry after reload completes")
        payload = _load_sample_payload_or_503(index, sample)
        annotation_gt = payload.get("annotation_gt", {}) if isinstance(payload, dict) else {}
        trace_payload = payload.get("trace_payload", {}) if isinstance(payload, dict) else {}
        annotation_type = str(annotation_gt.get("type", sample.annotation_type)) if isinstance(annotation_gt, dict) else sample.annotation_type
        annotation_value = annotation_gt.get("value", sample.annotation_value) if isinstance(annotation_gt, dict) else sample.annotation_value
        overlay_type, overlay_value = resolve_overlay_annotation(
            annotation_type=annotation_type,
            annotation_value=annotation_value,
            trace_payload=trace_payload if isinstance(trace_payload, dict) else {},
        )
        try:
            with PILImage.open(image_path) as source:
                rendered = render_annotation_overlay(
                    source.convert("RGB"),
                    annotation_type=str(overlay_type),
                    annotation_value=overlay_value,
                )
                buffer = io.BytesIO()
                rendered.save(buffer, format="PNG")
                buffer.seek(0)
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail="review media is being regenerated; retry after reload completes",
            ) from exc
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
            feedback_thread_events_by_feedback=feedback.thread_events_by_feedback(feedback_ids),
        ),
    )


def _build_scene_review_samples(
    *,
    index: ReviewIndex,
    tasks: list[Any],
    samples_per_query: int = 2,
) -> Dict[str, Any]:
    scene_ids: list[Dict[str, Any]] = []
    summary = {
        "task_count": len(tasks),
        "query_count": 0,
        "requested_card_count": 0,
        "sample_card_count": 0,
        "missing_card_count": 0,
        "samples_per_query": int(samples_per_query),
    }
    for task in tasks:
        query_groups: list[Dict[str, Any]] = []
        for query_id in sorted(task.query_counts):
            query_key = ReviewIndex.query_key(task.domain, task.scene_id, task.task_id, query_id)
            sample_ids = list(index.samples_by_query.get(query_key, []))
            cards: list[Dict[str, Any]] = []
            for slot_index in range(int(samples_per_query)):
                sample = index.samples[sample_ids[slot_index]] if slot_index < len(sample_ids) else None
                if sample is None:
                    summary["missing_card_count"] += 1
                else:
                    summary["sample_card_count"] += 1
                cards.append(
                    {
                        "slot": slot_index + 1,
                        "sample": sample,
                        "missing": sample is None,
                    }
                )
            summary["query_count"] += 1
            summary["requested_card_count"] += int(samples_per_query)
            query_groups.append(
                {
                    "query_id": str(query_id),
                    "query_sample_count": int(task.query_counts.get(query_id, 0) or 0),
                    "query_path": (
                        f"/domains/{_url_segment(task.domain)}"
                        f"/scenes/{_url_segment(task.scene_id)}"
                        f"/tasks/{_url_segment(task.task_id)}"
                        f"/queries/{_url_segment(query_id)}?view=images"
                    ),
                    "cards": cards,
                }
            )
        scene_ids.append(
            {
                "task": task,
                "task_path": (
                    f"/domains/{_url_segment(task.domain)}"
                    f"/scenes/{_url_segment(task.scene_id)}"
                    f"/tasks/{_url_segment(task.task_id)}"
                ),
                "query_groups": query_groups,
            }
        )
    return {"summary": summary, "scene_ids": scene_ids}


def _build_feedback_work_queue(*, index: ReviewIndex, feedback: FeedbackStore, domain: str = "") -> Dict[str, Any]:
    open_feedback = feedback.list_open_feedback()
    selected_domain = str(domain or "").strip()
    if selected_domain:
        open_feedback = [record for record in open_feedback if record.domain == selected_domain]
    open_by_task: Dict[str, list[Any]] = {}
    for record in open_feedback:
        key = ReviewIndex.task_key(record.domain, record.scene_id, record.task_id)
        open_by_task.setdefault(key, []).append(record)

    task_entries = []
    summary = {
        "task_count": 0,
        "open_feedback_count": len(open_feedback),
    }
    for task_key, open_records in sorted(open_by_task.items()):
        task = index.tasks.get(task_key)
        indexed = task is not None
        if task is None:
            first_record = open_records[0]
            if str(first_record.task_id):
                task = SimpleNamespace(
                    domain=first_record.domain,
                    scene_id=first_record.scene_id,
                    task_id=first_record.task_id,
                    sample_count=0,
                )
            else:
                scene = index.scenes.get(ReviewIndex.scene_key(first_record.domain, first_record.scene_id))
                task = SimpleNamespace(
                    domain=first_record.domain,
                    scene_id=first_record.scene_id,
                    task_id="Scene review",
                    sample_count=int(getattr(scene, "sample_count", 0) or 0),
                )
                indexed = scene is not None
        open_records = open_by_task.get(task_key, [])
        scene_scope = not str(open_records[0].task_id) if open_records else False
        task_entries.append(
            {
                "task": task,
                "scope": "scene" if scene_scope else "task",
                "indexed": indexed,
                "flags": (
                    [
                        {
                            "kind": "feedback",
                            "label": f"{len(open_records)} open issue"
                            f"{'' if len(open_records) == 1 else 's'}",
                        }
                    ]
                    + ([{"kind": "scene", "label": "scene-level"}] if scene_scope else [])
                    + ([] if indexed else [{"kind": "stale", "label": "not in current index"}])
                ),
                "open_feedback": open_records,
                "task_path": (
                    f"/domains/{_url_segment(task.domain)}/scenes/{_url_segment(task.scene_id)}/review"
                    if scene_scope
                    else f"/domains/{_url_segment(task.domain)}/scenes/{_url_segment(task.scene_id)}/tasks/{_url_segment(task.task_id)}"
                ),
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


def _feedback_domain_tabs(
    *,
    index: ReviewIndex,
    feedback_by_domain: Dict[str, Dict[str, int]],
    selected_domain: str,
) -> list[Dict[str, Any]]:
    total_open = sum(int(value.get("open", 0)) for value in feedback_by_domain.values())
    tabs: list[Dict[str, Any]] = [
        {
            "domain": "",
            "label": "All",
            "path": "/issues",
            "open": total_open,
            "active": not selected_domain,
        }
    ]
    domain_names = sorted(set(index.domains) | set(feedback_by_domain))
    for domain_name in domain_names:
        open_count = int(feedback_by_domain.get(domain_name, {}).get("open", 0))
        tabs.append(
            {
                "domain": domain_name,
                "label": domain_name,
                "path": f"/issues?domain={_url_segment(domain_name)}",
                "open": open_count,
                "active": selected_domain == domain_name,
            }
        )
    return tabs


def _build_three_d_object_review_state(
    *,
    feedback: FeedbackStore,
    selected_group: str = "",
    selected_decision: str = "",
) -> Dict[str, Any]:
    profiles = _three_d_object_profiles()
    reviews_by_profile = feedback.three_d_object_reviews_by_profile()
    group_counts: Dict[str, int] = {}
    group_labels: Dict[str, str] = {}
    for profile in profiles:
        group_id = _three_d_object_group_id(profile)
        group_counts[group_id] = group_counts.get(group_id, 0) + 1
        group_labels.setdefault(group_id, _three_d_object_group_label(profile))
    selected_group_id = str(selected_group or "all")
    if selected_group_id not in {"all", *group_counts.keys()}:
        selected_group_id = "all"
    decision_filter = str(selected_decision or "").strip().lower()
    if decision_filter not in {"approve", "remove", "improve", "unreviewed"}:
        decision_filter = ""
    selected_profiles = tuple(
        profile
        for profile in profiles
        if selected_group_id == "all" or _three_d_object_group_id(profile) == selected_group_id
    )
    summary = {
        "total": len(selected_profiles),
        "all": len(selected_profiles),
        "approve": 0,
        "remove": 0,
        "improve": 0,
        "unreviewed": 0,
    }
    entries: list[Dict[str, Any]] = []
    for profile in selected_profiles:
        review = reviews_by_profile.get(str(profile.profile_id))
        if review is None:
            review = _empty_three_d_object_review_for_profile(profile)
        decision = str(review.decision or "").strip().lower()
        if decision not in {"approve", "remove", "improve"}:
            decision = "unreviewed"
        summary[decision] += 1
        if decision_filter and decision != decision_filter:
            continue
        next_path = f"/three-d/objects?group={_url_segment(selected_group_id)}"
        if decision_filter:
            next_path = f"{next_path}&decision={_url_segment(decision_filter)}"
        entries.append(
            {
                "profile": profile,
                "review": review,
                "decision": decision,
                "status_label": _three_d_object_status_label(decision),
                "anchor_id": _three_d_object_anchor_id(profile.profile_id),
                "preview_path": f"/three-d/objects/previews/{quote(str(profile.profile_id), safe='')}.png",
                "group_id": _three_d_object_group_id(profile),
                "group_label": _three_d_object_group_label(profile),
                "next_path": f"{next_path}#{_three_d_object_anchor_id(profile.profile_id)}",
            }
        )
    summary["total"] = len(entries)
    group_tabs = (
        {
            "id": "all",
            "label": "All groups",
            "count": len(profiles),
            "active": selected_group_id == "all",
            "href": "/three-d/objects"
            + (f"?decision={_url_segment(decision_filter)}" if decision_filter else ""),
        },
        *tuple(
            {
                "id": group_id,
                "label": group_labels[group_id],
                "count": group_counts[group_id],
                "active": selected_group_id == group_id,
                "href": (
                    f"/three-d/objects?group={_url_segment(group_id)}"
                    + (f"&decision={_url_segment(decision_filter)}" if decision_filter else "")
                ),
            }
            for group_id in sorted(
                group_counts,
                key=lambda value: (_three_d_object_group_sort_index(value), group_labels[value]),
            )
        ),
    )
    group_query = "" if selected_group_id == "all" else f"?group={_url_segment(selected_group_id)}"
    group_and = "&" if group_query else "?"
    decision_tabs = (
        {
            "id": "",
            "label": "All decisions",
            "count": summary["all"],
            "active": not decision_filter,
            "href": f"/three-d/objects{group_query}",
        },
        {
            "id": "approve",
            "label": "Approved",
            "count": summary["approve"],
            "active": decision_filter == "approve",
            "href": f"/three-d/objects{group_query}{group_and}decision=approve",
        },
        {
            "id": "improve",
            "label": "Improve",
            "count": summary["improve"],
            "active": decision_filter == "improve",
            "href": f"/three-d/objects{group_query}{group_and}decision=improve",
        },
        {
            "id": "remove",
            "label": "Remove",
            "count": summary["remove"],
            "active": decision_filter == "remove",
            "href": f"/three-d/objects{group_query}{group_and}decision=remove",
        },
        {
            "id": "unreviewed",
            "label": "Unreviewed",
            "count": summary["unreviewed"],
            "active": decision_filter == "unreviewed",
            "href": f"/three-d/objects{group_query}{group_and}decision=unreviewed",
        },
    )
    return {
        "selected_group": selected_group_id,
        "selected_decision": decision_filter,
        "group_tabs": group_tabs,
        "decision_tabs": decision_tabs,
        "entries": entries,
        "summary": summary,
        "decisions": (
            {"id": "approve", "label": "Approve"},
            {"id": "remove", "label": "Remove"},
            {"id": "improve", "label": "Improve rendering"},
        ),
    }


def _empty_three_d_object_review_for_profile(profile: Any) -> Any:
    from .models import ThreeDObjectReviewRecord

    return ThreeDObjectReviewRecord(
        profile_id=str(profile.profile_id),
        canonical_id=str(profile.canonical_id),
        object_type=str(profile.object_type),
        renderer=str(profile.renderer),
        source_scene=str(profile.source_scene),
    )


@lru_cache(maxsize=1)
def _three_d_object_profiles() -> tuple[Any, ...]:
    from trace.tasks.three_d.shared.object_resources import THREE_D_OBJECT_PROFILES

    return tuple(
        sorted(
            THREE_D_OBJECT_PROFILES,
            key=lambda profile: (
                _three_d_object_group_sort_index(_three_d_object_group_id(profile)),
                str(profile.size_class) != "small",
                str(profile.display_name).lower(),
                str(profile.source_scene),
                str(profile.role),
                str(profile.object_type),
            ),
        )
    )


@lru_cache(maxsize=1)
def _three_d_object_profile_by_id() -> Dict[str, Any]:
    return {str(profile.profile_id): profile for profile in _three_d_object_profiles()}


@lru_cache(maxsize=512)
def _three_d_object_preview_png(profile_id: str) -> bytes:
    from trace.tasks.three_d.shared.object_inventory_preview import render_three_d_object_profile_preview

    profile = _three_d_object_profile_by_id().get(str(profile_id))
    if profile is None:
        raise ValueError(f"unknown 3D object profile: {profile_id}")
    preview = render_three_d_object_profile_preview(
        profile,
        canvas_width=420,
        canvas_height=330,
        instance_seed=17,
        crop_to_object=True,
        crop_padding_px=18,
    )
    buffer = io.BytesIO()
    preview.image.save(buffer, format="PNG")
    return buffer.getvalue()


def _decode_three_d_profile_token(profile_token: str) -> str:
    token = unquote(str(profile_token))
    if token.endswith(".png"):
        token = token[:-4]
    return token


def _three_d_object_group_id(profile: Any) -> str:
    return f"{profile.source_scene}__{profile.renderer}"


def _three_d_object_group_label(profile: Any) -> str:
    labels = {
        "object_scene__object_scene_shape": "Object Scene",
        "object_cluster__object_scene_shape": "Object Cluster",
        "room__room_wall_object": "Room Wall",
        "room__room_floor_object": "Room Floor",
        "street__street_object": "Street",
        "surface_fixture__surface_fixture": "Surface Fixture",
        "warehouse__warehouse_object": "Warehouse",
    }
    return labels.get(_three_d_object_group_id(profile), f"{profile.source_scene} / {profile.renderer}")


def _three_d_object_group_sort_index(group_id: str) -> int:
    order = {
        "object_scene__object_scene_shape": 0,
        "object_cluster__object_scene_shape": 1,
        "room__room_wall_object": 2,
        "room__room_floor_object": 3,
        "street__street_object": 4,
        "surface_fixture__surface_fixture": 5,
        "warehouse__warehouse_object": 6,
    }
    return order.get(str(group_id), 99)


def _three_d_object_status_label(decision: str) -> str:
    return {
        "approve": "Approved",
        "remove": "Remove",
        "improve": "Improve rendering",
        "unreviewed": "Unreviewed",
    }.get(str(decision), "Unreviewed")


def _three_d_object_anchor_id(profile_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(profile_id)).strip("-")
    return f"three-d-object-{cleaned or 'profile'}"


def _build_illustration_object_review_state(
    *,
    feedback: FeedbackStore,
    selected_renderer: str,
    selected_category: str,
    selected_decision: str = "",
) -> Dict[str, Any]:
    renderer = str(selected_renderer or "")
    if renderer not in ILLUSTRATION_RENDERER_LABELS:
        renderer = next(iter(ILLUSTRATION_RENDERER_LABELS))
    category = str(selected_category or "all")
    decision_filter = str(selected_decision or "").strip().lower()
    if decision_filter not in {*ILLUSTRATION_OBJECT_REVIEW_DECISIONS, "unreviewed"}:
        decision_filter = ""
    category_tabs = illustration_object_category_tabs(
        renderer_style=renderer,
        selected_category=category,
    )
    valid_categories = {str(tab["category"]) for tab in category_tabs}
    if category not in valid_categories:
        category = "all"
        category_tabs = illustration_object_category_tabs(
            renderer_style=renderer,
            selected_category=category,
        )
    items = filtered_illustration_object_items(
        renderer_style=renderer,
        category=category,
    )
    reviews_by_item = feedback.illustration_object_reviews_by_item()
    summary = {
        "total": len(items),
        "all": len(items),
        "approve": 0,
        "remove": 0,
        "improve": 0,
        "unreviewed": 0,
    }
    entries: list[Dict[str, Any]] = []
    for item in items:
        review = reviews_by_item.get(str(item.item_id))
        if review is None:
            review = _empty_illustration_object_review_for_item(item)
        decision = str(review.decision or "").strip().lower()
        if decision not in ILLUSTRATION_OBJECT_REVIEW_DECISIONS:
            decision = "unreviewed"
        summary[decision] += 1
        if decision_filter and decision != decision_filter:
            continue
        next_path = f"/illustrations/objects?renderer={_url_segment(renderer)}&category={_url_segment(category)}"
        if decision_filter:
            next_path = f"{next_path}&decision={_url_segment(decision_filter)}"
        entries.append(
            {
                "item": item,
                "review": review,
                "decision": decision,
                "status_label": _illustration_object_status_label(decision),
                "anchor_id": _illustration_object_anchor_id(item.item_id),
                "preview_path": f"/illustrations/objects/previews/{quote(str(item.item_id), safe='')}.png",
                "next_path": f"{next_path}#{_illustration_object_anchor_id(item.item_id)}",
            }
        )
    summary["total"] = len(entries)
    decision_tabs = (
        {"id": "", "label": "All decisions", "count": summary["all"], "active": not decision_filter},
        {"id": "approve", "label": "Approved", "count": summary["approve"], "active": decision_filter == "approve"},
        {"id": "improve", "label": "Improve", "count": summary["improve"], "active": decision_filter == "improve"},
        {"id": "remove", "label": "Remove", "count": summary["remove"], "active": decision_filter == "remove"},
        {"id": "unreviewed", "label": "Unreviewed", "count": summary["unreviewed"], "active": decision_filter == "unreviewed"},
    )
    return {
        "selected_renderer": renderer,
        "selected_category": category,
        "selected_decision": decision_filter,
        "renderer_tabs": illustration_object_renderer_tabs(renderer),
        "category_tabs": category_tabs,
        "decision_tabs": decision_tabs,
        "entries": entries,
        "summary": summary,
        "decisions": (
            {"id": "approve", "label": "Approve"},
            {"id": "remove", "label": "Remove"},
            {"id": "improve", "label": "Improve rendering"},
        ),
    }


def _empty_illustration_object_review_for_item(item: Any) -> Any:
    from .models import IllustrationObjectReviewRecord

    return IllustrationObjectReviewRecord(
        item_id=str(item.item_id),
        renderer_style=str(item.renderer_style),
        category=str(item.category),
        object_type=str(item.object_type),
        label=str(item.display_label),
    )


@lru_cache(maxsize=1024)
def _illustration_object_preview_png(item_id: str) -> bytes:
    preview = render_illustration_object_review_image(str(item_id))
    buffer = io.BytesIO()
    preview.save(buffer, format="PNG")
    return buffer.getvalue()


def _decode_illustration_object_token(item_token: str) -> str:
    token = unquote(str(item_token))
    if token.endswith(".png"):
        token = token[:-4]
    return token


def _illustration_object_status_label(decision: str) -> str:
    return {
        "approve": "Approved",
        "remove": "Remove",
        "improve": "Improve rendering",
        "unreviewed": "Unreviewed",
    }.get(str(decision), "Unreviewed")


def _illustration_object_anchor_id(item_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(item_id)).strip("-")
    return f"illustration-object-{cleaned or 'item'}"


def _context(request: Request, *, index: ReviewIndex, title: str, **extra: Any) -> Dict[str, Any]:
    feedback = request.app.state.review.feedback
    audit_by_task = _effective_audits_by_task(index, feedback.task_audits_by_task())
    task_status_by_task, status_by_scene, status_by_domain = _status_summaries(index, audit_by_task)
    feedback_by_domain = feedback.counts_by_domain()
    reload_status = request.app.state.review.reload_status()
    context: Dict[str, Any] = {
        "request": request,
        "title": title,
        "index": index,
        "review_root_display": _display_path(index.root, repo_root=index.repo_root),
        "review_index_stale": bool(reload_status.get("stale")),
        "review_reload_status": reload_status,
        "review_stale_scenes": reload_status.get("stale_scenes", []),
        "review_stale_scene_keys": [
            str(scene.get("key", ""))
            for scene in reload_status.get("stale_scenes", [])
            if isinstance(scene, dict)
        ],
        "review_full_reload_enabled": bool(getattr(request.app.state, "allow_full_reload", False)),
        "feedback_by_domain": feedback_by_domain,
        "feedback_by_scene": feedback.counts_by_scene(),
        "feedback_by_task": feedback.counts_by_task(),
        "feedback_by_sample": feedback.counts_by_sample(),
        "feedback_open_count": sum(int(value.get("open", 0)) for value in feedback_by_domain.values()),
        "audit_by_task": audit_by_task,
        "task_status_by_task": task_status_by_task,
        "status_by_scene": status_by_scene,
        "status_by_domain": status_by_domain,
        "feedback_source_path": _feedback_source_path,
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
            {"total": 0, "review_pass": 0, "solve_rate_pass": 0, "solve_artifact_pass": 0, "complete": 0},
        )
        domain_entry = domain_status.setdefault(
            task.domain,
            {"total": 0, "review_pass": 0, "solve_rate_pass": 0, "solve_artifact_pass": 0, "complete": 0},
        )
        for entry in (scene_entry, domain_entry):
            entry["total"] += 1
            entry["review_pass"] += int(payload["review_pass"])
            entry["solve_rate_pass"] += int(payload["solve_rate_pass"])
            entry["solve_artifact_pass"] += int(payload["solve_artifact_pass"])
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
    review_pass = bool(getattr(audit, "review_pass", False))
    solve_rate_pass = bool(getattr(audit, "solve_rate_pass", False))
    solve_artifact_pass = bool(getattr(task, "solve_pass", False))
    complete = bool(review_pass and solve_rate_pass)
    return {
        "review_pass": review_pass,
        "review_count": int(getattr(audit, "review_count", 0)),
        "review_total": int(getattr(audit, "review_total", 6)),
        "code_review_pass": bool(getattr(audit, "code_review_pass", False)),
        "taxonomy_review_pass": bool(getattr(audit, "taxonomy_review_pass", False)),
        "solve_rate_pass": solve_rate_pass,
        "solve_artifact_pass": solve_artifact_pass,
        "complete": complete,
        # Backward-compatible API aliases.
        "manual_pass": review_pass,
        "manual_count": int(getattr(audit, "review_count", 0)),
        "manual_total": int(getattr(audit, "review_total", 6)),
        "solve_pass": solve_artifact_pass,
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


def _feedback_task_path(record: Any) -> str:
    if not str(getattr(record, "task_id", "") or ""):
        return (
            f"/domains/{_url_segment(record.domain)}"
            f"/scenes/{_url_segment(record.scene_id)}"
            "/review"
        )
    return (
        f"/domains/{_url_segment(record.domain)}"
        f"/scenes/{_url_segment(record.scene_id)}"
        f"/tasks/{_url_segment(record.task_id)}"
    )


def _feedback_source_path(record: Any) -> str:
    taxonomy_path = _taxonomy_feedback_source_path(record)
    if taxonomy_path:
        return taxonomy_path
    task_path = _feedback_task_path(record)
    if not str(getattr(record, "task_id", "") or ""):
        return f"{task_path}#scene-feedback"
    if not getattr(record, "sample_uid", ""):
        return task_path
    query_id = str(getattr(record, "query_id", "") or "")
    if query_id:
        task_path = f"{task_path}/queries/{_url_segment(query_id)}"
    return f"{task_path}?view=rows#sample-{_url_segment(getattr(record, 'sample_uid', ''))}"


def _taxonomy_task_matches(task: Any, query: str) -> bool:
    haystack = " ".join(
        [
            str(task.domain),
            str(task.scene_id),
            str(task.current_task_id),
            str(task.current_objective),
            str(task.decision),
            " ".join(str(value) for value in getattr(task, "proposed_task_ids", [])),
            " ".join(str(getattr(row, "query_id", "")) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "proposed_objective", "")) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "program_signature_id", "")) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "program_schema", "")) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "base_program_contract", "")) for row in getattr(task, "queries", [])),
            " ".join(json.dumps(getattr(row, "program_arguments", {}), sort_keys=True) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "answer_schema", "")) for row in getattr(task, "queries", [])),
            " ".join(str(getattr(row, "annotation_schema", "")) for row in getattr(task, "queries", [])),
        ]
    ).lower()
    return query in haystack


def _taxonomy_task_approved(task: Any, review_by_task: Dict[str, Any]) -> bool:
    review = review_by_task.get(getattr(task, "task_key", ""))
    return bool(getattr(review, "approved", False))


def _taxonomy_task_path(round_id: str, task: Any) -> str:
    return (
        f"/taxonomy/{_taxonomy_round_slug(round_id)}"
        f"/domains/{_url_segment(getattr(task, 'domain', ''))}"
        f"/scenes/{_url_segment(getattr(task, 'scene_id', ''))}"
        f"/tasks/{_url_segment(getattr(task, 'current_task_id', ''))}"
    )


def _next_taxonomy_task(
    *,
    tasks: list[Any],
    current_task: Any,
    review_by_task: Dict[str, Any],
    pending_only: bool,
) -> Any | None:
    current_key = str(getattr(current_task, "task_key", ""))
    found_current = False
    for candidate in tasks:
        candidate_key = str(getattr(candidate, "task_key", ""))
        if not found_current:
            found_current = candidate_key == current_key
            continue
        if pending_only and _taxonomy_task_approved(candidate, review_by_task):
            continue
        return candidate
    return None


def _taxonomy_review_progress(
    *,
    tasks: list[Any],
    review_by_task: Dict[str, Any],
    open_issue_counts: Dict[str, int],
) -> Any:
    total = len(tasks)
    approved = sum(1 for task in tasks if _taxonomy_task_approved(task, review_by_task))
    open_issue_tasks = sum(1 for task in tasks if open_issue_counts.get(getattr(task, "task_key", ""), 0))
    open_issues = sum(open_issue_counts.get(getattr(task, "task_key", ""), 0) for task in tasks)
    pending = max(0, total - approved)
    return SimpleNamespace(
        total=total,
        approved=approved,
        pending=pending,
        open_issue_tasks=open_issue_tasks,
        open_issues=open_issues,
        percent=(100.0 * approved / total) if total else 0.0,
    )


def _taxonomy_open_issue_counts(records: list[Any], round_id: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for key, task_records in _taxonomy_open_issues_by_task(records, round_id).items():
        counts[key] = len(task_records)
    return counts


def _taxonomy_open_issues_by_task(records: list[Any], round_id: str) -> Dict[str, list[Any]]:
    issues_by_task: Dict[str, list[Any]] = {}
    for record in _taxonomy_feedback_records(records, round_id):
        if str(getattr(record, "status", "")) != "open":
            continue
        key = ReviewIndex.task_key(
            str(getattr(record, "domain", "")),
            str(getattr(record, "scene_id", "")),
            str(getattr(record, "task_id", "")),
        )
        issues_by_task.setdefault(key, []).append(record)
    return issues_by_task


def _build_taxonomy_tree(units: list[Any]) -> list[Any]:
    by_domain: Dict[str, Dict[str, Dict[str, list[Any]]]] = {}
    for unit in units:
        domain = str(getattr(unit, "domain", ""))
        root = str(getattr(unit, "semantic_root", "")) or "uncategorized"
        family = str(getattr(unit, "semantic_family", "")) or "uncategorized"
        by_domain.setdefault(domain, {}).setdefault(root, {}).setdefault(family, []).append(unit)

    tree: list[Any] = []
    for domain, roots in sorted(by_domain.items()):
        root_entries: list[Any] = []
        for root, families in sorted(roots.items()):
            family_entries: list[Any] = []
            for family, family_units in sorted(families.items()):
                ordered_units = sorted(family_units, key=lambda unit: (unit.scene_id, unit.proposed_task_id))
                family_entries.append(
                    SimpleNamespace(
                        family=family,
                        unit_count=len(ordered_units),
                        units=ordered_units,
                    )
                )
            root_entries.append(
                SimpleNamespace(
                    root=root,
                    unit_count=sum(entry.unit_count for entry in family_entries),
                    families=family_entries,
                )
            )
        tree.append(
            SimpleNamespace(
                domain=domain,
                unit_count=sum(entry.unit_count for entry in root_entries),
                roots=root_entries,
            )
        )
    return tree


def _normalize_taxonomy_round(round_slug: str) -> str:
    text = str(round_slug or DEFAULT_TAXONOMY_ROUND).strip().lower()
    aliases = {
        "current": DEFAULT_TAXONOMY_ROUND,
        "v0": DEFAULT_TAXONOMY_ROUND,
        "contract-v0": DEFAULT_TAXONOMY_ROUND,
        "contract_v0": DEFAULT_TAXONOMY_ROUND,
        "contract-v0-reanalysis": DEFAULT_TAXONOMY_ROUND,
    }
    return aliases.get(text, text)


def _taxonomy_round_slug(round_id: str) -> str:
    text = _normalize_taxonomy_round(round_id)
    if text == DEFAULT_TAXONOMY_ROUND:
        return "contract-v0"
    return text


def _taxonomy_feedback_prefix(round_id: str, *, query_id: str = "") -> str:
    normalized_round = _normalize_taxonomy_round(round_id)
    query_text = str(query_id or "").strip()
    if query_text:
        return f"[taxonomy:{normalized_round} query={query_text}]"
    return f"[taxonomy:{normalized_round}]"


def _taxonomy_feedback_records(records: list[Any], round_id: str) -> list[Any]:
    round_prefix = f"[taxonomy:{_normalize_taxonomy_round(round_id)}"
    return [record for record in records if str(getattr(record, "comment", "")).startswith(round_prefix)]


def _taxonomy_feedback_source_path(record: Any) -> str:
    comment = str(getattr(record, "comment", ""))
    match = re.match(r"\[taxonomy:([a-z0-9_-]+)(?: query=([^\]]+))?\]", comment)
    if not match:
        return ""
    round_slug = _taxonomy_round_slug(match.group(1))
    path = (
        f"/taxonomy/{_url_segment(round_slug)}"
        f"/domains/{_url_segment(getattr(record, 'domain', ''))}"
        f"/scenes/{_url_segment(getattr(record, 'scene_id', ''))}"
        f"/tasks/{_url_segment(getattr(record, 'task_id', ''))}"
    )
    query_id = str(match.group(2) or "").strip()
    if query_id:
        path = f"{path}#query-{_url_segment(query_id)}"
    return path


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


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _loading_review_index(*, review_root: Path, repo_root: Path) -> ReviewIndex:
    return ReviewIndex(
        root=Path(review_root).resolve(),
        repo_root=Path(repo_root).resolve(),
        built_at=_utc_timestamp(),
        errors=["Review index is loading in the background."],
    )


def _max_review_file_mtime_ns(root: Path) -> int:
    if not root.exists():
        return 0
    max_mtime = 0
    for path in _iter_review_marker_files(root):
        try:
            if path.is_file():
                max_mtime = max(max_mtime, path.stat().st_mtime_ns)
        except OSError:
            continue
    return max_mtime


def _review_stale_summary(root: Path, snapshot_ns: int) -> tuple[bool, list[Dict[str, str]]]:
    if not root.exists():
        return False, []
    stale = False
    scene_keys: dict[str, Dict[str, str]] = {}
    for path in _iter_review_marker_files(root):
        try:
            if not path.is_file():
                continue
            if path.stat().st_mtime_ns <= int(snapshot_ns):
                continue
        except OSError:
            continue
        stale = True
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if len(parts) < 3:
            continue
        domain, scene_id = str(parts[0]), str(parts[1])
        if domain.startswith(".") or scene_id.startswith("."):
            continue
        key = f"{domain}/{scene_id}"
        scene_keys.setdefault(key, {"domain": domain, "scene_id": scene_id, "key": key})
    return stale, [scene_keys[key] for key in sorted(scene_keys)]


def _iter_review_marker_files(root: Path):
    """Yield cheap review index marker files instead of every sample image/data file."""

    if not root.exists():
        return
    root_markers = ("review_summary.json",)
    for name in root_markers:
        yield root / name
    try:
        domain_dirs = [path for path in root.iterdir() if path.is_dir()]
    except OSError:
        return
    scene_markers = (
        "scene_review_manifest.json",
        "manual_code_audit_status.json",
        "taxonomy_review_status.json",
        "migration_test_status.json",
    )
    task_markers = (
        "manifest.json",
        "distribution.json",
        "solve_rate.json",
        "solve_rate_summary.json",
    )
    for domain_dir in domain_dirs:
        if domain_dir.name.startswith("."):
            continue
        if domain_dir.name in {"assets"}:
            continue
        try:
            scene_dirs = [path for path in domain_dir.iterdir() if path.is_dir()]
        except OSError:
            continue
        for scene_dir in scene_dirs:
            if scene_dir.name.startswith("."):
                continue
            for name in scene_markers:
                yield scene_dir / name
            try:
                task_dirs = [path for path in scene_dir.iterdir() if path.is_dir()]
            except OSError:
                continue
            for task_dir in task_dirs:
                if task_dir.name.startswith("."):
                    continue
                for name in task_markers:
                    yield task_dir / name


def _stale_review_scenes(root: Path, snapshot_ns: int) -> list[Dict[str, str]]:
    _stale, scenes = _review_stale_summary(root, snapshot_ns)
    return scenes


def _publish_in_progress_scenes(errors: Any) -> list[Dict[str, str]]:
    scenes: dict[str, Dict[str, str]] = {}
    for error in errors or []:
        scene = _publish_error_scene(error)
        if scene is None:
            continue
        scenes.setdefault(str(scene["key"]), scene)
    return [scenes[key] for key in sorted(scenes)]


def _filter_active_publish_errors(errors: Any, *, review_root: Path) -> list[Any]:
    """Keep publish-in-progress errors only while the scene lock is active."""

    filtered: list[Any] = []
    for error in errors or []:
        scene = _publish_error_scene(error)
        if scene is None:
            filtered.append(error)
            continue
        if review_file_lock_active(
            scene_publish_lock_path(
                review_root=review_root,
                domain=str(scene["domain"]),
                scene_id=str(scene["scene_id"]),
            )
        ):
            filtered.append(error)
    return filtered


def _publish_error_scene(error: Any) -> Dict[str, str] | None:
    """Parse a publish-in-progress index error into a scene key."""

    text = str(error)
    if PUBLISH_IN_PROGRESS_ERROR not in text:
        return None
    scene_text = text.split(":", 1)[0].strip()
    if "/" not in scene_text:
        return None
    domain, scene_id = scene_text.split("/", 1)
    if not domain or not scene_id:
        return None
    key = f"{domain}/{scene_id}"
    return {"domain": domain, "scene_id": scene_id, "key": key}


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


def _strip_base_url_from_scope(scope: dict[str, Any], base_url: str) -> None:
    """Accept requests whose proxy prefix was not stripped before forwarding."""

    base = _normalize_base_url(base_url)
    if not base:
        return
    path = str(scope.get("path") or "")
    if path == base:
        scope["path"] = "/"
    elif path.startswith(f"{base}/"):
        scope["path"] = path[len(base) :] or "/"


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


def _request_wants_json(request: Request) -> bool:
    requested_with = str(request.headers.get("x-requested-with", "")).strip().lower()
    accept = str(request.headers.get("accept", "")).strip().lower()
    return requested_with in {"fetch", "xmlhttprequest"} or "application/json" in accept


async def _request_data(request: Request) -> Dict[str, str]:
    content_type = str(request.headers.get("content-type", "")).lower()
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            return {str(key): "" if value is None else str(value) for key, value in payload.items()}
        return {}
    if "multipart/form-data" in content_type:
        form = await request.form()
        items = form.multi_items() if hasattr(form, "multi_items") else form.items()
        return {str(key): "" if value is None else str(value) for key, value in items}
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


def _load_sample_payload_or_503(index: ReviewIndex, sample: SampleRecord) -> Dict[str, Any]:
    try:
        return load_sample_payload(index, sample)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="review sample artifacts are being regenerated; retry after reload completes",
        ) from exc


def _transient_error_response(request: Request, *, status_code: int, detail: str) -> Response:
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": detail}, status_code=int(status_code))
    return HTMLResponse(
        (
            "<!doctype html><title>TRACE Review unavailable</title>"
            "<main style='font-family: sans-serif; max-width: 720px; margin: 48px auto;'>"
            f"<h1>{int(status_code)} Review app unavailable</h1>"
            f"<p>{detail}</p>"
            "<p>Refresh after the current artifact generation or reload finishes.</p>"
            "</main>"
        ),
        status_code=int(status_code),
    )


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
