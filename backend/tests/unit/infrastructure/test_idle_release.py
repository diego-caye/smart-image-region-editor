import threading

from app.infrastructure.idle_release import IdleReleaser


def test_releases_once_after_the_idle_period():
    released = threading.Event()
    releaser = IdleReleaser(0.05, released.set, name="test")
    releaser.touch()
    assert released.wait(timeout=2)


def test_each_touch_restarts_the_wait():
    calls = []
    releaser = IdleReleaser(0.3, lambda: calls.append(1), name="test")
    releaser.touch()
    threading.Event().wait(0.2)
    releaser.touch()  # still in use -> must not release at the first deadline
    threading.Event().wait(0.2)
    assert calls == []
    threading.Event().wait(0.3)
    assert calls == [1]


def test_zero_means_release_right_after_each_use():
    calls = []
    IdleReleaser(0, lambda: calls.append(1), name="test").touch()
    assert calls == [1]


def test_a_failing_release_does_not_raise():
    def boom():
        raise RuntimeError("server unreachable")

    IdleReleaser(0, boom, name="test").touch()  # logged, not raised


def test_flush_releases_a_pending_release_right_away_and_only_once():
    calls = []
    releaser = IdleReleaser(60, lambda: calls.append(1), name="test")
    releaser.touch()
    releaser.flush()
    releaser.flush()
    assert calls == [1]


def test_flush_does_nothing_once_the_release_already_ran():
    released = threading.Event()
    calls = []

    def release():
        calls.append(1)
        released.set()

    releaser = IdleReleaser(0.05, release, name="test")
    releaser.touch()
    assert released.wait(timeout=2)
    releaser.flush()
    assert calls == [1]
