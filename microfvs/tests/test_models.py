import subprocess

import pandas as pd
import pytest

from microfvs.constants import (
    DIAMETER_MAXIMUM,
    DIAMETER_MINIMUM,
    FVS_DATABASE_NAME,
    RESULT_TESTING_KEYFILE_CONTENT,
    STR_PROCESS,
    STR_STAND_ID,
    STR_STOP,
    TEST_FVS_WARNINGS_AND_ERRORS,
    TEST_STANDINIT_RECORDS,
    TEST_TREEINIT_RECORDS,
)
from microfvs.enums import FvsOutputTableName, FvsVariant
from microfvs.models import (
    FvsEvent,
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfile,
    FvsOutputTreeListRecord,
    FvsResult,
    FvsStandInit,
    FvsTreeInit,
    FvsTreeInitRecord,
)

EXPECTED_POPULATED_TABLES = [
    FvsOutputTableName.FVS_CASES,
    FvsOutputTableName.FVS_STAND_STOCK,
    FvsOutputTableName.FVS_STRUCTURE_CLASS,
    FvsOutputTableName.FVS_SUMMARY2,
    FvsOutputTableName.FVS_TREELIST,
]

TEST_FVS_DISTURBANCE = FvsEventLibrary().lookup(
    event_type=FvsEventType.DISTURBANCE, event_key="FIC1"
)
TEST_FVS_TREATMENT = FvsEventLibrary().lookup(
    event_type=FvsEventType.TREATMENT, event_key="CMCC"
)

TEST_STANDINIT = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
TEST_TREEINIT = [
    FvsTreeInitRecord.model_validate(tree) for tree in TEST_TREEINIT_RECORDS
]
NO_TREATMENT_MARKER = "*** NO TREATMENT ***"
NO_DISTURBANCE_MARKER = "*** NO DISTURBANCE ***"


def test_standid_as_int():
    stand_init = FvsStandInit(
        stand_id=12345,
        variant=FvsVariant.CA,
        inv_year=1990,
        basal_area_factor=0,
        inv_plot_size=1,
        brk_dbh=999,
    )
    assert stand_init.stand_id == "12345"


def test_keyfile_name():
    keyfile = FvsKeyfile(
        variant=FvsVariant.CA,
        stand_id="12345",
        treatments=[TEST_FVS_TREATMENT],
        disturbances=[TEST_FVS_DISTURBANCE],
    )
    assert keyfile.name == (
        f"{FvsVariant.CA}_12345_"
        f"{TEST_FVS_TREATMENT.name}_{TEST_FVS_DISTURBANCE.name}"
    )


@pytest.mark.parametrize("num_trees", [5, 10, 100])
def test_random_treelist(num_trees):
    trees = FvsOutputTreeListRecord._random_treelist(num_trees)
    assert len(trees) == num_trees
    assert trees[0]["dbh"] == DIAMETER_MINIMUM
    assert trees[-1]["dbh"] == DIAMETER_MAXIMUM
    assert (
        FvsOutputTreeListRecord._random_tree(smallest_tree=True).dbh
        == DIAMETER_MINIMUM
    )
    assert (
        FvsOutputTreeListRecord._random_tree(largest_tree=True).dbh
        == DIAMETER_MAXIMUM
    )
    with pytest.raises(
        ValueError,
        match="Only one of smallest_tree and largest_tree can be True.",
    ):
        FvsOutputTreeListRecord._random_tree(
            smallest_tree=True, largest_tree=True
        )


def test_fvs_result(tmp_path):
    keyfile = FvsKeyfile(
        variant=FvsVariant.CA,
        stand_id="12345",
        template=RESULT_TESTING_KEYFILE_CONTENT,
    )
    keyfile_path = f"{tmp_path}/{keyfile.name}.key"
    with open(keyfile_path, "w") as f:
        f.write(keyfile.content)

    cmd = [
        f"/usr/local/bin/FVS{keyfile.fvs_variant.lower()}",
        f"--keywordfile={keyfile_path}",
    ]
    proc = subprocess.run(cmd, capture_output=True, cwd=tmp_path)
    db_path = f"{tmp_path}/{FVS_DATABASE_NAME}"
    result = FvsResult.from_files(
        fvs_keyfile=keyfile,
        process=proc,
        path_to_dbout=db_path,
        path_to_outfile=keyfile_path.replace(".key", ".out"),
    )
    assert result.return_code == 0
    assert result.keyfile == keyfile.content
    assert result.command == " ".join(cmd)
    assert result.fvs_warnings is None
    assert result.outfile is not None
    assert set(result.fvs_data.keys()).issuperset(
        set(EXPECTED_POPULATED_TABLES)
    )
    for table in EXPECTED_POPULATED_TABLES:
        assert isinstance(result.fvs_data[table], list)
        assert len(result.fvs_data[table]) > 0
        assert isinstance(result.fvs_data[table][0], dict)

    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    dumped_json = result.model_dump_json()
    assert isinstance(dumped_json, str)


def test_parse_fvs_warnings_errors():
    problems = FvsResult._parse_fvs_warnings_and_errors(
        TEST_FVS_WARNINGS_AND_ERRORS
    )
    assert len(problems) == 3
    assert (
        problems[0].type == "WARNING"
        and problems[0].id == "FVS14"
        and problems[0].line_number == 1
    )
    assert (
        problems[1].type == "WARNING"
        and problems[1].id == "FFE MODEL"
        and problems[1].line_number == 3
    )
    assert (
        problems[2].type == "ERROR"
        and problems[2].id == "FVS01"
        and problems[2].line_number == 6
    )


def test_fvskeyfile():
    stand_init = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])

    keyfile = FvsKeyfile(
        variant=stand_init.variant,
        stand_id=stand_init.stand_id,
        treatments=[TEST_FVS_TREATMENT],
        disturbances=[TEST_FVS_DISTURBANCE],
    )

    assert isinstance(keyfile, FvsKeyfile)
    assert keyfile.stand_id == stand_init.stand_id
    assert keyfile.fvs_variant == stand_init.variant
    assert (
        keyfile.content.splitlines()[4]
        == TEST_STANDINIT_RECORDS[0][STR_STAND_ID]
    )
    assert keyfile.content.splitlines()[-2] == STR_PROCESS
    assert keyfile.content.splitlines()[-1] == STR_STOP


# -------------------------------------------------------
# Two-pass keyfile rendering order
# -------------------------------------------------------


def _make_keyfile(**overrides) -> FvsKeyfile:
    """Helper to build a FvsKeyfile with sensible defaults."""
    defaults: dict = {"variant": FvsVariant.CA, "stand_id": "99999"}
    defaults.update(overrides)
    return FvsKeyfile(**defaults)


def test_keyfile_default_when_no_events():
    keyfile = _make_keyfile()

    assert NO_TREATMENT_MARKER in keyfile.content
    assert NO_DISTURBANCE_MARKER in keyfile.content


def test_keyfile_renders_treatment_content():
    TREATMENT_MARKER = "THINDBH            0        60       200"
    treatment = FvsEvent(name="MY_THIN", content=TREATMENT_MARKER)
    keyfile = _make_keyfile(treatments=[treatment])

    assert TREATMENT_MARKER in keyfile.content
    assert NO_TREATMENT_MARKER not in keyfile.content


def test_keyfile_renders_disturbance_content():
    DISTURBANCE_MARKER = "SALVAGE            0       999"
    disturbance = FvsEvent(name="MY_SALVAGE", content=DISTURBANCE_MARKER)
    keyfile = _make_keyfile(disturbances=[disturbance])

    assert DISTURBANCE_MARKER in keyfile.content
    assert NO_DISTURBANCE_MARKER not in keyfile.content


def test_keyfile_two_pass_rendering():
    """Placeholders in treatment content are resolved."""
    PLACEHOLDER = '{{"{:>10d}".format(thin_max_dbh)}}'
    TREATMENT_WITH_PLACEHOLDER = f"THINDBH            0{PLACEHOLDER}       200"
    INJECT_VALUE = 60
    EXPECTED_TREATMENT_CONTENT = "THINDBH            0        60       200"
    treatment = FvsEvent(
        name="PARAM_THIN",
        content=TREATMENT_WITH_PLACEHOLDER,
    )
    keyfile = _make_keyfile(
        treatments=[treatment],
        template_params={"thin_max_dbh": INJECT_VALUE},
    )

    assert PLACEHOLDER in TREATMENT_WITH_PLACEHOLDER
    assert PLACEHOLDER not in keyfile.content
    assert EXPECTED_TREATMENT_CONTENT in keyfile.content


def test_keyfile_multiple_treatments_joined():
    t1 = FvsEvent(name="T1", content="KEYWORD_A")
    t2 = FvsEvent(name="T2", content="KEYWORD_B")
    keyfile = _make_keyfile(treatments=[t1, t2])

    assert "KEYWORD_A\nKEYWORD_B" in keyfile.content


# -------------------------------------------------------
# DataFrame methods
# -------------------------------------------------------


def test_tree_init_to_dataframe_none_trees():
    tree_init = FvsTreeInit(trees=None)
    df = tree_init.to_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    expected_cols = set(FvsTreeInitRecord.model_fields.keys())
    assert set(df.columns) == expected_cols


def test_tree_init_from_dataframe_case_insensitive():
    upper_records = [
        {k.upper(): v for k, v in rec.items()} for rec in TEST_TREEINIT_RECORDS
    ]
    df = pd.DataFrame(upper_records)
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]

    tree_init = FvsTreeInit.from_dataframe(
        df, stand_id=stand_id, column_name="STAND_ID"
    )
    assert tree_init.trees is not None
    assert len(tree_init.trees) > 0


def test_tree_init_from_dataframe_no_match_warns():
    df = pd.DataFrame(TEST_TREEINIT_RECORDS)

    with pytest.warns(UserWarning, match="No records found"):
        tree_init = FvsTreeInit.from_dataframe(df, stand_id="NONEXISTENT")
    assert tree_init.trees is None


def test_stand_init_to_dataframe():
    stand = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
    df = stand.to_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["stand_id"] == stand.stand_id
    assert df.iloc[0]["variant"] == stand.variant


def test_result_serialize_mixed_types():
    table_name = FvsOutputTableName.FVS_SUMMARY2
    records = [{"CaseID": "test", "Year": 2020, "BA": 100.0}]

    df_input = {table_name: pd.DataFrame(records)}
    serialized = FvsResult.serialize_dict_of_dataframes(df_input)
    assert serialized[table_name] == records

    list_input = {table_name: records}
    passthrough = FvsResult.serialize_dict_of_dataframes(list_input)
    assert passthrough[table_name] == records
