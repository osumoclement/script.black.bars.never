import xbmc
from src.globals import logger, config, notification

class ZoomService():
    def __init__(self):
        pass

    def set_content_and_player(self, content, player):
        self.content = content
        self.player = player

    def start_service(self):
        # Check if the processing flag is set to avoid re-entry
        if config.get_property("processing"):
            return
        
        config.set_property("processing", True)
        config.set_property("status", True)

        # Fetch IMDb metadata if multi-aspect ratios support is enabled or Android workaround is active
        if config.get_setting("multi_aspect_ratios_support", bool) or config.get_setting("android_workaround", bool):
            self.content.update_imdb_metadata()

        self.auto_refresh_status = self.content.multi_ar and not config.get_setting("android_workaround", bool)

        if self.auto_refresh_status:
            self.auto_refresh_zoom()
        else:
            self.execute_zoom()

        config.clear_property("processing")

    def auto_refresh_zoom(self):
        refresh_interval = config.get_setting("refresh_interval", int)

        while not self.player.monitor.abortRequested() and self.player.isPlayingVideo() and self.auto_refresh_status:
            self.execute_zoom()
            logger.off()
            if self.player.monitor.waitForAbort(refresh_interval):
                break

    def execute_zoom(self):
        zoom_amount = self._calculate_zoom()

        if zoom_amount is None:
            logger.log("Unable to calculate zoom", xbmc.LOGERROR)
            notification.notify("Unable to calculate zoom", override=True)
            return
        
        # Execute the zoom via JSON-RPC
        xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}'
            )
        
        if not self.auto_refresh_status:
            if zoom_amount > 1.0:
                notification.notify(f"Adjusted zoom to {zoom_amount}")

    def off_zoom(self):
        self.auto_refresh_status = False

        while config.get_property("processing"):
            if self.player.monitor.waitForAbort(2):
                return

        if not config.get_property("processing"):
            config.set_property("processing", True)
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0' + ' }}, "id": 1}'
            )
            config.set_property("status", False)
            notification.notify("Showing original aspect ratio", override=True)
            config.clear_property("processing")

    def toggle_zoom(self):
        status = config.get_property("status")

        if not self.player.isPlayingVideo():
            notification.notify("No video playing.", override=True)
            return
        
        if status:
            self.off_zoom()
        else:
            self.start_service()

    def _calculate_zoom(self):
        content_width, content_height = self.content.get_content_size()

        if content_width is None or content_height is None:
            return None
        
        content_ar = self.content.get_content_ar()
        logger.log(f"Content Dimension: {content_width:.2f}x{content_height:.2f}, Content Aspect Ratio: {content_ar:.2f}:1", level=xbmc.LOGINFO)

        monitor_width, monitor_height = self.player.get_monitor_size()
        monitor_ar = self.player.get_monitor_ar()
        logger.log(f"Monitor Size: {monitor_width}x{monitor_height}", level=xbmc.LOGINFO)

        if content_ar < monitor_ar:
            # Fill to height
            zoom_amount = round(float(monitor_height) / content_height, 2)
        else:
            # Fill to width
            zoom_amount = round(float(monitor_width) / content_width, 2)

        logger.log(f"Zoom amount: {zoom_amount}", level=xbmc.LOGINFO)
        return zoom_amount