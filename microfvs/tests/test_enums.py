import pytest

from microfvs.enums import FvsEventType, FvsKeyfileTemplate, FvsVariant
from microfvs.models import FvsEvent, FvsEventLibrary
from microfvs.utils.template_helpers import ClassifiedTemplateVariables

# -------------------------------------------------------
# FvsVariant
# -------------------------------------------------------


@pytest.mark.parametrize("variant", list(FvsVariant))
def test_variant_value_is_two_letter_code(variant):
    assert len(variant.value) == 2
    assert variant.value == variant.value.upper()


@pytest.mark.parametrize("variant", list(FvsVariant))
def test_variant_description_is_nonempty_string(variant):
    assert isinstance(variant.description, str)
    assert len(variant.description) > 0


# -------------------------------------------------------
# FvsKeyfileTemplate
# -------------------------------------------------------


def test_default_template_loads():
    template = FvsKeyfileTemplate.DEFAULT
    assert isinstance(template.value, str)
    assert "STDIDENT" in template.value
    assert "PROCESS" in template.value
    assert "STOP" in template.value


def test_default_template_get_params():
    params = FvsKeyfileTemplate.DEFAULT.get_template_params()
    assert isinstance(params, ClassifiedTemplateVariables)
    assert params.required == ["stand_id"]
    for optional in [
        "num_cycles",
        "cycle_length",
        "first_cycle_length",
        "mortality_modifiers",
        "sdimax",
        "econ",
        "growth_modifiers",
        "volume",
        "disturbance",
        "treatment",
    ]:
        assert optional in params.optional


# -------------------------------------------------------
# FvsEventLibrary
# -------------------------------------------------------


@pytest.fixture
def library() -> FvsEventLibrary:
    return FvsEventLibrary()


def test_treatments_non_empty(library):
    treatments = library.treatments
    assert isinstance(treatments, dict)
    assert len(treatments) > 0
    first = next(iter(treatments.values()))
    assert isinstance(first, FvsEvent)


def test_usfs_treatments_subset_of_treatments(library):
    usfs = library.usfs_treatments
    assert isinstance(usfs, dict)
    assert len(usfs) > 0
    assert set(usfs.keys()).issubset(set(library.treatments.keys()))


def test_disturbances_non_empty(library):
    disturbances = library.disturbances
    assert isinstance(disturbances, dict)
    assert len(disturbances) > 0
    first = next(iter(disturbances.values()))
    assert isinstance(first, FvsEvent)


def test_lookup_valid_treatment(library):
    key = next(iter(library.treatments.keys()))
    event = library.lookup(event_type=FvsEventType.TREATMENT, event_key=key)
    assert isinstance(event, FvsEvent)
    assert event.name == key


def test_lookup_valid_disturbance(library):
    key = next(iter(library.disturbances.keys()))
    event = library.lookup(event_type=FvsEventType.DISTURBANCE, event_key=key)
    assert isinstance(event, FvsEvent)
    assert event.name == key


def test_lookup_invalid_treatment_key_raises(library):
    with pytest.raises(IndexError, match="not a recognized treatment"):
        library.lookup(
            event_type=FvsEventType.TREATMENT,
            event_key="NONEXISTENT_KEY_XYZ",
        )


def test_lookup_invalid_disturbance_key_raises(library):
    with pytest.raises(IndexError, match="not a recognized disturbance"):
        library.lookup(
            event_type=FvsEventType.DISTURBANCE,
            event_key="NONEXISTENT_KEY_XYZ",
        )


def test_lookup_invalid_event_type_raises(library):
    with pytest.raises(ValueError, match="not a recognized FvsEventType"):
        library.lookup(event_type="BOGUS", event_key="anything")
