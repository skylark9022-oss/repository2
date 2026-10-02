import pandas as pd
import pytest

from pacific_radio import schema


def _one_row(**over):
    row = {c: None for c in schema.COLUMNS}
    row.update(
        record_id=schema.make_record_id("test", "f.csv", 0),
        source_db="test",
        source_file="f.csv",
        source_row=0,
        latitude=35.0,
        longitude=140.0,
        sampling_date=pd.Timestamp("2000-01-01"),
        depth_m=0.0,
        nuclide="Cs-137",
        value_orig=2.5,
        unit_orig="Bq/m3",
    )
    row.update(over)
    df = pd.DataFrame([row])
    return df.astype({c: t for c, t in schema.COLUMNS.items()})


def test_empty_frame_has_all_columns():
    df = schema.empty_frame()
    assert list(df.columns) == list(schema.COLUMNS)
    schema.validate(df)


def test_valid_row_passes():
    schema.validate(_one_row())


def test_unknown_nuclide_fails():
    with pytest.raises(ValueError, match="nuclide"):
        schema.validate(_one_row(nuclide="Cs-138"))


def test_missing_required_fails():
    with pytest.raises(ValueError, match="value_orig"):
        schema.validate(_one_row(value_orig=None))


def test_duplicate_record_id_fails():
    df = pd.concat([_one_row(), _one_row()], ignore_index=True)
    with pytest.raises(ValueError, match="중복"):
        schema.validate(df)


def test_extra_column_fails():
    df = _one_row()
    df["oops"] = 1
    with pytest.raises(ValueError, match="oops"):
        schema.validate(df)


def test_value_missing_allowed_when_below_dl():
    schema.validate(_one_row(value_orig=None, below_dl=True))
    with pytest.raises(ValueError, match="value_orig"):
        schema.validate(_one_row(value_orig=None, below_dl=False))
