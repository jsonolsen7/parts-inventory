from flask import Flask, request
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import json_util
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
import json

# Test App
from flask_pymongo import PyMongo

class Part:
    def __init__(self, partName, partNumber, inStock, onOrder):
        self.partName = partName
        self.partNumber = partNumber
        self.inStock = inStock
        self.onOrder = onOrder

screw = Part("Screw", 100007, 10, 5)

def pymongo_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config["MONGO_URI"] = "mongodb://localhost:27017/testDatabase"
    mongo = PyMongo(app)

    collection = mongo.db.parts

    @app.route("/test")
    def index():
        data = []
        for d in collection.find():
            data.append(d)
        return json.dumps(data, indent=4, default=json_util.default), 200

    @app.route("/test/part", methods=["POST"])
    def create_part():
        one_part = collection.insert_one(screw.__dict__)
        return json_util.dumps({"_id": str(one_part.inserted_id)})

    @app.route('/test/part/<part_id>', methods=["PUT"])
    def update_part(part_id):
        part = request.get_json()
        result = collection.update_one({"_id": ObjectId(part_id)}, {"$set": part})
        if result.matched_count > 0:
            return json_util.dumps({"status": "success"}), 200
        else:
            return json_util.dumps({"error": "Part not found"}), 404

    @app.route('/test/part/<part_id>', methods=["DELETE"])
    def delete_part(part_id):
        result = collection.delete_one({"_id": ObjectId(part_id)})
        if result.deleted_count > 0:
            return json_util.dumps({"status": "deleted"})
        else:
            return json_util.dumps({"error": "Part not found"}), 404
    
    return app

# Actual App
# load_dotenv()

# app = Flask(__name__)

# username = os.getenv("MONGO_USERNAME")
# password = os.getenv("MONGO_PASSWORD")
# client = MongoClient(f'mongodb+srv://{username}:{password}@parts.ubqerzo.mongodb.net/?retryWrites=true&w=majority')

# db = client["parts-inventory"]
# collection = db["parts"]

# @app.route("/")
# def index():
#     data = []
#     for d in collection.find():
#         data.append(d)

#     return json.dumps(data, indent=4, default=json_util.default), 200

# @app.route('/parts/<partName>')
# def get_part(partName):
#     part = collection.find_one({"partName": partName})
#     if part:
#         return json_util.dumps(part, indent=4, default=json_util.default), 200
#     else:
#         return json_util.dumps({"error": "Part not found"}), 404

# @app.route('/parts', methods=["POST"])
# def create_part():
#     part = request.get_json()
#     result = collection.insert_one(part)
#     return json_util.dumps({"_id": str(result.inserted_id)})

# @app.route('/parts/<partName>', methods=["PUT"])
# def update_part(partName):
#     part = request.get_json()
#     result = collection.update_one({"partName": partName}, {"$set": part})
#     if result.matched_count > 0:
#         return json_util.dumps({"status": "success"}), 200
#     else:
#         return json_util.dumps({"error": "Part not found"}), 404

# @app.route('/parts/<partName>', methods=["DELETE"])
# def delete_part(partName):
#     result = collection.delete_one({"partName": partName})
#     if result.deleted_count > 0:
#         return json_util.dumps({"status": "deleted"})
#     else:
#         return json_util.dumps({"error": "Part not found"}), 404

app = pymongo_app()

if __name__ == '__main__':
    app.run(DEBUG=True)