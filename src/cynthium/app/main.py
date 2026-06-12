import argparse
import os
import sys

from cynthium import __version__


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
	"""Parse CLI arguments before app imports so flags can influence early setup."""
	parser = argparse.ArgumentParser(
		prog="cynthium",
		description="Lunar rover traversal planning and terrain analysis.",
	)
	parser.add_argument(
		"--version",
		action="version",
		version=f"cynthium {__version__}",
		help="show version and exit",
	)
	parser.add_argument(
		"-v", "--verbose",
		action="store_true",
		help="enable verbose (INFO) logging",
	)
	parser.add_argument(
		"--debug",
		action="store_true",
		help="enable debug logging (implies --verbose)",
	)
	parser.add_argument(
		"--data-dir",
		type=str,
		default=None,
		help="override the data directory (default: ./data or XDG cache)",
	)
	# parse_known_args so unknown args (e.g. Qt's own) don't blow up
	parsed, _ = parser.parse_known_args(argv)
	return parsed


def _set_default_opengl_format():
	"""Set a stable OpenGL format for VTK before QApplication is created."""
	from PySide6.QtCore import QCoreApplication, Qt
	from PySide6.QtGui import QSurfaceFormat

	QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
	QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)

	fmt = QSurfaceFormat()
	fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
	fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
	fmt.setVersion(3, 2)
	fmt.setDepthBufferSize(24)
	fmt.setStencilBufferSize(8)
	fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
	fmt.setSwapInterval(1)
	QSurfaceFormat.setDefaultFormat(fmt)


def main():
	# --- 1. Parse CLI before any app imports (some flags affect module-level config) ---
	args = _parse_args()

	# --data-dir: inject env var *before* anything imports config.py
	if args.data_dir:
		os.environ["CYNTHIUM_DATA_DIR"] = args.data_dir

	# --verbose / --debug: configure root logger early
	if args.debug or args.verbose:
		import logging
		level = logging.DEBUG if args.debug else logging.INFO
		logging.basicConfig(level=level, force=False)

	# --debug also tweaks the module-level DEBUG flag in config
	if args.debug:
		import cynthium.app.config as _cfg
		_cfg.DEBUG = True

	# --- 2. Normal app startup ---
	_set_default_opengl_format()

	from PySide6.QtWidgets import QApplication

	from cynthium.app.window import Window

	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
