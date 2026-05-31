"""CLI helpers for ingestion scripts.

每个 ingestion 脚本通过 `build_arg_parser()` 获得一致的命令行参数：
    --start YYYYMMDD   起始日期（覆盖 DB 增量推断）
    --end YYYYMMDD     截止日期（默认今天）
    --stocks A,B,C     限定股票池（测试模式）
    --limit N          限定数量（test 模式快速验证）
    --dry-run          只拉取不写库

使用方式见 sync_*.py 的 _main()。
"""

import argparse
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class IngestionArgs:
    """Parsed CLI args for ingestion scripts.

    所有字段都是可选；调用方按需消费。
    """

    start: date | None = None
    end: date | None = None
    stocks: list[str] | None = None
    limit: int | None = None
    dry_run: bool = False


def _parse_yyyymmdd(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Date must be YYYYMMDD, got: {s}") from e


def _parse_stocks(s: str) -> list[str]:
    codes = [c.strip() for c in s.split(",") if c.strip()]
    if not codes:
        raise argparse.ArgumentTypeError("--stocks must contain at least one ts_code")
    return codes


def build_arg_parser(table_name: str) -> argparse.ArgumentParser:
    """Standard argument parser for ingestion scripts."""
    p = argparse.ArgumentParser(
        prog=f"sync_{table_name}",
        description=f"Sync Tushare data into {table_name}.",
    )
    p.add_argument(
        "--start",
        type=_parse_yyyymmdd,
        help="Start date YYYYMMDD (overrides DB-based incremental inference).",
    )
    p.add_argument(
        "--end",
        type=_parse_yyyymmdd,
        help="End date YYYYMMDD (default: today).",
    )
    p.add_argument(
        "--stocks",
        type=_parse_stocks,
        help="Comma-separated ts_codes to restrict sync (test mode), e.g. 000001.SZ,600000.SH",
    )
    p.add_argument(
        "--limit",
        type=int,
        help="Limit max stocks/days processed (test mode).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch from Tushare but skip DB writes.",
    )
    return p


def parse_args(table_name: str, argv: list[str] | None = None) -> IngestionArgs:
    """Parse argv into IngestionArgs."""
    ns = build_arg_parser(table_name).parse_args(argv)
    if ns.start and ns.end and ns.start > ns.end:
        raise SystemExit(f"--start ({ns.start}) must be <= --end ({ns.end})")
    return IngestionArgs(
        start=ns.start,
        end=ns.end,
        stocks=ns.stocks,
        limit=ns.limit,
        dry_run=ns.dry_run,
    )
