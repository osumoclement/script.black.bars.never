import xbmc
from src.imdb.imdbscraper import ImdbScraper
from src.globals import config, logger, notification

class Content():
    def __init__(self):
        self.imdb_scraper = ImdbScraper()
        self.reset_attributes()

    def reset_attributes(self):
        self.multi_ar = False
        self.imdb_ar = None
        self.content_ar = None

    def set_image_and_player(self, image, player):
        self.image = image
        self.player = player

    def _row_color_greater_than(self, row_index, threshold):
        bytesPerRow = self.image.image_width * 4
        totalIntensity = 0

        startIndex = row_index * bytesPerRow

        for i in range(startIndex, min(startIndex + bytesPerRow, len(self.image.image_byte_array)), 4):
            totalIntensity += (self.image.image_byte_array[i] + self.image.image_byte_array[i+1] + self.image.image_byte_array[i+2]) / 3

        avgIntensity = totalIntensity / self.image.image_width
        result = avgIntensity > threshold
        return result
    
    def _col_color_greater_than(self, col_index, threshold):
        bytesPerRow = self.image.image_width * 4
        totalIntensity = 0

        for row in range(self.image.image_height):
            index = (row * bytesPerRow) + (col_index * 4)
            totalIntensity += (self.image.image_byte_array[index] + self.image.image_byte_array[index+1] + self.image.image_byte_array[index+2]) / 3

        avgIntensity = totalIntensity / self.image.image_height
        result = avgIntensity > threshold
        return result
    
    def _find_boundary(self, start, end, step, check_function):
        for i in range(start, end, step):
            if check_function(i):
                return i
        return None
    
    def _calculate_content_image_size(self):
        threshold = 2     # Above this value is "non-black"
        offset = 2        # Offset start pixel to fix green line rendering bug
        bottom, right = self.image.image_height, self.image.image_width

        top = self._find_boundary(offset, self.image.image_height-1, 1, lambda i: self._row_color_greater_than(i, threshold))
        if top > offset:
            bottom = self._find_boundary(self.image.image_height-1-offset, top-1, -1, lambda i: self._row_color_greater_than(i, threshold))
        else:
            top -= offset

        left = self._find_boundary(offset, self.image.image_width-1, 1, lambda j: self._col_color_greater_than(j, threshold))
        if left > offset:
            right = self._find_boundary(self.image.image_width-1-offset, left-1, -1, lambda j: self._col_color_greater_than(j, threshold))
        else:
            left -= offset

        logger.log(f"Top/bottom/left/right: {top},{bottom},{left},{right}", xbmc.LOGINFO)

        content_image_height = bottom - top
        content_image_width = right - left

        return content_image_width, content_image_height
    
    def _get_content_size_from_image(self):
        video_w, video_h = self.player.get_video_size()
        player_width, player_height = self.player.get_video_player_size()
        player_ar = self.player.get_video_player_ar()
        image_height = 480
        image_width = int(image_height*player_ar)
        logger.log(f"Video Resolution: {video_w}x{video_h}, Video Player Aspect Ratio: {player_ar}, Image Dimensions: {image_width}x{image_height}", xbmc.LOGINFO)

        retry_delay = 5
        max_attempts = 36

        for attempt in range(max_attempts):
            self.image.capture_frame(image_width, image_height)

            if self.image.check_for_bright_frame():
                try:
                    content_image_width, content_image_height = self._calculate_content_image_size()
                    break
                except Exception as e:
                    logger.log(f"Error occurred: {e}", xbmc.LOGERROR)
                    return None, None
            else:
                logger.log(f"Frame is too dark. Attempt {attempt+1} of 36. Waiting to retry...", xbmc.LOGINFO)
                if self.player.monitor.waitForAbort(retry_delay):
                    return None, None

        height_scale = content_image_height / image_height
        width_scale = content_image_width / image_width
        content_width = float(player_width) * width_scale
        content_height = float(player_height) * height_scale
        return content_width, content_height
    
    def update_imdb_metadata(self):
        try:
            metadata = self.player.get_video_metadata()
            self.imdb_scraper.setMedia(metadata['title'], metadata['content_type'], metadata['imdb_number'])
            self.imdb_ar = self.imdb_scraper.parse_aspect_ratios()
            self.multi_ar = len(self.imdb_ar) > 1

            if self.multi_ar:
                logger.log(f"Multiple aspect ratios detected from Imdb: {self.imdb_ar}", xbmc.LOGINFO)
                notification.notify("Multiple aspect ratios detected", override=True)
        except Exception as e:
            logger.log(f"Error occurred: {e}", xbmc.LOGERROR)
            return
    
    def _get_content_size_from_data(self):
        content_ar = self.imdb_ar
        player_width, player_height = self.player.get_video_player_size()
        player_ar = self.player.get_video_player_ar()

        if self.multi_ar:
            content_width = player_width
            content_height = player_height
        else:
            content_ar = content_ar[0]
            logger.log(f"Content aspect ratio from Imdb: {content_ar}", xbmc.LOGINFO)

            if content_ar > player_ar:
                # Filled width, content width = player width
                content_width = player_width
                content_height = content_width / content_ar
            else:
                # Filled height, content height = player height
                content_height = player_height
                content_width = content_height * content_ar
        return content_width, content_height
    
    def get_content_ar(self):
        if self.content_ar is None:
            self.get_content_size()
        return self.content_ar
    
    def get_content_size(self):
        content_width, content_height = None, None

        if config.get_setting("android_workaround", bool):
            content_width, content_height = self._get_content_size_from_data()
        
        if content_width is None or content_height is None:
            content_width, content_height = self._get_content_size_from_image()

        if content_width is not None or content_height is not None:
            self.content_ar = content_width / content_height

        return content_width, content_height
