import json

def med_extracter(med_list):
    if isinstance(med_list, str):
        try:
            m = json.loads(med_list)
        except json.JSONDecodeError:
            # Create JSON if needed
            med_list_json = json.dumps([med_name for med_name in med_list.splitlines()])
            m = json.loads(med_list_json)
    else:
        m = med_list 
    return m


med_dict = {
  "medicine_list": [
    {
      "medicine_name": "order",
      "quantity": "10"
    },
    {
      "medicine_name": "dolo 650",
      "quantity": ""
    }
  ]
}

