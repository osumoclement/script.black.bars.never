import json
import xbmc
from src.globals import logger, config

class Player(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.monitor = xbmc.Monitor()

    def onAVStarted(self):
        logger.on()
        self.reset_attributes()

        if config.get_setting("automatically_execute", bool):
            self.zoom_service.start_service()

    def set_services(self, content, zoom_service):
        self.content = content
        self.zoom_service = zoom_service

    def reset_attributes(self):
        self.monitor_ar = None
        self.content.reset_attributes()

    def get_monitor_ar(self):
        if self.monitor_ar is None:
            self.get_monitor_size()
        return self.monitor_ar
    
    def get_monitor_size(self):
        width = int(xbmc.getInfoLabel('System.ScreenWidth'))
        height = int(xbmc.getInfoLabel('System.ScreenHeight'))

        if width is None or height is None:
            logger.log("Unable to get Monitor Size.", xbmc.LOGERROR)
            return None, None
        self.monitor_ar = width/ height
        return width, height
    
    def get_video_player_ar(self):
        return float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))

    def get_video_player_size(self):
        if self.isPlayingVideo():
            monitor_width, monitor_height = self.get_monitor_size()
            monitor_ar = monitor_width / monitor_height

            video_player_width, video_player_height = monitor_width, monitor_height
            video_player_ar = self.get_video_player_ar()

            if monitor_ar > video_player_ar:
                video_player_width = int(float(video_player_height) * video_player_ar)
            else:
                video_player_height = int(float(video_player_width) / video_player_ar)

            logger.log(f"Video Player Dimensions: {video_player_width}x{video_player_height}", level=xbmc.LOGINFO)
            return video_player_width, video_player_height
        else:
            logger.log(f"No video is currently playing.", level=xbmc.LOGINFO)
        return None, None
    
    def get_video_size(self):
        video_w_str = xbmc.getInfoLabel('Player.Process(videowidth)')
        video_h_str = xbmc.getInfoLabel('Player.Process(videoheight)')
        video_w = int(video_w_str.replace(",", ""))
        video_h = int(video_h_str.replace(",", ""))
        return video_w, video_h
    
    def get_video_metadata(self):
        if self.isPlayingVideo():
            title = xbmc.getInfoLabel('VideoPlayer.Title') or None
            content_type = 'tt' if xbmc.getInfoLabel('VideoPlayer.OriginalTitle') else 'ep' if xbmc.getInfoLabel('VideoPlayer.TVshowtitle') else None
            imdb_number = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or None
            season = xbmc.getInfoLabel('VideoPlayer.Season') or None
            episode = xbmc.getInfoLabel('VideoPlayer.Episode') or None

            metadata = {
                'title': title,
                'content_type': content_type,
                'imdb_number': imdb_number,
                'season': season,
                'episode': episode
            }
            logger.log(json.dumps(metadata, indent=4), xbmc.LOGINFO)
            return metadata
        else:
            logger.log("No video is currently playing", xbmc.LOGERROR)
            return None
