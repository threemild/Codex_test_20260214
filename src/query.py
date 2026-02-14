import argparse
import sqlite3
from typing import Any


def retrieve(db_path: str, question: str, region: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        base = """
        SELECT c.id, c.content, c.page_start, c.page_end, c.section_hint,
               r.title, r.region, r.authority
        FROM chunks_fts f
        JOIN chunks c ON c.id = f.chunk_id
        JOIN regulations r ON r.id = c.regulation_id
        WHERE f.content MATCH ?
        """
        params: list[Any] = [question]
        if region:
            base += " AND r.region = ?"
            params.append(region)
        base += " LIMIT ?"
        params.append(limit)

        rows = conn.execute(base, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def synthesize_answer(question: str, contexts: list[dict[str, Any]]) -> str:
    try:
        import os
        from openai import OpenAI
    except ImportError:
        return "openai 패키지가 없어 원문 근거만 반환합니다."

    if not contexts:
        return "관련 법규 근거를 찾지 못했습니다."

    if not os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY가 없어 원문 근거만 반환합니다."

    client = OpenAI()
    evidence = "\n\n".join(
        [
            f"[근거{i+1}] {c['title']} ({c['region']}) p.{c['page_start']}-{c['page_end']}\n{c['content'][:1200]}"
            for i, c in enumerate(contexts)
        ]
    )

    system = (
        "당신은 차량 법규 분석 보조 에이전트입니다. "
        "반드시 제공된 근거 텍스트 안에서만 답변하고, 모르면 모른다고 말하세요."
    )
    user = f"질문: {question}\n\n근거:\n{evidence}\n\n요구사항:\n1) 적용 가능성\n2) 핵심 조항 요약\n3) 확인이 필요한 리스크"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.1,
    )
    return resp.choices[0].message.content or "응답 없음"


def main():
    parser = argparse.ArgumentParser(description="Regulation QA query utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ask = sub.add_parser("ask", help="Ask a regulation question")
    p_ask.add_argument("--db", required=True)
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--region")
    p_ask.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    if args.cmd == "ask":
        contexts = retrieve(args.db, args.question, args.region, args.limit)
        print("=== 검색 근거 ===")
        for i, c in enumerate(contexts, start=1):
            print(f"[{i}] {c['title']} ({c['region']}) p.{c['page_start']}-{c['page_end']} {c['section_hint']}")

        print("\n=== 초안 답변 ===")
        answer = synthesize_answer(args.question, contexts)
        print(answer)


if __name__ == "__main__":
    main()
