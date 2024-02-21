import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

monitor = xbmc.Monitor()
capture = xbmc.RenderCapture()
player = xbmc.Player()

def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)

def log(msg, level=xbmc.LOGINFO):
    xbmc.log("Black Bars Never: " + msg, level=level)

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("blackbarsnever_status") == "on":
                self.showOriginal()
            else:
                self.abolishBlackBars()

    def onAVStarted(self):
        if xbmcaddon.Addon().getSetting("automatically_execute") == "true":
            self.abolishBlackBars()
        else:
            self.showOriginal()

    def CaptureFrame(self, capture_width, capture_height):
        capture.capture(capture_width, capture_height)
        capturedImage = capture.getImage(2000)
        return capturedImage

    def calculateAverageBrightness(self, img_data, image_width, image_height):
        total_brightness = 0
        for i in range(0, len(img_data), 4):  # Step through each pixel
            # Calculate brightness of each pixel
            brightness = 0.299*img_data[i+2] + 0.587*img_data[i+1] + 0.114*img_data[i]
            total_brightness += brightness
        average_brightness = total_brightness / (image_width * image_height)
        return average_brightness
    
    def getMonitorSize(self):
        # Get the width and height of the current Kodi window
        width = int(xbmc.getInfoLabel('System.ScreenWidth'))
        height = int(xbmc.getInfoLabel('System.ScreenHeight'))

        if width is None or height is None:
            log("Unable to get Monitor Size.", xbmc.LOGERROR)
            return None
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

            log(f"Video Player Dimensions: {video_player_width}x{video_player_height}", level=xbmc.LOGINFO)
            return video_player_width, video_player_height
        else:
            # If no video is playing, log this status
            log(f"No video is currently playing.", level=xbmc.LOGINFO)
        
        # If the function fails to retrieve dimensions, log an error.
        log("Error retrieving video player dimensions. Terminating.", level=xbmc.LOGERROR)
        return None

    def LineColorGreaterThan(self, _bArray, _lineIndex, _imageWidth, _imageHeight, _threshold):
        bytesPerRow = _imageWidth * 4
        __sliceStart = _lineIndex * bytesPerRow
        __sliceEnd = __sliceStart + bytesPerRow  # Span of one row

        # Ensure sliceEnd does not exceed the length of _bArray
        __sliceEnd = min(__sliceEnd, len(_bArray))

        # Calculate the average color intensity of the row
        __avgIntensity = sum(
            (_bArray[i] + _bArray[i+1] + _bArray[i+2]) / 3 
            for i in range(__sliceStart, __sliceEnd, 4)
        ) / (_imageWidth)

        # Check if the average color intensity of the line is greater than the threshold
        __result = __avgIntensity > _threshold

        return __result

    def ColumnColorGreaterThan(self, _bArray, _colIndex, _imageWidth, _imageHeight, _threshold):
        if _colIndex >= _imageWidth:
            log("Column index is out of the image width range.", level=xbmc.LOGERROR)
            return False

        bytesPerRow = _imageWidth * 4
        totalIntensity = 0

        for row in range(_imageHeight):
            index = (row * bytesPerRow) + (_colIndex * 4)
            if index + 3 < len(_bArray):  # Ensuring we're within bounds for BGRA
                # Accumulate the average color intensity of the column
                totalIntensity += (_bArray[index] + _bArray[index+1] + _bArray[index+2]) / 3
            else:
                log("Attempted to access an index out of range in ColumnColorGreaterThan.", level=xbmc.LOGERROR)
                return False

        # Calculate the average color intensity of the column
        __avgIntensity = totalIntensity / _imageHeight

        # Check if the average color intensity of the column is greater than the threshold
        __result = __avgIntensity > _threshold

        return __result
    
    def getContentDimensions(self, retry_delay=5, max_attempts=12):
        attempts = 0
        brightness_threshold = 10

        video_w_str = xbmc.getInfoLabel('Player.Process(videowidth)')
        video_h_str = xbmc.getInfoLabel('Player.Process(videoheight)')
        video_w = int(video_w_str.replace(",", ""))
        video_h = int(video_h_str.replace(",", ""))
        log(f"Video Resolution: {video_w}x{video_h}", xbmc.LOGINFO)

        player_ar = float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))
        player_width, player_height = self.getVideoPlayerDimensions() 
        log(f"Video Player Aspect Ratio: {player_ar}", xbmc.LOGINFO)

        image_height = 480
        image_width = int(image_height*player_ar)

        while attempts < max_attempts:
            # Capture a frame (wait time optional)
            __myimage = self.CaptureFrame(image_width,  image_height)

            # Calculate average brightness of the frame
            avg_brightness = self.calculateAverageBrightness(__myimage, image_width, image_height)
            log(f"Average Brightness: {avg_brightness}", xbmc.LOGINFO)

            # Check if the frame is too dark
            if avg_brightness < brightness_threshold:  # Arbitrary threshold for "too dark"
                log("Frame is too dark. Waiting to retry...", xbmc.LOGINFO)
                attempts += 1
                time.sleep(retry_delay)  # Wait for a few seconds before retrying
                continue
            break

        # Initialize variables for the positions of the first and last non-black pixels
        top, bottom, left, right = 0, image_height, 0, image_width

        # Above this value is "non-black"
        __threshold = 4
        # Offset start pixel to fix green line rendering bug
        offset = 2

        # Scan for the first and last non-black row
        for i in range(offset, image_height-1):
            if top == 0 and self.LineColorGreaterThan(__myimage, i, image_width, image_height, __threshold):
                top = i
                break

        # If top is found and is greater than 0, start scanning from the bottom to find the bottom boundary
        if top > offset:
            for i in range(image_height - offset - 1, top, -1):  # Start from the bottom and move upwards
                if self.LineColorGreaterThan(__myimage, i, image_width, image_height, __threshold):
                    bottom = i
                    break
        else:
            top -= offset
            
        # Scan for the first non-black column (left boundary)
        for j in range(offset, image_width - 1):
            if self.ColumnColorGreaterThan(__myimage, j, image_width, image_height, __threshold):
                left = j
                break  # Stop scanning once the first non-black column is found

        # If left boundary is found, continue to find the right boundary
        if left > offset:
            for j in range(image_width - offset - 1, left, -1):  # Start scanning from the right end towards the left
                if self.ColumnColorGreaterThan(__myimage, j, image_width, image_height, __threshold):
                    right = j
                    break  # Stop scanning once the first non-black column from the right is found
        else:
            left -= offset

        # Log an error if either left or right boundary couldn't be determined (indicating potential issues)
        if left is None or right is None:
            log("Left or right content boundaries could not be determined.", xbmc.LOGERROR)

        log(f"Top/bottom/left/right: {top},{bottom},{left},{right}", xbmc.LOGINFO)

        # Calculate the height and width of the video content
        content_height = bottom - top + 1 if top is not None and bottom is not None else 0
        content_width = right - left + 1 if left is not None and right is not None else 0

        height_scale = content_height / image_height
        width_scale = content_width / image_width

        content_width = float(player_width) * width_scale
        content_height = float(player_height) * height_scale
        return content_width, content_height

    def abolishBlackBars(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")
        self.CalculateZoom()

    def CalculateZoom(self):
        content_width, content_height = self.getContentDimensions()
        content_ar = content_width / content_height

        # Log the content size
        log(f"Content Dimension: {content_width:.2f}x{content_height:.2f}", level=xbmc.LOGINFO)
        log(f"Content Aspect Ratio: {content_ar:.3f}:1", level=xbmc.LOGINFO)

        monitor_width, monitor_height = self.getMonitorSize()
        monitor_ar = monitor_width / monitor_height
        log("Monitor Size: {}x{}".format(monitor_width, monitor_height), level=xbmc.LOGINFO)

        if (content_ar < monitor_ar):
            # Fill to height
            zoom_amount = float(monitor_height) / content_height
        else:
            # Fill to width
            zoom_amount = round(float(monitor_width) / content_width, 2)

        log("Zoom amount: {:.2f}".format(zoom_amount), level=xbmc.LOGINFO)
        
        # Execute the zoom via JSON-RPC
        xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}'
            )
        
        if (xbmcaddon.Addon().getSetting("show_notification") == "true"):
            if (zoom_amount > 1.0):
                # Notify the user of the action taken   
                notify("Adjusted zoom to {:.2f}".format(zoom_amount))

    def showOriginal(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0' + ' }}, "id": 1}'
        )
        notify("Showing original aspect ratio")

p = Player()

while not monitor.abortRequested():
    if monitor.waitForAbort(10):
        break