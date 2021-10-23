from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import time
import pandas as pd
from tenacity import retry, wait_fixed, stop_after_attempt
import signal
from tqdm import tqdm
from selenium.webdriver.common.keys import Keys

# https://joblib.readthedocs.io/en/latest/memory.html
from joblib import Memory
cache_dir = 'collection_cache'
memory = Memory(cache_dir, verbose=1)


# chromedriver_path = '/usr/local/bin/chromedriver'

url = "https://itch.io/games/downloadable/tag-twine"

wd = None

robots = """
User-agent: *
Disallow: /embed/
Disallow: /embed-upload/
Disallow: /search
Disallow: /checkout/
Disallow: /game/download/
Disallow: /bundle/download/
Disallow: /register-for-purchase/
Disallow: /email-feedback/

Sitemap: https://itch.io/sitemap.xml
"""


def collect_itch_twine_links(url, wd):
	"""Get links to itch twine games"""
	wd.get(url)
	all_links = set()
	new_links = True
	max_retries = 5
	while new_links:
		new_links = set()
		retries = 0
		while not new_links and retries < max_retries:
			titles = wd.find_elements_by_css_selector("a.game_link")
			links_in_page = set([elt.get_attribute("href") for elt in titles])
			new_links = links_in_page - all_links
			all_links = all_links | new_links
			time.sleep(0.2 + retries)  # There is a smarter way to do this, but I don't have time
			retries += 1
		print('new_links', new_links)
		scroll_down(wd)

	links_df = pd.DataFrame([{'link': link} for link in all_links])
	links_df.to_pickle('itch_twine_links.pkl')
	links_df.to_csv('itch_twine_links.csv')

	return links_df


def scroll_down(wd):
	wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")

def scroll_to_elt(wd, elt):
	wd.execute_script("arguments[0].scrollIntoView(true);", elt)


def get_all_twine_games(links):
	df = pd.DataFrame()
	for l in tqdm(links):
		row = get_twine_game(l)
		df = df.append(row, ignore_index=True)
		df.to_csv('scraping_results3.csv')
		df.to_pickle('scraping_results3.pkl')



# @memory.cache
def get_twine_game(game_url):
	success = False
	outer_err = None
	state = "start"

	try:
		wd.get(game_url)
		# input(f'url {url}')
		print(f'url {game_url}')
		state = "post url"

		print('buy now check 1')
		if not_here(wd):
			state = 'must purchase (1), skipping'
			print(state)
			return {'url': game_url, 'success': True, 'e': str(outer_err), 'state': state}

		purchase_success, state = do_purchase(game_url, wd)

		if not purchase_success:
			wd.get(game_url)
			state = 'will click download'
			print(state)
			elt, state = click_download(wd)
			print(state)

			if thanks(wd):
				state = 'thanks'
				print(state)
				return {'url': game_url, 'success': True, 'e': str(outer_err), 'state': state}

			state = 'buy now check 2'
			print(state)
			if not_here(wd):
				state = 'must purchase (2), skipping'
				print(state)
				return {'url': game_url, 'success': False, 'e': str(outer_err) + 'buy_now check 2', 'state': state}

			print('no thanks', end="\r")
			try:
				state = 'going into no thanks'
				print(state)
				no_thanks(wd)
				state = 'no thanks clicked'
				print(state)
			except Exception as err:
				state = 'Did not click no thanks'
				print(state)

			state = 'download 2'
			print(state)
			elt, state = click_download(wd)
			state = state + ' download 2'
	except Exception as err:
		outer_err = err
		print("exception with ", game_url, err)

	time.sleep(1)
	return {'url': game_url, 'success': success, 'error': str(outer_err).replace(',', ' ').replace('\n', ' '), 'got_to': state}

def do_purchase(game_url, wd):
	state = 'go to purchase'
	success = False
	print(state)

	wd.get(game_url + '/purchase')

	try:
		if not_here(wd):
			state = 'not here'
			return success, state
		else:
			state = 'going into no thanks'
			print(state)
			no_thanks(wd)
			state = 'no thanks clicked'
			print(state)

			state = 'download purchase'
			print(state)
			elt, state = click_download(wd)
			state = state + ' download purchase'
			success = True
	except Exception:
		pass

	return success, state

def thanks(wd):
	wd.implicitly_wait(2)
	try:
		thanks = find_element_by_text('Thanks for ', wd, 'h2')
		print('found thanks', thanks)
		if thanks:
			print('clicking close')
			clicked = click_close_button(wd)
			print('closed clicked')
	except NoSuchElementException:
		thanks = None

	return thanks


def click_close_button(wd):
	clicked = True
	try:
		close = wd.find_element_by_css_selector('button.icon_close')
		click_elt(wd, close)
	except NoSuchElementException:
		clicked = False

	return clicked


def not_here(wd):
	wd.implicitly_wait(1.25)
	try:
		buy_now = find_element_by_text('Buy Now', wd, 'a')
	except (NoSuchElementException, ElementNotInteractableException):
		buy_now = None

	try:
		couldnt_find = find_element_by_text('find your page', wd, 'h2')
	except (NoSuchElementException, ElementNotInteractableException):
		couldnt_find = None

	return bool(buy_now) or bool(couldnt_find)

# @retry(wait=wait_exponential(multiplier=1, min=1, max=2))
@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def no_thanks(wd):
	wd.implicitly_wait(3)
	elt = find_element_by_text('No thanks,', wd, 'a')
	click_elt(wd, elt)
	return elt


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def click_download(wd):
	# wd.implicitly_wait(10)
	elt = find_element_by_text('Download', wd, 'a')
	click_elt(wd, elt)
	state = 'download clicked'

	return elt, state


def download_2(wd):
	return WebDriverWait(wd, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.buy_btn"))).click()


def show_screenshot(elt):
	screenshot = elt.screenshot_as_png
	image = Image.open(BytesIO(screenshot))
	plt.imshow(image)
	plt.show()


def find_element_by_text(text, wd, elt='div'):
	return wd.find_element(By.XPATH, f'//{elt}[contains(text(),\'{text}\')]')

	# elt = WebDriverWait(wd, 10).until(
	# 	EC.element_to_be_clickable((By.XPATH, f'//{elt}[contains(text(),\'{text}\')]'))
	# )


def click_elt(wd, elt, s=10):
	print(f'going to click {elt}')
	ActionChains(wd).move_to_element(elt).perform()
	wait = WebDriverWait(wd, s)
	wait.until(EC.visibility_of(elt))
	wait.until(EC.element_to_be_clickable(elt))
	elt.click()
	return elt

# def exit_gracefully(signum, frame):
# 	# restore the original signal handler as otherwise evil things will happen
# 	# in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
# 	signal.signal(signal.SIGINT, original_sigint)
# 	wd.close()
# 	# restore the exit gracefully handler here
# 	signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == '__main__':
	chrome_options = webdriver.ChromeOptions()
	wd = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
	# wd.implicitly_wait(10)
	# chrome_options.add_argument('--headless')  # See wikipedia https://en.wikipedia.org/wiki/Headless_browser
	# chrome_options.add_argument('--no-sandbox')
	# chrome_options.add_argument('--disable-dev-shm-usage')

	# original_sigint = signal.getsignal(signal.SIGINT)


	# signal.signal(signal.SIGINT, exit_gracefully)

	# links = collect_itch_twine_links(url, wd)
	links = pd.read_pickle('data/itch_twine_links.pkl')
	get_all_twine_games(list(links['link']))

	get_twine_game('https://grecat.itch.io/this-folder-is-haunted')