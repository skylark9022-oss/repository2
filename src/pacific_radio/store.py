"""data/processed/ 에 통합 스키마 DB 를 쓰고 읽는 도우미."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import schema


def write_processed(df: pd.DataFrame, stem: str | Path, report: dict | None = None) -> list[Path]:
    """CSV 로 저장하고, pyarrow 가 있으면 parquet 도 함께. report 는 JSON 으로."""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    df = df[list(schema.COLUMNS)]
    paths = []
    csv_path = stem.with_suffix(".csv")
    df.to_csv(csv_path, index=False, date_format="%Y-%m-%d")
    paths.append(csv_path)
    try:
        import pyarrow  # noqa: F401
        pq_path = stem.with_suffix(".parquet")
        df.to_parquet(pq_path, index=False)
        paths.append(pq_path)
    except ImportError:
        pass
    if report is not None:
        rp = stem.with_name(stem.name + "_report.json")
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        paths.append(rp)
    return paths


def read_processed(path: str | Path) -> pd.DataFrame:
    """CSV 또는 parquet 을 스키마 dtype 으로 읽는다."""
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        date_cols = [c for c, t in schema.COLUMNS.items() if t.startswith("datetime")]
        df = pd.read_csv(path, parse_dates=date_cols)
    return df.astype({c: t for c, t in schema.COLUMNS.items() if c in df.columns})
