from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse
from twilio.rest import Client
from word2number import w2n
import pyodbc as db
import requests
import certifi
import openai
from common_utils import indicator
openai.api_key ='YOUR OPEN_AI API KEY'
from order_bot import OrderChatbot
print(indicator)
indicator = 0 

db_connection = 'DRIVER={ODBC Driver 11 for SQL Server};SERVER=YOUR_SERVER_NAME\SQLEXPRESS;DATABASE=MEDICINE_DATABASE;UID=sa;PWD=YOUR_PASSWORD'

conn = db.connect(db_connection)
conn.setdecoding(db.SQL_CHAR, encoding='latin1')
conn.setencoding('latin1')

app = Flask(__name__)
ca_bundle_path = certifi.where()
session = requests.Session()
session.verify = ca_bundle_path

# Create the Twilio client with the custom session
account_sid='PUT YOUR TWILIO ACCOUNT SID'
token = 'PUT YOUR TWILIO TOKEN'
twilio_client = Client(http_client=requests.Session())

order_bot = None  
user_name = None
phone_number = None


@app.route("/welcome", methods=['GET', 'POST'])
def welcome():
    response = VoiceResponse()
    print(f'Incoming call from {request.form["From"]}')
    phone_number = request.form["From"]
    print(phone_number)

    response.say('Welcome to medicine ordering chatbot.',voice = 'Polly.Raveena')
    response.redirect('/prescrip')
    return str(response)

@app.route("/prescrip", methods=['GET', 'POST'])
def prescp():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()
    
    response = VoiceResponse()
    gather = Gather(action='/handle_prescription', method='POST', input='dtmf', timeout = 5)
    gather.say('Press 0 if you have no prescription , Press 1 if you have prescription and you want to verify during delivery , Press 2 if you have prescription and you want to verify using code',voice = 'Google.en-IN-Standard-A')
    response.append(gather)
    return str(response)

@app.route("/handle_prescription", methods=['GET', 'POST'])
def handle_prescription():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()
    
    prescp_details = request.values.get('Digits', None)
    bot = order_bot.prescription_taker(prescp_details)
   
    if bot == '2':
            response = VoiceResponse()
            gather = Gather(action='/verify', method='POST', input='dtmf', timeout = 9)
            gather.say('Enter the prescription code',voice = 'Polly.Raveena')
            response.append(gather)
    else:
        response.redirect('/voice')
    return str(response)


@app.route("/verify", methods=['GET', 'POST'])
def verify():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()
    
    code = request.values.get('Digits', None)
    print(code)
    verify = order_bot.verify(code)
    response = VoiceResponse()
    if verify == 'true':
        response.say("Your code matched . Continue with your order",voice ='Polly.Raveena' )
        response.redirect('/voice')
    else :
        response.say("Your code does not match any user. Continue with your order",voice ='Polly.Raveena' )
        response.redirect('/voice')

    return str(response)    


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()
    
    response = VoiceResponse()
    gather = Gather(action='/handle-order', method='POST', input='speech',enhanced = True,speechModel = 'phone_call',language= 'en-IN',speech_timeout='auto')
    gather.say('Please say your order or "status" to know about your order',voice = 'Polly.Raveena')
    response.append(gather)
    return str(response)

@app.route('/add_more', methods=['POST'])
def add_items():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()

    response = VoiceResponse()

    gather = Gather(action='/handle-order', method='POST',language= 'en-IN',enhanced = True,speechModel = 'phone_call', input='speech',speech_timeout='auto')
    gather.say("Please say your order to add more items or say 'status' to check your order. If you are done then say done",voice = 'Polly.Raveena')
    response.append(gather)
    return str(response)

@app.route("/handle-order", methods=['POST'])
def handle_order():
    global order_bot

    order_details = request.values.get('SpeechResult', None)
    print('User: ', order_details)

    response = VoiceResponse()

    if order_details:
        order_bot_response = order_bot.process_input(order_details)
        print('Bot: ', order_bot_response)
        response.say(order_bot_response)
        if any(word in order_bot_response.lower() for word in ('invalid input', 'sorry', 'wrong input')):
            response.redirect('/voice')
        elif 'Added' in order_bot_response:
            response.redirect('/add_more')
        elif any(word.lower() in order_bot_response.lower() for word in ('which', 'press')):
            response.redirect('/get_user_choice')  # Redirect to ask for user's choice
        elif 'goodbye' in order_bot_response.lower(): 
            response.say("The call is now forwarded for payments",voice = 'Polly.Raveena') # Simplified condition for 'Thank'
            response.dial('+919324309587')
        else:
            response.say(order_bot_response,voice= 'Polly.Raveena')
    else:
        response.say("Sorry, I didn't catch that. Please try again.",voice = 'Polly.Raveena')

    return str(response)


@app.route("/get_user_choice", methods=['GET', 'POST'])
def get_user_choice():
    global order_bot

    response = VoiceResponse()

    gather = Gather( action="/handle-user-choice",method="POST",input='dtmf', timeout=5) 
    gather.say("Please press the number corresponding to your choice.",voice = 'Polly.Raveena')
    response.append(gather)
    return str(response)

@app.route("/handle-user-choice", methods=['GET', 'POST'])
def handle_user_choice():
    global order_bot
    response = VoiceResponse()
    response.say('Please wait till we process your order',voice = 'Polly.Raveena')
    c = 1
    choice = request.values.get('Digits', None)
  
    if choice and choice.isdigit():
        c = int(choice)
        
        if c<3:
            choice = c  
            print(choice)
            order_bot_response = order_bot.handle_user_choice(choice)
        elif 2<c<=4:
            order_bot_response = order_bot.handle_order(choice)   
        elif c == 5:
            order_bot_response = order_bot.handle_alternative(choice)   
        elif c == 6:
            response.redirect('/add_more')   
        
        response.say(order_bot_response)

        if 'Added' in order_bot_response:
            response.redirect('/add_more')  
        if 'Press' in order_bot_response:
            response.redirect('/get_user_choice')    
       
        else:
            response.redirect('/voice')  # Redirect to continue the conversation
    else:
        response = VoiceResponse()
        response.say("Invalid choice. Please try again.",voice = 'Polly.Raveena')
        response.redirect('/get_user_choice')  # Redirect to ask for user's choice

    return str(response)


if __name__ == '__main__':
    from pyngrok import ngrok
    port = 5000
    public_url = ngrok.connect(port, bind_tls=True).public_url
    print(public_url)

    number = twilio_client.incoming_phone_numbers.list()[0]

    number.update(voice_url=public_url + '/voice')
   
    print(f'Waiting for calls on {number.phone_number}')
   
    app.run(port=port)

    # order_bot = OrderChatbot()
    # order_bot.start_chat()