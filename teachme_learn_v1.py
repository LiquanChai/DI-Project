
# coding: utf-8

# In[1]:


import logging
from flask import Flask
from flask_ask import Ask, statement, question, context

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError


# In[2]:


###
# framework set up
###

# add debug logs
# log = logging.getLogger()
# log.addHandler(logging.StreamHandler())
# log.setLevel(logging.DEBUG)
logging.getLogger("flask_ask").setLevel(logging.DEBUG)

# initialise flask-ask
app = Flask(__name__)
ask = Ask(app, "/")

###
# database set up
###

dynamodb = boto3.resource("dynamodb", region_name="eu-west-2", endpoint_url="https://dynamodb.eu-west-2.amazonaws.com")
table = dynamodb.Table("Conversation") # the key is device_id


# In[41]:


###
# database utils
###

# get data from dynomodb, key error - no item found
def get_item(key): # key - device id
    key_dict = {"device_id": key}
    try:
        response = table.get_item(Key=key_dict)
    except ClientError as e:
        print(e.response["Error"]["Message"])
    else:
        item = response["Item"]
        return item

# put/update data to dynamodb
def update_item(key, intent_id, intent_name, corpus_name, mode_name):
    key_dict = {"device_id": key}
    expression ="set intent_id = :a, intent_name = :b, corpus_name = :c, mode_name = :d"
    expression_values = {":a": intent_id, ":b": intent_name, ":c": corpus_name, ":d": mode_name}
    try:
        response = table.update_item(Key=key_dict, UpdateExpression=expression, 
                                     ExpressionAttributeValues=expression_values,
                                     ReturnValues="UPDATED_NEW")
    except ClientError as e:
        print(e.response["Error"]["Message"])
        
def update_item_attribute(key, attribute_name, attribute_value):
    key_dict = {"device_id": key}
    expression ="set {} = :a".format(attribute_name)
    expression_values = {":a": attribute_value}
    try:
        response = table.update_item(Key=key_dict, UpdateExpression=expression, 
                                     ExpressionAttributeValues=expression_values,
                                     ReturnValues="UPDATED_NEW")
    except ClientError as e:
        print(e.response["Error"]["Message"])

# delete data from dynamodb, delete non-exiting item will not throw an error
def delete_item(key):
    key_dict = {"device_id": key}
    try:
        response = table.delete_item(Key=key_dict)
    except ClientError as e:
        print(e.response["Error"]["Message"])


# In[28]:


###
# functional utils
###

def extract_keywords(raw_sentence): # input card sentence, return str
    import re
    pattern = re.compile(r"\(([a-zA-Z0-9 \']+)\)")
    if pattern.search(raw_sentence):
        return "Keywords:\n" + ", ".join(pattern.findall(raw_sentence))
    else:
        return "No keywords listed"
    
def ignore_keywords(raw_sentence):
    import re
    pattern = re.compile(r"\(([a-zA-Z0-9 \']+)\)")
    if pattern.search(raw_sentence):
        raw_sentence = raw_sentence.replace("(", "")
        raw_sentence = raw_sentence.replace(")", "")
    return raw_sentence


# In[29]:


###
# model of corpus
###

class Corpus:
    def __init__(self, corpus_filename):
        self.meta_data = {}
        self.data = {}
        
        self.load_corpus(corpus_filename)
        
    def load_corpus(self, corpus_filename):
        with open(corpus_filename) as f:
            raw_data = []
            for line in f:
                raw_data.append(line)
        raw_data = [line.split("::")[-1].strip().replace("\\n", "\n") for line in raw_data]
        
        for i in range(0, len(raw_data), 7): # each conversational must have 7 lines
            self.meta_data[str(int(i/7))] = {}
            self.meta_data[str(int(i/7))]["intent_id"] =  str(int(i/7))
            self.meta_data[str(int(i/7))]["intent_name"] =  raw_data[i].split(",")[1].strip()
            self.meta_data[str(int(i/7))]["corpus_name"] =  raw_data[i].split(",")[-1].strip()
            
            self.data[str(int(i/7))] = {}
            self.data[str(int(i/7))]["user_response"] =  raw_data[i+1]
            self.data[str(int(i/7))]["alexa_response"] =  raw_data[i+2]
            self.data[str(int(i/7))]["card_text"] = raw_data[i+3]
            self.data[str(int(i/7))]["context"] = raw_data[i+4]
            self.data[str(int(i/7))]["img_url"] = raw_data[i+5]
            i += 7
        
    def get_meta_data(self, intent_id): # return dict
            return self.meta_data[intent_id]
            
    def get_data(self, intent_id):
            return self.data[intent_id] # return dict
        
    def get_end_id(self):
        return len(corpus.meta_data)


# In[34]:


corpus = Corpus("restaurant_corpus")
# print(len(corpus.meta_data))
# print(corpus.get_data("3")["alexa_response"].format("New York strip steak"))
# print(corpus.get_data("2")["card_text"])
# print(extract_keywords(corpus.get_data("2")["card_text"]))
# print(extract_keywords(corpus.get_data("8")["card_text"]))
# print(ignore_keywords(corpus.get_data("2")["card_text"]))
# print(ignore_keywords(corpus.get_data("8")["card_text"]))
extract_keywords(corpus.data["1"]["card_text"])


# In[ ]:


###
# main application
###

@ask.launch
def welcome_response():
    
    card_title = "Welcome!"
    
    card_content = "Welcome to teach me skill. What do you want to learn?\n"
    card_content += "\n"
    card_content += "You could say:\n"
    card_content += "1. Describe symptom in full sentence mode/keywords mode\n"
    card_content += "2. Order food in full sentence mode/keywords mode\n"
    card_content += "\n"
    card_content += "----------\n"
    card_content += "To end the skill: 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation: 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation: 'Alexa, ask teachme to clear the progress'\n"
    
    welcome_text = "Welcome to Teach me skill. Which scenario do you want to learn? I will help you to practice it."
    reprompt_text = "I'm sorry - I didn't get it, could you please say that again?"
    
    img_url = "https://s3.eu-west-2.amazonaws.com/echo.learn.image.bucket/blank.png"

    return question(welcome_text).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                        small_image_url=img_url, 
                                                                        large_image_url=img_url)

@ask.intent('AMAZON.CancelIntent')
def cancel_intent():
    return statement("Okay, good bye.")

@ask.intent('AMAZON.StopIntent')
def stop_intent():
    return statement("Okay, good bye.")

@ask.intent('AMAZON.HelpIntent')
def help_intent():
    
    card_title = "Help!"
    
    card_content += "To start a new scenario - e.g.'Describe symptom in keywords mode', 'Order food in full sentence mode'\n"
    card_content += "\n"
    card_content += "----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    img_url = "https://s3.eu-west-2.amazonaws.com/echo.learn.image.bucket/blank.png"
    
    return statement("Here is a list of command you could say.").standard_card(title=card_title, text=card_content, 
                                                                               small_image_url=img_url, 
                                                                               large_image_url=img_url)

@ask.intent("continue_intent")
def continue_intent():
    # get the previous conversation state from the database
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    intent_id = previous_data["intent_id"]
    intent_name = previous_data["intent_name"]
    corpus_name = previous_data["corpus_name"]
    mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Continue!"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # add image for the card
    img_url = "https://s3.eu-west-2.amazonaws.com/echo.learn.image.bucket/blank.png"
    
    # push the card with an empty question
    return question("Okay, now look at the card").reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                                        small_image_url=img_url, 
                                                                                        large_image_url=img_url)
    
@ask.intent("clear_intent")
def clear_intent():
    # clear all entries from the database
    device_id = context.System.device.deviceId
    delete_item(device_id)
    
    # push the card with an statement
    card_title = "Clear conversational data!"
    card_content = "Now the data is cleared.\nYou could invoke the skill again to start a new conversation."
    return statement("Okay, now the conversation is cleared").simple_card(title=card_title, content=card_content)

# intent to load restaurant corpus, choose mode and start the initial question
@ask.intent("start_restaurant_intent") # "0"
def start_restaurant_intent(mode_name):
    # initialise the conversation state to the database - "0"
    device_id = context.System.device.deviceId
    intent_id = "0"
    intent_name = "start_restaurant_intent"
    corpus_name = "restaurant_corpus"
    
    update_item(device_id, intent_id, intent_name, corpus_name, mode_name) # mode_name should be str

    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # get ready for the conversation
    start_template = "<speak>Loading corpus, please wait for 5 seconds. Get ready. <break time='5s'/> {}</speak>"
    
    # push the card with Alexa response from the current conversation state - "0"
    return question(start_template.format(alexa_response)).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                                                 small_image_url=img_url, 
                                                                                                 large_image_url=img_url)

@ask.intent("second_restaurant_intent") # "1"
def second_restaurant_intent():
    # get the previous conversation state from the database - "0"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "start_restaurant_intent":
        # update the current conversation state to the database - "1"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "second_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "1"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("third_restaurant_intent") # "2"
def third_restaurant_intent():
    # get the previous conversation state from the database - "1"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "second_restaurant_intent":
        # update the current conversation state to the database - "2"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "third_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "2"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("fourth_restaurant_intent") # "3"
def fourth_restaurant_intent():
    # get the previous conversation state from the database - "2"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "third_restaurant_intent":
        # update the current conversation state to the database - "3"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "fourth_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "3"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("fifth_restaurant_intent") # "4"
def fifth_restaurant_intent(food_name):
    # get the previous conversation state from the database - "3"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "fourth_restaurant_intent":
        # update the current conversation state to the database - "4"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "fifth_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    # send user's main course to the database as a new attribute
    import re
    if re.search("rib", food_name): # main course == rib-eye
        main_course_name = "rib eye steak"
    else:
        main_course_name = "New York strip steak"
    update_item_attribute(device_id, "main_course_name", main_course_name)
    
    # get response (main course name) from database
    alexa_response = corpus.data[intent_id]["alexa_response"].format(get_item(device_id)["main_course_name"])
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "4"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("sixth_restaurant_intent") # "5"
def sixth_restaurant_intent():
    # get the previous conversation state from the database - "4"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "fifth_restaurant_intent":
        # update the current conversation state to the database - "5"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "sixth_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    # get response (main course name) from database
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "5"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)
    

@ask.intent("seventh_restaurant_intent") # "6"
def seventh_restaurant_intent():
    # get the previous conversation state from the database - "5"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "sixth_restaurant_intent":
        # update the current conversation state to the database - "6"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "seventh_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    # get response (main course name) from database
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "6"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("eighth_restaurant_intent") # "7"
def eighth_restaurant_intent():
    # get the previous conversation state from the database - "6"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "seventh_restaurant_intent":
        # update the current conversation state to the database - "7"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "eighth_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    # get response (main course name) from database
    alexa_response = corpus.data[intent_id]["alexa_response"].format(get_item(device_id)["main_course_name"])
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "7"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

# intent for ninth step of restaurant corpus and the end of the conversation
@ask.intent("ninth_restaurant_intent") # "8"
def ninth_restaurant_intent():
    # get the previous conversation state from the database - "7"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "eighth_restaurant_intent":
        # update the current conversation state to the database - "8"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "ninth_restaurant_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Restaurant scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    # get response (main course name) from database
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # get ready for the end of the conversation
    end_template = "<speak>{} <break time='3s'/> Thank you for practicing. This is the end of the conversation.</speak>"
    
    # since it is the last intent of the conversation, clear the database
    delete_item(device_id)
    
    # push the card with Alexa response from the current conversation state - "8"
    return statement(end_template.format(alexa_response)).standard_card(title=card_title, text=card_content,
                                                                        small_image_url=img_url, 
                                                                        large_image_url=img_url)


# In[ ]:


# intent to load symptom corpus, choose mode and start the initial question
@ask.intent("start_symptom_intent") # "0"
def start_symptom_intent(mode_name):
    # initialise the conversation state to the database - "0"
    device_id = context.System.device.deviceId
    intent_id = "0"
    intent_name = "start_symptom_intent"
    corpus_name = "symptom_corpus"
    
    update_item(device_id, intent_id, intent_name, corpus_name, mode_name) # mode_name should be str

    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
        
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # get ready for the conversation
    start_template = "<speak>Loading corpus, please wait for 5 seconds. Get ready. <break time='5s'/>, {}</speak>"
    
    # push the card with Alexa response from the current conversation state - "0"
    return question(start_template.format(alexa_response)).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                                                 small_image_url=img_url, 
                                                                                                 large_image_url=img_url)

@ask.intent("second_symptom_intent") # "1"
def second_symptom_intent():
    # get the previous conversation state from the database - "0"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "start_symptom_intent":
        # update the current conversation state to the database - "1"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "second_symptom_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update, stay at the current state
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "1"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("third_symptom_intent") # "2"
def third_symptom_intent():
    # get the previous conversation state from the database - "1"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "second_symptom_intent":
        # update the current conversation state to the database - "2"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "third_symptom_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update, stay at the current state
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "2"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("fourth_symptom_intent") # "3"
def fourth_symptom_intent():
    # get the previous conversation state from the database - "2"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "third_symptom_intent":
        # update the current conversation state to the database - "3"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "fourth_symptom_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update, stay at the current state
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "3"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

@ask.intent("fifth_symptom_intent") # "4"
def fifth_symptom_intent():
    # get the previous conversation state from the database - "3"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "fourth_symptom_intent":
        # update the current conversation state to the database - "4"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "fifth_symptom_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update, stay at the current state
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # add extra time for user to response
    reprompt_text = "Sorry, I didn't get it. Could you please say that again?"
    
    # push the card with Alexa response from the current conversation state - "4"
    return question(alexa_response).reprompt(reprompt_text).standard_card(title=card_title, text=card_content, 
                                                                          small_image_url=img_url, 
                                                                          large_image_url=img_url)

# intent for sixth step of symptom corpus and the end of the conversation
@ask.intent("sixth_symptom_intent") # "5"
def sixth_symptom_intent():
    # get the previous conversation state from the database - "4"
    device_id = context.System.device.deviceId
    previous_data = get_item(device_id)
    
    # check if the previous intent name equal to restaurant_start_intent
    previous_intent = previous_data["intent_name"]
    if previous_intent == "fifth_symptom_intent":
        # update the current conversation state to the database - "5"
        intent_id = str(int(previous_data["intent_id"]) + 1)
        intent_name = "sixth_symptom_intent"
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
        update_item(device_id, intent_id, intent_name, corpus_name, mode_name)
    else: # do not update, stay at the current state
        intent_id = previous_data["intent_id"]
        intent_name = previous_data["intent_name"]
        corpus_name = previous_data["corpus_name"]
        mode_name = previous_data["mode_name"]
    
    # get data from the corpus
    corpus = Corpus(corpus_name)
    card_title = "Symptom scenario"
    card_content = corpus.data[intent_id]["context"]
    card_content += "\n"
    card_content += " "
    card_content += "\n"
    
    # choose what to display according to the mode
    if mode_name == "keywords":
        card_content += extract_keywords(corpus.data[intent_id]["card_text"])
    else:
        card_content += ignore_keywords(corpus.data[intent_id]["card_text"])
    
    alexa_response = corpus.data[intent_id]["alexa_response"]
    img_url = corpus.data[intent_id]["img_url"]
    
    # add hints for voice commands
    card_content += "\n\n----------\n"
    card_content += "To end the skill - 'Alexa, exit/stop'\n"
    card_content += "To resume the conversation - 'Alexa, ask teachme to continue'\n"
    card_content += "To clear the previous conversation - 'Alexa, ask teachme to clear the progress'\n"
    
    # get ready for the end of the conversation
    end_template = "<speak>{} <break time='3s'/> Thank you for practicing. This is the end of the conversation.</speak>"
    
    # since it is the last intent of the conversation, clear the database
    delete_item(device_id)
    
    # push the card with Alexa response from the current conversation state - "5"
    return statement(end_template.format(alexa_response)).standard_card(title=card_title, text=card_content, 
                                                                                                small_image_url=img_url, 
                                                                                                large_image_url=img_url)


# In[42]:


# key = "abc"
# main_course_name = "rib eye steak"

# update_item("abc", "0","start_intent", "symptom", "keywords")


# In[45]:


# update_item_attribute("abc", "main_course_name", "rib eye steak")
# get_item("abc")["main_course_name"]


# In[ ]:


if __name__ == '__main__':
    app.run(debug=True)

