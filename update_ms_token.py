import requests as req
import json
import sys
import os
from base64 import b64encode
from nacl import encoding, public
import redis


#公钥获取
def getpublickey(Auth,geturl):
    headers={'Authorization': Auth}

    html = req.get(geturl,headers=headers)
    jsontxt = json.loads(html.text)
    if 'key' in jsontxt:
        print("公钥获取成功")
    else:
        #print("公钥获取失败，请检查secret里 GH_TOKEN 格式与设置是否正确")
        print(jsontxt)

    public_key = jsontxt['key']
    global key_id 
    key_id = jsontxt['key_id']
    return public_key

#微软refresh_token获取
#POST https://login.live.com/oauth20_token.srf
#Content-Type: application/x-www-form-urlencoded
#client_id={client_id}&redirect_uri={redirect_uri}&client_secret={client_secret}
#&refresh_token={refresh_token}&grant_type=refresh_token


def getmstoken(ms_token, client_id, client_secret):
    headers={'Content-Type':'application/x-www-form-urlencoded'
            }
    data={'grant_type': 'refresh_token',
          'refresh_token': ms_token,
          'client_id':client_id,
          'client_secret':client_secret,
          'redirect_uri':'https://localhost/e5',
          'scope':'offline_access mail.read'
         }

    html = req.post('https://login.microsoftonline.com/common/oauth2/v2.0/token',data=data,headers=headers)
    jsontxt = json.loads(html.text)
    if 'refresh_token' in jsontxt:
        print(r'账号/应用的微软密钥获取成功')

    else:
        print(r'账号/应用的微软密钥获取失败'+'\n'+'请检查secret里 CLIENT_ID , CLIENT_SECRET , MS_TOKEN 格式与内容是否正确，然后重新设置')
        return None,None
    refresh_token = jsontxt['refresh_token']
    access_token = jsontxt['access_token']
    return refresh_token, access_token


#token上传
def setsecret(encrypted_value,skey_id, gh_repo, str_name):
    headers={'Accept': 'application/vnd.github.v3+json','Authorization': Auth}
    #data={'encrypted_value': encrypted_value,'key_id': key_id}  ->400error
    data_str=r'{"encrypted_value":"'+encrypted_value+r'",'+r'"key_id":"'+key_id+r'"}'
    secret_url = r'https://api.github.com/repos/'+skey_id +'/' +gh_repo+r'/actions/secrets/'+str_name


    putstatus=req.put(secret_url,headers=headers,data=data_str)
    if putstatus.status_code >= 300:
        print(r'账号/应用的密钥上传失败，请检查secret里 GH_TOKEN 格式与设置是否正确')
    else:
        print(r'账号/应用的密钥上传成功')
    return putstatus

#token加密
def createsecret(public_key,secret_value):
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")
    



gh_token=os.getenv('GH_TOKEN')
client_id=os.getenv('CLIENT_ID')
client_secret=os.getenv('CLIENT_SECRET')
heartbeat = os.getenv('GITACTION_HEARTBEAT)
                      
r_host = 'redis-12906.c285.us-west-2-2.ec2.cloud.redislabs.com'
r_port = 12906
r_passwd = os.getenv('REDIS_PWD')

gh_repo = r'auto_notification'

#=========================test=======================
#str要求大写
#gh_repo = r'auto_notification'
#====================================================
Auth=r'token '+gh_token
skey_id=r'hexcoo'

geturl='https://api.github.com/repos/'+skey_id+r'/'+gh_repo+r'/actions/secrets/public-key'

try:

    r= redis.StrictRedis(host=r_host,port=r_port,password=r_passwd, charset="utf-8", decode_responses=True)
    #get token
    
    refresh_token = os.getenv('MAIL_REFRESH_TOKEN')
 #   print(refresh_token)
    #get update_token
    refresh_token, access_token = getmstoken(refresh_token, client_id, client_secret)
    #if not refresh_token == None:
        #r.set('mail_refresh_token', refresh_token)
    r.set('mail_access_token', access_token)
    #else:
        #r.set('mail_refresh_token', refresh_token)

    #update github secret
    str_name = 'MAIL_REFRESH_TOKEN'
    encrypted_value=createsecret(getpublickey(Auth, geturl), refresh_token)
    setsecret(encrypted_value, skey_id,gh_repo, str_name)
    req.get(heartbeat, timeout=3)
#        print('get access_token: \n')
#        print(access_token)
#        print('get refresh_token')
#        print(refresh_token)
    '''
    #upload secret 
    pub_key = getpublickey(Auth, geturl)
    encrypted_value=createsecret(pub_key, client_secret)
    setsecret(encrypted_value, skey_id, gh_repo, str_name)
    '''
except Exception as e:
    print('error: ')
    print(e)
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
