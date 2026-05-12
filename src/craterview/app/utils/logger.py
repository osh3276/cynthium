import logging

from craterview.app.config import DEBUG


def get_logger(name: str) -> logging.Logger:
	logger = logging.getLogger(name)

	if not logger.handlers:
		handler = logging.StreamHandler()
		formatter = logging.Formatter(
			"%(asctime)s [%(levelname)s] %(name)s: %(message)s"
		)
		handler.setFormatter(formatter)
		logger.addHandler(handler)

	logger.setLevel(logging.DEBUG if DEBUG else logging.CRITICAL + 1)
	logger.disabled = not DEBUG

	return logger
