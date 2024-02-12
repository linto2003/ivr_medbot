from twilio.rest import Client
import requests
import certifi
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

ca_bundle_path = certifi.where()
session = requests.Session()
session.verify = ca_bundle_path

# Create the Twilio client with the custom session
account_sid='YOUR_TWILIO_SID'
token = 'YOUR_TWILIO_TOKEN'
twilio_client = Client(http_client=requests.Session())

def sms(text, number):

  message = twilio_client.messages.create(
      body=text,
      from_= '+16517287139',
      to = number
  )

  print(message.sid)
