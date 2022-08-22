import requests
from bs4 import BeautifulSoup

from datetime import datetime

from pymongo import MongoClient
from config import *

import sys

from rabota_ru_api import Employer, Vacancy

cluster = MongoClient("mongodb+srv://kaden:172327287@cluster0.bgbmhao.mongodb.net/?retryWrites=true&w=majority")
employers_db = cluster["employers_db"]
employers_collection = employers_db["employers_col"]

city = sys.argv[1]


for page in range(1, settings["page_count"]):
    try:
        response = requests.get(f"https://{city}.rabota.ru/?page={page}")
        html = BeautifulSoup(response.text, "lxml")

        for employer_card in html.find_all("div", class_="vacancy-preview-card__wrapper"):
            employer = Employer(employer_card)
            vacancy_list = []

            for vacancy in employer.vacancies:
                vacancy = Vacancy(city, vacancy, employer_card)

                vacancy_list.append({
                    "id": vacancy.id,
                    "link": vacancy.link,
                    "speciality": vacancy.speciality,
                    "time": vacancy.time,
                    "address": vacancy.address,
                    "is_remote": vacancy.is_remote,
                    "work_schedule": vacancy.work_schedule,
                    "education": vacancy.education_type,
                    "work_experience": vacancy.work_experience,
                    "salary_monthly": vacancy.salary,
                    "city": vacancy.city,
                    "duties": vacancy.duties,
                    "skills": vacancy.skills,
                    "region": city.replace("www", "moskow"),
                    "description": vacancy.card_description
                })


            if employers_collection.count_documents({"_id": employer.id}) == 0: 
                employers_collection.insert_one({
                    "_id": employer.id,
                    "company_name": employer.name,
                    "contact_phone": vacancy.company_phone,
                    "profarea": employer.profarea,
                    "vacancies": vacancy_list
                })


    except:
        continue