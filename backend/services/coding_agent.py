"""services/coding_agent.py — Coding Workspace AI.

Paste code → FRIDAY reviews it, explains bugs, generates docs / unit tests,
suggests refactors. Groq (free tier), stateless, max ~12k chars of code.

All prompts enforce honesty: if the code can't be understood, say so rather
than inventing issues.
"""

import os

MAX_CODE_CHARS = 12000


class CodingUnavailableError(RuntimeError):
    """Raised when the LLM is unavailable."""


def _llm(system: str, code: str, extra: str = "") -> str:
    from services.brain import _get_groq_client

    client = _get_groq_client()
    if client is None:
        raise CodingUnavailableError("GROQ_API_KEY is not configured — can't run the coding agent.")
    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"CODE:\n```\n{code[:MAX_CODE_CHARS]}\n```\n{extra}"},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return (getattr(completion.choices[0].message, "content", "") or "").strip()
    except Exception as exc:
        raise CodingUnavailableError(f"LLM call failed: {exc}") from exc


def review_code(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to review.")
    lang = f" ({language})" if language else ""
    return _llm(
        "You are F.R.I.D.A.Y.'s senior code reviewer. Review the code for bugs, "
        "security issues, performance problems, and style. Give a short verdict "
        "line, then numbered issues with severity (🔴 critical / 🟡 warning / ⚪ nit). "
        "If the code is fine, say so. Be honest — never invent issues.",
        code, f"Language:{lang}",
    )


def explain_code(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to explain.")
    return _llm(
        "You are F.R.I.D.A.Y.'s code explainer. Explain what this code does "
        "step by step in plain language, then note any tricky parts. Keep it "
        "clear and skimmable for a developer.",
        code, f"Language:{language}",
    )


def find_bugs(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to analyze.")
    return _llm(
        "You are F.R.I.D.A.Y.'s bug hunter. Find actual bugs and edge cases in "
        "this code. For each: what breaks, when, and the fix. If you find none, "
        "say 'No obvious bugs found.' Never hallucinate bugs.",
        code, f"Language:{language}",
    )


def generate_tests(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to test.")
    return _llm(
        "You are F.R.I.D.A.Y.'s test engineer. Write unit tests for this code. "
        "Use the language's idiomatic framework (pytest/Jest/JUnit/etc). Cover "
        "happy path, edge cases, and failure modes. Output only the test code "
        "in a fenced block.",
        code, f"Language:{language}",
    )


def generate_docs(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to document.")
    return _llm(
        "You are F.R.I.D.A.Y.'s technical writer. Write documentation for this "
        "code: what it does, key functions/classes, inputs/outputs, usage "
        "example, and gotchas. Concise markdown.",
        code, f"Language:{language}",
    )


def suggest_refactor(code: str, language: str = "") -> str:
    if not code.strip():
        raise CodingUnavailableError("No code to refactor.")
    return _llm(
        "You are F.R.I.D.A.Y.'s refactoring expert. Suggest concrete refactors: "
        "naming, structure, duplication, SOLID, readability. Show before/after "
        "for the top 2 changes. Be pragmatic — small wins first.",
        code, f"Language:{language}",
    )
