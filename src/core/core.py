import xbmc
import xbmcgui
import xbmcaddon


class CoreServices:
    def __init__(self):
        self.addon = AddonManager(xbmcaddon.Addon())
        self.window = WindowManager(xbmcgui.Window(10000), self.addon)
        self.notification = NotificationManager(self.addon)
        self.logger = LogManager(self.addon)
        self.monitor = xbmc.Monitor()


class AddonManager:
    def __init__(self, addon):
        self.addon = addon

    @property
    def addon_name(self):
        return self.addon.getAddonInfo('name')
    
    @property
    def addon_icon(self):
        return self.addon.getAddonInfo('icon')
    
    @property
    def addon_id(self):
        return self.addon.getAddonInfo('id')
    
    def get_setting(self, setting_id, value_type):
        setting_value = self.addon.getSetting(setting_id)

        if value_type == bool:
            # Kodi stores booleans as 'true' or 'false' strings.
            return setting_value.lower() in ("true", "yes", "1", "on")
        elif value_type == int:
            return int(setting_value)
        elif value_type == float:
            return float(setting_value)
        else:
            # Return as string by default
            return setting_value
        

class WindowManager:
    def __init__(self, window, addon: AddonManager):
        self.window = window
        self.__addon = addon

    def clear_property(self, property_id):
        self.window.clearProperty(self.__addon.addon_name + "_" + property_id)
    
    def set_property(self, property_id, is_true):
        if is_true:
            self.window.setProperty(self.__addon.addon_name + "_" + property_id, "true")
        else:
            self.window.setProperty(self.__addon.addon_name + "_" + property_id, "false")

    def get_property(self, property_id):
        return self.window.getProperty(self.__addon.addon_name + "_" + property_id).lower() in ("true", "yes", "1", "on")
    

class NotificationManager:
    def __init__(self, addon: AddonManager):
        self.__addon = addon
        self.status = True

    def on(self):
        self.status = True

    def off(self):
        self.status = False

    def notify(self, msg, override=False):
        self.notification_status = self.__addon.get_setting("show_notification", bool)

        if (self.notification_status or override) and self.status:
            xbmcgui.Dialog().notification(self.__addon.addon_name, msg, self.__addon.addon_icon, 1000)


class LogManager:
    def __init__(self, addon: AddonManager):
        self.__addon = addon
        self.logging_status = True

    def on(self):
        self.logging_status = True

    def off(self):
        self.logging_status = False
    
    def log(self, msg, level=xbmc.LOGINFO):
        if self.logging_status:
            xbmc.log(f"{self.__addon.addon_name}: {msg}", level=level)
