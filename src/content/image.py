import xbmc
from src.core import core


class RenderImage():
    def __init__(self):
        self.capture = xbmc.RenderCapture()
        self.byte_array = None
        self.width = None
        self.height = None

    def capture_frame(self, capture_width, capture_height):
        try:
            self.width = capture_width
            self.height = capture_height
            self.capture.capture(capture_width, capture_height)
            self.byte_array = self.capture.getImage(2000)
        except Exception as e:
            core.logger.log(f"Failed to capture frame: {e}", xbmc.LOGERROR)
    
    def get_image_dimensions(self):
        return self.width, self.height
    

class ImageAnalysisService:
    def __init__(self, image: RenderImage):
        self.image = image

    def _row_color_greater_than(self, row_index, threshold):
        bytesPerRow = self.image.width * 4
        totalIntensity = 0

        startIndex = row_index * bytesPerRow

        for i in range(startIndex, min(startIndex + bytesPerRow, len(self.image.byte_array)), 4):
            totalIntensity += (self.image.byte_array[i] + self.image.byte_array[i+1] + self.image.byte_array[i+2]) / 3

        avgIntensity = totalIntensity / self.image.width
        return avgIntensity > threshold
    
    def _col_color_greater_than(self, col_index, threshold):
        bytesPerRow = self.image.width * 4
        totalIntensity = 0

        for row in range(self.image.height):
            index = (row * bytesPerRow) + (col_index * 4)
            totalIntensity += (self.image.byte_array[index] + self.image.byte_array[index+1] + self.image.byte_array[index+2]) / 3

        avgIntensity = totalIntensity / self.image.height
        return avgIntensity > threshold
    
    def _find_boundary(self, start, end, step, check_function):
        for i in range(start, end, step):
            if check_function(i):
                return i
        return None
    
    def calculate_content_image_size(self):
        threshold = 2     # Above this value is "non-black"
        offset = 2        # Offset start pixel to fix green line rendering bug
        bottom, right = self.image.height, self.image.width

        top = self._find_boundary(offset, self.image.height-1, 1, lambda i: self._row_color_greater_than(i, threshold))
        if top > offset:
            bottom = self._find_boundary(self.image.height-1-offset, top-1, -1, lambda i: self._row_color_greater_than(i, threshold))
        else:
            top -= offset

        left = self._find_boundary(offset, self.image.width-1, 1, lambda j: self._col_color_greater_than(j, threshold))
        if left > offset:
            right = self._find_boundary(self.image.width-1-offset, left-1, -1, lambda j: self._col_color_greater_than(j, threshold))
        else:
            left -= offset

        core.logger.log(f"Top/bottom/left/right: {top},{bottom},{left},{right}", xbmc.LOGINFO)

        content_image_height = bottom - top
        content_image_width = right - left

        return content_image_width, content_image_height
    
    def get_non_black_pixels_percentage(self):
        non_black_pixel_count = 0

        for i in range(0, len(self.image.byte_array), 4):
            if not (self.image.byte_array[i] == self.image.byte_array[i+1] == self.image.byte_array[i+2] == 0):
                non_black_pixel_count += 1
        
        total_pixel_count = self.image.width * self.image.height
        non_black_pixel_percentage = non_black_pixel_count / total_pixel_count
        return non_black_pixel_percentage
    
    def check_for_bright_frame(self, non_black_pixel_threshold=0.6):
        non_black_pixel_percentage = self.get_non_black_pixels_percentage()
        core.logger.log(f"Non-Black pixels Percentage: {non_black_pixel_percentage}", xbmc.LOGINFO)
        return non_black_pixel_percentage >= non_black_pixel_threshold