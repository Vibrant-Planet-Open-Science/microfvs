import pytest

from microfvs.enums import FvsKeyfileTemplate
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.utils.template_helpers import (
    classify_template_variables,
    render_template,
)

# -------------------------------------------------------
# classify_template_variables
# -------------------------------------------------------


def test_classify_bare_variables():
    """Variables without guards are required."""
    template = "{{ foo }}\n{{ bar }}"
    required, optional = classify_template_variables(template)
    assert required == ["bar", "foo"]
    assert optional == []


def test_classify_default_filter():
    """Variables with | default() are optional."""
    template = '{{ foo | default("x") }}'
    required, optional = classify_template_variables(template)
    assert required == []
    assert optional == ["foo"]


def test_classify_defined_guard():
    """Variables inside {% if var is defined %} are optional."""
    template = "{% if foo is defined %}{{ foo }}{% endif %}"
    required, optional = classify_template_variables(template)
    assert required == []
    assert optional == ["foo"]


def test_classify_mixed():
    """Required, default-guarded, and defined-guarded together."""
    template = (
        "{{ required_var }}\n"
        '{{ defaulted | default("x") }}\n'
        "{% if guarded is defined %}{{ guarded }}{% endif %}"
    )
    required, optional = classify_template_variables(template)
    assert required == ["required_var"]
    assert optional == ["defaulted", "guarded"]


def test_classify_chained_filter():
    """A default filter chained with other filters is optional."""
    template = "{{ foo | default(0) | int }}"
    required, optional = classify_template_variables(template)
    assert required == []
    assert optional == ["foo"]


def test_classify_variable_both_bare_and_defaulted():
    """A variable used bare anywhere is required."""
    template = '{{ foo | default("x") }}\n{{ foo }}'
    required, optional = classify_template_variables(template)
    assert required == ["foo"]
    assert optional == []


def test_classify_default_keyfile_template():
    """Only stand_id is required in the default template."""
    required, optional = classify_template_variables(FvsKeyfileTemplate.DEFAULT)
    assert "stand_id" in required
    assert "num_cycles" in optional
    assert "cycle_length" in optional
    assert "first_cycle_length" in optional
    assert "treatment" in optional
    assert "disturbance" in optional


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
