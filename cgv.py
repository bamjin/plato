#!/usr/bin/python3
#-*- coding: utf-8 -*-

import os
import re
import requests
import datetime
import sqlite3
import time, datetime
import telepot
import json
from bs4 import BeautifulSoup
from telepot.loop import MessageLoop
from telepot.delegate import per_chat_id, create_open, pave_event_space

TICKET_FORMAT = re.compile(r"popupSchedule\('(.*)','(.*)','(\d\d:\d\d)','(\d*)','(\d*)', '(\d*)', '(\d*)', '(\d*)',")
CONFIG_FILE = 'setting.json'
DB_FILE = os.path.join(os.path.dirname(__file__), 'TICKET.db')

def getTimelist(playYMD):
	data = {'theaterCd':"0013", 'playYMD':playYMD}
	response = requests.post('http://m.cgv.co.kr/Schedule/cont/ajaxMovieSchedule.aspx', data)
	soup = BeautifulSoup(response.text, "lxml")
	
	return soup.find_all("ul", "timelist")

def getDateRange():
	base = datetime.datetime.today()
	dateRange = list()
	for x in range(0,25):
		dateRange.append((base + datetime.timedelta(days=x)).strftime("%Y%m%d"))
	
	return dateRange

def isImaxMovie(timelist):
	return (str(timelist).find('IMAX') != -1)

def getImaxTicketList():
	TICKET = list()

	for playYMD in getDateRange():
		for timelist in getTimelist(playYMD):
			if isImaxMovie(timelist):
				for ticket in timelist.find_all('a'):
					rawData = TICKET_FORMAT.findall(str(ticket))
					if len(rawData) == 1:
						ticketData = rawData[0]
						movieTitle = ticketData[0]
						ticketType = ticketData[1]
						ticketTime = ticketData[2]
						remaining = ticketData[3]
						maxseat = ticketData[4]
						movieIdx = ticketData[5]
						empty = ticketData[6]
						ticketDate = ticketData[7]

						TICKET.append({'theaterCd': '0013', 'movieIdx': movieIdx, 'movieTitle': movieTitle,'ticketDate': ticketDate, 'ticketTime': ticketTime})
	return TICKET

def noti(msg):
	content_type, chat_type, chat_id = telepot.glance(msg)
	while True:
		TICKET = getImaxTicketList()
		for imaxTicket in TICKET:
			query = (imaxTicket['theaterCd'], imaxTicket['movieIdx'], imaxTicket['ticketDate'], imaxTicket['ticketTime'])
			cursor.execute('SELECT * FROM ticket WHERE theaterCd=? AND movieIdx=? AND ticketDate=? AND ticketTime=?', query)
			savedTicket = cursor.fetchone()

			if savedTicket is None:
				cursor.execute('INSERT INTO ticket VALUES (?,?,?,?,?,0)', (imaxTicket['theaterCd'], imaxTicket['movieIdx'], imaxTicket['ticketDate'], imaxTicket['ticketTime'], imaxTicket['ticketTime']))
				date = datetime.datetime.strptime(imaxTicket["ticketDate"], '%Y%m%d').date()
				result = ("용산 IMAX 예매가능\n'%s', %s %s" %(imaxTicket["movieTitle"], date, imaxTicket["ticketTime"]))
				bot.sendMessage(chat_id, result)
			else:
				time.sleep(60)

def parseConfig(filename):
	f = open(filename, 'r')
	js = json.loads(f.read())
	f.close()
	return js

def getConfig(config):
	global TOKEN
	TOKEN = config['common']['token']

if __name__ == '__main__':
	conn = sqlite3.connect(DB_FILE)
	cursor = conn.cursor()
	config = parseConfig(CONFIG_FILE)
	
	if not bool(config):
		print("Err: Setting file is not found")
		exit()

	getConfig(config)
	bot = telepot.Bot(TOKEN)
	conn.commit()
	MessageLoop(bot, noti).run_forever()
	conn.close()

