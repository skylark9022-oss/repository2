"""끝까지 돌려서 값이 정확히 들어오는지 확인하고 결과를 docs/evidence/verification_report.json 에 남긴다.

    python scripts/run_verification.py
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import synth_tabular as syn  # noqa: E402
from pacific_radio import verify  # noqa: E402
from pacific_radio.parsers import hamglobal, maris, tabular  # noqa: E402

HELCOM = ROOT / "tests" / "data" / "maris_sample_helcom_2024.nc"


def main() -> int:
    out = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # MARIS 실제 형식 샘플
        df, rep = maris.parse(HELCOM, pacific_only=False)
        out["maris_helcom"] = {"reconcile": verify.reconcile_maris(HELCOM, df), "accounting": verify.accounting_check(rep),
                               "roundtrip": verify.roundtrip_check(df, td / "maris")}
        # 합성 표 자료 (정답 대조)
        truth = syn.make_truth(3000, seed=7)
        tdf = syn.truth_records(truth)
        p = td / "wide.csv"; syn.render_wide_csv(truth, p)
        dfw, repw = hamglobal.parse(p, pacific_only=False)
        out["synthetic_wide_csv"] = {"truth": syn.compare_to_truth(dfw, tdf, lambda r: int(r["source_row"])),
                                     "accounting": verify.accounting_check(repw), "roundtrip": verify.roundtrip_check(dfw, td / "wide")}
        q = td / "long.xlsx"; syn.render_long_xlsx(truth, q)
        g = tabular.guess_mapping(dict(tabular.load_tables(q))["Data"].columns); g["notes_columns"] = ["truth_idx"]
        dfl, repl = hamglobal.parse(q, g, pacific_only=False)
        out["synthetic_long_xlsx"] = {"truth": syn.compare_to_truth(dfl, tdf, lambda r: int(re.search(r"truth_idx=(\d+)", r["notes"]).group(1))),
                                      "accounting": verify.accounting_check(repl), "roundtrip": verify.roundtrip_check(dfl, td / "long")}
    for k, v in out.items():
        for kk in ("reconcile", "roundtrip"):
            if kk in v:
                v[kk].pop("mismatches", None); v[kk].pop("paths", None)
    dest = ROOT / "docs" / "evidence" / "verification_report.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    ok = (out["maris_helcom"]["reconcile"]["n_mismatches"] == 0 and out["maris_helcom"]["roundtrip"]["ok"]
          and all(out[k]["truth"]["n_mismatches"] == 0 and out[k]["truth"]["n_missing"] == 0 and out[k]["roundtrip"]["ok"]
                  for k in ("synthetic_wide_csv", "synthetic_long_xlsx")))
    print(json.dumps({k: {kk: {x: y for x, y in vv.items() if x in ("n_mismatches", "n_missing", "n_matched", "n_truth", "n_compared", "ok", "n_in", "sum")}
                           for kk, vv in v.items()} for k, v in out.items()}, ensure_ascii=False, indent=2))
    print("ALL OK" if ok else "FAILURES PRESENT")
    print("wrote", dest)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
