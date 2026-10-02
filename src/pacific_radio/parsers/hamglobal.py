"""HAMGlobal2021 (Aoyama, 2021, 쓰쿠바대 CRiED) → 통합 스키마.

!! 형식 미확인 !!
이 파서를 만든 세션에서는 HAMGlobal2021 파일을 내려받지 못해 **열 구성을 확인하지 못했다**
(docs/data_sources.md A3). 그래서 `parsers/tabular.py` 의 열 자동 탐지 엔진을 쓴다.

처음 쓰는 절차
  1. python -m pacific_radio.parsers.hamglobal data/raw/hamglobal2021/<파일> --inspect > data/raw/hamglobal2021/inspect.json
  2. inspect.json 의 guessed_mapping 을 column_map.json 으로 저장하고 실제 열에 맞게 고친다
     (특히 단위 default_unit, 날짜 열, 불확도 열 연결, unmapped_columns 처리).
  3. python -m pacific_radio.parsers.hamglobal data/raw/hamglobal2021/<파일> --map data/raw/hamglobal2021/column_map.json \
         --out data/processed/hamglobal2021_pacific_seawater

HAMGlobal2021 에는 MARIS 에서 가져온 33,433 건이 포함되어 있다 (검색 확인). MARIS 와 합칠 때 중복 제거 필요.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .. import schema
from ..store import write_processed
from . import tabular

SOURCE_DB = "hamglobal2021"


def parse(path, mapping: dict | None = None, **kw) -> tuple[pd.DataFrame, dict]:
    return tabular.parse_file(path, SOURCE_DB, mapping=mapping, **kw)


def parse_many(paths, mapping: dict | None = None, **kw) -> tuple[pd.DataFrame, dict]:
    frames, reports = [], []
    for p in paths:
        df, rep = parse(p, mapping, **kw)
        frames.append(df)
        reports.append(rep)
    out = pd.concat(frames, ignore_index=True) if frames else schema.empty_frame()
    summary = {"n_files": len(reports), "n_kept_total": int(len(out)),
               "kept_nuclide_counts": out["nuclide"].value_counts().to_dict() if len(out) else {}, "files": reports}
    if len(out):
        schema.validate(out)
    return out, summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HAMGlobal2021 표 파일 → 통합 스키마 CSV/parquet")
    ap.add_argument("files", nargs="+", help="CSV/TSV/XLSX 파일 (여러 개 가능)")
    ap.add_argument("--inspect", action="store_true", help="헤더·첫 행·추정 매핑을 JSON 으로 출력하고 끝냄")
    ap.add_argument("--map", help="열 매핑 JSON (inspect 결과의 guessed_mapping 을 고쳐 저장한 것)")
    ap.add_argument("--sheet", help="엑셀 시트 이름 (없으면 모든 시트)")
    ap.add_argument("--header-row", type=int, help="헤더 행 번호 (0 부터). 없으면 자동 탐지")
    ap.add_argument("--default-unit", help="단위 열/헤더가 없을 때 쓸 단위 (예: Bq/m3). 지정하지 않으면 UNKNOWN 으로 남김")
    ap.add_argument("--out", default="data/processed/hamglobal2021_pacific_seawater")
    ap.add_argument("--all-regions", action="store_true")
    ap.add_argument("--keep-invalid", action="store_true")
    a = ap.parse_args(argv)
    if a.inspect:
        for f in a.files:
            print(json.dumps(tabular.inspect_file(f, a.sheet, a.header_row), ensure_ascii=False, indent=2, default=str))
        return 0
    mapping = tabular.load_mapping(a.map)
    df, report = parse_many(a.files, mapping, sheet=a.sheet, header_row=a.header_row,
                            pacific_only=not a.all_regions, drop_invalid=not a.keep_invalid, default_unit=a.default_unit)
    paths = write_processed(df, a.out, report)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False, indent=2, default=str))
    for rep in report["files"]:
        for t in rep["tables"]:
            if t.get("unmapped_columns"):
                print(f"[주의] {rep['source_file']} / {t['table']}: 매핑되지 않은 열 {t['unmapped_columns']}")
        if rep.get("n_unit_unknown"):
            print(f"[주의] {rep['source_file']}: 단위를 모르는 행 {rep['n_unit_unknown']} 건 → --default-unit 또는 매핑의 unit 지정")
    for p in paths:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
