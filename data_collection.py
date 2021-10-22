from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import time

# https://joblib.readthedocs.io/en/latest/memory.html
from joblib import Memory
cache_dir = 'collection_cache'
memory = Memory(cache_dir, verbose=1)


# chromedriver_path = '/usr/local/bin/chromedriver'

url = "https://itch.io/games/downloadable/tag-twine"


def collect_twine_links(url, wd):
	# TODO
	wd.get(url)
	elt = find_element_by_text('Downloadable', wd, elt='span')
	show_screenshot(elt)
	input()


def get_twine(links):
	for l in links:
		twine = get_twine_from_url(l)


@memory.cache
def get_twine_from_url(url):
	# TODO
	time.sleep(1)
	return '<html>Twine Game<html>'


def show_screenshot(elt):
	screenshot = elt.screenshot_as_png
	image = Image.open(BytesIO(screenshot))
	plt.imshow(image)
	plt.show()


def find_element_by_text(text, wd, elt='div'):
	return wd.find_element(By.XPATH, f'//{elt}[contains(text(),\'{text}\')]')


if __name__ == '__main__':
	chrome_options = webdriver.ChromeOptions()
	# chrome_options.add_argument('--headless')  # See wikipedia https://en.wikipedia.org/wiki/Headless_browser
	# chrome_options.add_argument('--no-sandbox')
	# chrome_options.add_argument('--disable-dev-shm-usage')

	wd = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
	links = collect_twine_links(url, wd)

	# print(get_twine_from_url(url+ '5'))