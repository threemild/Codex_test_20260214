import argparse
import datetime as dt
import sqlite3
from pathlib import Path



def now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def init_db(db_path: Path, schema_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def extract_pages(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return pages


def chunk_pages(pages: list[str], max_chars: int = 1200, overlap: int = 200):
    merged = []
    for i, txt in enumerate(pages, start=1):
        if txt:
            merged.append((i, txt))

    chunks = []
    buffer = ""
    page_start = None
    last_page = None

    for page_no, text in merged:
        if page_start is None:
            page_start = page_no
        last_page = page_no

        if len(buffer) + len(text) + 1 <= max_chars:
            buffer += ("\n" if buffer else "") + text
            continue

        if buffer:
            chunks.append((page_start, last_page - 1 if last_page and last_page > page_start else page_start, buffer))

        if overlap > 0 and buffer:
            buffer = buffer[-overlap:] + "\n" + text
        else:
            buffer = text
        page_start = page_no

    if buffer:
        chunks.append((page_start, last_page or page_start, buffer))

    return chunks


def ingest_pdf(
    db_path: Path,
    pdf_path: Path,
    title: str,
    region: str,
    authority: str | None,
    effective_date: str | None,
):
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO regulations(title, region, authority, effective_date, source_path, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (title, region, authority, effective_date, str(pdf_path), now_iso()),
        )
        regulation_id = cur.lastrowid

        for i, (p_start, p_end, content) in enumerate(chunks):
            section_hint = content.split("\n", 1)[0][:200]
            cur.execute(
                """
                INSERT INTO chunks(regulation_id, chunk_index, page_start, page_end, section_hint, content, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (regulation_id, i, p_start, p_end, section_hint, content, now_iso()),
            )
            chunk_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO chunks_fts(content, section_hint, region, authority, title, chunk_id)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (content, section_hint, region, authority or "", title, chunk_id),
            )

        conn.commit()
        print(f"ingested regulation_id={regulation_id}, chunks={len(chunks)}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Regulation PDF ingestion utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize database schema")
    p_init.add_argument("--db", required=True)
    p_init.add_argument("--schema", default="schema.sql")

    p_ing = sub.add_parser("ingest", help="Ingest a regulation PDF")
    p_ing.add_argument("--db", required=True)
    p_ing.add_argument("--pdf", required=True)
    p_ing.add_argument("--title", required=True)
    p_ing.add_argument("--region", required=True)
    p_ing.add_argument("--authority")
    p_ing.add_argument("--effective-date")

    args = parser.parse_args()

    if args.cmd == "init":
        init_db(Path(args.db), Path(args.schema))
        print("database initialized")
    elif args.cmd == "ingest":
        ingest_pdf(
            db_path=Path(args.db),
            pdf_path=Path(args.pdf),
            title=args.title,
            region=args.region,
            authority=args.authority,
            effective_date=args.effective_date,
        )


if __name__ == "__main__":
    main()
