from __future__ import annotations

from jinja2 import Environment, StrictUndefined, UndefinedError, nodes
from pydantic import BaseModel, ConfigDict

from microfvs.exceptions import FvsTemplateRenderError


class ClassifiedTemplateVariables(BaseModel):
    """Classified template variables.

    Attributes:
        required (list[str]): List of required template variables.
        optional (list[str]): List of optional template variables.
    """

    required: list[str]
    optional: list[str]

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        return (
            "Template variables:\n"
            f"  Required: {self.required}\n"
            f"  Optional: {self.optional}"
        )


def classify_template_variables(
    template: str,
) -> ClassifiedTemplateVariables:
    """Classify template variables as required or optional.

    Parses the Jinja2 AST and identifies two patterns that make a
    variable optional:
    - ``{{ var | default(...) }}``
    - ``{% if var is defined %} ... {% endif %}``

    A variable that appears at least once without either guard is
    considered required.

    Args:
        template: Jinja2 template string.

    Returns:
        A tuple of ``(required, optional)`` where each element is a
        sorted list of variable names.
    """
    env = Environment(undefined=StrictUndefined)
    ast = env.parse(template)
    occurrences = _walk_ast(ast)

    all_names: set[str] = set()
    optional_names: set[str] = set()
    required_names: set[str] = set()

    for name, is_optional in occurrences:
        all_names.add(name)
        if is_optional:
            optional_names.add(name)
        else:
            required_names.add(name)

    truly_optional = optional_names - required_names
    return ClassifiedTemplateVariables(
        required=sorted(required_names),
        optional=sorted(truly_optional),
    )


def render_template(template: str, context: dict[str, str]) -> str:
    """Render a Jinja2 template with strict undefined checking.

    Uses ``StrictUndefined`` so that missing required variables
    raise immediately.  When rendering fails, the error includes
    all template variables classified as required vs optional.

    Args:
        template: Jinja2 template string.
        context: Variable names and values to inject.

    Returns:
        The rendered template string.

    Raises:
        FvsTemplateRenderError: if the template references a
            required variable not present in *context*.
    """
    classified = classify_template_variables(template)
    required, optional = classified.required, classified.optional
    provided_keys = set(context.keys())
    missing_required = sorted(set(required) - provided_keys)
    missing_optional = sorted(set(optional) - provided_keys)

    env = Environment(undefined=StrictUndefined)
    try:
        return env.from_string(template).render(**context)
    except UndefinedError as exc:
        raise FvsTemplateRenderError(
            template_variables=sorted(required + optional),
            provided_variables=sorted(provided_keys),
            missing_required=missing_required,
            missing_optional=missing_optional,
        ) from exc


def _walk_ast(
    node: nodes.Node,
    inside_default: bool = False,
    inside_defined_guard: bool = False,
) -> list[tuple[str, bool]]:
    """Recursively walk AST nodes, tracking optional-variable context.

    Returns a list of ``(variable_name, is_optional)`` tuples.
    """
    results: list[tuple[str, bool]] = []

    if isinstance(node, nodes.Filter) and node.name == "default":
        for child in node.iter_child_nodes():
            results.extend(
                _walk_ast(
                    child,
                    inside_default=True,
                    inside_defined_guard=inside_defined_guard,
                )
            )
        return results

    if isinstance(node, nodes.If):
        guarded = _extract_defined_guard_names(node.test)
        for child in node.iter_child_nodes():
            results.extend(
                _walk_ast(
                    child,
                    inside_default=inside_default,
                    inside_defined_guard=inside_defined_guard or bool(guarded),
                )
            )
        return results

    if isinstance(node, nodes.Name):
        results.append((node.name, inside_default or inside_defined_guard))

    for child in node.iter_child_nodes():
        results.extend(_walk_ast(child, inside_default, inside_defined_guard))

    return results


def _extract_defined_guard_names(test_node: nodes.Node) -> set[str]:
    """Extract variable names from ``is defined`` tests."""
    names: set[str] = set()
    if isinstance(test_node, nodes.Test) and test_node.name == "defined":
        if isinstance(test_node.node, nodes.Name):
            names.add(test_node.node.name)
    return names
