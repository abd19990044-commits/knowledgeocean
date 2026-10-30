"""Bounded PDF workers, reusable search-time batches, and complete multipart indexes."""
import atexit
import csv
import hashlib
import html
import json
import multiprocessing
import os
import shutil
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

from config_loader import bounded_env_int

_POOL = None
_POOL_LOCK = threading.Lock()
_SLOTS = threading.BoundedSemaphore(4)


def _pool():
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            # Spawn avoids forking a multithreaded web server and its SQLite locks.
            _POOL = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"))
        return _POOL


def _shutdown():
    if _POOL is not None:
        _POOL.shutdown(wait=False, cancel_futures=True)


atexit.register(_shutdown)


def _render(job):
    # Both ordinary and comprehensive reports use the existing rendering code.
    from app import generate_documents, generate_all_papers_index
    path = job["path"]
    temp_path = path + ".partial"
    try:
        if job["kind"] == "index":
            generate_all_papers_index(job["query"], job["papers"], temp_path, title_prefix=job["label"])
        else:
            generate_documents(job["query"], job["papers"], temp_path, **job["options"])
        with open(temp_path, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError("PDF renderer produced an invalid document")
            stream.seek(max(0, os.path.getsize(temp_path) - 1024))
            if b"%%EOF" not in stream.read():
                raise ValueError("PDF renderer produced an incomplete document")
        os.replace(temp_path, path)
        return path
    finally:
        if os.path.isfile(temp_path):
            os.remove(temp_path)


def _submit(job, *, blocking=True):
    if not _SLOTS.acquire(blocking=blocking):
        return None
    try:
        future = _pool().submit(_render, job)
    except BaseException:
        _SLOTS.release()
        raise
    future.add_done_callback(lambda _: _SLOTS.release())
    return future


def _snapshot(papers, include_abstracts):
    result = []
    for paper in papers:
        row = paper.to_dict() if hasattr(paper, "to_dict") else dict(paper)
        # Relevance and citation HTML are not PDF inputs. Changes to real metadata
        # still invalidate a prepared batch, including a newly imported abstract.
        for key in ("_relevance", "relevance_score", "apa", "apa_html", "apa_plain"):
            row.pop(key, None)
        if not include_abstracts:
            row["abstract"] = ""
        result.append(row)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


class ReportBuilder:
    """Prebuild full batches during collection, then refresh changed metadata.

    At most two PDF jobs per task are in flight; all tasks share two processes
    and four queue slots. No unbounded executor queue or single enormous PDF.
    """
    def __init__(self, directory, query, stem, *, db_source="all", include_abstracts=False, is_other=False):
        self.directory = directory
        self.query = query
        self.stem = stem
        self.include_abstracts = include_abstracts
        self.options = {"db_source": db_source, "include_abstracts": include_abstracts, "is_guest": False, "is_other": is_other}
        self.batch_size = bounded_env_int("REPORT_BATCH_SIZE", 100 if include_abstracts else 250, 25, 250)
        self.index_size = bounded_env_int("REPORT_INDEX_BATCH_SIZE", 250, 25, 250)
        self.workdir = tempfile.mkdtemp(prefix=".report_", dir=directory)
        self.prepared = []
        self.covered = set()
        self.futures = []

    def _job(self, kind, papers, group, number):
        suffix = "PeerReviewed" if group == "published" else "Preprints"
        name = f"{number:04d}_{self.stem}_{suffix}.pdf" if kind == "report" else f"INDEX_{suffix}_{self.stem}_Part_{number:04d}.pdf"
        options = dict(self.options, doc_type="Peer-Reviewed" if group == "published" else "Preprint")
        return {"kind": kind, "query": self.query, "papers": papers, "path": os.path.join(self.workdir, name), "label": f"({suffix}) - Part {number}", "options": options}

    def prepare(self, papers):
        """Nonblocking: retrieval never waits for an available PDF worker."""
        if sum(not part["future"].done() for part in self.prepared) >= 2:
            return
        offered = 0
        for group, is_preprint in (("published", False), ("preprints", True)):
            waiting = [p for p in papers if id(p) not in self.covered and bool(p.is_preprint) == is_preprint]
            while len(waiting) >= self.batch_size:
                members, waiting = waiting[:self.batch_size], waiting[self.batch_size:]
                rows, digest = _snapshot(members, self.include_abstracts)
                number = 1 + sum(part["group"] == group for part in self.prepared)
                job = self._job("report", rows, group, number)
                future = _submit(job, blocking=False)
                if future is None:
                    return
                self.futures.append(future)
                ids = [id(p) for p in members]
                self.prepared.append({"ids": ids, "digest": digest, "future": future, "job": {k: v for k, v in job.items() if k != "papers"}, "group": group})
                self.covered.update(ids)
                offered += 1
                if offered >= 2 or sum(not part["future"].done() for part in self.prepared) >= 2:
                    return

    def finish(self, papers, progress=None):
        selected = {id(p): p for p in papers}
        pending_jobs = []
        ready = []
        manifest = []
        covered = set()

        def add_manifest(job, count, reused=False):
            manifest.append({"filename": os.path.basename(job["path"]), "kind": job["kind"], "records": count, "group": job["options"]["doc_type"], "prepared_during_search": reused})

        for part in self.prepared:
            # Wait before reusing its path. A late provider may have enriched or
            # reclassified records since this batch was initially prepared.
            part["future"].result()
            members = [selected[key] for key in part["ids"] if key in selected and bool(selected[key].is_preprint) == (part["group"] == "preprints")]
            if not members:
                continue
            rows, digest = _snapshot(members, self.include_abstracts)
            job = dict(part["job"], papers=members)
            covered.update(id(p) for p in members)
            if digest == part["digest"]:
                ready.append(job["path"])
            else:
                pending_jobs.append(job)
            add_manifest(job, len(rows), digest == part["digest"])

        for group, is_preprint in (("published", False), ("preprints", True)):
            members = [p for p in papers if bool(p.is_preprint) == is_preprint]
            remaining = [p for p in members if id(p) not in covered]
            number = 1 + sum(part["group"] == group for part in self.prepared)
            for start in range(0, len(remaining), self.batch_size):
                batch = remaining[start:start + self.batch_size]
                job = self._job("report", batch, group, number)
                pending_jobs.append(job)
                add_manifest(job, len(batch))
                number += 1
            for number, start in enumerate(range(0, len(members), self.index_size), 1):
                batch = members[start:start + self.index_size]
                job = self._job("index", batch, group, number)
                pending_jobs.append(job)
                add_manifest(job, len(batch))

        # Bound payloads submitted to the process pool, not just worker count.
        total = len(ready) + len(pending_jobs)
        jobs = iter(pending_jobs)
        active = set()
        while True:
            while len(active) < 2:
                job = next(jobs, None)
                if job is None:
                    break
                rows, _ = _snapshot(job["papers"], self.include_abstracts and job["kind"] == "report")
                future = _submit(dict(job, papers=rows))
                self.futures.append(future)
                active.add(future)
            if progress:
                progress(len(ready), total)
            if not active:
                break
            completed, active = wait(active, return_when=FIRST_COMPLETED)
            # Never publish a successful package that silently omits a failed PDF.
            for future in completed:
                ready.append(future.result())

        paths = []
        for path in ready:
            destination = os.path.join(self.directory, os.path.basename(path))
            os.replace(path, destination)
            paths.append(destination)
        manifest.sort(key=lambda part: (part["kind"], part["filename"]))
        manifest_path = os.path.join(self.directory, f"MANIFEST_{self.stem}.json")
        with open(manifest_path, "w", encoding="utf-8") as stream:
            json.dump({"query": self.query, "total_records": len(papers), "parts": manifest}, stream, ensure_ascii=False, indent=2)
        paths.append(manifest_path)
        csv_path = os.path.join(self.directory, f"INDEX_COMPLETE_{self.stem}.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Record", "Title", "Authors", "Year", "Journal", "DOI", "Sources", "Abstract"])
            for idx, paper in enumerate(papers, 1):
                # Prevent formula execution when bibliographic text is opened in Excel.
                row = [str(idx), paper.title, "; ".join(paper.authors), paper.year, paper.journal, paper.doi or "", "; ".join(paper.sources), paper.abstract if self.include_abstracts and paper.has_substantive_abstract else ""]
                writer.writerow(["'" + str(value) if str(value).lstrip().startswith(("=", "+", "-", "@")) else str(value) for value in row])
        paths.append(csv_path)
        guide = os.path.join(self.directory, f"START_HERE_{self.stem}.html")
        links = "\n".join(f'<li><a href="{html.escape(part["filename"], quote=True)}">{html.escape(part["filename"])}</a> ({part["records"]})</li>' for part in manifest)
        with open(guide, "w", encoding="utf-8") as stream:
            stream.write('<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Knowledge Ocean - Report index</title><style>body{font:18px/1.8 sans-serif;max-width:1000px;margin:40px auto;padding:20px}li{direction:ltr;text-align:left;overflow-wrap:anywhere}</style><h1>دليل ملفات البحث / Report file guide</h1><p>فك ضغط الحزمة أولًا. قُسّمت التقارير والفهارس الكبيرة إلى أجزاء لتسهيل فتحها. تحتوي الأجزاء مجتمعة على جميع السجلات، دون حذف النتائج.</p><p dir="ltr">Extract the archive first. Large reports and indexes are divided into manageable PDF parts. Together, the parts contain all retrieved records. The complete CSV index includes every record.</p><p>' + html.escape(self.query) + f' - {len(papers)} records</p><p><a href="{html.escape(os.path.basename(csv_path), quote=True)}">الفهرس الكامل / Complete CSV index</a></p><ul>' + links + '</ul></html>')
        paths.append(guide)
        return paths, manifest

    def close(self):
        # A worker must not be writing into a directory while it is deleted.
        for future in self.futures:
            try:
                future.result()
            except Exception:
                pass
        shutil.rmtree(self.workdir, ignore_errors=True)
