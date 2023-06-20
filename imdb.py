import requests
from bs4 import BeautifulSoup


def getOriginalAspectRatio(query):
    BASE_URL = "https://www.imdb.com/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

    URL = BASE_URL + "find/?q={}".format(query)
    searchpage = requests.get(URL, headers=HEADERS)

    soup = BeautifulSoup(searchpage.text, 'lxml')

    if soup.css.select('.ipc-metadata-list-summary-item__t'):
        # we have matches, pick the first one
        title_url = soup.css.select(
            '.ipc-metadata-list-summary-item__t')[0].get('href')

        URL = BASE_URL + title_url

        titlepage = requests.get(URL, headers=HEADERS)

        soup = BeautifulSoup(titlepage.text, 'lxml')

        aspect_ratio_full = soup.find(
            attrs={"data-testid": "title-techspec_aspectratio"}).css.select(".ipc-metadata-list-item__list-content-item")[0].decode_contents()
        aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')

        return aspect_ratio
