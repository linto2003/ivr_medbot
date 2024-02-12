import openai
from med_extract import med_extracter
from test_sms import sms
from test_search import med_classifier
from word2number import w2n
import pyodbc as db
from ast import literal_eval
import uuid
from firebase_admin import credentials,auth
from firebase_admin import firestore
import datetime
import firebase_admin

openai.api_key = 'OPEN_AI API KEY'
phone_number = None

cred = credentials.Certificate("./ivrapp-a8748-firebase-adminsdk-oktco-0f76968c07.json")
defaultApp = firebase_admin.initialize_app(cred)

db_fire = firestore.client()

conn = db.connect('DRIVER={ODBC Driver 11 for SQL Server};SERVER=YOUR_SERVER_NAME\SQLEXPRESS;DATABASE=MEDICINE_DATABASE;UID=sa;PWD=YOUR_PASSWORD')
conn.setdecoding(db.SQL_CHAR, encoding='latin1')
conn.setencoding('latin1')




class OrderChatbot:
    def __init__(self):
        self.order = []
        self.current_order = {}
        self.order_number = 1
        self.current_item = None
        self.current_quantity = None
        self.available  = None
        self.total_cost = 0
        self.medicine = []
        self.indicator = 0

    def start_chat(self):
        print("Welcome to the Order Chatbot!")
        print("You can order items by typing 'order <item> <quantity>'.")
        print("Type 'done' when you are finished with your order.")
        
        while True:
            user_input = input("User: ")
            response = self.process_input(user_input)
            print("Bot:", response)
            

         

    def process_input(self, user_input):
       
        if user_input.lower() == 'done':# Order final
            return self.finalize_order()
        elif user_input.lower() == 'status': #Know about order details
            return self.check_order_status()
        elif any(word in user_input.lower() for word in ('order','want','give')): #Order command
            return self.add_to_order(user_input)
        elif user_input.isdigit() and int(user_input)<3: # User choice
            return self.handle_user_choice(user_input)
        elif user_input.isdigit() and 4>=int(user_input)>2:# select quantity available or alternative
            return self.handle_order(user_input)
        elif user_input.isdigit() and int(user_input)==5:
            return self.handle_alternative(user_input)
        elif user_input.isdigit() and int(user_input)==6:
            return self.add_to_order(user_input)
        else:
            return "Sorry, I didn't understand that. Please use the format 'order quantity medicine name ' or say 'status' to check your order."



    def medicine_getter_chat(self , userinput):
        message = userinput
        messages = [ {"role": "system", "content": "you are dumb only do what is said"} ]
        message = "give a json list (\"medicine_list\") of medicine names(only medicine name) as \"name\" and quantity respectively from the following : " + message
        messages.append( 
                {"role": "user", "content": message}, 
            ) 
        chat = openai.ChatCompletion.create( 
                model="gpt-3.5-turbo", messages=messages 
            ) 
        med_list = dict()
        reply = chat.choices[0].message.content
        med_list = reply
        messages.append({"role": "assistant", "content": reply})
        return med_list 
    
    def prescription_taker(self,user_input):
        
        self.indicator = user_input
        return self.indicator



    def add_to_order(self, user_input):
        try:
            # _, quantity, item = user_input.split()
            
           
            item_list = self.medicine_getter_chat(user_input)
           
        
            try:
                    item_list = med_extracter(item_list)
          
                    
                    item = item_list['medicine_list'][0]['name']
                    quantity = item_list['medicine_list'][0]['quantity']
                    if str(quantity).isdigit():
                        quantity = int(quantity)
                    else:
                        quantity = w2n.word_to_num(quantity)
            except Exception as e:
                    print(f"An error occurred while extracting information: {e}")
                    
                    return "Invalid input. Please use the format 'order <item> <quantity>'."
 

            options = self.get_item_options(item)
            if options:
                self.current_item = item
                self.current_quantity = quantity
                return self.ask_user_for_choice(item, options)
                
            if item in self.order:
                available = self.check_inventory(item,quantity)
                if available == 'yes':
                    self.current_order = {'medicine':item,'quantity':quantity}
                    if self.order:
                        for i in range(1,len(self.order)):
                          if self.order[i]['medicine'] == item:
                              self.order[i]['quantity'] +=quantity
                              

                elif available!='yes'or'no':
                    return self.ask_order(item,quantity,available)    
                else:
                    return self.find_alternative(item,quantity)    
            else:
                 if self.check_inventory(item,quantity)=='yes':
                    self.order.append({'medicine':item,'quantity':quantity})
                    print('adding new item')
                    self.order_number += 1
                    return f"Added {quantity} {item}(s) to your order."
                 else:
                     return "Sorry we don't have the required medicine try saying only the first name of the medicine"    
                
           
        except ValueError:
            return "Invalid input. Please use the format 'order <item> <quantity>'."

    
    def ask_order(self,item,available):
        self.available = available
        prompt =f"Inventory only have {available} quantity of {item} if you want to proceed Press 3 for alternative press 4"
        return prompt

    def handle_order(self,choice):
          choice = int(choice)
          if choice == 3:
                self.current_order = {'medicine':self.current_item,'quantity':self.available}
                order_present = -1
                if self.order:
                    for key , order in enumerate(self.order):
                      if order['medicine'] == self.current_item:
                          order_present = key
                              
                if order_present>=0:  
                   self.order[order_present]['quantity'] += self.available

                else:
                  self.order.append(self.current_order)
                  self.order_number +=1
                return f"Added {self.available} {self.current_item}(s) to your order."       
          else :
            return self.find_alternative(self.current_item, self.current_quantity)



    def check_inventory(self,item,quant):
        cursor = conn.cursor()
 
        cursor.execute("""SELECT quantity, prescription FROM inventory 
                       join medicines on inventory.med_key = medicines.med_key
                       join prescription on inventory.med_key = prescription.med_key
                        where name = ? """,f'{item}')
        rows = cursor.fetchall()
       
        try:
            prescription = (rows[0][1])
            print(type(prescription))
            quantity = (rows[0][0])
          
        except:
            quantity = 0   
            prescription = -1 
        if quantity>0 and quantity>quant and prescription == 0:
            return 'yes'
        elif quantity>0 and quantity<quant and prescription == 0:
            return quantity
        elif prescription == 1:
            return 'prescription'
        else:
            return'no'

    def find_alternative(self,item,quantity):
        cursor = conn.cursor()
        cursor.execute("select use_key,comp_id from medicines where name = ?",item)
      
        rows = cursor.fetchall()

        cursor.execute("""
                SELECT m.name ,s.side_effects
                FROM medicines m     
                JOIN uses u ON m.use_key = u.use_id
                JOIN inventory i ON i.med_key = m.med_key
                JOIN side_effect s ON s.side_effect_id = m.side_effect_id      
                WHERE u.use_id = ? AND m.comp_id = ? AND i.quantity > ? """, (rows[0][0], rows[0][1], quantity)  )
        rows = cursor.fetchall()
        
        if rows:
            self.current_item = rows[1][0]
            se_list = literal_eval(rows[1][1])
            se_prompt =', '.join(str(se) for se in se_list) 
        else :
            return 'We have no alternative for this medicine in the provided quantity'   
       
 
        return f'{item} is unavailable, consider {self.current_item} with possible side effects {se_prompt}. Press 5 to proceed or 6 to cancel.'       

    def handle_alternative(self,choice):
        choice = int(choice)
        if choice == 5 :
            order_present = -1
            self.current_order = {'medicine':self.current_item,'quantity':self.current_quantity}
            if self.order:
                  for key , order in enumerate(self.order):
                      if order['medicine'] == self.current_item:
                          order_present = key

                              
            if order_present>=0:
                self.order[order_present]['quantity'] += self.current_quantity
            else:
                self.order.append(self.current_order)
                self.order_number+=1
               
            return f"Added {self.current_quantity} {self.current_item}(s) to your order."
        else:
            return 'Since you haven\'t pressed any key or pressed the wrong one, we\'ll continue with your order'
                    

    def ask_user_for_choice(self, item, options):
       
        options_prompt = "\n".join(f"Press {i+1} for {option}" for i, option in enumerate(options))
        options_list = " or ".join(f"{option}" for option in options)
        prompt = f"By saying {item} did you mean {options_list}? {options_prompt}"
        return prompt
    
    def handle_user_choice(self, choice):
        options = self.get_item_options(self.current_item)
      
        choice = int(choice)
      
        if choice < 0 or choice > len(options):
            options_prompt = "\n".join(f"Press {i+1} for {option}" for i, option in enumerate(options))
            return f"Invalid choice. Please try again.{options_prompt}"
      
        item = options[choice-1]
        self.current_item = item
        available = self.check_inventory(item,self.current_quantity)
        print(self.current_item ,"is there : ",self.check_inventory(item,self.current_quantity))
        print("Ind::",self.indicator) 
      
        print(available == 'prescription' and self.indicator == '2')
        if self.check_inventory(item,self.current_quantity) =='yes':
           
            order_present = -1
            self.current_order = {'medicine':self.current_item,'quantity':self.current_quantity}
           
            if self.order :
                 for key , order in enumerate(self.order):
                      if str(order['medicine']) == str(self.current_item):
                          order_present = key

           
            if order_present>=0:
                self.order[order_present]['quantity'] += self.current_quantity
            
            else:
             
                self.order.append(self.current_order)
                self.order_number += 1
            return f"Added {self.current_quantity} {item} to your order."
        
        elif available not in ['yes', 'no', 'prescription']:
            
                return self.ask_order(item,available)
           
        elif available == 'prescription' and self.indicator == '0':
            return "You can not order this medicine without prescription "
        elif available == 'prescription' and self.indicator == '2':
           
            if self.current_item in self.medicine:
                order_present = -1
                self.current_order = {'medicine':self.current_item,'quantity':self.current_quantity}
            
                if self.order :
                    for key , order in enumerate(self.order):
                        if str(order['medicine']) == str(self.current_item):
                            order_present = key

            
                if order_present>=0:
                    self.order[order_present]['quantity'] += self.current_quantity
                
                else:
                
                    self.order.append(self.current_order)
                    self.order_number += 1
                return f"Added {self.current_quantity} {item} to your order."
            else:
                return"You can not order this medicine without prescription" 
                  
        else:
            return  "We dont have the medicine in the inventory"  

    def verify(self, code):
        print('Verifying')
        query = db_fire.collection("users").where("phoneNumber", "==",phone_number)
        docs = query.get()
        if docs:
            userid = docs[0].id
            print(userid)

        query = db_fire.collection("prescriptions").where("userid","==",userid)  
        docs = query.get()
        for doc in docs:
            doc = doc.to_dict()
            code_verify = doc['id']
            print("Code type",type(int(code)))
            print("code_verify",type(code_verify))
            if int(code)== code_verify:
                 self.medicine = doc['medicines'] 
                 return 'true'
            
            
    def finalize_order(self):
        if not self.order:
            return "Your order is empty. Goodbye!"
        items = []
        quants = []
       
        total_cost = sum(self.calculate_cost(data['medicine'], data['quantity']) for data in self.order)
       
        for order in self.order:
            quants.append(order['quantity'])
            items.append(order['medicine'])
            quantity_prompt = "\n".join(f"{quants[i]} quantity of {item}" for i, item in enumerate(items))    
        self.total_cost = total_cost
        order = {'id':str(uuid.uuid4()) ,'medicineName':[]}

        query = db_fire.collection("users").where("phoneNumber", "==",phone_number)

        docs = query.get()
        if docs:
            userid = docs[0].id
        else:
            user = {'address':'','email':'','id':str(uuid.uuid4()),'phoneNumber':phone_number,'username':''}
            db_fire.collection("users").document(user['id']).set(user)
            userid = user['id']

      
        order['medicineName'] = items
        order['quantity'] = quants
        order['totalCost'] =self.total_cost
        order['userid'] = userid
        order['orderTitle'] = 'Linto'
        order['phoneNumber'] = phone_number
        now = datetime.datetime.now()
        order['orderDate'] = now.strftime("%Y-%m-%d %H:%M:%S")
        order['order_type'] = self.indicator

        print(order)
        db_fire.collection("orders").document(order['id']).set(order)
        sms(f"Thank you for your order! You ordered {quantity_prompt} with a total cost of ${self.total_cost:.2f}.\nPlease confirm your order by paying the ammount . Click the link ::\n upi://pay?pa=9372846997@ybl&pn=Aniket&mc=&tid=&tr=Payment&tn=Payment&am={self.total_cost:.2f}&cu=INR",phone_number)
        return f"Thank you for your order! You ordered {quantity_prompt} with a total cost of ${self.total_cost:.2f}. Goodbye!"

    def calculate_cost(self, item, quantity):
        
        item_price = 5
        return item_price * quantity


    def check_order_status(self):
        if not self.order:
            return "Your order is empty."
        else:
            return f"Your current order: {self.order}"
        
    def get_item_options(self, item):
        cursor = conn.cursor()
        item = item.split()
        item_new = item[0]
        
        cursor.execute(f"SELECT TOP 20 name FROM medicines where name like '{item_new}%'")
        
        rows = cursor.fetchall()
        medicine_names = [medicine[0] for medicine in rows]
        item = str(item)
        med = med_classifier(medicine_names, item)
        options_map = {
            
        }
        lst = []
       
        try:
         if len(med) > 0 and str(type(med))=='<class \'list\'>':
            lst.append(med[0])

         if len(med) > 1 and str(type(med))=='<class \'list\'>':
            lst.append(med[1])
         elif str(type(med)) =='<class \'str\'>':
             lst.append(med)
        except IndexError:
         pass
        options_map[item] = lst
       
        return options_map.get(item, [])
    


