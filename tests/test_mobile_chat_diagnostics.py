"""Static safety checks for the native mobile-chat Edge Function diagnostics."""
from pathlib import Path


SOURCE = Path("supabase/functions/mobile-chat/index.ts").read_text(encoding="utf-8")


def test_mobile_chat_validates_json_container_before_reading_fields():
    container_guard = SOURCE.index(
        'if (typeof payload !== "object" || payload === null || Array.isArray(payload))'
    )
    field_access = SOURCE.index("const message = typeof input.message")
    assert container_guard < field_access
    assert 'return fail(400, "INVALID_INPUT")' in SOURCE[container_guard:field_access]


def test_mobile_chat_has_stage_aware_catch_and_request_correlation():
    assert 'const requestId = crypto.randomUUID()' in SOURCE
    assert 'headers: {\n      ...corsHeaders,' in SOURCE
    assert '"X-Request-Id": requestId' in SOURCE
    assert 'event: "mobile_chat_unhandled_error"' in SOURCE
    assert 'stage,' in SOURCE
    assert 'request_id: requestId' in SOURCE
    assert 'return json(mapped.status' in SOURCE


def test_mobile_chat_logs_do_not_include_private_exception_or_chat_content():
    assert "error.message" not in SOURCE
    assert "error.stack" not in SOURCE
    assert 'message: message' not in SOURCE[SOURCE.index("console.warn"):SOURCE.index("return json(status")]
    assert 'content: answer' not in SOURCE[SOURCE.index("console.warn"):SOURCE.index("return json(status")]


def test_mobile_chat_defensively_validates_history_and_memory_rows():
    assert 'typeof row === "object" && row !== null && !Array.isArray(row)' in SOURCE
    assert 'typeof item !== "object" || item === null || Array.isArray(item)' in SOURCE
