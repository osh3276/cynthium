import logging

from cynthium.app.config import DEBUG


class ColorFormatter(logging.Formatter):
	BLUE = "\033[94m"
	RESET = "\033[0m"

	def format(self, record):
		format_orig = self._style._fmt
		if record.levelno == logging.INFO:
			self._style._fmt = f"{self.BLUE}{format_orig}{self.RESET}"
		
		result = super().format(record)
		self._style._fmt = format_orig
		return result


def get_logger(name: str) -> logging.Logger:
	logger = logging.getLogger(name)

	if not logger.handlers:
		handler = logging.StreamHandler()
		formatter = ColorFormatter(
			"%(asctime)s [%(levelname)s] %(name)s: %(message)s"
		)
		handler.setFormatter(formatter)
		logger.addHandler(handler)

	logger.setLevel(logging.DEBUG if DEBUG else logging.CRITICAL + 1)
	logger.disabled = not DEBUG

	return logger
