from motor.motor_asyncio import AsyncIOMotorClient
from bson.json_util import dumps
import json
from bson.objectid import ObjectId

# motor MongoDb connection

client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client['eva_platform']

class dbname():

    async def getName():
        db= client['eva_platform']
        result= await db.projects.find_one({"project_id":2})
        return json.loads(dumps(result))


class refreshDB():

    async def refreshdb():
        print('received request to refresh database')
        return "Success"


class projectsModel():

    async def getProjects():
        cursor= db.projects.find()
        result=await cursor.to_list(length=1000)
        print("Projects sent {}".format(json.loads(dumps(result))))
        return json.loads(dumps(result))

    async def createProjects(record):

        json_record = json.loads(json.dumps(record))

        # Validation to check if project already exists

        val_res = await db.projects.find_one({"project_name": json_record['project_name']})

        if val_res is not None:
            print('Project already exists')
            return {"status": "Error", "message": "Project already exists"}
        else:
            result = await db.projects.insert_one(json_record)
            print("project created {}".format(result.inserted_id))
            return {"status": "Success", "message": "Project Created with ID {}".format(result.inserted_id)}

    async def deleteProject(object_id):
        query = {"_id": ObjectId("{}".format(object_id))}

        # TODO
        ''' 
        Need to add sections for Delete Intents Entities Responses '''

        # Delete Domains

        result = await db.domains.delete_many({"project_id": object_id})
        print("Domains Deleted - count {}".format(result))

        # Delete Project
        result = await db.projects.delete_one(query)
        print("Project Deleted count {}".format(result))
        return {"status": "Success", "message": "Project Deleted Successfully"}

    async def updateProject(record):

        json_record = json.loads(json.dumps(record))

        val_res = await db.projects.find_one({"project_name": json_record['project_name']})

        if val_res is not None:
            print('Project already exists')
            return {"status": "Error", "message": "Project name already exists"}
        else:
            query = {"_id": ObjectId("{}".format(json_record['object_id']))}
            update_field = {"$set": {"project_name": json_record['project_name'],
                                     "project_description": json_record['project_description']
                                     }}
            result = db.projects.update_one(query,update_field)
            print("Project Updated , rows modified {}".format(result))
            return {"status": "Success", "message": "Project details updated successfully"}

    async def copyProject(record):
        json_record = json.loads(json.dumps(record))

        # check if the project name exists

        val_res = await db.projects.find_one({"project_name": json_record['project_name']})

        if val_res is not None:
            print('Project already exists')
            return {"status": "Error", "message": "Project already exists"}
        else:

            # get source project ID

            source_project = await db.projects.find_one({"project_name": json_record['source']})
            source_project_id = source_project.get('_id')
            print("Source project ID {}".format(source_project_id))

            # Create Project

            new_project = await db.projects.insert_one(json_record)
            print("project created {}".format(new_project.inserted_id))

            # Copy domains

            domains_cursor = db.domains.find({"project_id": str(source_project_id)})
            for domain in await domains_cursor.to_list(length=100):
                del domain['_id']
                domain['project_id'] = "{}".format(new_project.inserted_id)
                new_domain = await db.domains.insert_one(domain)
                print("new domain inserted with id {}".format(new_domain.inserted_id))

            # Copy Intents Entities etc TODO

            return {"status": "Success", "message": "Project Copied ID {}".format(new_project.inserted_id)}



class domainsModel():

    async def getDomains(project_id):
        query = {"project_id": project_id}
        cursor = db.domains.find(query)
        result = await cursor.to_list(length=1000)
        print("Domains sent {}".format(json.loads(dumps(result))))
        return json.loads(dumps(result))

    async def createDomain(record):

        json_record = json.loads(json.dumps(record))

        insert_record = {"project_id": json_record['project_id'], "domain_name": json_record['domain_name'],
                         "domain_description": json_record['domain_description']}

        # Check if domain exists already

        val_res = await db.domains.find_one({"project_id": json_record['project_id'],
                                             "domain_name": json_record['domain_name']})

        if val_res is not None:
            print('Domain already exists')
            return {"status": "Error", "message": "Domain already exists"}, None
        else:
            insert_result = await db.domains.insert_one(json.loads(json.dumps(insert_record)))
            print("Domain created with ID {}".format(insert_result.inserted_id))

            domains_list = await domainsModel.getDomains(json_record['project_id'])
            return {"status": "Success", "message": "Domain created successfully"}, domains_list

    async def deleteDomain(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}

        delete_record = await db.domains.delete_one(query)
        print("Domain Deleted count {}".format(delete_record))

        domains_list = await domainsModel.getDomains(json_record['project_id'])

        return {"status": "Success", "message": "Domain Deleted Successfully"}, domains_list

    async def updateDomain(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}
        update_field = {"$set": { "domain_name": json_record['domain_name'],
                                  "domain_description": json_record['domain_description']}}

        # Check if Domain already exists
        val_res = await db.domains.find_one({"project_id": json_record['project_id'],
                                             "domain_name": json_record['domain_name']})

        if val_res is None:
            update_record = await db.domains.update_one(query, update_field)
            print("Domain Updated , rows modified {}".format(update_record))

            domains_list = await domainsModel.getDomains(json_record['project_id'])
            return {"status": "Success", "message": "Domain updated successfully "}, domains_list

        elif val_res['domain_name'] == json_record['domain_name']:
            print("updating domain description")

            update_record = await db.domains.update_one(query, update_field)
            print("Domain Updated , rows modified {}".format(update_record))

            domains_list = await domainsModel.getDomains(json_record['project_id'])
            return {"status": "Success", "message": "Domain updated successfully "}, domains_list

        else:
            print('Domain already exists')
            return {"status": "Error", "message": "Domain already exists"}, None


class intentsModel():

    async def getIntents(record):

        json_record = json.loads(json.dumps(record))

        cursor = db.intents.find(json_record, {"project_id": 1, "domain_id": 1, "intent_name": 1, "intent_description": 1})
        result = await cursor.to_list(length=1000)
        json_result = json.loads(dumps(result))
        print("Intents sent {}".format(json_result))
        return json_result

    async def createIntent(record):

        json_record = json.loads(json.dumps(record))

        insert_record = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id'],
                         "intent_name": json_record['intent_name'],
                         "intent_description": json_record['intent_description'], "text_entities": [""]}

        val_res = await db.intents.find_one({"project_id": json_record['project_id'],
                                             "domain_id": json_record['domain_id'],
                                             "intent_name": json_record['intent_name']})

        if val_res is not None:
            print('Intent already exists')
            return {"status": "Error", "message": "Intent already exists"}, None
        else:
            result = await db.intents.insert_one(json.loads(json.dumps(insert_record)))
            message = {"status": "Success", "message": "Intent created with ID {}".format(result.inserted_id)}

            get_intents = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
            intents_list = await intentsModel.getIntents(get_intents)

            return message, intents_list

    async def deleteIntent(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}

        result = await db.intents.delete_one(query)
        print("Intent deleted successfully {}".format(result))
        message = {"status": "Success", "message": "Intent deleted successfully "}

        get_intents = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
        intents_list = await intentsModel.getIntents(get_intents)

        return message, intents_list

    async def updateIntent(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}
        update_field = {"$set": {"intent_name": json_record['intent_name'],
                                 "intent_description": json_record['intent_description']}}

        # Check if intent already exists
        val_res = await db.intents.find_one({"project_id": json_record['project_id'],
                                             "domain_id": json_record['domain_id'],
                                             "intent_name": json_record['intent_name']})

        if val_res is None or val_res['intent_name'] == json_record['intent_name']:

            update_record = await db.intents.update_one(query, update_field)

            print("Intent Updated , rows modified {}".format(update_record))

            get_intents = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
            intents_list = await intentsModel.getIntents(get_intents)

            return {"status": "Success", "message": "Intent Updated Successfully"}, intents_list
        else:
            return {"status": "Error", "message": "Intent Name already exists"}, None


class responsesModel():

    async def getResponses(record):

        json_record = json.loads(json.dumps(record))

        cursor = db.responses.find(json_record, {"project_id": 1, "domain_id": 1, "response_name": 1, "response_description": 1})
        result = await cursor.to_list(length=1000)

        print("Responses sent {}".format(json.loads(dumps(result))))
        return json.loads(dumps(result))


    async def createResponse(record):

        json_record = json.loads(json.dumps(record))

        insert_record = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id'],
                         "response_name": json_record['response_name'],
                         "response_description": json_record['response_description'], "text_entities": [""]}

        val_res = await db.responses.find_one({"project_id": json_record['project_id'],
                                               "domain_id": json_record['domain_id'],
                                               "response_name": json_record['response_name']})

        if val_res is not None:
            print('Response already exists')
            return {"status": "Error", "message": "Response already exists"}, None
        else:

            result = await db.responses.insert_one(json.loads(insert_record))
            print("Response created with ID {}".format(result.inserted_id))

            get_responses = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
            responses_list = await responsesModel.getResponses(get_responses)

            return {"status": "Success", "message": "Response created successfully"}, responses_list

    async def deleteResponse(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}

        result = await db.responses.delete_one(query)
        print("Response Deleted count {}".format(result))

        get_responses = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
        responses_list = await responsesModel.getResponses(get_responses)

        return {"status": "Success", "message": "Response Deleted successfully"}, responses_list

    async def updateResponse(record):

        json_record = json.loads(json.dumps(record))

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}
        update_field = {"$set": {"response_name": json_record['response_name'],
                                 "response_description": json_record['response_description']}}

        # Check if Response already exists
        val_res = await db.responses.find_one({"project_id": json_record['project_id'],
                                               "domain_id": json_record['domain_id'],
                                               "response_name": json_record['response_name']})

        if val_res is None or val_res['response_name'] == json_record['response_name']:
            update_record = await db.responses.update_one(query, update_field)

            print("Response Updated , rows modified {}".format(update_record))

            get_responses = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
            responses_list = await responsesModel.getResponses(get_responses)

            return {"status": "Success", "message": "Response Updated successfully"}, responses_list
        else:
            return {"status": "Error", "message": "Response Name already exists"}, None


class storyModel():

    async def getStories(record):

        json_record = json.load(record)

        cursor = db.stories.find(json_record)
        result = await cursor.to_list(length=1000)

        print("Stories sent {}".format(json.loads(dumps(result))))
        return json.loads(dumps(result))

    async def createStory(record):

        json_record = json.load(record)

        insert_record = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id'],
                         "story_id": json_record['story_id'], "story_name": json_record['story_name'],
                         "story_description": json_record['story_description'], "intents_responses": [""]}

        result = await db.stories.insert_one(json.loads(insert_record))
        print("Story created with ID {}".format(result.inserted_id))

        get_stories = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
        stories_list = await getStories(get_stories)

        return result, stories_list

    async def deleteStory(record):

        json_record = json.loads(record)

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}

        result = await db.stories.delete_one(query)
        print("Story Deleted count {}".format(result))

        get_stories = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
        stories_list = await getStories(get_stories)

        return result, stories_list

    async def updateStory(self):

        json_record = json.load(record)

        query = {"_id": ObjectId("{}".format(json_record['object_id']))}
        update_field = {"$set": {"story_id": json_record['story_id'], "story_name": json_record['story_name'],
                                 "story_description": json_record['story_description']}}
        update_record = await db.stories.update_one(query, update_field)

        print("Story Updated , rows modified {}".format(update_record))

        get_stories = {"project_id": json_record['project_id'], "domain_id": json_record['domain_id']}
        stories_list = await getStories(get_stories)

        return update_record, stories_list


class entityModel():

    async def getEntities(record):

        json_record = json.load(record)

        cursor = db.entities.find(json_record)
        result = await cursor.to_list(length=1000)

        print("Entities sent {}".format(json.loads(dumps(result))))
        return json.loads(dumps(result))