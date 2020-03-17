from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
from flask_httpauth import HTTPBasicAuth
from jsonschema import validate
from pymongo import MongoClient
from bson.objectid import ObjectId
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

MONGO_HOST = os.environ.get('MONGO_HOST', 'db')
MONGO_PORT = os.environ.get('MONGO_PORT', 27017)
DEFAULT_USER = os.environ.get('DEFAULT_USER', 'prometheus')
DEFAULT_PASSWORD = os.environ.get('DEFAULT_PASSWORD', 'prometheus')

app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == DEFAULT_USER:
        return DEFAULT_PASSWORD
    return None


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


schema = {
     "type" : "object",
     "properties": {
         "target": {"type": "string"},
         "labels": {"type": "object"}
     },
     "required": ["target"]
}

delete_schema = {
     "type": "object",
     "properties" : {
         "id": {"type": "string"},
     },
     "required": ["id"]
}

# class IndexPage(Resource):
#     def get(self):
#         return {"message": "Need Web UI, Please add UI support https://github.com/narate/prom-file-sd"}


class PromTargets(Resource):
    decorators = [auth.login_required]

    def get(self):
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client.prom
        col = db.targets
        targets = []
        for o in col.find():
            targets.append({'target': o['target'], 'labels': o.get('labels', {}), 'id': str(o['_id'])})
        return {'targets': targets}
    
    def post(self):
        body = request.get_json()
        try:
            validate(body, schema)
        except:
            return {
                    'message': 'Input data invalid or miss some value, required: {}'.format(schema['required'])
                }, 400
        
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client.prom
        col = db.targets
        labels = body.get('labels', {})
        doc = {
            'target': body['target'],
            'labels': labels
        }
        
        sel = {
            'target': body['target']
        }
        metrics_path = labels.get('__metrics_path__')
        if metrics_path is not None:
            sel['labels.__metrics_path__'] = metrics_path
        else:
            doc['labels']['__metrics_path__'] = '/metrics'
        
        col.replace_one(sel, doc, True)
        with open('/prom/conf/targets.json', 'w') as f:
            targets = []
            for o in col.find({}, projection={'_id': False}):
                targets.append(
                    {
                        'targets': [o['target']],
                        'labels': o.get('labels', {})
                    }
                )
    
            f.write(json.dumps(targets, indent=2))
            f.flush()
            os.fsync(f.fileno())
        return {
            'status': 'created',
            'data': doc
        }, 201

    def delete(self):
        body = request.get_json()
        try:
            validate(body, delete_schema)
        except:
            return {
                    'message': 'Input data invalid or miss some value, required: {}'.format(schema['required'])
                }, 400
        
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client.prom
        col = db.targets
        sel = {
            '_id': ObjectId(body['id'])
        }
        col.delete_one(sel)
        with open('/prom/conf/targets.json', 'w') as f:
            targets = []
            for o in col.find({}, projection={'_id': False}):
                targets.append(
                    {
                        'targets': [o['target']],
                        'labels': o.get('labels',{})
                    }
                )
    
            f.write(json.dumps(targets, indent=2))
            f.flush()
            os.fsync(f.fileno())
        return None, 204

# api.add_resource(IndexPage, '/')


api.add_resource(PromTargets, '/targets')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
