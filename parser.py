import re

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

import pymorphy2

from datetime import datetime

from pymongo import MongoClient
from config import *

import sys

import traceback

options = Options()
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--proxy-server='direct://'")
options.add_argument("--proxy-bypass-list=*")
options.add_argument("--start-maximized")
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--ignore-certificate-errors')

driver = webdriver.Firefox(options=options)

cluster = MongoClient("mongodb+srv://kaden:172327287@cluster0.bgbmhao.mongodb.net/?retryWrites=true&w=majority")
employers_db = cluster["employers_db"]
employers_collection = employers_db["employers_col"]

city = sys.argv[1]

morph = pymorphy2.MorphAnalyzer()

for page in range(1, settings["page_count"]):
    try:
        response = requests.get(f"https://{city}.rabota.ru/?page={page}")
        html = BeautifulSoup(response.text, "lxml")

        for employer_card in html.find_all("div", class_="vacancy-preview-card__wrapper"):
            try:
                employer_link = employer_card.find("span", class_="vacancy-preview-card__company-name").find("a")["href"]
            except:
                continue

            response = requests.get(employer_link)
            html = BeautifulSoup(response.text, "lxml")
            employer_name = html.find("h1", "company-nav__name-headline").text.strip().replace("Проверено Работой.ру", "").replace("Мы проверили этого работодателя на финансовые и юридические показатели.", "").strip()
            employer_id = employer_link.split("/")[4]

            employer_profarea = html.find("span", class_="info-table__sub-item").text.strip().replace(",", "")
            employer_vacancies = html.find_all("div", class_="vacancy-preview-card__wrapper")

            try:
                query_city = html.find("span", "vacancy-preview-location__address-text").text.strip().replace(",", "")

            except:
                query_city = None

            vacancy_list = []

            for vacancy in employer_vacancies:
                vacancy_link = f"https://{city}.rabota.ru" + vacancy.find("h3").find("a")["href"]
                vacancy_id = vacancy_link.split("/")[4]
                vacancy_speciality = vacancy.find("h3").text.strip()


                driver.get(vacancy_link)
                
                driver.implicitly_wait(5)
                
                driver.find_element(By.CLASS_NAME, "vacancy-response__phones-show-link").click()
                
                driver.implicitly_wait(5)
                
                company_phone = driver.find_element(By.CLASS_NAME, "vacancy-response__phone").text
                
                vacancy_time = str(datetime.now())

                try:
                    vacancy_city = html.find("span", "vacancy-preview-location__address-text").text.strip().replace(",", "")
                except:
                    continue

                html = BeautifulSoup(driver.page_source, "lxml")

                if vacancy_city != None:
                    if vacancy_city != "Удаленная работа":
                        vacancy_city = morph.parse(vacancy_city)[0].inflect({"nomn"}).word.split()[-1].title()


                if vacancy_city != None:    
                    vacancy_address = f"{vacancy_city}, {html.find('div', class_='vacancy-locations__address').text.strip()}"
                else:
                    vacancy_address = html.find('div', class_='vacancy-locations__address').text.strip()

                vacancy_salary_card = html.find("h3", attrs={"itemprop": "baseSalary"}).text.strip().split("—")[-1].replace("руб.", "").strip()

                try:                

                    vacancy_salary = int(re.sub("[^0-9]", "", vacancy_salary_card))
                except:
                    vacancy_salary = vacancy_salary_card

                try:
                    vacancy_requirements = html.find("span", class_="vacancy-requirements_uppercase").text.strip().lower()

                    vacancy_is_remote = False

                    education_types = ["любое", "высшее", "неполное высшее", "среднее профессиональное", "среднее"]
                    experience_types = ["не имеет значения", "без опыта", "менее года", "от 1 года", "от 2 лет", "от 3 лет", "от 4 лет", "от 5 лет", "от 6 лет", "от 7 лет", "от 8 лет", "от 9 лет", "от 10 лет"]
                    work_types = ["полный рабочий день", "сменный график", "свободный график", "удаленная работа", "вахта"]

                    for education_type in education_types:
                        if education_type in vacancy_requirements:
                            education = education_type
                            break
                            
                        education_type = None

                    for experience_type in experience_types:
                        if experience_type in vacancy_requirements:
                            work_experience = experience_type
                            break

                        work_experience = None

                    for work_type in work_types:
                        if work_type in vacancy_requirements:
                            work_schedule = work_type
                            break

                        work_schedule = None

                    if vacancy_city == "Удаленная работа":
                        vacancy_is_remote = True

                    if work_schedule == "удаленная работа":
                        vacancy_is_remote = True
                        vacancy_city = "Удаленная работа"  

                except:
                    education_type = html.find("div", attrs={"itemprop": "educationRequirements"}).text.strip()
                    work_schedule = html.find("div", attrs={"itemprop": "workHours"}).text.strip()
                    work_experience = html.find("div", attrs={"itemprop": "experienceRequirements"}).text.strip()
                    vacancy_is_remote = False

                description = html.find("div", attrs={"itemprop": "description"})
                card_description = description.text.strip()
                full_description = description.find_all("ul")

                try:
                    skills = full_description[1].text.strip().split("\n")
                except:
                    skills = None
                try:
                    duties = full_description[0].text.strip().split("\n")
                except:
                    duties = None


                vacancy_list.append({
                    "id": vacancy_id,
                    "link": vacancy_link,
                    "speciality": vacancy_speciality,
                    "time": vacancy_time,
                    "address": vacancy_address,
                    "is_remote": vacancy_is_remote,
                    "work_schedule": work_schedule,
                    "education": education_type,
                    "work_experience": work_experience,
                    "salary_monthly": vacancy_salary,
                    "city": vacancy_city,
                    "duties": duties,
                    "skills": skills,
                    "region": city.replace("www", "moskow"),
                    "description": card_description
                })

            if employers_collection.count_documents({"_id": employer_id}) == 0: 
                employers_collection.insert_one({
                    "_id": employer_id,
                    "company_name": employer_name,
                    "contact_phone": company_phone,
                    "profarea": employer_profarea,
                    "vacancies": vacancy_list
                })


    except Exception as e:
        print(traceback.format_exc())
        continue