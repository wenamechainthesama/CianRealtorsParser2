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
from constants import *


logger.add("realtor_parser.log", format="{time} {level} {message}", level="INFO")


def get_region_idxs(adspower_id: str, adspower_driver: AdspowerDriver):
    adspower_browser = adspower_driver.get_browser(adspower_id=adspower_id)
    adspower_browser.get(URL.format(1))
    time.sleep(1)
    regions_button = WebDriverWait(adspower_browser, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "filter-holder-icon"))
    )
    ActionChains(adspower_browser).click(regions_button).perform()
    time.sleep(1)
    regions = WebDriverWait(adspower_browser, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "rm-col-line"))
    )
    region_idxs = []
    for region in regions:
        if region.get_attribute("idnt") is None:
            continue
        region_idxs.append(int(region.get_attribute("idnt")[7:]))
    return region_idxs


def parse_realtors_data(
    adspower_id: str,
    adspower_name: str,
    region_idxs: list[int],
    start_region_pos: int,
    end_region_pos: int,
    adspower_driver: AdspowerDriver,
):
    adspower_browser = adspower_driver.get_browser(adspower_id=adspower_id)
    current_region_pos = start_region_pos
    current_page_idx = 1
    while True:
        adspower_browser.get(
            URL.format(region_idxs[current_region_pos]) + f"&page={current_page_idx}"
        )
        time.sleep(1)

        # Парсинг ссылок на всех риелторов на странице
        realtors_links = WebDriverWait(adspower_browser, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "text-box-info-title"))
        )

        # Фильтруем риелторов по дате регистрации
        realtors_registration_data = WebDriverWait(adspower_browser, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "prop-el"))
        )
        for data in realtors_registration_data:
            if not data.get_attribute("title").startswith("Дата регистрации"):
                continue
            if int(data.text[13:17]) < 2017:
                data_idx = realtors_registration_data.index(data)
                realtors_links.pop(data_idx)

        # Заходим по каждой ссылке и собираем данные по одному конкретному риелтору:
        # 1) Имя
        # 2) Телефон
        # 3) Специализация
        # 4) Регион
        for link in realtors_links:
            realtor_link = link.get_attribute("href")
            adspower_browser.get(realtor_link)

            # Сбор данных со странички
            # ...

            time.sleep(DELAY)

        if realtors_links == []:
            current_region_pos += 1
            if current_region_pos == end_region_pos:
                logger.success("Все доступные риелторы собраны")
                break

        current_page_idx += 1
        time.sleep(1)


if __name__ == "__main__":
    adspower_driver = AdspowerDriver()
    # region_idxs = get_region_idxs(
    #     adspower_id=ADSPOWER_ID1, adspower_driver=adspower_driver
    # )
    region_idxs = REGION_IDXS
    task1 = multiprocessing.Process(
        target=parse_realtors_data,
        args=[
            ADSPOWER_ID1,
            ADSPOWER_NAME1,
            region_idxs,
            0,
            REGION_IDXS_AMOUNT // 2,
            adspower_driver,
        ],
    )
    task1.start()
    # task2 = multiprocessing.Process(
    #     target=parse_realtors_data,
    #     args=[
    #         ADSPOWER_ID2,
    #         ADSPOWER_NAME2,
    #         region_idxs,
    #         REGION_IDXS_AMOUNT // 2 + 1,
    #         REGION_IDXS_AMOUNT - 1,
    #         adspower_driver,
    #     ],
    # )
    # task2.start()
    task1.join()
    # task2.join()
