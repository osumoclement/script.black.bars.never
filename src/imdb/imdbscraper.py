import re
import requests
from bs4 import BeautifulSoup

class ImdbScraper():
    HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}
    BASE_URL = "https://www.imdb.com/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def setMedia(self, title=None, media_type="tt", imdb_id=None):
        self.title = title
        self.media_type = media_type

        if title is None and imdb_id is None:
            raise Exception("Must have either title or imdb_id")

        if imdb_id is None:
            self.imdb_id = self._parse_imdb_id()
        else:
            self.imdb_id = imdb_id
    
    def _parse_imdb_id(self):
        SEARCH_URL = self.BASE_URL + "find/"

        params = {
        's': self.media_type,
        'q': self.title
        }

        search_page = self.session.get(SEARCH_URL, params=params)

        if search_page.status_code == 200:
            soup = BeautifulSoup(search_page.text, 'html.parser')
            title_url_tag = soup.find(class_="ipc-metadata-list-summary-item__t")
            
            if title_url_tag:
                title_url = title_url_tag['href']
                imdb_number = title_url.rsplit('/title/', 1)[-1].split("/")[0]

            return imdb_number
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