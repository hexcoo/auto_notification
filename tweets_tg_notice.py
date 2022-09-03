import twint
import os
import sys
from datetime import datetime

#rewrite twint method tweets
import logging as logme
from asyncio import get_event_loop, TimeoutError, ensure_future, new_event_loop, set_event_loop

#for function checkData 
from twint.tweet import Tweet
from twint.output import datecheck
from twint.output import _output
from twint.storage import db
from twint import datelock, verbose, storage

import re

#for telegram bot 
import requests #as req
import redis

r_host = 'redis-12906.c285.us-west-2-2.ec2.cloud.redislabs.com'
r_port = 12906
r_passwd = os.getenv('REDIS_PWD')

_tghost = 'api.telegram.org'
_tgbot_token = os.getenv('TG_TOKEN')

_chat_id = os.getenv('TG_CHAT_ID')

_slack_webhook = os.getenv('SLACK_HOOK')
_slack_channel = '#twitter'

desp = ''

def formatDateTime(datetimestamp):
    try:
        return int(datetime.strptime(datetimestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    except ValueError:
        return int(datetime.strptime(datetimestamp, "%Y-%m-%d").timestamp())
def tg_bot_send(msg):
    data = (
         ('chat_id', _chat_id),
         ('text', msg + '\n\n' + desp)
    )
    response = requests.post('https://' + _tghost + '/bot' + _tgbot_token + '/sendMessage', data=data)
    if response.status_code != 200:
        print('Telegram Bot 推送失败')
    else:
        print('Telegram Bot 推送成功')

def slack_send(channel, msg):
    data = {
        "channel": channel,
        "username":"arm-test",
        "text": msg + "\n\n" ,
        "icon_emoji": ":robot_face:"
    }
    
    response = requests.post(_slack_host, json=data)
    if response.status_code != 200:
        print(response.text)
        print('Slack failure')
    else:
        print('Slack success')

'''
Test.py - Testing TWINT to make sure everything works.
'''


def get_twitter(config, callback=None):
    logme.debug(__name__ + ':Search')

    config.TwitterSearch = True
    config.Favorites = False
    config.Following = False
    config.Followers = False
    config.Profile = False
    #into def run
    try:
        get_event_loop()
    except RuntimeError as e:
        if "no current event loop" in str(e):
            set_event_loop(new_event_loop())
        else:
            logme.exception(__name__ + ':run:Unexpected exception while handling an expected RuntimeError.')
            raise
    except Exception as e:
        logme.exception(
                __name__ + ':run:Unexpected exception occurred while attempting to get or create a new event loop.')
        raise
    get_event_loop().run_until_complete(Twints(config).main(callback))


def format(config, t):
    if config.Format:
        output = config.Format.replace("{id}", t.id_str)
        output = output.replace("{conversation_id}", t.conversation_id)
        output = output.replace("{date}", t.datestamp)
        output = output.replace("{time}", t.timestamp)
        output = output.replace("{user_id}", t.user_id_str)
        output = output.replace("{username}", t.username)
        output = output.replace("{name}", t.name)
        output = output.replace("{place}", t.place)
        output = output.replace("{timezone}", t.timezone)
        output = output.replace("{urls}", ",".join(t.urls))
        output = output.replace("{photos}", ",".join(t.photos))
        output = output.replace("{video}", str(t.video))
        output = output.replace("{thumbnail}", t.thumbnail)
        output = output.replace("{tweet}", t.tweet)
        output = output.replace("{language}", t.lang)
        output = output.replace("{hashtags}", ",".join(t.hashtags))
        output = output.replace("{cashtags}", ",".join(t.cashtags))
        output = output.replace("{quote_url}", t.quote_url)
        #omit
    else:
        logme.debug(__name__+':Tweet:notFormat')
        output = f"{t.id_str} {t.datestamp} {t.timestamp} {t.timezone} "
        # TODO: someone who is familiar with this code, needs to take a look at what this is <also see tweet.py>
        # if t.retweet:
        #    output += "RT "
        output += f"<{t.username}> {t.tweet}"
        if config.Show_hashtags:
            hashtags = ",".join(t.hashtags)
            output += f" {hashtags}"
        if config.Show_cashtags:
            cashtags = ",".join(t.cashtags)
            output += f" {cashtags}"
        if config.Stats:
            output += f" | {t.replies_count} replies {t.retweets_count} retweets {t.likes_count} likes"
        if config.Translate:
            output += f" {t.translate} {t.trans_src} {t.trans_dest}"
    return output

async def checkData(tweet, config, conn):
    logme.debug(__name__ + ':checkData')
    tweet = Tweet(tweet, config)
    if not tweet.datestamp:
        logme.critical(__name__ + ':checkData:hiddenTweetFound')
        print("[x] Hidden tweet found, account suspended due to violation of TOS")
        return
    if datecheck(tweet.datestamp + " " + tweet.timestamp, config):
        #need to check newer massage
        config.new_Since.append(tweet.datestamp + " " + tweet.timestamp)
        output = format(config, tweet)
        #console print 
        _output(tweet, output, config)
        #telegram bot send 
        tg_bot_send(output)
        #slack_bot send
        slack_send(_slack_channel, output)


async def Tweets(tweets, config, conn):
    logme.debug(__name__ + ':Tweets')
    if config.Favorites or config.Location:
        logme.debug(__name__ + ':Tweets:fav+full+loc')
        for tw in tweets:
            await checkData(tw, config, conn)
    elif config.TwitterSearch or config.Profile:
            logme.debug(__name__ + ':Tweets:TwitterSearch')
            await checkData(tweets, config, conn)
    else:
        logme.debug(__name__ + ':Tweets:else')
        if int(tweets["data-user-id"]) == config.User_id or config.Retweets:
            await checkData(tweets, config, conn)




class Twints(twint.run.Twint):
    
    def __init__(self, config):
        logme.debug(__name__ + ':Twint:__init__')
        if config.Resume is not None and (config.TwitterSearch or config.Followers or config.Following):
            logme.debug(__name__ + ':Twint:__init__:Resume')
            self.init = self.get_resume(config.Resume)
        else:
            self.init = -1

        config.deleted = []
        self.feed: list = [-1]
        self.count = 0
        self.user_agent = ""
        self.config = config
        # TODO might have to make some adjustments for it to work with multi-treading
        # USAGE : to get a new guest token and bearer token do `self.refresh()`
        self.refresh()
        self.conn = db.Conn(config.Database)
        self.d = datelock.Set(self.config.Until, self.config.Since)
        verbose.Elastic(config.Elasticsearch)

        if self.config.Store_object:
            logme.debug(__name__ + ':Twint:__init__:clean_follow_list')
            output._clean_follow_list()

        if self.config.Pandas_clean:
            logme.debug(__name__ + ':Twint:__init__:pandas_clean')
            storage.panda.clean()


    def get_resume(self, resumeFile):
        if not os.path.exists(resumeFile):
            return '-1'
        with open(resumeFile, 'r') as rFile:
            _init = rFile.readlines()[-1].strip('\n')
            return _init


    async def tweets(self):
        await self.Feed()
        #TODO : need to take care of this later
        if self.config.Location:
            logme.debug(__name__ + ' :TWint:tweets:location')
            self.count += await get.Multi(self.feed, self.config, self.conn)
        else:
            logme.debug(__name__ + ' :Twint:tweets:notLocation')            
            for tweet in self.feed:
                self.count += 1
                await Tweets(tweet, self.config, self.conn)

#token     
    def refresh(self):
        _session = requests.Session()
        logme.debug('Retrieving guest token')
        _session.headers.update({
            "user-agent"	:	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "accept"	:	"*/*",
            "accept-language"	:	"de,en-US;q=0.7,en;q=0.3",
            "accept-encoding"	:	"gzip, deflate, br",
            "te"	:	"trailers",
        })
        main_js = _session.get("https://abs.twimg.com/responsive-web/client-web/main.e46e1035.js").text
        token = re.search(r"s=\"([\w\%]{104})\"", main_js)[1]
        _session.headers.update({"authorization"	:	f"Bearer {token}"})
        self.config.Bearer_token = f"Bearer {token}"
        guest_token = _session.post("https://api.twitter.com/1.1/guest/activate.json").json()["guest_token"]
        self.config.Guest_token = guest_token

        
def custom(c, run, _type):
    print("[+] Beginning custom {} test in {}".format(_type, str(run)))
    c.Custom['tweet'] = ["id", "username"]
    c.Custom['user'] = ["id", "username"]
    run(c)

def main():
    c = twint.Config()
    #c.Username = "caolei1"
    c.Limit = 20
    c.Store_object = False
    #c.Images = True
    c.Debug = True
    c.User_id = "297811887"     #caolei1
#    c.Format = "{id} {date} {time} {tweet} {rn} {photos} {rn} {quote_url}"
    c.Format = "{date} {time} {tweet} {photos} {quote_url}"

    # Separate objects are necessary.

    #f = twint.Config()
    c.Username = "caolei1"
    #f.Limit = 20
    #f.Store_object = True
    #f.User_full = True

    c.Since = "2021-10-21 20:30:22"
#    c.Since = "2021-10-26 06:50:42"
    c.tmp_since = ''
    while (1):
        count = 0
        r = redis.StrictRedis(host=r_host,port=r_port,password=r_passwd, charset="utf-8", decode_responses=True)
        tmp_date = r.get("297811887")
        #add bear_token
        #c.Bearer_token = r.get('bear_token')
        if not None == tmp_date and len(tmp_date) > 2:
            #get new Since
            c.Since = tmp_date
        c.new_Since = []

        get_twitter(c)
        c.tmp_since = c.Since

        for since in c.new_Since:
            count += 1
            if datecheck(since, c):
                c.Since = since

        #update since
        #add 1 sec
#        '''
        if count > 0:
            new_timestap = formatDateTime(c.Since) + 1
            new_since = datetime.fromtimestamp(new_timestap).strftime('%Y-%m-%d %H:%M:%S')
   
            r.set('297811887', new_since)
        break
'''
    except Exception as e:
        print("error: \r\n")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print(e)
'''
#    print("[+] Testing complete!")


if __name__ == '__main__':
    main()
