# CianRealtorsParser2

## Описание проекта

`CianRealtorsParser2` — это инструмент для парсинга данных о риелторах с сайта Циан. Этот проект автоматизирует сбор данных о риелторах, включая такие сведения, как имя, телефон, электронная почта и регион работы. Проект полезен для быстрой агрегации и анализа данных риелторов для исследовательских или деловых целей.

## Содержание

- [Установка](#установка)
- [Запуск](#запуск)
- [Структура проекта](#структура-проекта)
- [Настройка](#настройка)
- [Примеры использования](#примеры-использования)
- [Инструменты и ресурсы](#инструменты-и-ресурсы)

## Установка

Для работы проекта потребуется Python версии 3.8 и выше, а также соответствующие библиотеки. Следуйте этим шагам для установки всех необходимых зависимостей:

1. Клонируйте репозиторий:
   ```bash
   git clone [URL репозитория]
   cd [название директории]
   ```

2. Установите все зависимости, используя `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

3. Создайте файл `.env` в корневой директории проекта для настройки необходимых переменных окружения, таких как ключи API, пути к базе данных и другие конфигурационные параметры.

## Запуск

Для запуска проекта используйте следующую команду:
```bash
python main.py
```
Файл `main.py` является основным файлом запуска, с которого начинается работа программы, включая запуск парсера и сбор данных о риелторах.

## Структура проекта

```
.
├── .gitignore             # Исключает временные файлы и конфиденциальные данные из Git
├── cian_parser.py         # Модуль, отвечающий за парсинг данных с сайта Циан
├── config.py              # Файл конфигурации с настройками, загружаемыми из .env
├── constants.py           # Константы, такие как URL-адреса, параметры запросов и прочее
├── main.py                # Главный файл для запуска программы
├── requirements.txt       # Список зависимостей проекта
└── README.md              # Документация проекта
```

## Настройка

Перед запуском программы создайте файл `.env` в корневой директории проекта и добавьте туда необходимые переменные среды. Эти переменные автоматически загружаются в `config.py` с помощью `dotenv`, упрощая настройку.

## Примеры использования

### Запуск проекта с основного файла

Чтобы запустить парсинг, начните с файла `main.py`:
```bash
python main.py
```

## Инструменты и ресурсы

Этот проект использует следующие ресурсы и инструменты:

- [Afy.ru](https://afy.ru) — источник данных о риелторах, используемый для парсинга информации.
- [AdsPower](https://www.adspower.com) — сервис для управления множеством аккаунтов, который помогает организовать безопасное парсинг-средство.
