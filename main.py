import time
import random
import multiprocessing

import requests
from loguru import logger
from sqlalchemy import create_engine
from fake_useragent import UserAgent
from sqlalchemy.orm import sessionmaker
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import ADSPOWER_ID1, ADSPOWER_NAME1, ADSPOWER_ID2, ADSPOWER_NAME2
from adspower_driver import AdspowerDriver


logger.add("realtor_parser.log", format="{time} {level} {message}", level="INFO")

URL = "https://rossiya.afy.ru/user/?type_trade=&folder=&mp_id=1&mp_id_way=&mp_id_street=&mp_id_bor=&mp_id_bor_sup=&mp_id_metro=&q=&sort%5Bby%5D=rating&limit=50"
BATCH_SIZE = 50
DELAY = 3


def parse_realtors_data(
    adspower_id: str, adspower_name: str, start_page: int, end_page: int, adspower_driver: AdspowerDriver
):
    additional_region_idxs = [2147, 2157]
    adspower_browser = adspower_driver.get_browser(adspower_id=adspower_id)
    page_idx = 101
    region_idx = 1
    for page_idx in range(start_page, end_page + 1):
        adspower_browser.get(URL + f"&page={page_idx}")
        time.sleep(1)
        # Парсинг всех риелторов на странице

        # Если на странице нет риелторов, то region_idx += 1
        # Если region_idx == 93 (92 + 1), то используем additional_region_idxs


        time.sleep(DELAY)

if __name__ == "__main__":
    adspower_driver = AdspowerDriver()
    task1 = multiprocessing.Process(
        target=parse_realtors_data,
        args=[ADSPOWER_ID1, ADSPOWER_NAME1, 1, 50, adspower_driver],
    )
    task1.start()
    task2 = multiprocessing.Process(
        target=parse_realtors_data,
        args=[ADSPOWER_ID2, ADSPOWER_NAME2, 51, 100, adspower_driver],
    )
    task2.start()
    task1.join()
    task2.join()
