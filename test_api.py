import requests, io
from PIL import Image
SERVER='http://localhost:5000'
requests.post(f'{SERVER}/register', json={'username':'debuguser','email':'debug@test.com','password':'pwd'})
r_login=requests.post(f'{SERVER}/login', json={'username':'debuguser','password':'pwd'})
token=r_login.json().get('token')
img=io.BytesIO()
Image.new('RGB', (224,224), color='red').save(img, 'JPEG')
img.seek(0)
r=requests.post(f'{SERVER}/predict', headers={'Authorization':f'Bearer {token}'}, files={'image': ('im.jpg', img, 'image/jpeg')})
print(r.status_code, r.text)
