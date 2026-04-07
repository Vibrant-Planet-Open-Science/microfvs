from __future__ import annotations


class FvsTemplateRenderError(Exception):
    """Raised when a template cannot be rendered.

    This currently handles errors due to missing variables.

    Attributes:
        template_variables: Sorted list of all variables
            referenced by the template.
        provided_variables: Sorted list of variable names that
            were available to the template at render time.
        missing_variables: Sorted list of template variables that
            were referenced but not provided.
    """

    def __init__(
        self,
        message: str,
        template_variables: list[str],
        provided_variables: list[str],
        missing_variables: list[str],
    ):
        self.template_variables = template_variables
        self.provided_variables = provided_variables
        self.missing_variables = missing_variables
        super().__init__(message)
