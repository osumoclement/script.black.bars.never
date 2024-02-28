import xbmc
from src.core import core

class OnlineMetadataService:
    def __init__(self, scraper):
        self._scraper = scraper

    def scrape_metadata(self, video_metadata):
        try:
            self._scraper.setMedia(video_metadata)
            aspect_ratios = self._scraper.parse_aspect_ratios()
        except Exception as e:
            core.logger.log(f"Error occurred: {e}", xbmc.LOGERROR)
            return None

        scraped_metadata = {
            "aspect_ratios": aspect_ratios
        }

        return scraped_metadata