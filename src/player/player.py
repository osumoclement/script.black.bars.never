import json
import xbmc
from src.core import core

class Player(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.onAVStarted_callbacks = []
        self.reset_attributes()

    def reset_attributes(self):
        self.monitor_ar = None

    def set_onAVStarted_callback(self, callback):
        self.onAVStarted_callbacks.append(callback)

    def onAVStarted(self):
        for callback in self.onAVStarted_callbacks:
            callback()

    def get_video_size(self):
        video_w_str = xbmc.getInfoLabel('Player.Process(videowidth)')
        video_h_str = xbmc.getInfoLabel('Player.Process(videoheight)')
        video_w = int(video_w_str.replace(",", ""))
        video_h = int(video_h_str.replace(",", ""))
        return video_w, video_h

    def get_monitor_ar(self):
        if self.monitor_ar is None:
            self.get_monitor_size()
        return self.monitor_ar
    
    def get_monitor_size(self):
        width = int(xbmc.getInfoLabel('System.ScreenWidth'))
        height = int(xbmc.getInfoLabel('System.ScreenHeight'))

        if width is None or height is None:
            core.logger.log("Unable to get Monitor Size.", xbmc.LOGERROR)
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

            core.logger.log(f"Video Player Dimensions: {video_player_width}x{video_player_height}", level=xbmc.LOGINFO)
            return video_player_width, video_player_height
        else:
            core.logger.log(f"No video is currently playing.", level=xbmc.LOGINFO)
        return None, None
    
    def get_video_metadata(self):
        if self.isPlayingVideo():
            title = xbmc.getInfoLabel('VideoPlayer.Title') or None
            show_title = xbmc.getInfoLabel('VideoPlayer.TVshowtitle') or None  # Show name
            original_title = xbmc.getInfoLabel('VideoPlayer.OriginalTitle')
            tv_show_title = show_title  # Using the fetched show title
            imdb_number = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or None
            
            # Adjust content_type based on the presence of original title or TV show title
            content_type = 'tt' if original_title and not tv_show_title else 'ep' if tv_show_title else None
            
            season_label = xbmc.getInfoLabel('VideoPlayer.Season')
            episode_label = xbmc.getInfoLabel('VideoPlayer.Episode')
            
            # Safely convert season and episode labels to integers
            season = int(season_label) if season_label.isdigit() else None
            episode = int(episode_label) if episode_label.isdigit() else None

            if season is not None and episode is not None:
                content_type = 'ep'

            metadata = {
                'title': title,
                'show_title': show_title,  # Include show title in metadata
                'episode_title': title if tv_show_title else None,  # Episode name, if applicable
                'content_type': content_type,
                'imdb_number': imdb_number,
                'season': season,
                'episode': episode
            }
            
            core.logger.log(json.dumps(metadata, indent=4), xbmc.LOGINFO)
            return metadata
        else:
            core.logger.log("No video is currently playing", xbmc.LOGERROR)
            return None