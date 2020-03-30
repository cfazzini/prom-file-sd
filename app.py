from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
from flask_httpauth import HTTPBasicAuth
from jsonschema import validate
from pymongo import MongoClient
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

MONGO_HOST = os.environ.get('MONGO_HOST', '127.0.0.1')
MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017))
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
     "type": "object",
     "properties": {
         "exporter": {"type": "string"},
         "target": {"type": "string"},
         "labels": {"type": "object"}
     },
     "required": ["exporter", "target"]
}

class IndexPage(Resource):
    # return list of targets 
    def get(self):
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    db = client.prom
    col = db.targets
    targets = []
    for target in col.find():
        targets.append({'exporter': target['exporter'], 'target': target['target'], 'labels': target.get('labels', {})})
    return {'targets': targets}
#     def get(self):
#         return {"message": "Need Web UI, Please add UI support https://github.com/narate/prom-file-sd"}


class PromTargets(Resource):
    # disable auth for now
    # decorators = [auth.login_required]

    def get(self):
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client.prom
        col = db.targets
        targets = []
        for target in col.find():
            targets.append({'exporter': target['exporter'], 'target': target['target'], 'labels': target.get('labels', {})})
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
        result = {
            'exporter': body['exporter'],
            'target': body['target'],
            'labels': labels
        }
        replace_proto = {
            'exporter': body['exporter'],
            'target': body['target']
        }
        find_proto = {
            'exporter': body['exporter']
        }
        metrics_path = labels.get('__metrics_path__')
        if metrics_path is not None:
            replace_proto['labels.__metrics_path__'] = metrics_path
        else:
            result['labels']['__metrics_path__'] = '/metrics'
        
        col.replace_one(replace_proto, result, True)
        with open('/prom/conf/' + body['exporter'] + '.json', 'w') as f:
            targets = []
            for target in col.find(find_proto, projection={'_id': False}):
                targets.append(
                    {
                        'targets': [target['target']],
                        'labels': target.get('labels', {})
                    }
                )
    
            f.write(json.dumps(targets, indent=2))
            f.flush()
            os.fsync(f.fileno())
        return {
            'status': 'created',
            'data': result
        }, 201

    def delete(self):
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
        delete_proto = {
            'exporter': body['exporter'],
            'target': body['target']
        }
        find_proto = {
            'exporter': body['exporter']
        }
        col.delete_one(delete_proto)
        with open('/prom/conf/' + body['exporter'] + '.json', 'w') as f:
            targets = []
            for target in col.find(find_proto, projection={'_id': False}):
                targets.append(
                    {
                        'targets': [target['target']],
                        'labels': target.get('labels', {})
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
