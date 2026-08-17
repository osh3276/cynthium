from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
	QDialog,
	QLabel,
	QProgressBar,
	QPushButton,
	QVBoxLayout,
)

from cynthium.app.utils.cancellation import CancelledError


class ProgressPopup(QDialog):
	"""Non-modal popup with an indeterminate progress bar and a Cancel button.

	Closing the popup (X button, Esc, or the Cancel button) emits ``cancelled``
	once, so the caller can stop the background worker. Call :meth:`finish`
	before closing after a normal completion to suppress the cancel signal.
	"""

	cancelled = Signal()

	def __init__(self, title: str = "Working...", text: str = "Please wait...", parent=None):
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setModal(False)
		self.setFixedSize(300, 140)

		self._cancel_emitted = False

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self._label = QLabel(text)
		self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(self._label)

		bar = QProgressBar()
		bar.setRange(0, 0)  # indeterminate / busy
		bar.setFixedWidth(250)
		layout.addWidget(bar)

		self._cancel_button = QPushButton("Cancel")
		self._cancel_button.setFixedWidth(100)
		self._cancel_button.clicked.connect(self.reject)
		layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

	def set_text(self, text: str):
		self._label.setText(text)

	def finish(self):
		"""Mark the work as finished so closing does not emit ``cancelled``."""
		self._cancel_emitted = True

	def done(self, result: int):
		"""Any dismissal while work is still running counts as a cancel request."""
		if not self._cancel_emitted:
			self._cancel_emitted = True
			self.cancelled.emit()
		super().done(result)


class Worker(QObject):
	"""Runs a callable in a background QThread.

	Pass a shared ``threading.Event`` as a ``cancel_event`` keyword argument to
	the wrapped callable; engine code checks it in its hot loops and raises
	:class:`CancelledError`, which is caught here and reported through the
	``cancelled`` signal instead of ``failed``.
	"""

	finished = Signal(object)
	failed = Signal(str)
	cancelled = Signal()

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
		except CancelledError:
			self.cancelled.emit()
		except Exception:
			self.failed.emit(traceback.format_exc())
