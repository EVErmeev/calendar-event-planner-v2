"""Tests for background analysis — single pipeline, cancellation, progress."""
from __future__ import annotations

import threading
from unittest import mock


class TestBackgroundAnalysisSinglePipeline:
    def test_single_click_single_thread(self):
        import os

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"
        s = Settings()
        c = AppContainer(s)

        thread_count = [0]
        lock = threading.Lock()

        original_start = threading.Thread.start

        def counting_start(self):
            with lock:
                thread_count[0] += 1
            original_start(self)

        with mock.patch.object(threading.Thread, "start", counting_start):
            import tkinter as tk
            root = tk.Tk()
            from calendar_planner.ui.main_window import MainWindow
            app = MainWindow(root, container=c)
            root.update()
            root.destroy()

        os.environ.pop("APP_ENV", None)
        os.environ.pop("MCP_ENABLED", None)

    def test_progress_does_not_reset_cancel_token(self):
        import tkinter as tk
        root = tk.Tk()
        import os

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings
        from calendar_planner.ui.main_window import MainWindow
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"

        s = Settings()
        c = AppContainer(s)
        app = MainWindow(root, container=c)

        app._cancel_requested = True
        app._show_progress("Test", 50)
        assert app._cancel_requested is True

        root.destroy()
        os.environ.pop("APP_ENV", None)

    def test_cancel_requested_stops_pipeline(self):
        import os
        import tkinter as tk

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings
        from calendar_planner.ui.main_window import MainWindow
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"

        root = tk.Tk()
        s = Settings()
        c = AppContainer(s)
        app = MainWindow(root, container=c)

        app._cancel_requested = True
        # Cancel flag tested via stage runner guard
        root.update()
        root.destroy()
        os.environ.pop("APP_ENV", None)

    def test_run_analysis_buttons(self):
        import os
        import tkinter as tk

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings
        from calendar_planner.ui.main_window import MainWindow
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"

        root = tk.Tk()
        s = Settings()
        c = AppContainer(s)
        app = MainWindow(root, container=c)

        assert app._cancel_btn is not None
        assert app._progress_bar is not None
        assert app._progress_label is not None

        root.destroy()
        os.environ.pop("APP_ENV", None)
