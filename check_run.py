# -*- coding: UTF-8 -*-
import os
import sys
import requests as req
import redis

_host = 'redis-12906.c285.us-west-2-2.ec2.cloud.redislabs.com'
_port = 12906
_passwd = os.getenv('REDIS_PWD')

_tghost = 'api.telegram.org'
_tgbot_token = os.getenv('TG_TOKEN')
_chat_id = os.getenv('TG_CHAT_ID')
desp = ''

# Telegram Bot Push https://core.telegram.org/bots/api#authorizing-your-bot
def telegram(msg):
    data = (
        ('chat_id', _chat_id),
        ('text', msg + '\n\n' + desp)
    )
    response = req.post('https://' + _tghost + '/bot' + _tgbot_token + '/sendMessage', data=data)
    if response.status_code != 200:
        print('Telegram Bot 推送失败')
    else:
        print('Telegram Bot 推送成功')


msg = ''


try:
    r=redis.StrictRedis(host=_host,port=_port,password=_passwd)
    cookie_flag="valid"
    battery_percent=""
    tmp_flag=r.get('w-cookie')
    tmp_battery_percent=r.get('percent')

    if len(tmp_flag)==2:
        cookie_flag="expire"
        msg='weibo_cookie_status: ' + cookie_flag + ', battery_percent: ' + str(tmp_battery_percent)
        telegram(msg)
    tmp_battery_percent = int(tmp_battery_percent)
    if 27 > tmp_battery_percent:
        msg='weibo_cookie_status: ' + cookie_flag + ', battery_percent: ' + str(tmp_battery_percent)
        telegram(msg)
    
except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    print('error: ')
    print(e)
