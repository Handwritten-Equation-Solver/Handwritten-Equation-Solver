from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import requests
import time

def setup_headless():
    options = Options()
    options.add_argument("--headless")
    return options

def new_browser():
    options = setup_headless()
    driver = webdriver.Firefox(firefox_options=options)
    return driver

def send_request(equation, driver):
    elem = driver.find_element_by_id("query")
    elem.clear()
    elem.send_keys(equation)
    elem.send_keys(Keys.RETURN)

def downloader(image_url):
    img = requests.get(image_url)
    filename = "output.gif"
    with open(filename, 'wb') as file:
        file.write(img.content)
        file.close()

def find_image(driver):
    imgsrc = ''
    for i in range(0, 1000):
        try:
            imgsrc = driver.find_elements_by_css_selector("#Result > section:nth-child(1) > div:nth-child(2) > div:nth-child(1) > img:nth-child(2)")[0].get_attribute('src')
            break
        except:
            try:
                imgsrc = driver.find_elements_css_selector(".recalcPod")[0].get_attribute('src')
                break
            except:
                time.sleep(1)
                i += 1
    return imgsrc

def find_solution(equation):
    driver = new_browser()
    url = "http://www.wolframalpha.com"
    driver.get(url)
    assert "Wolfram" in driver.title
    send_request(equation, driver)
    img = find_image(driver)
    downloader(img)
