# -*- coding: UTF-8 -*-
import os
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


