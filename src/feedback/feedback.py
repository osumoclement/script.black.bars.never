import xbmc
import xbmcgui

class LoggingService():
    def __init__(self):
        self.addon_name = None
        self.status = True

    def set_addon_name(self, addon_name):
        self.addon_name = addon_name

    def on(self):
        self.status = True

    def off(self):
        self.status = False

    def get_status(self):
        return self.status

    def log(self, msg, level=xbmc.LOGINFO):
        if self.addon_name is None:
            raise ValueError("Addon name has not been set.")
        
        if self.get_status():
            xbmc.log(f"{self.addon_name}: {msg}", level=level)

class NotificationService():
    def __init__(self):
        self.addon_name = None
        self.status = True

    def set_addon_name(self, addon_name):
        self.addon_name = addon_name

    def on(self):
        self.status = False

    def off(self):
        self.status = True

    def get_status(self):
        return self.status

    def notify(self, msg, override=False):
        if self.addon_name is None:
            raise ValueError("Addon name has not been set.")
        
        if self.get_status() or override:
            xbmcgui.Dialog().notification(self.addon_name, msg, None, 1000)