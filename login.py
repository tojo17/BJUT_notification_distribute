#!/usr/bin/env python3
# coding=utf-8
import requests
from lxml import etree
import sqlite3
import re
import sys
import time
import json

debug = False
def retry_get(retry, session, h_url, **kwargs):
	ctTry = 0
	while 1:
		try:
			print_debug("retry_get", ctTry)
			res = session.get(h_url, timeout=30, **kwargs)
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
	while 1:
		try:
			print_debug("retry_post", ctTry)
			res = session.post(h_url, timeout=30, **kwargs)
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

def login(user, password):
	# get lt and exe
	url = 'https://cas.bjut.edu.cn/login'
	print_log("Logging in...")
	session = requests.session()
	res = retry_get(30, session, url, verify = False)
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
	res = retry_post(30, session, url, data = data, verify = False)
	if '<div id="msg" class="success">' in res.text:
		print_log('Login success!')
		return session
	else:
		print_log('Login failed!')
		return None

def get_institute_noti(session):
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
	json = retry_get(30, session, url, params = params, verify = False).text
	return json

if __name__ == '__main__':
	# wait for another self to exit
	# time.sleep(20)
	while session == None:
		session = login('15071025', 'cixi19344243')
	json = get_institute_noti(session)



