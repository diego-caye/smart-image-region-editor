from app.application.dto.edit_progress import EditProgress, EditStage
from app.infrastructure.progress.in_memory_edit_progress_tracker import InMemoryEditProgressTracker


def test_returns_the_latest_report_per_id():
    tracker = InMemoryEditProgressTracker()
    tracker.report("a", EditProgress.at(EditStage.SEGMENTING))
    tracker.report("a", EditProgress.at(EditStage.DONE))
    tracker.report("b", EditProgress.at(EditStage.LOADING_MODEL))

    assert tracker.get("a").stage is EditStage.DONE
    assert tracker.get("b").stage is EditStage.LOADING_MODEL
    assert tracker.get("unknown") is None


def test_keeps_only_the_most_recent_ids():
    tracker = InMemoryEditProgressTracker(max_entries=2)
    for progress_id in ("a", "b", "c"):
        tracker.report(progress_id, EditProgress.at(EditStage.DONE))

    assert tracker.get("a") is None
    assert tracker.get("c") is not None
