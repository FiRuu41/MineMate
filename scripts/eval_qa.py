"""Eval qa_set.jsonl against the full workflow.

Usage:
    uv run python -m scripts.eval_qa [--limit N] [--output result.json]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure project root importable when invoked as module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.workflow import McmodWorkflow  # noqa: E402
from agents.router import RouterAgent  # noqa: E402
from agents.answerer import AnswererAgent  # noqa: E402
from agents.critic import CriticAgent  # noqa: E402
from kb.retriever import HybridRetriever  # noqa: E402


QA_PATH = Path(__file__).resolve().parent.parent / "tests" / "eval" / "qa_set.jsonl"


def _load_qa(limit: int | None = None) -> list[dict]:
    items = []
    with QA_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items[:limit] if limit else items


def _keyword_hit_rate(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    hits = sum(1 for k in keywords if k in text)
    return hits / len(keywords)


def _judge(result: dict, expected: dict) -> dict:
    """Verdict per qa item."""
    intent_match = result["intent"] == expected["expected_intent"]
    hit_rate = _keyword_hit_rate(result["answer"], expected["expected_keywords"])
    passed = intent_match and hit_rate >= 0.7
    return {
        "query": expected["query"],
        "expected_intent": expected["expected_intent"],
        "actual_intent": result["intent"],
        "intent_match": intent_match,
        "expected_keywords": expected["expected_keywords"],
        "hit_rate": hit_rate,
        "answer_preview": result["answer"][:200],
        "passed": passed,
    }


async def main_async(limit: int | None, output: Path | None) -> int:
    qa = _load_qa(limit)
    print("Loading workflow components ...")
    workflow = McmodWorkflow(
        router=RouterAgent(),
        retriever=HybridRetriever(),
        answerer=AnswererAgent(),
        critic=CriticAgent(),
    )

    results = []
    t0 = time.time()
    for i, item in enumerate(qa, 1):
        t1 = time.time()
        try:
            r = await workflow.run(query=item["query"])
        except Exception as e:
            r = {"intent": "error", "answer": f"ERROR: {e}", "chunks": [], "tool_results": {}}
        verdict = _judge(r, item)
        results.append(verdict)
        status = "PASS" if verdict["passed"] else "FAIL"
        print(f"[{i:2d}/{len(qa)}] {status} ({time.time()-t1:.1f}s) "
              f"[{verdict['expected_intent']:<18} / {verdict['actual_intent']:<18}] "
              f"hit={verdict['hit_rate']*100:.0f}%  {item['query'][:40]}")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    intent_correct = sum(1 for r in results if r["intent_match"])
    avg_hit = sum(r["hit_rate"] for r in results) / total if total else 0
    elapsed = time.time() - t0

    print()
    print("=" * 70)
    print(f"Overall: {passed}/{total} passed ({passed/total*100:.0f}%) in {elapsed:.0f}s")
    print(f"  Intent accuracy:  {intent_correct}/{total} ({intent_correct/total*100:.0f}%)")
    print(f"  Avg keyword hit:  {avg_hit*100:.0f}%")
    print("=" * 70)

    fails = [r for r in results if not r["passed"]]
    if fails:
        print()
        print(f"Failed cases ({len(fails)}):")
        for r in fails:
            print(f"  - {r['query'][:50]}  [{r['actual_intent']} vs {r['expected_intent']}, hit={r['hit_rate']*100:.0f}%]")

    if output:
        output.write_text(
            json.dumps({
                "total": total, "passed": passed,
                "intent_correct": intent_correct,
                "avg_hit_rate": avg_hit,
                "elapsed_seconds": elapsed,
                "results": results,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nDetailed report: {output}")

    return 0 if passed == total else 1


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    code = asyncio.run(main_async(args.limit, args.output))
    sys.exit(code)


if __name__ == "__main__":
    main()
