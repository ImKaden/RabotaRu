import uuid
import ast
import datetime


from flask import Flask, jsonify, request

from config import settings

from pymongo import MongoClient


app = Flask(__name__)

app.config["JSON_AS_ASCII"] = False

cities = []

cluster = MongoClient("mongodb+srv://kaden:172327287@cluster0.bgbmhao.mongodb.net/?retryWrites=true&w=majority")
users_db = cluster["users_db"]
users_collection = users_db["users_col"]

employers_db = cluster["employers_db"]
employers_collection = employers_db["employers_col"]

@app.route("/rabota_ru", methods=["GET"])
def rabota_ru():
    employers = []
    
    if request.args["key"] == settings["token"]:
        for data in employers_collection.find():
            for vacancy in data["vacancies"]:
                with open("file", "w", encoding="utf-8") as file:
                    file.write(str(vacancy))
                if vacancy["region"] in request.args.getlist("region[]"):
                    try:
                        city_time = users_collection.find_one({"_id": request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).replace(".", "")})["cities"]["".join(request.args.getlist("region[]"))

]
                        if datetime.datetime.strptime(city_time, "%Y-%m-%d %H:%M:%S.%f") < datetime.datetime.strptime(vacancy["time"], "%Y-%m-%d %H:%M:%S.%f"): 
                            if data not in employers:
                                employers.append(data)
                    except:
                        if data not in employers:
                            employers.append(data)

        if users_collection.count_documents({"_id": request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).replace(".", "")}) == 0: 
            users_collection.insert_one({
                "_id": request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).replace(".", ""),
                "cities": {"".join(request.args.getlist("region[]")): str(datetime.datetime.now())}
            })
        else:
            cities = users_collection.find_one({"_id": request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).replace(".", "")})["cities"]
            cities["".join(request.args.getlist("region[]"))] = str(datetime.datetime.now())
            users_collection.update_one({"_id": request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).replace(".", "")}, {"$set": {"cities": cities}})

        return jsonify({
                "request_id": str(uuid.uuid4()), 
                "count": len(employers), 
                "employers": ast.literal_eval(str(employers).replace("_id", "id"))
        })

    return f"Not valid key... Your IP: {request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)}"



if __name__ == "__main__":
    app.run()