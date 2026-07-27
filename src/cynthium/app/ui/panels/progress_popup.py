from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class ProgressPopup(QDialog):
	"""Non‑modal popup with an indeterminate progress bar."""

	def __init__(self, title: str = "Working...", text: str = "Please wait...", parent=None):
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setModal(False)
		self.setFixedSize(300, 100)

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self._label = QLabel(text)
		self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(self._label)

		bar = QProgressBar()
		bar.setRange(0, 0)  # indeterminate / busy
		bar.setFixedWidth(250)
		layout.addWidget(bar)

	def set_text(self, text: str):
		self._label.setText(text)


class Worker(QObject):
	"""Runs a callable in a background QThread.

	Emits ``finished(result)`` on success or ``failed(error_msg)`` on exception.
	"""

	finished = Signal(object)
	failed = Signal(str)

	def __init__(self, fn, *args, **kwargs):
		super().__init__()
		self._fn = fn
		self._args = args
		self._kwargs = kwargs

	@Slot()
	def run(self):
		try:
			result = self._fn(*self._args, **self._kwargs)
			self.finished.emit(result)
		except Exception:
			self.failed.emit(traceback.format_exc())
