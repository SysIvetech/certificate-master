"""ChromaDB 데이터 조회용 단일 페이지 엔드포인트."""

from __future__ import annotations

import html
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.vector_store import VectorStoreService


class DeleteBatchRequest(BaseModel):
    """배치 삭제 요청 스키마."""

    ids: list[str]


router = APIRouter()


def get_vector_store_service() -> VectorStoreService:
    """VectorStoreService 의존성 생성자."""
    return VectorStoreService()


@router.delete("/chroma/{vector_id}")
async def delete_single_vector(
    vector_id: str,
    service: VectorStoreService = Depends(get_vector_store_service),
):
    """단일 벡터를 삭제하고 DB 보강 데이터를 리셋합니다.

    ChromaDB에서 벡터 삭제 + MariaDB에서 보강 데이터 초기화.
    유지 필드: id, series, title, raw_id, categories
    리셋 필드: overview, difficulty, study_period_days 등
    """
    service.delete_certificate_with_reset(vector_id)
    return {"success": True, "deleted_id": vector_id}


@router.post("/chroma/delete")
async def delete_batch_vectors(
    request: DeleteBatchRequest,
    service: VectorStoreService = Depends(get_vector_store_service),
):
    """여러 벡터를 배치로 삭제하고 DB 보강 데이터를 리셋합니다.

    ChromaDB에서 벡터 삭제 + MariaDB에서 보강 데이터 초기화.
    유지 필드: id, series, title, raw_id, categories
    리셋 필드: overview, difficulty, study_period_days 등
    """
    reset_result = service.delete_certificates_batch_with_reset(request.ids)
    return {
        "success": True,
        "deleted_count": len(request.ids),
        "reset_result": reset_result,
    }


def _render_metadata(metadata: dict) -> str:
    """메타데이터를 읽기 좋은 JSON 문자열로 렌더링합니다."""
    return html.escape(json.dumps(metadata or {}, ensure_ascii=False, indent=2))


def _render_embedding_preview(values: Optional[list]) -> str:
    """임베딩 프리뷰 문자열을 생성합니다."""
    if not values:
        return ""

    preview_values = [str(v) for v in values[:12]]
    preview = ", ".join(preview_values)
    suffix = " ..." if len(values) > 12 else ""
    return f"<p><strong>Embedding preview</strong>: {html.escape(preview + suffix)}</p>"


def _render_vectors_table(
    vectors: list[dict], limit: int, offset: int, search: str, selected_id: str = ""
) -> str:
    """벡터 리스트 테이블 HTML을 생성합니다."""
    if not vectors:
        return "<tr><td colspan='4'>No vectors found</td></tr>"

    search_param = f"&q={html.escape(search)}" if search else ""
    rows = []
    for vector in vectors:
        vector_id = html.escape(str(vector.get("id", "")))
        metadata = vector.get("metadata", {}) or {}
        title = html.escape(str(metadata.get("title", "")))
        category = html.escape(str(metadata.get("category", "")))
        row_url = f"/chroma?id={vector_id}&limit={limit}&offset={offset}{search_param}"
        is_selected = "selected" if vector_id == selected_id else ""
        rows.append(
            f'<tr class="clickable-row {is_selected}" data-id="{vector_id}">'
            f'<td class="checkbox-col" onclick="event.stopPropagation()">'
            f'<input type="checkbox" class="row-checkbox" value="{vector_id}" onchange="updateBulkActions()" />'
            f"</td>"
            f"<td onclick=\"window.location.href='{row_url}'\"><code>{vector_id}</code></td>"
            f"<td onclick=\"window.location.href='{row_url}'\">{title}</td>"
            f"<td onclick=\"window.location.href='{row_url}'\">{category}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_detail_section(detail: Optional[dict]) -> str:
    """상세 정보를 위한 HTML 섹션을 생성합니다."""
    if not detail:
        return "<p>선택된 벡터가 없습니다.</p>"

    metadata = detail.get("metadata") or {}
    metadata_html = _render_metadata(metadata)
    values = detail.get("values") or []

    # 주요 정보 추출
    vector_id = html.escape(str(detail.get("id", "")))
    title = html.escape(str(metadata.get("title", "N/A")))
    category = html.escape(str(metadata.get("category", "N/A")))
    difficulty = metadata.get("difficulty", "N/A")
    study_days = metadata.get("study_period_days", "N/A")

    return f"""
        <p><strong>ID</strong>: <code>{vector_id}</code></p>
        <p><strong>Title</strong>: {title}</p>
        <p><strong>Category</strong>: {category}</p>
        <p><strong>Difficulty</strong>: {difficulty}/5</p>
        <p><strong>Study Period</strong>: {study_days}일</p>
        <p><strong>Vector size</strong>: {len(values) if values else 0}</p>
        {_render_embedding_preview(values)}
        <div class="delete-section">
            <button class="delete-btn" onclick="deleteVector('{vector_id}')">🗑️ 삭제</button>
        </div>
        <details open>
            <summary><strong>Full Metadata (JSON)</strong></summary>
            <pre>{metadata_html}</pre>
        </details>
    """


def _render_pagination(total: int, limit: int, offset: int, search: str) -> str:
    """페이지네이션 컨트롤을 렌더링합니다."""
    current_page = (offset // limit) + 1
    total_pages = max(1, (total + limit - 1) // limit)

    prev_offset = max(0, offset - limit)
    next_offset = offset + limit

    search_param = f"&q={html.escape(search)}" if search else ""

    prev_disabled = "disabled" if offset == 0 else ""
    next_disabled = "disabled" if next_offset >= total else ""

    # 페이지 번호 버튼 생성 (최대 5개)
    page_buttons = []
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, start_page + 4)
    start_page = max(1, end_page - 4)

    for page in range(start_page, end_page + 1):
        page_offset = (page - 1) * limit
        active = "active" if page == current_page else ""
        page_buttons.append(
            f'<a href="/chroma?limit={limit}&offset={page_offset}{search_param}" class="page-btn {active}">{page}</a>'
        )

    return f"""
        <div class="pagination">
            <a href="/chroma?limit={limit}&offset={prev_offset}{search_param}" class="page-btn {prev_disabled}">← Prev</a>
            {''.join(page_buttons)}
            <a href="/chroma?limit={limit}&offset={next_offset}{search_param}" class="page-btn {next_disabled}">Next →</a>
            <span class="page-info">Page {current_page} of {total_pages} ({total} total)</span>
        </div>
    """


@router.get("/chroma", response_class=HTMLResponse)
async def chroma_dashboard(
    id: str | None = Query(default=None, description="Vector ID to inspect"),
    q: str | None = Query(default=None, description="Search query (title)"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    """ChromaDB 컬렉션을 조회할 수 있는 단일 페이지 (페이지네이션 + 검색)."""
    stats = service.get_collection_stats()
    total_vectors = stats.get("total_vectors", 0)

    # 검색어 유무에 따라 다른 처리
    search_query = q.strip() if q else ""

    if search_query:
        # ChromaDB where 필터는 $contains 미지원
        # 전체 벡터를 가져온 후 Python에서 타이틀 필터링
        all_vectors = service.list_vectors(
            limit=10000, offset=0, include_embeddings=False, where=None
        )
        # 타이틀에 검색어가 포함된 벡터만 필터링
        vectors = [
            v
            for v in all_vectors
            if search_query.lower()
            in (v.get("metadata", {}).get("title", "") or "").lower()
        ]
        # 페이지네이션 적용
        vectors = vectors[offset : offset + limit]
        display_total = len(
            [
                v
                for v in all_vectors
                if search_query.lower()
                in (v.get("metadata", {}).get("title", "") or "").lower()
            ]
        )
    else:
        # 일반 목록 조회
        vectors = service.list_vectors(
            limit=limit, offset=offset, include_embeddings=False, where=None
        )
        display_total = total_vectors

    detail = None
    if id:
        detail = service.get_by_id(id)
    if not detail and vectors:
        detail = service.get_by_id(vectors[0]["id"])

    search_value = html.escape(q) if q else ""

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <title>ChromaDB Inspector</title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                font-family: "Segoe UI", -apple-system, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                margin: 0;
                padding: 20px;
                line-height: 1.5;
            }}
            h1 {{
                margin: 0 0 16px 0;
                font-size: 1.75rem;
            }}
            h3 {{
                margin: 0 0 12px 0;
                font-size: 1.1rem;
                color: #94a3b8;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                margin-bottom: 20px;
            }}
            .card {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.35);
            }}
            .card > div:first-child {{
                font-size: 0.85rem;
                color: #94a3b8;
                margin-bottom: 4px;
            }}
            .card strong {{
                font-size: 1.1rem;
                color: #f1f5f9;
            }}

            /* Search */
            .search-box {{
                margin-bottom: 16px;
            }}
            .search-form {{
                display: flex;
                gap: 8px;
                align-items: center;
            }}
            .search-input {{
                flex: 1;
                max-width: 400px;
                padding: 10px 14px;
                border: 1px solid #334155;
                border-radius: 6px;
                background: #0f172a;
                color: #e2e8f0;
                font-size: 0.95rem;
            }}
            .search-input:focus {{
                outline: none;
                border-color: #38bdf8;
            }}
            .search-input::placeholder {{
                color: #64748b;
            }}
            .search-btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                background: #3b82f6;
                color: white;
                font-size: 0.95rem;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .search-btn:hover {{
                background: #2563eb;
            }}
            .clear-btn {{
                padding: 10px 16px;
                border: 1px solid #475569;
                border-radius: 6px;
                background: transparent;
                color: #94a3b8;
                font-size: 0.95rem;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.2s;
            }}
            .clear-btn:hover {{
                background: #334155;
                color: #e2e8f0;
            }}

            /* Table */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
            }}
            th, td {{
                padding: 10px 12px;
                border-bottom: 1px solid #334155;
                text-align: left;
            }}
            th {{
                color: #94a3b8;
                font-weight: 600;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            tr:hover td {{
                background: #0b1224;
            }}
            tr.clickable-row {{
                cursor: pointer;
            }}
            tr.clickable-row:hover td {{
                background: #1e3a5f;
            }}
            code {{
                background: #0b1224;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.85rem;
                color: #94a3b8;
            }}
            a {{
                color: #38bdf8;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}

            /* Pagination */
            .pagination {{
                display: flex;
                align-items: center;
                gap: 6px;
                margin-top: 16px;
                flex-wrap: wrap;
            }}
            .page-btn {{
                padding: 8px 14px;
                border: 1px solid #334155;
                border-radius: 6px;
                background: #1e293b;
                color: #94a3b8;
                text-decoration: none;
                font-size: 0.9rem;
                transition: all 0.2s;
            }}
            .page-btn:hover:not(.disabled):not(.active) {{
                background: #334155;
                color: #e2e8f0;
                text-decoration: none;
            }}
            .page-btn.active {{
                background: #3b82f6;
                border-color: #3b82f6;
                color: white;
            }}
            .page-btn.disabled {{
                opacity: 0.4;
                pointer-events: none;
            }}
            .page-info {{
                margin-left: 12px;
                color: #64748b;
                font-size: 0.85rem;
            }}

            /* Detail */
            pre {{
                background: #0b1224;
                border-radius: 8px;
                padding: 12px;
                white-space: pre-wrap;
                word-break: break-all;
                border: 1px solid #334155;
                font-size: 0.85rem;
                max-height: 400px;
                overflow-y: auto;
            }}
            details {{
                margin-top: 12px;
            }}
            summary {{
                cursor: pointer;
                padding: 8px 0;
                color: #94a3b8;
            }}
            summary:hover {{
                color: #e2e8f0;
            }}

            /* Delete */
            .delete-section {{
                margin: 16px 0;
                padding-top: 12px;
                border-top: 1px solid #334155;
            }}
            .delete-btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                background: #dc2626;
                color: white;
                font-size: 0.95rem;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .delete-btn:hover {{
                background: #b91c1c;
            }}
            .delete-btn:disabled {{
                background: #6b7280;
                cursor: not-allowed;
            }}

            /* Checkbox */
            .checkbox-col {{
                width: 40px;
                text-align: center;
            }}
            .row-checkbox {{
                width: 18px;
                height: 18px;
                cursor: pointer;
            }}
            .bulk-actions {{
                margin-bottom: 12px;
                padding: 12px;
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                display: none;
                align-items: center;
                gap: 12px;
            }}
            .bulk-actions.visible {{
                display: flex;
            }}
            .bulk-delete-btn {{
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                background: #dc2626;
                color: white;
                font-size: 0.9rem;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .bulk-delete-btn:hover {{
                background: #b91c1c;
            }}
            .selected-count {{
                color: #94a3b8;
                font-size: 0.9rem;
            }}
            tr.selected td {{
                background: #1e3a5f;
            }}

            /* Layout */
            .layout {{
                display: grid;
                grid-template-columns: 3fr 2fr;
                gap: 16px;
            }}
            @media (max-width: 1024px) {{
                .layout {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>🔍 ChromaDB Inspector</h1>

        <!-- Stats -->
        <div class="stats">
            <div class="card">
                <div>Host</div>
                <strong>{html.escape(str(stats.get("host", "")))}</strong>
            </div>
            <div class="card">
                <div>Port</div>
                <strong>{html.escape(str(stats.get("port", "")))}</strong>
            </div>
            <div class="card">
                <div>Collection</div>
                <strong>{html.escape(str(stats.get("collection_name", "")))}</strong>
            </div>
            <div class="card">
                <div>Total Vectors</div>
                <strong>{total_vectors:,}</strong>
            </div>
        </div>

        <!-- Search -->
        <div class="search-box">
            <form class="search-form" method="get" action="/chroma">
                <input type="text" name="q" class="search-input"
                       placeholder="Search by title..."
                       value="{search_value}"
                       autocomplete="off" />
                <input type="hidden" name="limit" value="{limit}" />
                <button type="submit" class="search-btn">Search</button>
                {f'<a href="/chroma?limit={limit}" class="clear-btn">Clear</a>' if q else ''}
            </form>
        </div>

        <div class="layout">
            <!-- Vector List -->
            <div class="card">
                <h3>Vectors {f'(filtered: "{html.escape(q)}")' if q else ''}</h3>

                <!-- Bulk Actions -->
                <div class="bulk-actions" id="bulk-actions">
                    <span class="selected-count"><span id="selected-count">0</span>개 선택됨</span>
                    <button class="bulk-delete-btn" onclick="deleteSelected()">🗑️ 선택 삭제</button>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th class="checkbox-col">
                                <input type="checkbox" id="select-all" onchange="toggleSelectAll()" />
                            </th>
                            <th>ID</th>
                            <th>Title</th>
                            <th>Category</th>
                        </tr>
                    </thead>
                    <tbody>
                        {_render_vectors_table(vectors, limit, offset, q or "", id or "")}
                    </tbody>
                </table>
                {_render_pagination(display_total, limit, offset, q or "")}
            </div>

            <!-- Detail -->
            <div class="card">
                <h3>Detail</h3>
                {_render_detail_section(detail)}
            </div>
        </div>

        <script>
            // 단일 벡터 삭제
            async function deleteVector(vectorId) {{
                if (!confirm(`벡터 "${{vectorId}}"를 삭제하시겠습니까?`)) {{
                    return;
                }}

                try {{
                    const response = await fetch(`/chroma/${{vectorId}}`, {{
                        method: 'DELETE'
                    }});

                    if (response.ok) {{
                        alert('삭제되었습니다.');
                        window.location.href = '/chroma?limit={limit}&offset={offset}' + ('{q or ""}' ? '&q={q or ""}' : '');
                    }} else {{
                        const error = await response.json();
                        alert('삭제 실패: ' + (error.detail || '알 수 없는 오류'));
                    }}
                }} catch (e) {{
                    alert('삭제 중 오류 발생: ' + e.message);
                }}
            }}

            // 선택된 항목 업데이트
            function updateBulkActions() {{
                const checkboxes = document.querySelectorAll('.row-checkbox:checked');
                const count = checkboxes.length;
                document.getElementById('selected-count').textContent = count;

                const bulkActions = document.getElementById('bulk-actions');
                if (count > 0) {{
                    bulkActions.classList.add('visible');
                }} else {{
                    bulkActions.classList.remove('visible');
                }}

                // 전체 선택 체크박스 상태 업데이트
                const allCheckboxes = document.querySelectorAll('.row-checkbox');
                const selectAll = document.getElementById('select-all');
                selectAll.checked = allCheckboxes.length > 0 && allCheckboxes.length === count;
                selectAll.indeterminate = count > 0 && count < allCheckboxes.length;
            }}

            // 전체 선택/해제
            function toggleSelectAll() {{
                const selectAll = document.getElementById('select-all');
                const checkboxes = document.querySelectorAll('.row-checkbox');
                checkboxes.forEach(cb => cb.checked = selectAll.checked);
                updateBulkActions();
            }}

            // 선택된 벡터 일괄 삭제
            async function deleteSelected() {{
                const checkboxes = document.querySelectorAll('.row-checkbox:checked');
                const ids = Array.from(checkboxes).map(cb => cb.value);

                if (ids.length === 0) {{
                    alert('삭제할 항목을 선택하세요.');
                    return;
                }}

                if (!confirm(`${{ids.length}}개의 벡터를 삭제하시겠습니까?`)) {{
                    return;
                }}

                try {{
                    const response = await fetch('/chroma/delete', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ ids: ids }})
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        alert(`${{result.deleted_count}}개 삭제되었습니다.`);
                        window.location.reload();
                    }} else {{
                        const error = await response.json();
                        alert('삭제 실패: ' + (error.detail || '알 수 없는 오류'));
                    }}
                }} catch (e) {{
                    alert('삭제 중 오류 발생: ' + e.message);
                }}
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_body)
