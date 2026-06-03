"""Screener 主入口 —— 5 阶段流水线。

Stage 0: 数据加载  →  失败 ⇒ 整个 job FAIL
Stage 1: Layer 1 通用 Filter  →  失败 ⇒ 整个 job FAIL
Stage 2-4: 按赛道循环(Layer 2 Filter + Strategy 评分 + 原子落库) →  单赛道失败仅该赛道 partial
Stage 5: 返回 RunResult,由调用方写 job_runs

详见 docs/screener.md §3.5 / §7.3。

CLI:
    uv run python -m pulse_core.screener.runner --date 2026-05-21
    uv run python -m pulse_core.screener.runner    # 默认最近交易日(今日)
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import asyncpg
import yaml  # pyright: ignore[reportMissingModuleSource]

from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.logger import logger
from pulse_core.outbox.writer import (
    PickPayloadItem,
    TrackPayload,
    enqueue_screener_picks,
)
from pulse_core.screener.context_builder import _build_context
from pulse_core.screener.contracts import ScreenerData
from pulse_core.screener.data_loader import load_screener_data
from pulse_core.screener.db_writer import PickRow, write_track_picks
from pulse_core.screener.registry import UNIVERSAL_FILTERS, get_filter, get_strategy

TRACKS_DIR = Path(__file__).parent / "tracks"


@dataclass
class TrackResult:
    track:     str
    status:    str    # "success" | "failed"
    inserted:  int = 0
    error:     str | None = None
    # 仅 success 时填充;outbox 早报聚合用(只取 top_n,与 daily_picks 对齐)。
    top_picks: list[PickRow] = field(default_factory=list)


@dataclass
class RunResult:
    trade_date:    date
    total_rows:    int = 0
    track_results: list[TrackResult] = field(default_factory=list)

    @property
    def status(self) -> str:
        """整体 job 状态:全成功 → success;有失败 → partial;全失败 → failed。"""
        if not self.track_results:
            return "failed"
        statuses = [tr.status for tr in self.track_results]
        if all(s == "success" for s in statuses):
            return "success"
        if all(s == "failed" for s in statuses):
            return "failed"
        return "partial"

    def to_details(self) -> dict[str, Any]:
        return {
            "trade_date": str(self.trade_date),
            "tracks": [
                {
                    "track":    tr.track,
                    "status":   tr.status,
                    "inserted": tr.inserted,
                    "error":    tr.error,
                }
                for tr in self.track_results
            ],
        }


async def run_screener(
    trade_date: date,
    *,
    tracks: list[str] | None = None,
    run_id: int | None = None,
) -> RunResult:
    """跑完整的 5 阶段流水线。

    Args:
        trade_date: 目标交易日。
        tracks: 指定跑的赛道列表;None = 跑 tracks/ 目录下全部 yaml。
        run_id: scheduler_runs.id;handler 路径必传,CLI 路径为 None
            (None ⇒ 跳过 outbox enqueue,避免本地试跑发出"假早报")。

    Returns:
        RunResult,含整体状态 + 每赛道明细。
    """
    track_files = _discover_track_files(tracks)
    if not track_files:
        raise ValueError(f"未发现可用赛道配置:tracks={tracks} dir={TRACKS_DIR}")

    async with acquire() as conn:
        data = await load_screener_data(conn, trade_date)
        layer1_passed = _run_layer1(data)
        logger.info(f"Stage 1 (Layer 1): universe {len(data['universe'])} → {len(layer1_passed)}")

        result = RunResult(trade_date=trade_date)
        for track_file in track_files:
            tr = await _run_track(conn, track_file, data, layer1_passed)
            result.track_results.append(tr)
            result.total_rows += tr.inserted

    # Plan A: outbox 在所有 per-track 事务提交后,以独立顶层事务写入。
    # 失败损耗 = 早报缺失,不回滚 picks(用户裁定优先保 picks)。
    if run_id is not None:
        await _enqueue_outbox(trade_date, run_id, result.track_results)

    return result


async def _enqueue_outbox(
    trade_date: date,
    run_id: int,
    track_results: list[TrackResult],
) -> None:
    successful = [tr for tr in track_results if tr.status == "success" and tr.top_picks]
    if not successful:
        logger.info(
            f"[run_id={run_id}] 无成功赛道或 top_picks 为空,跳过 outbox enqueue"
        )
        return

    payloads = [
        TrackPayload(
            track=tr.track,
            picks=[
                PickPayloadItem(
                    ts_code=p.ts_code,
                    strategy=p.strategy,
                    final_score=p.scorecard.axis_scores["final"],
                    rank=p.rank if p.rank is not None else 0,
                )
                for p in tr.top_picks
            ],
        )
        for tr in successful
    ]
    try:
        async with acquire() as conn:
            async with conn.transaction():
                outbox_id = await enqueue_screener_picks(
                    conn,
                    trade_date=trade_date,
                    run_id=run_id,
                    tracks=payloads,
                )
        logger.info(
            f"[run_id={run_id}] outbox enqueued: id={outbox_id} "
            f"tracks={len(payloads)}"
        )
    except Exception as e:
        logger.error(
            f"[run_id={run_id}] outbox enqueue FAILED (picks 已落库,仅丢失早报): {e}",
            exc_info=True,
        )


def _discover_track_files(tracks: list[str] | None) -> list[Path]:
    if tracks is None:
        return sorted(TRACKS_DIR.glob("*.yaml"))
    return [TRACKS_DIR / f"{t}.yaml" for t in tracks]


def _run_layer1(data: ScreenerData) -> set[str]:
    """顺序执行所有通用 Filter,取交集。失败抛异常 → 整 job FAIL。"""
    candidates = set(data["universe"])
    for FilterCls in UNIVERSAL_FILTERS:
        f = FilterCls()
        scoped = cast(ScreenerData, cast(object, {**data, "universe": sorted(candidates)}))
        result = f.apply(scoped)
        candidates = result.passed
        logger.info(
            f"Layer 1 {f.name}: passed={len(result.passed)} rejected={len(result.rejected)}"
        )
    return candidates


async def _run_track(
    conn: asyncpg.Connection,
    track_file: Path,
    data: ScreenerData,
    layer1_passed: set[str],
) -> TrackResult:
    """跑一条赛道:Layer 2 → Strategy 打分 → 排序截 top_n → 落库。"""
    track_name = track_file.stem
    try:
        cfg = _load_track_yaml(track_file)
        if cfg["track"] != track_name:
            raise ValueError(
                f"yaml 内 track={cfg['track']} 与文件名 {track_name} 不一致"
            )

        candidates = _run_layer2(cfg.get("filters", []), data, layer1_passed)
        logger.info(
            f"Stage 2 {track_name} (Layer 2): {len(layer1_passed)} → {len(candidates)}"
        )

        picks = _run_strategies(cfg.get("strategies", []), data, candidates)
        all_sorted = sorted(
            picks,
            key=lambda p: p.scorecard.axis_scores["final"],
            reverse=True,
        )
        all_with_rank = [
            PickRow(ts_code=p.ts_code, strategy=p.strategy, scorecard=p.scorecard, rank=i + 1)
            for i, p in enumerate(all_sorted)
        ]
        top_n = int(cfg.get("top_n", 0))
        top_picks = all_with_rank[:top_n]
        logger.info(
            f"Stage 3 {track_name}: scored={len(picks)} top_n={top_n} "
            f"top={len(top_picks)} candidates={len(all_with_rank)}"
        )

        result = await write_track_picks(
            conn, data["trade_date"], track_name, top_picks, all_with_rank,
        )
        return TrackResult(
            track=track_name,
            status="success",
            inserted=result.picks_inserted,
            top_picks=top_picks,
        )

    except Exception as e:
        logger.error(f"Track {track_name} FAILED: {e}", exc_info=True)
        return TrackResult(track=track_name, status="failed", error=str(e))


def _load_track_yaml(track_file: Path) -> dict[str, Any]:
    with track_file.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict) or "track" not in cfg or "top_n" not in cfg:
        raise ValueError(f"track yaml 缺少必填字段 (track / top_n):{track_file}")
    return cfg


def _run_layer2(
    filter_names: list[str],
    data: ScreenerData,
    layer1_passed: set[str],
) -> set[str]:
    candidates = set(layer1_passed)
    for name in filter_names:
        FilterCls = get_filter(name)
        f = FilterCls()
        scoped = cast(ScreenerData, cast(object, {**data, "universe": sorted(candidates)}))
        result = f.apply(scoped)
        candidates = result.passed
        logger.info(
            f"Layer 2 {f.name}: passed={len(result.passed)} rejected={len(result.rejected)}"
        )
    return candidates


def _run_strategies(
    strategy_names: list[str],
    data: ScreenerData,
    candidates: set[str],
) -> list[PickRow]:
    """对每个策略 × 每只候选股调 score(),收集所有 Scorecard。"""
    picks: list[PickRow] = []
    if not strategy_names or not candidates:
        return picks

    for name in strategy_names:
        StrategyCls = get_strategy(name)
        strat = StrategyCls()
        for ts_code in sorted(candidates):
            ctx = _build_context(ts_code, data)
            scorecard = strat.score(ctx)
            if scorecard is not None:
                picks.append(PickRow(ts_code=ts_code, strategy=name, scorecard=scorecard))
    return picks


def _parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="pulse_core.screener.runner")
    p.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
        help="Trading date in YYYY-MM-DD; default today",
    )
    p.add_argument(
        "--tracks",
        nargs="*",
        default=None,
        help="Track names; empty means all",
    )
    return p.parse_args()


async def _main_async() -> int:
    args = _parse_cli()
    try:
        result = await run_screener(args.date, tracks=args.tracks)
        logger.info(
            f"Screener done: trade_date={result.trade_date} status={result.status} "
            f"total_rows={result.total_rows} details={result.to_details()}"
        )
        return 0 if result.status in ("success", "partial") else 1
    finally:
        await close_pool()


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
