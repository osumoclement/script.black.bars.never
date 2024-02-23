import sys
import json
import xbmc
import xbmcaddon
import xbmcgui
from imdb_scraper import ImdbScraper

def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)

class Player(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._initialized = True
        self.monitor = xbmc.Monitor()
        self.capture = xbmc.RenderCapture()

        if "toggle" in sys.argv:
            self.toggleZoomAdjustment()

    def onAVStarted(self):
        self.multi_ar = False
        self.imdb_data = None
        self.imdb_ar = None
        self.enter_recalc_loop = False
        self.logging_status = True

        if xbmcaddon.Addon().getSetting("automatically_execute") == "true":
            self.abolishBlackBars()

    def log(self, msg, level=xbmc.LOGINFO):
        if self.logging_status:
            xbmc.log("Black Bars Never: " + msg, level=level)

    def CaptureFrame(self, capture_width, capture_height):
        self.capture.capture(capture_width, capture_height)
        capturedImage = self.capture.getImage(2000)
        return capturedImage

    def calculateAverageBrightness(self, img_data, image_width, image_height):
        total_brightness = 0
        for i in range(0, len(img_data), 4):  # Step through each pixel
            # Calculate brightness of each pixel, weighting coefficients of luminosity
            brightness = 0.299*img_data[i+2] + 0.587*img_data[i+1] + 0.114*img_data[i]
            total_brightness += brightness
        average_brightness = total_brightness / (image_width * image_height)
        return average_brightness
    
    def checkForBrightFrame(self, image_data, image_width, image_height):
        brightness_threshold = 32.0
        avg_brightness = self.calculateAverageBrightness(image_data, image_width, image_height)
        self.log(f"Average Brightness: {avg_brightness}", xbmc.LOGINFO)
        return avg_brightness >= brightness_threshold
    
    def getMonitorSize(self):
        # Get the width and height of the current Kodi window
        width = int(xbmc.getInfoLabel('System.ScreenWidth'))
        height = int(xbmc.getInfoLabel('System.ScreenHeight'))

        if width is None or height is None:
            self.log("Unable to get Monitor Size.", xbmc.LOGERROR)
            return None, None
        return width, height
    
    def getVideoPlayerDimensions(self):
        # Check if a video is currently playing
        if self.isPlayingVideo():
            monitor_width, monitor_height = self.getMonitorSize()
            monitor_ar = monitor_width / monitor_height

            video_player_width, video_player_height = monitor_width, monitor_height
            video_player_ar = float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))

            if (monitor_ar > video_player_ar):
                video_player_width = int(float(video_player_height) * video_player_ar)
            else:
                video_player_height = int(float(video_player_width) / video_player_ar)

            self.log(f"Video Player Dimensions: {video_player_width}x{video_player_height}", level=xbmc.LOGINFO)
            return video_player_width, video_player_height
        else:
            # If no video is playing, log this status
            self.log(f"No video is currently playing.", level=xbmc.LOGINFO)
        
        # If the function fails to retrieve dimensions, log an error.
        self.log("Error retrieving video player dimensions. Terminating.", level=xbmc.LOGERROR)
        return None, None
    
    def getVideoDimensions(self):
        video_w_str = xbmc.getInfoLabel('Player.Process(videowidth)')
        video_h_str = xbmc.getInfoLabel('Player.Process(videoheight)')
        video_w = int(video_w_str.replace(",", ""))
        video_h = int(video_h_str.replace(",", ""))
        return video_w, video_h

    def LineColorGreaterThan(self, _bArray, _lineIndex, _imageWidth, _imageHeight, _threshold):
        if _lineIndex >= _imageHeight:
            self.log("Line index is out of the image height range.", level=xbmc.LOGERROR)
            return False

        bytesPerRow = _imageWidth * 4
        totalIntensity = 0

        # Calculate the start index for the specified line
        startIndex = _lineIndex * bytesPerRow

        # Ensure we do not exceed the array bounds
        if startIndex >= len(_bArray):
            self.log("Start index for the line is out of the _bArray bounds.", level=xbmc.LOGERROR)
            return False

        # Iterate through each pixel in the line
        for i in range(startIndex, min(startIndex + bytesPerRow, len(_bArray)), 4):
            # Accumulate the average color intensity of the pixel
            totalIntensity += (_bArray[i] + _bArray[i+1] + _bArray[i+2]) / 3

        avgIntensity = totalIntensity / _imageWidth
        result = avgIntensity > _threshold

        return result

    def ColumnColorGreaterThan(self, _bArray, _colIndex, _imageWidth, _imageHeight, _threshold):
        if _colIndex >= _imageWidth:
            self.log("Column index is out of the image width range.", level=xbmc.LOGERROR)
            return False

        bytesPerRow = _imageWidth * 4
        totalIntensity = 0

        for row in range(_imageHeight):
            index = (row * bytesPerRow) + (_colIndex * 4)
            if index + 3 < len(_bArray):  # Ensuring we're within bounds for BGRA
                # Accumulate the average color intensity of the column
                totalIntensity += (_bArray[index] + _bArray[index+1] + _bArray[index+2]) / 3
            else:
                self.log("Attempted to access an index out of range in ColumnColorGreaterThan.", level=xbmc.LOGERROR)
                return False

        __avgIntensity = totalIntensity / _imageHeight
        __result = __avgIntensity > _threshold

        return __result
    
    def _getContentImageDimensions(self, image, image_width, image_height):
        threshold = 4     # Above this value is "non-black"
        offset = 2        # Offset start pixel to fix green line rendering bug
        top, bottom, left, right = offset, image_height, offset, image_width

        # Scan for the first and last non-black row
        for i in range(top, image_height-1):
            if self.LineColorGreaterThan(image, i, image_width, image_height, threshold):
                top = i
                break

        # If top is found, start scanning from the bottom to find the bottom boundary
        if top > offset:
            for i in range(image_height - offset - 1, top, -1):  # Start from the bottom and move upwards
                if self.LineColorGreaterThan(image, i, image_width, image_height, threshold):
                    bottom = i
                    break
        else:
            top -= offset
            
        # Scan for the first non-black column (left boundary)
        for j in range(left, image_width - 1):
            if self.ColumnColorGreaterThan(image, j, image_width, image_height, threshold):
                left = j
                break  # Stop scanning once the first non-black column is found

        # If left boundary is found, continue to find the right boundary
        if left > offset:
            for j in range(image_width - offset - 1, left, -1):  # Start scanning from the right end towards the left
                if self.ColumnColorGreaterThan(image, j, image_width, image_height, threshold):
                    right = j
                    break  # Stop scanning once the first non-black column from the right is found
        else:
            left -= offset

        self.log(f"Top/bottom/left/right: {top},{bottom},{left},{right}", xbmc.LOGINFO)

        # Calculate the height and width of the video content
        content_image_height = bottom - top if top is not None and bottom is not None else 0
        content_image_width = right - left if left is not None and right is not None else 0

        return content_image_width, content_image_height
    
    def getImdbMeta(self):
        try:
            metadata = self.getVideoMetadata()
            self.log(json.dumps(metadata, indent=4), xbmc.LOGINFO)
            self.imdb_data = ImdbScraper(metadata['title'], metadata['content_type'], metadata['imdb_number'])
            self.imdb_ar = self.imdb_data.parse_aspect_ratios()
            self.multi_ar = len(self.imdb_ar) > 1

            if self.multi_ar:
                self.log(f"Multiple aspect ratios detected from Imdb: {self.imdb_ar}", xbmc.LOGINFO)
                if xbmcaddon.Addon().getSetting("show_notification") == "true":
                    notify("Multiple aspect ratios detected")
        except Exception as e:
            self.imdb_data = None
            self.imdb_ar = None
            self.log(f"Error occurred: {e}", xbmc.LOGERROR)
            return

    def _getContentDimensionsFromData(self, player_width, player_height, player_ar):
        content_ar = self.imdb_ar

        if self.multi_ar:
            content_width = player_width
            content_height = player_height
        else:
            content_ar = content_ar[0]
            self.log(f"Content aspect ratio from Imdb: {content_ar}", xbmc.LOGINFO)

            if content_ar > player_ar:
                # Filled width, content width = player width
                content_width = player_width
                content_height = content_width / content_ar
            else:
                # Filled height, content height = player height
                content_height = player_height
                content_width = content_height * content_ar
        return content_width, content_height
    
    def _getContentDimensionsFromImage(self, player_width, player_height, player_ar):
        attempts = 1
        retry_delay = 5
        max_attempts = 36
        image_height = 480
        image_width = int(image_height*player_ar)
        self.log(f"Image Dimensions: {image_width}x{image_height}", xbmc.LOGINFO)

        while attempts < max_attempts:
            image_data = self.CaptureFrame(image_width, image_height)

            if self.checkForBrightFrame(image_data, image_width, image_height):
                # If a bright frame is found, process it.
                try:
                    content_image_width, content_image_height = self._getContentImageDimensions(image_data, image_width, image_height)
                except Exception as e:
                    self.log(f"Error occurred: {e}", xbmc.LOGERROR)
                    return None, None
                break
            else:
                # If the frame is too dark, log the attempt and wait before retrying.
                self.log(f"Frame is too dark. Attempt {attempts} of {max_attempts}. Waiting to retry...", xbmc.LOGINFO)
                if self.monitor.waitForAbort(retry_delay):
                    return None, None
                attempts += 1

        if attempts == max_attempts:
            self.log("Unable to find bright frame after maximum attempts", xbmc.LOGERROR)
            notify("Unable to find bright frame")
            return None, None

        height_scale = content_image_height / image_height
        width_scale = content_image_width / image_width
        content_width = float(player_width) * width_scale
        content_height = float(player_height) * height_scale
        return content_width, content_height

    def getContentDimensions(self):
        video_w, video_h = self.getVideoDimensions()
        self.log(f"Video Resolution: {video_w}x{video_h}", xbmc.LOGINFO)

        player_ar = float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))
        player_width, player_height = self.getVideoPlayerDimensions() 
        self.log(f"Video Player Aspect Ratio: {player_ar}", xbmc.LOGINFO)

        use_workaround = xbmcaddon.Addon().getSetting("android_workaround") == "true"
        content_width, content_height = None, None

        if use_workaround:
            content_width, content_height = self._getContentDimensionsFromData(player_width, player_height, player_ar)

        if content_width is None or content_height is None:
            content_width, content_height = self._getContentDimensionsFromImage(player_width, player_height, player_ar)

        return content_width, content_height
    
    def getVideoMetadata(self):
        # Check if a video is currently playing
        if xbmc.Player().isPlayingVideo():
            # Retrieve specific metadata properties
            title = xbmc.getInfoLabel('VideoPlayer.Title') or None
            content_type = 'tt' if xbmc.getInfoLabel('VideoPlayer.OriginalTitle') else 'ep' if xbmc.getInfoLabel('VideoPlayer.TVshowtitle') else None
            imdb_number = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or None
            season = xbmc.getInfoLabel('VideoPlayer.Season') or None
            episode = xbmc.getInfoLabel('VideoPlayer.Episode') or None

            # Compile the metadata into a dictionary
            metadata = {
                'title': title,
                'content_type': content_type,
                'imdb_number': imdb_number,
                'season': season,
                'episode': episode
            }
            
            return metadata
        else:
            self.log("No video is currently playing", xbmc.LOGERROR)
            return None

    def CalculateZoom(self):
        content_width, content_height = self.getContentDimensions()

        if content_width is None or content_height is None:
            self.log("Unable to calculate zoom", xbmc.LOGERROR)
            return
        
        content_ar = content_width / content_height
        self.log(f"Content Dimension: {content_width:.2f}x{content_height:.2f}", level=xbmc.LOGINFO)
        self.log(f"Content Aspect Ratio: {content_ar:.3f}:1", level=xbmc.LOGINFO)

        monitor_width, monitor_height = self.getMonitorSize()
        monitor_ar = monitor_width / monitor_height
        self.log("Monitor Size: {}x{}".format(monitor_width, monitor_height), level=xbmc.LOGINFO)

        if content_ar < monitor_ar:
            # Fill to height
            zoom_amount = float(monitor_height) / content_height
        else:
            # Fill to width
            zoom_amount = round(float(monitor_width) / content_width, 2)

        self.log("Zoom amount: {:.2f}".format(zoom_amount), level=xbmc.LOGINFO)
        
        # Execute the zoom via JSON-RPC
        xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}'
            )
        
        if xbmcaddon.Addon().getSetting("show_notification") == "true" and not self.enter_recalc_loop:
            if zoom_amount > 1.0:
                # Notify the user of the action taken   
                notify("Adjusted zoom to {:.2f}".format(zoom_amount))

    def CalculateZoomPeriodically(self, delay=5):
        while not self.monitor.abortRequested() and self.isPlayingVideo():
            self.CalculateZoom()
            self.logging_status = False
            if self.monitor.waitForAbort(delay):
                break

    def showOriginal(self):
        if xbmcgui.Window(10000).getProperty("blackbarsnever_processing") != "true":
            xbmcgui.Window(10000).setProperty("blackbarsnever_processing", "true")
            
            xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0' + ' }}, "id": 1}'
            )
            notify("Showing original aspect ratio")

            xbmcgui.Window(10000).clearProperty("blackbarsnever_processing")

    def toggleZoomAdjustment(self):
        status = xbmcgui.Window(10000).getProperty("blackbarsnever_status")
        if status == "on":
            self.showOriginal()
        else:
            self.abolishBlackBars()
    
    def abolishBlackBars(self):
        # Check if the processing flag is set to avoid re-entry
        if xbmcgui.Window(10000).getProperty("blackbarsnever_processing") == "true":
            return
        
        xbmcgui.Window(10000).setProperty("blackbarsnever_processing", "true")
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")
        
        # Fetch IMDb metadata if multi-aspect ratios support is enabled or Android workaround is active
        if xbmcaddon.Addon().getSetting("multi_aspect_ratios_support") == "true" or xbmcaddon.Addon().getSetting("android_workaround") == "true":
            self.getImdbMeta()

        self.enter_recalc_loop = self.multi_ar and xbmcaddon.Addon().getSetting("android_workaround") == "false"

        if self.enter_recalc_loop:
            # Loop for periodic recalculations if conditions are met
            self.CalculateZoomPeriodically()
        else:
            # Perform a single zoom calculation otherwise
            self.CalculateZoom()

        xbmcgui.Window(10000).clearProperty("blackbarsnever_processing")

if __name__ == "__main__":
    player = Player()
    while not player.monitor.abortRequested():
        if player.monitor.waitForAbort(10):
            break