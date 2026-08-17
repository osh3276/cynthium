"""Cooperative cancellation for long-running background computations."""

from __future__ import annotations


class CancelledError(Exception):
	"""Raised when the user cancels a background autopath or simulation.

	The GUI worker thread catches this and emits its ``cancelled`` signal
	instead of treating it as a failure. Engine code checks a shared
	``threading.Event`` in its hot loops and raises this exception as soon
	as the event is set, so the background thread exits promptly.
	"""
