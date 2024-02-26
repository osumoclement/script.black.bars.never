from src.feedback import LoggingService, NotificationService
from src.config.ConfigurationManager import ConfigurationManager

config = ConfigurationManager()
logger = LoggingService()
notification = NotificationService()

config.set_logger(logger)
logger.set_addon_name(config.get_addon_name())
notification.set_addon_name(config.get_addon_name())

