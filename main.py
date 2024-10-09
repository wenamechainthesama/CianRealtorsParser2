import re
import time
import random
import multiprocessing

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

from config import (
    DATABASE_URL,
    ADSPOWER_ID1,
    ADSPOWER_ID2,
)
from adspower_driver import AdspowerDriver
from constants import *


logger.add("realtor_parser.log", format="{time} {level} {message}", level="INFO")


# Создание модели БД
engine = create_engine(DATABASE_URL)

Base = declarative_base()


class RealtorData(Base):
    __tablename__ = "realtors_data"

    link = Column(String(200), primary_key=True, unique=True)
    name = Column(String(50))
    phone_number = Column(String(20), unique=True)
    region = Column(String(200))
    specializations = Column(String(1000))
    date = Column(Integer)


Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()


# Сбор ids всех регионов
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
    logger.success("Ids всех регионов успешно собраны")
    return region_idxs


def parse_realtors_data(
    adspower_id: str,
    region_idxs: list[int],
    start_region_pos: int,
    end_region_pos: int,
    adspower_driver: AdspowerDriver,
):
    adspower_browser = adspower_driver.get_browser(adspower_id=adspower_id)
    current_region_pos = start_region_pos
    realtors_exceptions_counter = 0
    current_page_idx = 1
    while True:
        adspower_browser.get(
            URL.format(region_idxs[current_region_pos]) + f"&page={current_page_idx}"
        )
        logger.info(f"Номер страницы: {current_page_idx}, idx региона: {current_region_pos}")
        time.sleep(1)

        # Парсинг ссылок на всех риелторов на странице
        try:
            bad_realtors_links = WebDriverWait(adspower_browser, 5).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "text-box-info-title")
                )
            )

            realtors_exceptions_counter = 0

        except Exception as error:
            realtors_exceptions_counter += 1
            logger.warning(
                f"Произошла ошибка во время сбора данных риелторов (current_region_pos={current_region_pos}, current_page_idx={current_page_idx}):\n{error}"
            )
            if realtors_exceptions_counter >= 2:
                logger.success(f"Все данные по региону (current_region_pos={current_region_pos}) собраны")
                current_region_pos += 1
                realtors_exceptions_counter = 0
            continue

        try:
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
        except Exception as error:
            logger.warning(
                f"Ошибка во время парсинга специализаций какого-то риелтора:\n{error}"
            )

        realtors_links = [link.get_attribute("href") for link in bad_realtors_links]

        # Фильтруем риелторов по дате регистрации
        realtors_registration_date = WebDriverWait(adspower_browser, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "prop-el"))
        )

        updated = []
        for date in realtors_registration_date:
            if date.get_attribute("title").startswith("Дата регистрации"):
                updated.append(date)
                continue

        if len(realtors_links) == 0 or current_page_idx > 100:
            current_page_idx = 1
            current_region_pos += 1
            logger.success(
                f"Риелторы по региону (current_region_pos={current_region_pos}) собраны"
            )
            if current_region_pos == end_region_pos:
                logger.success("Все доступные риелторы собраны")
                break

        i = -1
        new_realtors_links = {}
        new_realtors_specializations = []
        for date_idx, date in enumerate(updated):
            i += 1
            date_int = int(date.text[13:17])
            if date_int >= 2017:
                new_realtors_links.setdefault(realtors_links[date_idx], date_int)
                new_realtors_specializations.append(
                    " || ".join(bad_realtors_specializations[i])
                )

        # Заходим по каждой ссылке и собираем данные по одному конкретному риелтору:
        # 1) Имя
        # 2) Телефон
        # 3) Специализация
        # 4) Регион
        realtor_idx = 0
        for link, date in new_realtors_links.items():
            name = None
            phone_number = None
            region = None
            adspower_browser.get(link)

            # Проверка на отсутствие данного риелтора в БД
            id_already_in_db = session.query(
                session.query(RealtorData).filter_by(link=link).exists()
            ).scalar()

            if id_already_in_db:
                logger.warning(f"Этот риелтор (link={link}) уже есть в БД")
                continue

            # Сбор данных со странички
            # Имя
            try:
                name = WebDriverWait(adspower_browser, 1).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                name = re.sub("\n", " ", name.text)
                logger.info(f"Имя риелтора (link={link}) собрано: {name}")
            except:
                try:
                    name = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "realtor__info-name")
                        )
                    )
                    name = re.sub("\n", " ", name.text)
                    logger.info(f"Имя риелтора (link={link}) собрано: {name}")
                except:
                    logger.warning(f"Имя риелтора (link={link}) не найдено")

            # Дата регистрации
            logger.info(f"Дата регистрации риелтора: {date}")

            # Телефон
            source = adspower_browser.page_source
            phone_number = re.findall(
                r"\+\d{1,3}[-\s]?\(?\d{1,5}\)?[-\s]?\(?\d{1,5}\)?[-\s]?\d{1,5}[-\s]?\d{1,5}[-\s]?\d{1,5}",
                source,
            )
            if phone_number:
                phone_number = phone_number[0]
                logger.info(f"Телефон риелтора (link={link}) собран: {phone_number}")
            else:
                phone_number = None
                logger.warning(f"Телефон риелтора (link={link}) не найден")

            # Регион
            finished = False
            try:
                if not finished:
                    company_contacts = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CLASS_NAME, "company-contacts")
                        )
                    )
                    if len(company_contacts) < 2:
                        raise TimeoutException()
                    company_contacts = company_contacts[1]
                    iss: list[WebElement] = WebDriverWait(company_contacts, 1).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "i"))
                    )
                    for i in iss:
                        if i.get_attribute("class") == "icon-point":
                            parent = WebDriverWait(i, 1).until(
                                EC.presence_of_element_located((By.XPATH, "./.."))
                            )
                            region = parent.text
                            finished = True
                            break
            except:
                pass

            try:
                if not finished:
                    region = WebDriverWait(adspower_browser, 1).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "realtor__info-place")
                        )
                    ).text
                    finished = True
            except:
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
                    ).text
                    finished = True
            except:
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
                    ).text
                    finished = True
            except:
                pass

            if finished:
                logger.info(f"Регион риелтора (link={link}) собран: {region}")
            else:
                logger.warning(f"Регион риелтора (link={link}) не найден")

            # Специализации
            specializations = new_realtors_specializations[realtor_idx]
            logger.info(
                f"Специализации риелтора (link={link}) собраны: '{specializations}'"
            )

            try:
                session.add(
                    RealtorData(
                        link=link,
                        name=name,
                        phone_number=phone_number,
                        region=region,
                        specializations=specializations,
                        date=date,
                    )
                )
                session.commit()
                logger.success(f"Риелтор (link={link}) под номером {len(session.query(RealtorData).all())} добавлен в БД")
            except Exception as error:
                logger.error(f"Ошибка во время записи данных риелтора в бд: {error}")
                realtor_idx += 1
                continue

            time.sleep(random.randint(3, 5))

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
            region_idxs,
            4, # 0,
            REGION_IDXS_AMOUNT // 2 + 15,
            adspower_driver,
        ],
    )
    task1.start()

    task2 = multiprocessing.Process(
        target=parse_realtors_data,
        args=[
            ADSPOWER_ID2,
            region_idxs,
            72, # REGION_IDXS_AMOUNT // 2 + 15 + 1,
            REGION_IDXS_AMOUNT - 1,
            adspower_driver,
        ],
    )
    task2.start()

    task1.join()
    task2.join()
