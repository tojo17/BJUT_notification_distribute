#!/usr/bin/env python3
# coding=utf-8
import requests
from lxml import etree
import sqlite3
import re
import sys
import time
import json

debug = True
def retry_get(retry, session, h_url, **kwargs):
	ctTry = 0
	global debug
	while 1:
		try:
			print_debug("retry_get", ctTry)
			res = session.get(h_url, timeout=30, verify = debug, **kwargs)
		except:
			if ctTry < retry:
				ctTry += 1
				print_log('Error: Retrying...', ctTry)
				sys.stdout.flush()
			else:
				print_log("Failed to get page. Exiting.")
				# restart self
				os.execl('daemon.sh', '')
				sys.exit()
		else:
			break
	return res

def retry_post(retry, session, h_url, **kwargs):
	ctTry = 0
	global debug
	while 1:
		try:
			print_debug("retry_post", ctTry)
			res = session.post(h_url, timeout=30, verify = debug, **kwargs)
		except:
			if ctTry < retry:
				ctTry += 1
				print_log('Error: Retrying...', ctTry)
				sys.stdout.flush()
			else:
				print_log("Failed to get page. Exiting.")
				# restart self
				os.execl('daemon.sh', '')
				sys.exit()
		else:
			break
	return res

def print_log(*text):
	print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) ,*text)
	sys.stdout.flush()
	return

def print_debug(*text):
	global debug
	if debug: print_log(*text)
	return

def init_db():
    global conn
    conn = sqlite3.connect("webdata.db")
    log_out("DB link success.")
    c = conn.cursor()
    if not ex_append:
        data = c.execute('SELECT name FROM sqlite_master;')
        for row in data:
            print(row)
            if (row[0] != 'sqlite_sequence'):
                c.execute('DROP TABLE %s;' %row[0])
            else:
                c.execute('DELETE FROM %s;' %row[0])

        c.execute('''
            CREATE TABLE sites (
                id          INTEGER NOT NULL    PRIMARY KEY AUTOINCREMENT   UNIQUE,
                name        TEXT    NOT NULL,
                url         TEXT,
                country     TEXT,
                category    TEXT,
                description TEXT
            );
        ''')
        conn.commit()

def login(user, password):
	global session
	# get lt and exe
	url = 'https://cas.bjut.edu.cn/login'
	print_log("Logging in...")
	session = requests.session()
	res = retry_get(30, session, url)
	etr = etree.HTML(res.text)
	lt = etr.xpath('////div[@class="form-group  dl-btn"]/input[@name="lt"]/@value')[0]
	execution = etr.xpath('////div[@class="form-group  dl-btn"]/input[@name="execution"]/@value')[0]
	# login
	data = {
		'username':	user,
		'password':	password,
		'lt':	lt,
		'execution':	execution,
		'_eventId':	'submit',
		'submit':	''
	}
	res = retry_post(30, session, url, data = data)
	if '<div id="msg" class="success">' in res.text:
		print_log('Login success!')
		return True
	else:
		print_log('Login failed!')
		return False

def get_institute_noti():
	global session
	url = 'https://my1.bjut.edu.cn/group/undergraduate/index'
	params = {
		'p_p_id':	'bulletinListForCustom_WAR_infoDiffusionV2portlet_INSTANCE_O5zYIiq6Mmwb',
		'p_p_state':	'exclusive',
		'_bulletinListForCustom_WAR_infoDiffusionV2portlet_INSTANCE_O5zYIiq6Mmwb_action': 'listMoreAjaxQuery',
		'sEcho': 1,
		'sColumns': 'title,publis_dept,published',
		'iDisplayStart': 0,
		'iDisplayLength': 10,
		'sSearch': ''
	}
	json = retry_get(30, session, url, params = params).text
	return json

if __name__ == '__main__':
	# wait for another self to exit
	# time.sleep(20)
	while not login('15071025', 'cixi19344243'):
		pass
	json = get_institute_noti()



