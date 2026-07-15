"""FastAPI server for browsing benchmark model-performance artifacts."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import threading
import time
from typing import Any
from urllib.parse import quote, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .indexing import build_benchmark_index, load_sample_payload
from .models import BenchmarkIndex, SampleRecord


class BenchmarkReviewState:
    """Mutable benchmark-review state shared by routes."""

    def __init__(self, *, run_root: Path, repo_root: Path) -> None:
        self.run_root = Path(run_root).resolve()
        self.repo_root = Path(repo_root).resolve()
        self._lock = threading.RLock()
        self._index = build_benchmark_index(self.run_root, repo_root=self.repo_root)
        self._mtime_snapshot_ns = _max_file_mtime_ns(self.run_root)
        self._stale_cache = False
        self._stale_cache_until_ns = 0

    def index(self) -> BenchmarkIndex:
        with self._lock:
            return self._index

    def reload(self) -> BenchmarkIndex:
        fresh = build_benchmark_index(self.run_root, repo_root=self.repo_root)
        fresh_mtime = _max_file_mtime_ns(self.run_root)
        with self._lock:
            self._index = fresh
            self._mtime_snapshot_ns = fresh_mtime
            self._stale_cache = False
            self._stale_cache_until_ns = 0
            return fresh

    def stale(self) -> bool:
        now = time.monotonic_ns()
        with self._lock:
            if now < self._stale_cache_until_ns:
                return self._stale_cache
            snapshot = self._mtime_snapshot_ns
        stale = _max_file_mtime_ns(self.run_root) > snapshot
        with self._lock:
            self._stale_cache = stale
            self._stale_cache_until_ns = now + 2_000_000_000
        return stale


def create_app(
    *,
    run_root: Path | str = "runs/external_benchmarks/qwen25vl7b/20260522T062435Z",
    repo_root: Path | str | None = None,
    token: str | None = None,
    base_url: str = "",
) -> FastAPI:
    """Create the standalone benchmark-review web app."""

    resolved_run_root = Path(run_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root(resolved_run_root)
    resolved_base_url = _normalize_base_url(base_url)
    state = BenchmarkReviewState(run_root=resolved_run_root, repo_root=resolved_repo_root)

    package_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(package_dir / "templates"))
    templates.env.filters["pretty_json"] = _pretty_json
    templates.env.filters["excerpt"] = _excerpt
    templates.env.filters["pct"] = _pct
    templates.env.filters["score"] = _score
    templates.env.globals["app_path"] = lambda path="": _app_path(resolved_base_url, str(path))
    templates.env.globals["benchmark_path"] = lambda benchmark, filter_name="all", category="all", q="": _benchmark_path(
        resolved_base_url,
        str(benchmark),
        filter_name=str(filter_name),
        category=str(category),
        q=str(q),
    )
    templates.env.globals["static_version"] = _static_version(package_dir / "static")

    app = FastAPI(title="Trace Benchmark Review")
    app.state.benchmark_review = state
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
    async def healthz() -> dict[str, str]:
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
                response.set_cookie("trace_benchmark_review_token", submitted, httponly=True, samesite="lax")
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
        response.delete_cookie("trace_benchmark_review_token")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index_page(request: Request) -> HTMLResponse:
        index = state.index()
        return templates.TemplateResponse(request, "index.html", _context(request, index=index, title="Benchmarks"))

    @app.get("/benchmarks", response_class=HTMLResponse)
    async def benchmarks_index_page(request: Request) -> HTMLResponse:
        index = state.index()
        return templates.TemplateResponse(request, "index.html", _context(request, index=index, title="Benchmarks"))

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request, q: str = "") -> HTMLResponse:
        index = state.index()
        query = str(q or "").strip().lower()
        samples: list[SampleRecord] = []
        if query:
            for sample in index.samples.values():
                haystack = " ".join(
                    [
                        sample.display,
                        sample.doc_id,
                        sample.task_name,
                        sample.prompt,
                        sample.model_response,
                        sample.target_label,
                        sample.extracted_answer,
                        sample.category,
                    ]
                ).lower()
                if query in haystack:
                    samples.append(sample)
                if len(samples) >= 250:
                    break
        return templates.TemplateResponse(
            request,
            "search.html",
            _context(request, index=index, title="Search", q=q, samples=samples),
        )

    @app.get("/benchmarks/{benchmark}", response_class=HTMLResponse)
    async def benchmark_page(
        request: Request,
        benchmark: str,
        filter: str = "all",
        category: str = "all",
        q: str = "",
    ) -> HTMLResponse:
        index = state.index()
        record = index.benchmarks.get(benchmark)
        if record is None:
            raise HTTPException(status_code=404, detail="unknown benchmark")
        active_filter = _normalize_filter(filter)
        active_category = _normalize_category(record, category)
        samples = _samples_for_benchmark(index, benchmark, active_filter, q, active_category)
        return templates.TemplateResponse(
            request,
            "benchmark.html",
            _context(
                request,
                index=index,
                title=record.display,
                benchmark=record,
                samples=samples,
                active_filter=active_filter,
                active_category=active_category,
                q=q,
            ),
        )

    @app.get("/samples/{sample_uid}", response_class=HTMLResponse)
    async def sample_page(request: Request, sample_uid: str) -> HTMLResponse:
        index = state.index()
        sample = index.samples.get(sample_uid)
        if sample is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        payload = load_sample_payload(index, sample)
        return templates.TemplateResponse(
            request,
            "sample.html",
            _context(
                request,
                index=index,
                title=f"{sample.display} sample {sample.doc_id}",
                sample=sample,
                payload=payload,
            ),
        )

    @app.get("/media/{media_id}")
    async def media(media_id: str) -> FileResponse:
        index = state.index()
        path = index.media.get(media_id)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="unknown media")
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    @app.post("/api/reload")
    async def api_reload(request: Request) -> Response:
        index = state.reload()
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(_app_path(resolved_base_url, "/"), status_code=303)
        return JSONResponse(index.as_summary())

    @app.get("/api/index")
    async def api_index() -> dict[str, Any]:
        return state.index().as_summary()

    @app.get("/api/search-suggest")
    async def api_search_suggest(q: str = "") -> dict[str, Any]:
        return {"results": _search_suggestions(state.index(), q, base_url=resolved_base_url)}

    return app


def _context(request: Request, *, index: BenchmarkIndex, title: str, **extra: Any) -> dict[str, Any]:
    state: BenchmarkReviewState = request.app.state.benchmark_review
    context = {
        "request": request,
        "index": index,
        "title": title,
        "run_root_display": _display_path(index.run_root, repo_root=index.repo_root),
        "index_stale": state.stale(),
    }
    context.update(extra)
    return context


def _samples_for_benchmark(
    index: BenchmarkIndex,
    benchmark: str,
    filter_name: str,
    query: str,
    category: str = "all",
) -> list[SampleRecord]:
    query_l = str(query or "").strip().lower()
    category_name = str(category or "all")
    out: list[SampleRecord] = []
    for uid in index.samples_by_benchmark.get(benchmark, []):
        sample = index.samples[uid]
        if filter_name != "all" and sample.status != filter_name:
            continue
        if category_name != "all" and sample.category != category_name:
            continue
        if query_l:
            haystack = " ".join(
                [
                    sample.doc_id,
                    sample.task_name,
                    sample.prompt,
                    sample.model_response,
                    sample.target_label,
                    sample.extracted_answer,
                    sample.category,
                ]
            ).lower()
            if query_l not in haystack:
                continue
        out.append(sample)
    return out


def _normalize_filter(value: str) -> str:
    value = str(value or "all").lower().strip()
    return value if value in {"all", "correct", "incorrect", "unknown"} else "all"


def _normalize_category(benchmark: Any, value: str) -> str:
    value = str(value or "all").strip()
    if not value or value == "all":
        return "all"
    category_counts = getattr(benchmark, "category_counts", {}) or {}
    if value in category_counts:
        return value
    lowered = value.lower()
    for category in category_counts:
        if str(category).lower() == lowered:
            return str(category)
    return "all"


def _search_suggestions(index: BenchmarkIndex, q: str, *, base_url: str) -> list[dict[str, str]]:
    query = str(q or "").strip().lower()
    if not query:
        return []
    results: list[dict[str, str]] = []
    for benchmark, record in index.benchmarks.items():
        if query in benchmark.lower() or query in record.display.lower():
            results.append(
                {
                    "type": "benchmark",
                    "label": record.display,
                    "detail": f"{record.sample_count} samples",
                    "url": _app_path(base_url, f"/benchmarks/{benchmark}"),
                }
            )
    for sample in index.samples.values():
        haystack = " ".join([sample.display, sample.doc_id, sample.task_name, sample.prompt]).lower()
        if query in haystack:
            results.append(
                {
                    "type": "sample",
                    "label": f"{sample.display} #{sample.doc_id}",
                    "detail": sample.prompt[:90],
                    "url": _app_path(base_url, f"/samples/{sample.uid}"),
                }
            )
        if len(results) >= 20:
            break
    return results[:20]


def _request_is_public(request: Request) -> bool:
    path = request.url.path
    return path.startswith("/static") or path.startswith("/media") or path in {"/healthz", "/login"}


def _request_has_token(request: Request, token: str) -> bool:
    auth = request.headers.get("authorization", "")
    if auth == f"Bearer {token}":
        return True
    if request.cookies.get("trace_benchmark_review_token") == token:
        return True
    return str(request.query_params.get("token") or "") == token


async def _request_data(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        return dict(data) if isinstance(data, dict) else {}
    form = await request.form()
    return dict(form)


def _safe_next(value: str) -> str:
    text = str(value or "/")
    if not text.startswith("/") or text.startswith("//"):
        return "/"
    return text


def _benchmark_path(base_url: str, benchmark: str, *, filter_name: str = "all", category: str = "all", q: str = "") -> str:
    params: dict[str, str] = {"filter": _normalize_filter(filter_name)}
    category_name = str(category or "all").strip()
    if category_name and category_name != "all":
        params["category"] = category_name
    query = str(q or "").strip()
    if query:
        params["q"] = query
    return _app_path(base_url, f"/benchmarks/{quote(str(benchmark), safe='')}?{urlencode(params)}")


def _pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _excerpt(value: Any, length: int = 240) -> str:
    text = "" if value is None else str(value)
    if len(text) <= length:
        return text
    return text[: max(0, length - 3)].rstrip() + "..."


def _pct(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "n/a"


def _score(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _normalize_base_url(base_url: str) -> str:
    text = str(base_url or "").strip()
    if not text:
        return ""
    return "/" + text.strip("/")


def _app_path(base_url: str, path: str = "") -> str:
    suffix = "/" + str(path or "").lstrip("/")
    if suffix == "/":
        suffix = "/"
    return f"{base_url}{suffix}" if base_url else suffix


def _static_version(static_dir: Path) -> str:
    latest = 0
    for path in static_dir.rglob("*"):
        if path.is_file():
            latest = max(latest, path.stat().st_mtime_ns)
    return str(latest or int(time.time()))


def _max_file_mtime_ns(root: Path) -> int:
    latest = 0
    if not root.exists():
        return 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                latest = max(latest, path.stat().st_mtime_ns)
            except OSError:
                pass
    return latest


def _infer_repo_root(path: Path) -> Path:
    current = path.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return Path.cwd().resolve()
