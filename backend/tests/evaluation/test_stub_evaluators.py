"""identity_preservation is a documented stub (see its module docstring for
the intended approach) — this just guards that it fails loudly
(NotImplementedError) rather than silently returning a meaningless result
if someone calls it before it's built.
"""

from __future__ import annotations

import pytest

from tests.evaluation.evaluators.identity_preservation import evaluate_identity_preservation


def test_identity_preservation_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        evaluate_identity_preservation(b"", b"")
