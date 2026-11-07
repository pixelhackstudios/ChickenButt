"""Keep a conversation inside the context window Ollama allocated.

Pure planning: no GTK, no HTTP. The visible transcript never changes — only
the history sent to Ollama shrinks. Two steps, applied only when the history
would not fit:

1. Drop ``thinking`` from every assistant message except the newest.
2. Replace the oldest messages with a rolling summary, keeping the newest
   messages verbatim.

Ollama's own overflow handling drops whole earlier messages without notice
(measured on 0.40.15), so a summary keeps far more of the conversation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Ollama allocates 4096 when num_ctx is omitted on GPUs under 24 GiB; the
# smallest window it picks, so the safe assumption while it is unknown.
DEFAULT_WINDOW = 4096

# Conservative until calibrated from prompt_eval_count (English averages ~4).
DEFAULT_CHARS_PER_TOKEN = 3.0
MIN_CHARS_PER_TOKEN = 2.0
MAX_CHARS_PER_TOKEN = 5.0

# Chat-template tokens per message (role markers, separators).
MESSAGE_OVERHEAD_TOKENS = 8

# Use at most this share of the window for the prompt plus reply reserve.
WINDOW_FILL = 0.9
# After summarizing, verbatim recent messages fill at most this share of the
# prompt budget, leaving room for the summary and later turns.
KEEP_RECENT_SHARE = 0.5

SUMMARY_PREFIX = (
    "Summary of the earlier part of this conversation (older messages were "
    "condensed to fit the model's context window):\n\n"
)

SUMMARY_SYSTEM_PROMPT = (
    "You condense chat history so a conversation can continue within a small "
    "context window. Write a concise summary that preserves facts, names, "
    "numbers, decisions, code identifiers, user preferences, and open "
    "questions the user may refer back to. Use short plain sentences or "
    "bullet points. Output only the summary."
)


def is_api_message(m: Any) -> bool:
    """Same filter as ``MessageActionController.api_messages``."""
    if not isinstance(m, dict):
        return False
    if m.get("role") not in ("user", "assistant"):
        return False
    if m.get("content") is None and not (m.get("thinking") or ""):
        return False
    return True


def api_row(m: dict[str, Any], *, keep_thinking: bool = True) -> dict[str, Any]:
    """One Ollama chat row, built the way ``api_messages`` builds it."""
    row: dict[str, Any] = {
        "role": m["role"],
        "content": m.get("content") if m.get("content") is not None else "",
    }
    thinking = (m.get("thinking") or "").strip()
    if keep_thinking and m.get("role") == "assistant" and thinking:
        row["thinking"] = m.get("thinking") or ""
    return row


def estimate_tokens(text: str, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    if not text:
        return 0
    cpt = max(MIN_CHARS_PER_TOKEN, float(chars_per_token))
    return int(math.ceil(len(text) / cpt))


def row_tokens(row: dict[str, Any], chars_per_token: float) -> int:
    n = MESSAGE_OVERHEAD_TOKENS
    n += estimate_tokens(str(row.get("content") or ""), chars_per_token)
    n += estimate_tokens(str(row.get("thinking") or ""), chars_per_token)
    return n


def rows_tokens(rows: list[dict[str, Any]], chars_per_token: float) -> int:
    return sum(row_tokens(r, chars_per_token) for r in rows)


def reply_reserve(window: int, num_predict: int | None = None) -> int:
    """Tokens kept free for the model's reply."""
    half = max(1, window // 2)
    if isinstance(num_predict, int) and not isinstance(num_predict, bool) and num_predict > 0:
        return min(num_predict, half)
    return min(max(512, window // 4), half)


def prompt_budget(window: int, num_predict: int | None = None) -> int:
    return max(1, int(window * WINDOW_FILL) - reply_reserve(window, num_predict))


def summary_row(text: str) -> dict[str, Any]:
    return {"role": "system", "content": SUMMARY_PREFIX + text.strip()}


@dataclass(frozen=True)
class StoredSummary:
    """A rolling summary covering history up to and including one message."""

    through_message_id: str
    content: str


@dataclass(frozen=True)
class CompactionPlan:
    """What to send for one request.

    ``rows`` is the outbound history when no new summary is needed (or as
    the fallback if summarizing fails). When ``needs_summary`` is set, the
    caller summarizes ``to_summarize`` (with ``prior_summary``) and sends
    ``summary_row(new) + kept_rows``; the new summary covers messages
    through ``summary_through_id``.
    """

    rows: list[dict[str, Any]]
    compacted: bool = False
    stripped_thinking: bool = False
    used_summary: StoredSummary | None = None
    needs_summary: bool = False
    to_summarize: tuple[dict[str, Any], ...] = ()
    prior_summary: str = ""
    kept_rows: tuple[dict[str, Any], ...] = ()
    summary_through_id: str | None = None
    oversize: bool = False


def _strip_rows(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows with thinking dropped from all but the newest assistant message."""
    last_asst = -1
    for i, m in enumerate(msgs):
        if m.get("role") == "assistant":
            last_asst = i
    return [api_row(m, keep_thinking=(i == last_asst)) for i, m in enumerate(msgs)]


def plan_outbound(
    history: list[dict[str, Any]],
    *,
    window: int,
    summary: StoredSummary | None = None,
    num_predict: int | None = None,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    extra_tail_tokens: int = 0,
) -> CompactionPlan:
    """Fit *history* (id-bearing conversation messages) into *window*.

    ``extra_tail_tokens`` accounts for rows the caller appends after the
    history (Continue's instruction row).
    """
    msgs = [m for m in history if is_api_message(m)]
    full = [api_row(m) for m in msgs]
    budget = prompt_budget(window, num_predict) - max(0, extra_tail_tokens)
    cpt = chars_per_token

    if rows_tokens(full, cpt) <= budget:
        return CompactionPlan(rows=full)

    stripped = _strip_rows(msgs)
    if rows_tokens(stripped, cpt) <= budget:
        return CompactionPlan(rows=stripped, compacted=True, stripped_thinking=True)

    # Existing summary still valid only if its anchor message is still here.
    base = 0
    prior = ""
    used: StoredSummary | None = None
    if summary is not None and summary.content.strip():
        for i, m in enumerate(msgs):
            if m.get("id") == summary.through_message_id:
                base = i + 1
                prior = summary.content
                used = summary
                break

    if used is not None:
        with_summary = [summary_row(prior)] + stripped[base:]
        if rows_tokens(with_summary, cpt) <= budget:
            return CompactionPlan(
                rows=with_summary,
                compacted=True,
                stripped_thinking=True,
                used_summary=used,
            )

    # Newest messages always kept verbatim: the last one, plus the user turn
    # it answers when it is an assistant (Continue).
    n = len(msgs)
    if n == 0:
        return CompactionPlan(rows=full)
    min_keep = n - 1
    if msgs[-1].get("role") == "assistant" and n >= 2:
        min_keep = n - 2

    keep_budget = int(budget * KEEP_RECENT_SHARE)
    keep_from = min_keep
    total = rows_tokens(stripped[min_keep:], cpt)
    while keep_from - 1 >= base:
        cost = row_tokens(stripped[keep_from - 1], cpt)
        if total + cost > keep_budget:
            break
        total += cost
        keep_from -= 1

    oversize = rows_tokens(stripped[min_keep:], cpt) > budget
    fallback = ([summary_row(prior)] if used is not None else []) + stripped[base:]

    if keep_from <= base:
        # Nothing new to summarize; send what we have and let Ollama cope.
        return CompactionPlan(
            rows=fallback,
            compacted=True,
            stripped_thinking=True,
            used_summary=used,
            oversize=oversize,
        )

    return CompactionPlan(
        rows=fallback,
        compacted=True,
        stripped_thinking=True,
        used_summary=used,
        needs_summary=True,
        to_summarize=tuple(msgs[base:keep_from]),
        prior_summary=prior,
        kept_rows=tuple(stripped[keep_from:]),
        summary_through_id=str(msgs[keep_from - 1].get("id") or "") or None,
        oversize=oversize,
    )


def _speaker(role: str) -> str:
    return "User" if role == "user" else "Assistant"


def _clip(text: str, max_chars: int) -> str:
    """Keep head and tail of an over-long message for summarizing only."""
    if len(text) <= max_chars:
        return text
    if max_chars < 40:
        return text[:max_chars]
    half = (max_chars - 20) // 2
    return text[:half] + "\n[…]\n" + text[-half:]


def summary_reply_tokens(window: int) -> int:
    return max(256, min(1024, window // 4))


def summary_chunks(
    messages: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    window: int,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> list[list[str]]:
    """Split messages into transcript-line chunks that each fit one request.

    Each request also carries the system prompt and the summary so far
    (bounded by ``summary_reply_tokens``), so those are budgeted first.
    """
    cpt = max(MIN_CHARS_PER_TOKEN, float(chars_per_token))
    reply = summary_reply_tokens(window)
    fixed = (
        estimate_tokens(SUMMARY_SYSTEM_PROMPT, cpt)
        + reply  # prior summary is at most one reply long
        + 64  # instructions + template
    )
    room = max(64, int(window * WINDOW_FILL) - reply - fixed)
    max_chars = int(room * cpt)

    chunks: list[list[str]] = []
    cur: list[str] = []
    used = 0
    for m in messages:
        text = str(m.get("content") or "").strip()
        if not text:
            continue
        line = f"{_speaker(str(m.get('role')))}: {_clip(text, max_chars - 16)}"
        cost = estimate_tokens(line, cpt) + 2
        if cur and used + cost > room:
            chunks.append(cur)
            cur, used = [], 0
        cur.append(line)
        used += cost
    if cur:
        chunks.append(cur)
    return chunks


def summary_request(prior_summary: str, lines: list[str]) -> list[dict[str, Any]]:
    """Messages for one rolling summarization call."""
    parts: list[str] = []
    if prior_summary.strip():
        parts.append("Summary so far:\n" + prior_summary.strip())
    parts.append("New messages:\n" + "\n\n".join(lines))
    parts.append(
        "Write the updated summary of the whole conversation so far."
        if prior_summary.strip()
        else "Write a summary of these messages."
    )
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


class TokenCalibration:
    """Learn chars-per-token for one model from ``prompt_eval_count``.

    ``prompt_eval_count`` counts the whole prompt, cached prefix included
    (measured on 0.40.15). Samples taken when the prompt may have overflowed
    are skipped: Ollama then drops messages and the count shrinks.
    """

    def __init__(self) -> None:
        self._cpt: dict[str, float] = {}

    def chars_per_token(self, model: str) -> float:
        return self._cpt.get(model, DEFAULT_CHARS_PER_TOKEN)

    def observe(
        self,
        model: str,
        *,
        rows: list[dict[str, Any]],
        prompt_eval_count: Any,
        window: int,
    ) -> None:
        if isinstance(prompt_eval_count, bool) or not isinstance(
            prompt_eval_count, (int, float)
        ):
            return
        count = int(prompt_eval_count)
        if count < 64:
            return
        chars = sum(
            len(str(r.get("content") or "")) + len(str(r.get("thinking") or ""))
            for r in rows
        )
        overhead = MESSAGE_OVERHEAD_TOKENS * len(rows)
        text_tokens = count - overhead
        if chars <= 0 or text_tokens <= 0:
            return
        # Possibly truncated by Ollama: the pessimistic estimate overflowed.
        if rows_tokens(rows, MIN_CHARS_PER_TOKEN) >= window:
            return
        sample = chars / text_tokens
        sample = min(MAX_CHARS_PER_TOKEN, max(MIN_CHARS_PER_TOKEN, sample))
        # Lean conservative: under-estimating chars/token over-counts tokens.
        sample *= 0.9
        prev = self._cpt.get(model)
        self._cpt[model] = sample if prev is None else (prev * 0.6 + sample * 0.4)
