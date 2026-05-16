import pytest

from microfvs.enums import FvsKeyfileTemplate
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.utils.template_helpers import (
    ClassifiedTemplateVariables,
    classify_fvs_keyfile_template_variables,
    classify_template_variables,
    render_template,
)

# -------------------------------------------------------
# classify_template_variables
# -------------------------------------------------------


def test_classify_bare_variables():
    """Variables without guards are required."""
    template = "{{ foo }}\n{{ bar }}"
    result = classify_template_variables(template)
    assert isinstance(result, ClassifiedTemplateVariables)
    assert result.required == ["bar", "foo"]
    assert result.optional == []


def test_classify_default_filter():
    """Variables with | default() are optional."""
    template = '{{ foo | default("x") }}'
    result = classify_template_variables(template)
    assert result.required == []
    assert result.optional == ["foo"]


def test_classify_defined_guard():
    """Variables inside {% if var is defined %} are optional."""
    template = "{% if foo is defined %}{{ foo }}{% endif %}"
    result = classify_template_variables(template)
    assert result.required == []
    assert result.optional == ["foo"]


def test_classify_mixed():
    """Required, default-guarded, and defined-guarded together."""
    template = (
        "{{ required_var }}\n"
        '{{ defaulted | default("x") }}\n'
        "{% if guarded is defined %}{{ guarded }}{% endif %}"
    )
    result = classify_template_variables(template)
    assert result.required == ["required_var"]
    assert result.optional == ["defaulted", "guarded"]


def test_classify_chained_filter():
    """A default filter chained with other filters is optional."""
    template = "{{ foo | default(0) | int }}"
    result = classify_template_variables(template)
    assert result.required == []
    assert result.optional == ["foo"]


def test_classify_variable_both_bare_and_defaulted():
    """A variable used bare anywhere is required."""
    template = '{{ foo | default("x") }}\n{{ foo }}'
    result = classify_template_variables(template)
    assert result.required == ["foo"]
    assert result.optional == []


def test_classify_default_keyfile_template():
    """Only stand_id is required in the default template."""
    result = classify_template_variables(FvsKeyfileTemplate.DEFAULT)
    assert "stand_id" in result.required
    assert "variant" not in result.required
    assert "num_cycles" in result.optional
    assert "cycle_length" in result.optional
    assert "first_cycle_length" in result.optional
    assert "treatment" in result.optional
    assert "disturbance" in result.optional


def test_classify_fvs_keyfile_template_includes_variant():
    """API classification always lists variant as required."""
    result = classify_fvs_keyfile_template_variables("{{ foo }}")
    assert result.required == ["foo", "variant"]


# -------------------------------------------------------
# render_template
# -------------------------------------------------------


def test_render_succeeds_with_all_variables():
    """Rendering works when all variables are provided."""
    template = "Hello {{ name }}"
    result = render_template(template, {"name": "world"})
    assert result == "Hello world"


def test_render_succeeds_with_only_optional_missing():
    """Missing optional variables do not raise."""
    template = '{{ required }} {{ opt | default("fallback") }}'
    result = render_template(template, {"required": "hi"})
    assert result == "hi fallback"


def test_render_raises_on_missing_required():
    """Missing required variable raises FvsTemplateRenderError."""
    template = "{{ required_var }}"
    with pytest.raises(FvsTemplateRenderError, match="required_var"):
        render_template(template, {})


def test_render_error_has_correct_attributes():
    """Error attributes reflect classification."""
    template = (
        '{{ required_a }}\n{{ required_b }}\n{{ optional_c | default("x") }}'
    )
    with pytest.raises(FvsTemplateRenderError) as exc_info:
        render_template(template, {})

    err = exc_info.value
    assert err.missing_required == ["required_a", "required_b"]
    assert err.missing_optional == ["optional_c"]
    assert err.provided_variables == []
    assert set(err.template_variables) == {
        "required_a",
        "required_b",
        "optional_c",
    }


def test_render_error_excludes_provided_from_missing():
    """Provided variables do not appear in missing lists."""
    template = "{{ a }}\n{{ b }}\n{{ c | default(1) }}"
    with pytest.raises(FvsTemplateRenderError) as exc_info:
        render_template(template, {"a": "ok"})

    err = exc_info.value
    assert err.missing_required == ["b"]
    assert err.missing_optional == ["c"]
    assert "a" in err.provided_variables
