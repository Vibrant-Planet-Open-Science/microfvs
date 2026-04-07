from __future__ import annotations


class FvsTemplateRenderError(Exception):
    """Raised when a template cannot be rendered.

    This currently handles errors due to missing variables.

    Attributes:
        template_variables: Sorted list of all variables
            referenced by the template.
        provided_variables: Sorted list of variable names that
            were available to the template at render time.
        missing_required: Sorted list of required template
            variables that were not provided.
        missing_optional: Sorted list of optional template
            variables (those with ``| default()`` or
            ``is defined`` guards) that were not provided.
    """

    def __init__(
        self,
        message: str,
        template_variables: list[str],
        provided_variables: list[str],
        missing_required: list[str],
        missing_optional: list[str],
    ):
        self.template_variables = template_variables
        self.provided_variables = provided_variables
        self.missing_required = missing_required
        self.missing_optional = missing_optional
        super().__init__(message)
