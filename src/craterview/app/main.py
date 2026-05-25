import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from craterview.app.window import Window


def _set_default_opengl_format():
	"""Set a stable OpenGL format for VTK before QApplication is created."""
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
	"""
	Runs the application entry point.

	:return: None
	"""
	_set_default_opengl_format()
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
