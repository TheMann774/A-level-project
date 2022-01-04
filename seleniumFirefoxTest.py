from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup as bs

options = Options()
options.headless = True
options.set_preference('javascript.enabled', True)
driver = webdriver.Firefox(options=options)
driver.get("https://www.sainsburys.co.uk/gol-ui/product/all-cereals/weetabix-chocolate-x24-540g")
soup_file=driver.page_source
soup = bs(soup_file, "html.parser")
print(soup.find('h1', class_="pd__header").text)
