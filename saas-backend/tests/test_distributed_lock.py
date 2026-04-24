"""Tests for the distributed lock mechanism."""

from unittest.mock import MagicMock, patch

from app.core.distributed_lock import with_distributed_lock


class TestWithDistributedLock:
    def setup_method(self):
        # Reset the module-level state
        import app.core.distributed_lock as dl_mod
        dl_mod._redis_client = None
        dl_mod._redis_checked = False

    def test_runs_without_redis(self):
        """When Redis is unavailable, job runs normally."""
        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "ok"

        with patch("app.core.distributed_lock.settings") as mock_settings:
            mock_settings.redis_url = ""
            import app.core.distributed_lock as dl_mod
            dl_mod._redis_checked = False
            result = my_job()

        assert result == "ok"
        assert call_log == ["ran"]

    def test_acquires_lock_and_runs(self):
        """When lock is acquired, job runs and lock is released."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # Lock acquired
        mock_redis.eval.return_value = 1  # Lock released

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "result"

        with patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result == "result"
        assert call_log == ["ran"]
        mock_redis.set.assert_called_once()
        mock_redis.eval.assert_called_once()

    def test_skips_when_lock_held(self):
        """When lock is already held, job is skipped."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = False  # Lock NOT acquired

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")

        with patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result is None
        assert call_log == []

    def test_skips_on_redis_error_during_acquire(self):
        """On Redis error during acquire, job is skipped to avoid duplicate side effects."""
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Redis down")

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "ok"

        with patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result is None
        assert call_log == []

    def test_skips_when_configured_redis_unavailable(self):
        """When REDIS_URL is configured but unavailable, fail closed."""
        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "ok"

        with (
            patch("app.core.distributed_lock._get_redis", return_value=None),
            patch("app.core.distributed_lock.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            result = my_job()

        assert result is None
        assert call_log == []

    def test_handles_release_failure(self):
        """If releasing the lock fails, job still completes."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_redis.eval.side_effect = Exception("Redis down during release")

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            return "ok"

        with patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result == "ok"

    def test_preserves_function_metadata(self):
        @with_distributed_lock("test_job")
        def my_named_job():
            """My docstring."""
            pass

        assert my_named_job.__name__ == "my_named_job"
        assert my_named_job.__doc__ == "My docstring."
