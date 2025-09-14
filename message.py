import requests

API_KEY = 'pk_rk5nsrnXmOw71DE6W057hdT3aqVPYLuzEPlpFuKn_kY'
MESSAGE = 'send a message in the group chat that I have with seven'

response = requests.post(
    'https://poke.com/api/v1/inbound-sms/webhook',
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    },
    json={'message': MESSAGE}
)

print(response.json())