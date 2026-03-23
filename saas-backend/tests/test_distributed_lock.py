"""Tests for the distributed lock mechanism."""

from unittest.mock import MagicMock, patch

from app.core.distributed_lock import with_distributed_lock


class TestWithDistributedLock:
    def setup_method(self):
        # Reset the module-level state
        import app.core.distributed_lock as dl_mod
        dl_mod._redis_client = None
        dl_mod._redis_checked = False

    def test_runs_without_redis(self, caplog):
        """When Redis is unavailable, job runs normally."""
        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "ok"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock.settings") as mock_settings:
            mock_settings.redis_url = ""
            import app.core.distributed_lock as dl_mod
            dl_mod._redis_checked = False
            result = my_job()

        assert result == "ok"
        assert call_log == ["ran"]
        assert any(
            getattr(record, "extra_fields", {}).get("event") == "lock_unavailable"
            for record in caplog.records
        )
        assert any(
            getattr(record, "extra_fields", {}).get("fail_open") is True
            for record in caplog.records
            if hasattr(record, "extra_fields")
        )

    def test_acquires_lock_and_runs(self, caplog):
        """When lock is acquired, job runs and lock is released."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # Lock acquired
        mock_redis.eval.return_value = 1  # Lock released

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "result"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result == "result"
        assert call_log == ["ran"]
        mock_redis.set.assert_called_once()
        mock_redis.eval.assert_called_once()
        assert any(
            getattr(record, "extra_fields", {}).get("event") == "lock_acquired"
            for record in caplog.records
        )

    def test_skips_when_lock_held(self, caplog):
        """When lock is already held, job is skipped."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = False  # Lock NOT acquired

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")

        with caplog.at_level("INFO"), patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result is None
        assert call_log == []
        assert any(
            getattr(record, "extra_fields", {}).get("event") == "job_skipped_lock"
            for record in caplog.records
        )

    def test_runs_on_redis_error_during_acquire(self, caplog):
        """On Redis error during acquire, job runs anyway (fail-open)."""
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Redis down")

        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job():
            call_log.append("ran")
            return "ok"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result == "ok"
        assert call_log == ["ran"]
        assert any(
            getattr(record, "extra_fields", {}).get("event") == "lock_acquire_failed"
            for record in caplog.records
        )

    def test_skips_without_redis_when_fail_closed(self, caplog):
        call_log = []

        @with_distributed_lock("critical_job", ttl_seconds=10, fail_open=False)
        def my_job():
            call_log.append("ran")
            return "ok"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock.settings") as mock_settings:
            mock_settings.redis_url = ""
            import app.core.distributed_lock as dl_mod
            dl_mod._redis_checked = False
            result = my_job()

        assert result is None
        assert call_log == []
        skipped = [
            record for record in caplog.records
            if getattr(record, "extra_fields", {}).get("event") == "job_skipped_lock_unavailable"
        ]
        assert skipped
        assert skipped[0].extra_fields["fail_open"] is False

    def test_skips_on_redis_error_during_acquire_when_fail_closed(self, caplog):
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Redis down")
        call_log = []

        @with_distributed_lock("critical_job", ttl_seconds=10, fail_open=False)
        def my_job():
            call_log.append("ran")
            return "ok"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock._get_redis", return_value=mock_redis):
            result = my_job()

        assert result is None
        assert call_log == []
        events = [getattr(record, "extra_fields", {}).get("event") for record in caplog.records]
        assert "lock_acquire_failed" in events
        assert "job_skipped_lock_unavailable" in events

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

    def test_second_execution_is_skipped_while_first_holds_lock(self, caplog):
        class FakeRedis:
            def __init__(self):
                self._locks = {}

            def set(self, key, value, nx=True, ex=None):
                if key in self._locks:
                    return False
                self._locks[key] = value
                return True

            def eval(self, script, numkeys, key, value):
                if self._locks.get(key) == value:
                    self._locks.pop(key, None)
                    return 1
                return 0

        fake_redis = FakeRedis()
        call_log = []

        @with_distributed_lock("test_job", ttl_seconds=10)
        def my_job(reentered=False):
            call_log.append("ran")
            if not reentered:
                nested_result = my_job(True)
                assert nested_result is None
            return "outer"

        with caplog.at_level("INFO"), patch("app.core.distributed_lock._get_redis", return_value=fake_redis):
            result = my_job()

        assert result == "outer"
        assert call_log == ["ran"]
        assert any(
            getattr(record, "extra_fields", {}).get("event") == "job_skipped_lock"
            for record in caplog.records
        )

    def test_critical_scheduler_job_does_not_run_without_lock_backend(self):
        from app.background_jobs.jobs import daily_automations_job

        with patch("app.background_jobs.jobs.settings.scheduler_critical_lock_fail_open", False), patch(
            "app.core.distributed_lock._get_redis", return_value=None
        ), patch("app.background_jobs.jobs.SessionLocal") as session_local, patch(
            "app.background_jobs.jobs.run_automation_rules"
        ) as run_automation_rules:
            result = daily_automations_job()

        assert result is None
        session_local.assert_not_called()
        run_automation_rules.assert_not_called()
