import xbmc
from src.scraper import imdb_scraper
from src.content.metadata import OnlineMetadataService
from src.core import core
from src.player import Player
from src.content.image import RenderImage, ImageAnalysisService

class ContentManager:
    def __init__(self, player: Player):
        self.player = player
        self.image = RenderImage()
        self.image_analysis = ImageAnalysisService(self.image)
        self.online_metadata_service = OnlineMetadataService(imdb_scraper)
        self.reset_attributes()

    def reset_attributes(self):
        self.content_ars = None
        self.content_ar = None
        self.multi_ar = False
        self.online_metadata = None

    def fetch_online_metadata(self):
        self.online_metadata = self.online_metadata_service.scrape_metadata(self.player.get_video_metadata())

        if self.online_metadata is None:
            return
        
        self.content_ars = self.online_metadata["aspect_ratios"]
        self.multi_ar = len(self.content_ars) > 1

    def get_content_ar(self):
        if self.content_ar is None:
            self.get_content_size()
        return self.content_ar

    def _get_content_size_from_image(self):
        video_w, video_h = self.player.get_video_size()
        player_width, player_height = self.player.get_video_player_size()
        player_ar = self.player.get_video_player_ar()
        image_height = 480 * core.addon.get_setting("sample_resolution", float)
        image_width = int(image_height*player_ar)
        core.logger.log(f"Video Resolution: {video_w}x{video_h}, Video Player Aspect Ratio: {player_ar}, Image Dimensions: {image_width}x{image_height}", xbmc.LOGINFO)

        retry_delay = 5
        max_attempts = 36

        for attempt in range(max_attempts):
            self.image.capture_frame(image_width, image_height)

            if self.image_analysis.check_for_bright_frame():
                try:
                    content_image_width, content_image_height = self.image_analysis.calculate_content_image_size()
                    break
                except Exception as e:
                    core.logger.log(f"Error occurred: {e}", xbmc.LOGERROR)
                    return None, None
            else:
                core.logger.log(f"Frame is too dark. Attempt {attempt+1} of 36. Waiting to retry...", xbmc.LOGINFO)
                if core.monitor.waitForAbort(retry_delay):
                    return None, None

        height_scale = content_image_height / image_height
        width_scale = content_image_width / image_width
        content_width = float(player_width) * width_scale
        content_height = float(player_height) * height_scale
        return content_width, content_height

    def _get_content_size_from_data(self):
        player_width, player_height = self.player.get_video_player_size()
        player_ar = self.player.get_video_player_ar()

        if self.content_ars is None:
            core.logger.log("Unable to get aspect ratios online.", xbmc.LOGERROR)
            return None, None
        
        if self.multi_ar:
            content_width = player_width
            content_height = player_height
        else:
            self.content_ar = self.content_ars[0]
            core.logger.log(f"Content aspect ratio from Imdb: {self.content_ar}", xbmc.LOGINFO)

            if self.content_ar > player_ar:
                # Filled width, content width = player width
                content_width = player_width
                content_height = content_width / self.content_ar
            else:
                # Filled height, content height = player height
                content_height = player_height
                content_width = content_height * self.content_ar
        return content_width, content_height

    def get_content_size(self):
        content_width, content_height = None, None

        if core.addon.get_setting("android_workaround", bool):
            content_width, content_height = self._get_content_size_from_data()
        
        if content_width is None or content_height is None:
            content_width, content_height = self._get_content_size_from_image()
            try:
                self.content_ar = content_width / content_height
            except Exception as e:
                core.logger.log(e, xbmc.LOGERROR)
                return None, None

        return content_width, content_height
