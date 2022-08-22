import re
import json

import requests
from bs4 import BeautifulSoup

from datetime import datetime

from pymongo import MongoClient

from config import *

import pymorphy2


morph = pymorphy2.MorphAnalyzer()


class Employer:
    def __init__(self, employer_card):
        self.link = employer_card.find("span", class_="vacancy-preview-card__company-name").find("a")["href"]

        response = requests.get(self.link)
        html = BeautifulSoup(response.text, "lxml")
            
        self.name = html.find("h1", "company-nav__name-headline").text.strip().replace("Проверено Работой.ру", "").replace("Мы проверили этого работодателя на финансовые и юридические показатели.", "").strip()
        self.id = self.link.split("/")[4]
        
        try:
            self.profarea = html.find("span", class_="info-table__sub-item").text.strip().replace(",", "")
        except:
            self.profarea = None
        
        self.vacancies = html.find_all("div", class_="vacancy-preview-card__wrapper")



class Vacancy:
    def __init__(self, city, vacancy, employer_html):
        self.link = f"https://{city}.rabota.ru" + vacancy.find("h3").find("a")["href"]
        self.id = int(self.link.split("/")[4])
        self.speciality = vacancy.find("h3").text.strip()

        self.response = requests.get(self.link)
        self.html = BeautifulSoup(self.response.text, "lxml")

        self.time = str(datetime.now())
        self.requirements = self.html.find("span", class_="vacancy-requirements_uppercase").text.strip().lower()

        self.salary_not_filtred = self.html.find("h3", class_="vacancy-card__salary").text.strip().split("—")[-1].replace("руб.", "").strip()
        self.salary = int(re.sub("[^0-9]", "", self.salary_not_filtred))

        self.request_parametres = {"request":{"vacancy_id": self.id},"request_id":9245225,"application_id":13,"rabota_ru_id":"6300f1a6195460009868970513510108","user_tags":[{"id":0,"add_date":"2022-08-20","name":"usp_feedback_tooltip_target"},{"id":0,"add_date":"2022-08-20","name":"web_vacancy_recomendations_ml_new_target1"},{"id":0,"add_date":"2022-08-20","name":"web_autoresponsedesktop_target2"},{"id":0,"add_date":"2022-08-20","name":"web_favorite_vacancy_target1"},{"id":0,"add_date":"2022-08-20","name":"web_salary-filter_target1"},{"id":0,"add_date":"2022-08-20","name":"web_upload_file_resume_target"},{"id":0,"add_date":"2022-08-20","name":"web_autoresponse_from_resume"},{"id":0,"add_date":"2022-08-20","name":"web_autoresponse_from_2016_target"},{"id":0,"add_date":"2022-08-20","name":"usp_banner_company_feedback_control1"},{"id":0,"add_date":"2022-08-20","name":"web_resume-skills_target1"},{"id":0,"add_date":"2022-08-20","name":"search_exclude_reloc2_target"},{"id":0,"add_date":"2022-08-20","name":"hr_new_scheduled_action_list_active"}]}
        self.response = requests.post("https://kostromskaya.rabota.ru/api-web/v4/vacancy/phone.json", json=self.request_parametres)
        self.company_phone = json.loads(self.response.text)["response"]["service_provider_phones"][0]["number_international"]

        self.education_types = ["любое", "высшее", "неполное высшее", "среднее профессиональное", "среднее"]
        self.experience_types = ["не имеет значения", "без опыта", "менее года", "от 1 года", "от 2 лет", "от 3 лет", "от 4 лет", "от 5 лет", "от 6 лет", "от 7 лет", "от 8 лет", "от 9 лет", "от 10 лет"]
        self.work_types = ["полный рабочий день", "сменный график", "свободный график", "удаленная работа", "вахта"]

        self.education = None
        self.work_experience = None
        self.work_schedule = None

        self.is_remote = False

        try:
            for education_type in self.education_types:
                if education_type in self.requirements:
                    self.education_type = education_type
                    break


            for experience_type in self.experience_types:
                if experience_type in self.requirements:
                    self.work_experience = experience_type
                    break

            for work_type in self.work_types:
                if work_type in self.requirements:
                    self.work_type = work_type
                    
                    if work_type == "удаленная работа":
                        self.is_remote = True
                    
                    break
        except:
            self.education_type = self.html.find("div", attrs={"itemprop": "educationRequirements"}).text.strip()
            self.work_schedule = self.html.find("div", attrs={"itemprop": "workHours"}).text.strip()
            self.work_experience = self.html.find("div", attrs={"itemprop": "experienceRequirements"}).text.strip()
            self.vacancy_is_remote = False

        self.address = self.html.find("div", class_="vacancy-locations__address").text.strip()

        try:
            self.city = employer_html.find("span", "vacancy-preview-location__address-text").text.strip().replace(",", "")
        except:
            self.city = None

        if self.city != None:
            if self.city != "Удаленная работа":
                self.city = morph.parse(self.city)[0].inflect({"nomn"}).word.split()[-1].title()
            else:
                self.is_remote = True

        if self.is_remote:
            self.city = "Удаленная работа"


        self.description = self.html.find("div", attrs={"itemprop": "description"})
        
        try:
            self.card_description = self.description.text.strip()
        except:
            self.card_description = None

        self.full_description = self.description.find_all("ul")
        
        try:
            self.skills = self.full_description[1].text.strip().split("\n")
        except:
            self.skills = None

        try:
            self.duties = self.full_description[0].text.strip().split("\n")
        except:
            self.duties = None

