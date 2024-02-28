import re
import requests
from bs4 import BeautifulSoup

class ImdbScraper:
    HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}
    BASE_URL = "https://www.imdb.com/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def setMedia(self, video_metadata):
        self.title = video_metadata.get('title')
        self.show_title = video_metadata.get('show_title')
        self.episode_title = video_metadata.get('episode_title')
        self.media_type = video_metadata.get('content_type')
        self.imdb_id = video_metadata.get('imdb_number')

        # Ensure there's enough information to proceed
        if not self.title and not self.imdb_id:
            raise Exception("Must have either title or imdb_id")

        # If imdb_id is not provided, attempt to parse it
        if not self.imdb_id:
            self.imdb_id = self._parse_imdb_id()
    
    def _parse_imdb_id(self):
        SEARCH_URL = self.BASE_URL + "find/"

        # Determine the search query based on media type
        query = self.episode_title if self.media_type == 'ep' and self.episode_title else self.title
        if not query:  # Safety check if query is somehow empty
            raise Exception("No valid query for IMDB search.")

        params = {
            's': 'ep' if self.media_type == 'ep' else 'tt',
            'q': query
        }

        search_page = self.session.get(SEARCH_URL, params=params)

        if search_page.status_code == 200:
            soup = BeautifulSoup(search_page.text, 'html.parser')
            title_url_tag = soup.find(class_="ipc-metadata-list-summary-item__t")

            imdb_number = None
            
            if title_url_tag:
                title_url = title_url_tag['href']
                imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0]

            if imdb_number:
                return imdb_number
            else:
                raise Exception("IMDB ID not found from search.")
        else:
            raise Exception("Search page not successfully resolved.")

        
    def parse_aspect_ratios(self):
        technical_page = self.session.get(f"{self.BASE_URL}title/{self.imdb_id}/technical/")

        if technical_page.status_code == 200:
            soup = BeautifulSoup(technical_page.text, 'html.parser')
            aspect_ratio_element = soup.find(id="aspectratio")
            aspect_ratios = aspect_ratio_element.find_all(class_="ipc-metadata-list-item__list-content-item")
            aspect_ratios_text = [ratio.get_text() for ratio in aspect_ratios]

            aspect_ratios_float = []
            for text in aspect_ratios_text:
                # Find all float or integer numbers in the string
                numbers = re.findall(r"[\d.]+", text)
                # Assuming the first number is the aspect ratio, convert to float and append
                if numbers:
                    aspect_ratios_float.append(float(numbers[0]))

            return aspect_ratios_float
        else:
            raise Exception("Technical page not successfully resolved.")