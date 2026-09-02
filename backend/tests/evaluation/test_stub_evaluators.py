"""edit_quality and identity_preservation are documented stubs (see their
module docstrings for the intended approach) — this just guards that they
fail loudly (NotImplementedError) rather than silently returning a
meaningless result if someone calls them before they're built.
"""

from __future__ import annotations

import pytest

from tests.evaluation.evaluators.edit_quality import evaluate_edit_quality
from tests.evaluation.evaluators.identity_preservation import evaluate_identity_preservation


def test_edit_quality_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        evaluate_edit_quality(b"", "some prompt")


def test_identity_preservation_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        evaluate_identity_preservation(b"", b"")
