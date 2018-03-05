#!/usr/bin/env python3
# coding=utf-8
import requests
from lxml import etree
from newspaper import fulltext
from newspaper import Article
import sqlite3
import re
import sys
import time
import json
import userinfo

debug = False
ex_log = False
token = {'token': '0', 'time': 0, 'expire': 0}

def retry_get(retry, session, h_url, **kwargs):
	ctTry = 0
	global debug
	while 1:
		try:
			print_debug("retry_get", ctTry)
			res = session.get(h_url, timeout=30, verify = not debug, **kwargs)
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
			res = session.post(h_url, timeout=30, verify = not debug, **kwargs)
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
	conn = sqlite3.connect("noti.db")
	print_log("DB link success.")

def write_db(noti):
	print_log("Write into DB")
	conn.cursor().execute('INSERT INTO institute (title, url, publisher, publish_time, content)\
		VALUES (?, ?, ?, ?, ?)',\
		(noti['title'], noti['url'], noti['publisher'], noti['publish_time'], noti['content']))
	conn.commit()

def login(user, password):
	global session
	# get lt and exe
	url = 'https://cas.bjut.edu.cn/login'
	print_log("Logging in...")
	session = requests.session()
	res = retry_get(30, session, url)
	etr = etree.HTML(res.text)
	lt = etr.xpath('//div[@class="form-group  dl-btn"]/input[@name="lt"]/@value')[0]
	execution = etr.xpath('//div[@class="form-group  dl-btn"]/input[@name="execution"]/@value')[0]
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
	jstr = retry_get(30, session, url, params = params).text
	return jstr

def analyse_noti(jstr):
	print_log("Analysing...")
	# bulletin link base url
	s_url = 'https://my1.bjut.edu.cn/group/undergraduate/index?p_p_id=bulletinListForCustom_WAR_infoDiffusionV2portlet_INSTANCE_O5zYIiq6Mmwb&p_p_lifecycle=0&p_p_state=pop_up&p_p_mode=view&_bulletinListForCustom_WAR_infoDiffusionV2portlet_INSTANCE_O5zYIiq6Mmwb_action=browse&wid='
	jnoti = json.loads(jstr)
	for item in jnoti['aaData']:
		noti = {}
		etr = etree.HTML(item['title'])
		noti['title'] = etr.xpath('//a/text()')[0]
		url = etr.xpath('//a/@href')[0]
		if url == 'javascript:void(0);' :
			# bulletin link
			noti['url'] = s_url + etr.xpath('//a/@onclick')[0][16:-3]
		else:
			noti['url'] = url
		noti['publisher'] = item['publis_dept']
		noti['publish_time'] = item['published']
		if not check_noti_exist(noti):
			# if new noti
			print_log("Got new Noti!", noti['title'])
			get_noti_detail(noti)
			write_db(noti)
			push_notify(noti)

def get_noti_detail(noti):
	global session
	print_log("Getting noti text")
	html = retry_get(30, session, noti['url']).text
	try:
		text = fulltext(html, language='zh')
	except:
		# hard to parse, maybe utf-8
		try:
			article = Article(noti['url'], language='zh')
			article.download()
			article.parse()
			text = article.text
		except:
			# unable to parse main text
			text = html
	noti['content'] = text

def check_noti_exist(noti):
	qstr = 'SELECT * from institute where url = "%s"' % noti['url']
	r = conn.cursor().execute(qstr).fetchall()
	if len(r) == 0:
		return False
	else:
		return True


def push_notify(noti):
	global token
	session = requests.Session()
	# if expired, get new token and save
	if time.time() >= token['time'] + token['expire']:
		print_log("Requireing new token...")
		t_url = "https://api.weixin.qq.com/cgi-bin/token"
		t_params = {
			'grant_type': 'client_credential',
			'appid': userinfo.appid,
			'secret': userinfo.appsecret
		}
		r = retry_get(30, session, t_url,  params=t_params)
		r_token = json.loads(r.text)
		token['token'] = r_token['access_token']
		token['time'] = time.time()
		token['expire'] = r_token['expires_in']
		print_log(token)
		with open('token.json', 'w') as f_json:
			json.dump(token, f_json)

	p_url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
	p_params = {
		'access_token': token['token']
	}
	p_msg = {
		'touser': userinfo.wechatid,
		'template_id': userinfo.templeid,
		'url': noti['url'],
		'topcolor': '#3B74AC',
		'data': {
			'title': {
				'value': noti['title'],
				'color': '#ff0000'
			},
			'publisher': {
				'value': noti['publisher'],
				'color': '#173177'
			},
			'publish_time': {
				'value': noti['publish_time'],
				'color': '#173177'
			},
			'url': {
				'value': noti['url'],
				'color': '#173177'
			},
			'content': {
				'value': noti['content'],
				'color': '#173177'
			}
		}
	}
	p_data = json.dumps(p_msg)
	r = retry_post(3, session, p_url, params=p_params, data=p_data)
	print_log(noti)
	print_log(r.text)

if __name__ == '__main__':
	# wait for another self to exit
	# time.sleep(20)
	init_db()
	while 1:
		while not login(userinfo.usr, userinfo.pwd):
			pass
		jstr = get_institute_noti()
		analyse_noti(jstr)
		# check every 5 minutes
		time.sleep(300)
	conn.close()


