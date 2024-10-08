import re
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
from selenium.common.exceptions import TimeoutException
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
    region_idxs.remove(1203)
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
        try:
            bad_realtors_links = WebDriverWait(adspower_browser, 5).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "text-box-info-title")
                )
            )

            bad_realtors_specializations = [
                [
                    j.text
                    for j in i.find_elements(
                        By.CLASS_NAME, "gallery-text-box-spec-list"
                    )
                ]
                for i in WebDriverWait(adspower_browser, 5).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "desc"))
                )
            ]
        except TimeoutException:
            print("Риелторы по данному региону закончились")
            current_region_pos += 1
            continue

        realtors_links = [link.get_attribute("href") for link in bad_realtors_links]

        # Фильтруем риелторов по дате регистрации
        realtors_registration_data = WebDriverWait(adspower_browser, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "prop-el"))
        )

        updated = []
        for data in realtors_registration_data:
            if data.get_attribute("title").startswith("Дата регистрации"):
                updated.append(data)
                continue

        if len(realtors_links) == 0:
            current_region_pos += 1
            print("Риелторы по региону собраны")
            if current_region_pos == end_region_pos:
                logger.success("Все доступные риелторы собраны")
                break

        i = -1
        new_realtors_links = []
        new_realtors_specializations = []
        for data_idx, data in enumerate(updated):
            i += 1
            if int(data.text[13:17]) >= 2017:
                new_realtors_links.append(realtors_links[data_idx])
                new_realtors_specializations.append(bad_realtors_specializations[i])

        # Заходим по каждой ссылке и собираем данные по одному конкретному риелтору:
        # 1) Имя
        # 2) Телефон
        # 3) Специализация
        # 4) Регион
        for realtor_idx, link in enumerate(new_realtors_links):
            adspower_browser.get(link)

            # Сбор данных со странички
            # Имя
            try:
                name = WebDriverWait(adspower_browser, 1).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except TimeoutException:
                name = WebDriverWait(adspower_browser, 1).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "realtor__info-name")
                    )
                )
            print(name.text)

            # Телефон
            source = adspower_browser.page_source
            phone_number = re.findall(
                r"\+\d{1,3}[-\s]?\(?\d{1,5}\)?[-\s]?\(?\d{1,5}\)?[-\s]?\d{1,5}[-\s]?\d{1,5}[-\s]?\d{1,5}",
                source,
            )[0]
            print(phone_number)

            # Регион
            finished = False
            region = None
            try:
                if not finished:
                    company_contacts = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "company-contacts")
                        )
                    )
                    if len(company_contacts) < 2:
                        print("u")
                        raise TimeoutException()
                    company_contacts = company_contacts[1]
                    # divs = WebDriverWait(company_contacts, 1).until(
                    #     EC.presence_of_all_elements_located((By.TAG_NAME, "div"))
                    # )
                    divs = company_contacts.find_elements(By.XPATH, ".//*")
                    print(len(divs))
                    for div in divs:
                        print("1", div.text)
                        i = WebDriverWait(div, 1).until(
                            EC.presence_of_element_located((By.TAG_NAME, "i"))
                        )
                        print(i.get_attribute("class"))
                        if i.get_attribute("class") == "icon-point":
                            region = WebDriverWait(div, 1).until(
                                EC.presence_of_all_elements_located(
                                    (By.CLASS_NAME, "info")
                                )
                            ),
                            break
                    # region = list(
                    #     filter(
                    #         lambda x: WebDriverWait(x, 0.5)
                    #         .until(EC.presence_of_element_located((By.TAG_NAME, "i")))
                    #         .get_attribute("class")
                    #         == "icon-point",
                    #         WebDriverWait(company_contacts, 1).until(
                    #             EC.presence_of_all_elements_located(
                    #                 (By.TAG_NAME, "div")
                    #             )
                    #         ),
                    #     )
                    # )[0]
                    # print("asdf", region.text)
                    finished = True
            except TimeoutException:
                pass

            try:
                if not finished:
                    region = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "realtor__info-place")
                        )
                    )
                    finished = True
            except TimeoutException:
                pass

            try:
                if not finished:
                    block_col = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "block-col")
                        )
                    )
                    if len(block_col) < 2:
                        raise TimeoutException()
                    block_col = block_col[1]
                    block_col_line = WebDriverWait(block_col, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "block-col-line")
                        )
                    )
                    if len(block_col_line) < 3:
                        raise TimeoutException()
                    block_col_line = block_col_line[2]
                    region = WebDriverWait(block_col_line, 1).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    finished = True
            except TimeoutException:
                pass

            try:
                if not finished:
                    block_col = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "block-col")
                        )
                    )
                    if len(block_col) < 2:
                        raise TimeoutException()
                    block_col = block_col[1]
                    block_col_line = WebDriverWait(block_col, 1).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "block-col-line")
                        )
                    )
                    region = WebDriverWait(block_col_line, 1).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    finished = True
            except TimeoutException:
                pass

            print(region.text)

            # Специализация
            print(new_realtors_specializations[realtor_idx])

            time.sleep(DELAY)

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
            73,
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
