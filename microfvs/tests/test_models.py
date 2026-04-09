import subprocess

import pandas as pd
import pytest
from pydantic import ValidationError

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
from microfvs.exceptions import FvsTemplateRenderError
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
        assert isinstance(result.fvs_data[table], pd.DataFrame)
        assert len(result.fvs_data[table]) > 0

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
# FvsKeyfile validators and computed fields
# -------------------------------------------------------


def _make_keyfile(**overrides) -> FvsKeyfile:
    """Helper to build a FvsKeyfile with sensible defaults."""
    defaults: dict = {"variant": FvsVariant.CA, "stand_id": "99999"}
    defaults.update(overrides)
    return FvsKeyfile(**defaults)


def test_keyfile_standid_cast_from_int():
    keyfile = _make_keyfile(stand_id=12345)
    assert keyfile.stand_id == "12345"


def test_keyfile_resolve_treatment_single_string():
    keyfile = _make_keyfile(treatments="CMCC")
    assert len(keyfile.treatments) == 1
    assert keyfile.treatments[0].name == "CMCC"


def test_keyfile_resolve_treatment_list_of_strings():
    keyfile = _make_keyfile(treatments=["CMCC", "RMGP"])
    assert len(keyfile.treatments) == 2
    assert keyfile.treatments[0].name == "CMCC"
    assert keyfile.treatments[1].name == "RMGP"


def test_keyfile_resolve_treatment_mixed_list():
    manual = FvsEvent(name="CUSTOM", content="KEYWORD")
    keyfile = _make_keyfile(treatments=["CMCC", manual])
    assert keyfile.treatments[0].name == "CMCC"
    assert keyfile.treatments[1].name == "CUSTOM"


def test_keyfile_resolve_disturbance_single_string():
    keyfile = _make_keyfile(disturbances="FIC1")
    assert len(keyfile.disturbances) == 1
    assert keyfile.disturbances[0].name == "FIC1"


def test_keyfile_treatment_name_joins_with_plus():
    keyfile = _make_keyfile(treatments=["CMCC", "RMGP"])
    assert keyfile.treatment_name == "CMCC+RMGP"


def test_keyfile_disturbance_name_joins_with_plus():
    d1 = FvsEvent(name="D1", content="X")
    d2 = FvsEvent(name="D2", content="Y")
    keyfile = _make_keyfile(disturbances=[d1, d2])
    assert keyfile.disturbance_name == "D1+D2"


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
# Template rendering error handling
# -------------------------------------------------------


def test_custom_template_missing_variable_raises():
    """Undefined variable raises FvsTemplateRenderError."""
    template = "{{ stand_id }}\n{{ missing_var }}"
    keyfile = _make_keyfile(template=template)
    with pytest.raises(FvsTemplateRenderError, match="missing_var"):
        keyfile.content


def test_custom_template_reports_all_missing_variables():
    """Error reports every unprovided variable, not just the first."""
    template = "{{ stand_id }}\n{{ aaa }}\n{{ zzz }}"
    keyfile = _make_keyfile(template=template)
    with pytest.raises(FvsTemplateRenderError) as exc_info:
        keyfile.content

    err = exc_info.value
    assert err.missing_required == ["aaa", "zzz"]
    assert "stand_id" in err.template_variables
    assert "aaa" in err.template_variables
    assert "zzz" in err.template_variables


def test_custom_template_reports_provided_variables():
    """Error includes provided variable names."""
    template = "{{ stand_id }}\n{{ missing_var }}"
    keyfile = _make_keyfile(template=template)
    with pytest.raises(FvsTemplateRenderError) as exc_info:
        keyfile.content

    err = exc_info.value
    assert "stand_id" in err.provided_variables
    assert "treatment" in err.provided_variables
    assert "disturbance" in err.provided_variables


def test_custom_template_all_variables_provided_renders():
    """Custom template renders when all variables supplied."""
    template = "Stand: {{ stand_id }}\nNote: {{ my_note }}"
    keyfile = _make_keyfile(
        template=template,
        template_params={"my_note": "test value"},
    )

    assert "Stand: 99999" in keyfile.content
    assert "Note: test value" in keyfile.content


def test_default_template_renders_without_template_params():
    """The default template's | default() filters prevent errors."""
    keyfile = _make_keyfile()
    assert keyfile.content  # renders without raising


def test_second_pass_missing_variable_raises():
    """Treatment placeholder raises on second pass."""
    treatment = FvsEvent(
        name="BAD",
        content="THINDBH  {{ missing_param }}",
    )
    keyfile = _make_keyfile(
        treatments=[treatment],
        template_params={"some_other_param": 1},
    )
    with pytest.raises(FvsTemplateRenderError, match="missing_param"):
        keyfile.content


# -------------------------------------------------------
# Reserved template_params keys
# -------------------------------------------------------


def test_keyfile_rejects_reserved_stand_id_in_template_params():
    with pytest.raises(ValidationError, match="reserved key"):
        _make_keyfile(template_params={"stand_id": "evil"})


def test_keyfile_rejects_reserved_treatment_in_template_params():
    with pytest.raises(ValidationError, match="reserved key"):
        _make_keyfile(template_params={"treatment": "evil"})


def test_keyfile_rejects_reserved_variant_in_template_params():
    with pytest.raises(ValidationError, match="reserved key"):
        _make_keyfile(template_params={"variant": "SN"})


def test_keyfile_rejects_reserved_disturbance_in_template_params():
    with pytest.raises(ValidationError, match="reserved key"):
        _make_keyfile(template_params={"disturbance": "evil"})


def test_keyfile_allows_non_reserved_template_params():
    keyfile = _make_keyfile(template_params={"num_cycles": 10})
    assert keyfile.template_params == {"num_cycles": 10}


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


def test_tree_init_from_dataframe_happy_path():
    df = pd.DataFrame(TEST_TREEINIT_RECORDS)
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]

    tree_init = FvsTreeInit.from_dataframe(df, stand_id=stand_id)

    assert tree_init.trees is not None
    assert len(tree_init.trees) == len(TEST_TREEINIT_RECORDS)
    assert all(t.stand_id == stand_id for t in tree_init.trees)


def test_tree_init_to_dataframe_roundtrip():
    df_in = pd.DataFrame(TEST_TREEINIT_RECORDS)
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]
    tree_init = FvsTreeInit.from_dataframe(df_in, stand_id=stand_id)

    df_out = tree_init.to_dataframe()

    assert isinstance(df_out, pd.DataFrame)
    assert len(df_out) == len(TEST_TREEINIT_RECORDS)
    assert set(FvsTreeInitRecord.model_fields.keys()).issubset(
        set(df_out.columns)
    )
    assert all(df_out["stand_id"] == stand_id)


def test_tree_init_raises_on_multiple_stand_ids():
    stand_a = dict(TEST_TREEINIT_RECORDS[0], stand_id="stand_a")
    stand_b = dict(TEST_TREEINIT_RECORDS[0], stand_id="stand_b")
    records = [
        FvsTreeInitRecord.model_validate(stand_a),
        FvsTreeInitRecord.model_validate(stand_b),
    ]

    with pytest.raises(ValidationError, match="single stand_id"):
        FvsTreeInit(trees=records)


def test_tree_init_stand_id_computed_field():
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]
    df = pd.DataFrame(TEST_TREEINIT_RECORDS)
    tree_init = FvsTreeInit.from_dataframe(df, stand_id=stand_id)

    assert tree_init.stand_id == stand_id


def test_tree_init_stand_id_none_when_no_trees():
    assert FvsTreeInit(trees=None).stand_id is None


def test_stand_init_from_dataframe_happy_path():
    df = pd.DataFrame(TEST_STANDINIT_RECORDS)
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]

    stand = FvsStandInit.from_dataframe(df, stand_id=stand_id)

    assert isinstance(stand, FvsStandInit)
    assert stand.stand_id == stand_id
    assert stand.variant == TEST_STANDINIT_RECORDS[0]["variant"]


def test_stand_init_from_dataframe_zero_matches_raises():
    df = pd.DataFrame(TEST_STANDINIT_RECORDS)

    with pytest.raises(ValueError, match="Found 0 records"):
        FvsStandInit.from_dataframe(df, stand_id="NONEXISTENT")


def test_stand_init_from_dataframe_multiple_matches_raises():
    duplicate_records = [TEST_STANDINIT_RECORDS[0], TEST_STANDINIT_RECORDS[0]]
    df = pd.DataFrame(duplicate_records)
    stand_id = TEST_STANDINIT_RECORDS[0]["stand_id"]

    with pytest.raises(ValueError, match="Found 2 records"):
        FvsStandInit.from_dataframe(df, stand_id=stand_id)


# -------------------------------------------------------
# FvsResult fvs_data coercion and serialization
# -------------------------------------------------------

_SUMMARY2_RECORDS = [
    {"CaseID": "test", "Year": 2020, "BA": 100.0},
    {"CaseID": "test", "Year": 2025, "BA": 110.0},
]
_TREELIST_RECORDS = [
    {"CaseID": "test", "Year": 2020, "DBH": 8.0},
]

_FVS_RESULT_ATTRS = {
    "name": "TEST_RESULT",
    "fvs_variant": "CA",
    "stand_id": "99999",
    "treatment": "NONE",
    "disturbance": "NONE",
    "keyfile": "STDIDENT\n99999\nSTOP\n",
    "command": "/usr/local/bin/FVSca --keywordfile=test.key",
    "return_code": 0,
    "stdout": None,
    "stderr": None,
    "outfile": "",
    "fvs_data": {
        FvsOutputTableName.FVS_SUMMARY2: _SUMMARY2_RECORDS,
        FvsOutputTableName.FVS_TREELIST: _TREELIST_RECORDS,
    },
}


def _make_fvs_result(**overrides) -> FvsResult:
    attrs = dict(_FVS_RESULT_ATTRS)
    attrs.update(overrides)
    return FvsResult.model_validate(attrs)


def test_fvs_data_coerces_records_to_dataframes():
    result = _make_fvs_result()
    assert isinstance(
        result.fvs_data[FvsOutputTableName.FVS_SUMMARY2], pd.DataFrame
    )
    assert result.fvs_data[FvsOutputTableName.FVS_SUMMARY2].shape == (2, 3)
    assert isinstance(
        result.fvs_data[FvsOutputTableName.FVS_TREELIST], pd.DataFrame
    )


def test_fvs_data_serializes_dataframes_to_records():
    result = _make_fvs_result()
    dumped = result.model_dump()
    summary = dumped["fvs_data"][FvsOutputTableName.FVS_SUMMARY2]
    assert isinstance(summary, list)
    assert isinstance(summary[0], dict)
    assert summary == _SUMMARY2_RECORDS


def test_table_names():
    result = _make_fvs_result()
    names = result.table_names
    assert isinstance(names, list)
    assert FvsOutputTableName.FVS_SUMMARY2 in names
    assert FvsOutputTableName.FVS_TREELIST in names
    assert len(names) == 2
