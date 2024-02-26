import xbmcaddon
import xbmcgui

class ConfigurationManager:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.window = xbmcgui.Window(10000)
        self.logger = None
    
    def set_logger(self, logger):
        self.logger = logger

    def get_addon_name(self):
        return self.addon.getAddonInfo('name')
    
    def get_addon_id(self):
        return self.addon.getAddonInfo('id')
    
    def get_addon_icon(self):
        return self.addon.getAddonInfo('icon')
    
    def clear_property(self, property_id):
        self.window.clearProperty(self.get_addon_name() + "_" + property_id)
    
    def set_property(self, property_id, is_true):
        if is_true:
            self.window.setProperty(self.get_addon_name() + "_" + property_id, "true")
        else:
            self.window.setProperty(self.get_addon_name() + "_" + property_id, "false")
    
    def get_property(self, property_id):
        return self.window.getProperty(self.get_addon_name() + "_" + property_id).lower() in ("true", "yes", "1", "on")

    def get_setting(self, setting_id, value_type):
        setting_value = self.addon.getSetting(setting_id)
        try:
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
        except ValueError as e:
            self.logger.log(f"Error converting setting {setting_id} to {value_type}: {e}")
            return None