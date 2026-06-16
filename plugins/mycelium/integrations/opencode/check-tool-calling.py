#!/usr/bin/env python3
"""
check-tool-calling.py — does your local Ollama model emit STRUCTURED tool calls?

opencode (like Roo Code) requires native structured `tool_calls`; it has no
client-side text/XML fallback (unlike Cline). Many local models — notably stock
`qwen2.5-coder` (any size) — emit the tool-call JSON as plain TEXT instead of a
structured call, because their Ollama Modelfile TEMPLATE doesn't parse it. Such a
model silently does nothing in opencode: it "knows" to call the tool but the call
never executes.

This script asks a model to call a tool and reports whether Ollama returns a
structured `tool_calls` field (PASS = usable in opencode) or leaks it as text
(FAIL = unusable in opencode until you switch model or fix its template).

Usage:  python3 check-tool-calling.py [model]   (default: llama3.1:8b)
        OLLAMA_HOST=http://localhost:11434 python3 check-tool-calling.py qwen2.5-coder:14b

Verified 2026-06-16: llama3.1:8b → PASS (structured), stock qwen2.5-coder:14b → FAIL (text).
Known-broken family: qwen2.5-coder / qwen3 (template gap). Fixes: a working-template
model (llama3.1, Dolphin 3, Qwen3-Coder with the unsloth tool-calling-fix template,
or hhao/qwen2.5-coder-tools). Also bump context: Ollama defaults to 4K (num_ctx),
which overflows on agentic prompts — set OLLAMA_CONTEXT_LENGTH=32768 (or a Modelfile
PARAMETER num_ctx) so tool-calling survives Mycelium's larger system/tool prompts.
"""
import json, os, sys, urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
TOOLS = [{"type": "function", "function": {
    "name": "read_file", "description": "Read a file and return its contents",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]
MSG = [{"role": "user", "content": "Read the file sample.txt and tell me its first line. Use the read_file tool."}]

def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)

def main():
    print(f"Model: {MODEL}   Host: {HOST}")
    try:
        r = post(f"{HOST}/api/chat", {"model": MODEL, "messages": MSG, "tools": TOOLS, "stream": False})
    except Exception as e:
        print(f"ERROR contacting Ollama: {e}"); return 2
    m = r.get("message", {})
    tc = m.get("tool_calls")
    if tc:
        print("PASS — structured tool_calls emitted (usable in opencode):")
        print("  " + json.dumps(tc))
        return 0
    print("FAIL — no structured tool_calls; the call leaked into text content:")
    print("  " + repr((m.get("content") or "")[:200]))
    print("\nThis model is NOT usable for opencode tool-calling as-is. Switch to a")
    print("working-template model (e.g. llama3.1:8b) or fix the model's tool template.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
