'''
@author: The Junky
'''

import ConfigParser

import MySQLdb
import threading
from collections import deque
import BotUtilities
#import types
#import time
import logging


class AElement:
	
	TYPE_NONE =0
	TYPE_QUERY=1
	TYPE_MESSAGE=2
	TYPE_RESULT=3
	
	def getType(self):
		return AElement.TYPE_NONE

class AMessage(AElement):
	DB_NOT_CONNECTED = 0
	DB_CONNECTED = 1
	PING = 2
	TERMINATE = 3
	def __init__(self):
		self.id = None
		self.message = None   
	def getType(self):
		return AElement.TYPE_MESSAGE

class AQuery(AElement):
	def __init__(self,query,query_tuple,extra_data):
		self.text = query
		self.tuple = query_tuple
		self.data = extra_data   
	def getType(self):
		return AElement.TYPE_QUERY


				
class AResult(AElement):
	def __init__(self):
		self.messages = None
		self.error_no = None
		self.error_msg = None 
		self.last_row_id = None
		self.description = None 
		self.rows = None #the actual results
		self.rows_affected = None # inserts/deletes/updates will set this 
		self.query = None #Original Aquery
		self.info = None 
		#eg. can do things like (Query_type,name_of_pperson who issued it,extradata)
		#or a class whatever u want 
	def getType(self):
		return AElement.TYPE_RESULT
	
	def executeQueryAndStoreResults(self,conn,cursor,q):
		self.query = q
		try:
			cursor.execute(q.text,q.tuple)
			self.last_row_id = conn.insert_id()
			self.info = conn.info()
			self.description = cursor.description
			self.rows = cursor.fetchall()
			self.messages = cursor.messages
			self.rows_affected = cursor.rowcount
			
			

		except MySQLdb.Error, e:
			self.error_no  = e.args[0]
			self.error_msg = e.args[1]

	def GenericResultPrettyPrinterdefault(self,ssbot):
		"""
		this function will print any result nicely on screen with proper formatting 
		"""
		rp = ssbot.findPlayerByName(self.query.data)
		if rp is None:
			return
		
		if self.rows is None or len(self.rows) == 0:
			if self.rows_affected:
				ssbot.sendPrivateMessage(rp,"RowsAffected: " + str(self.rows_affected))
			if self.last_row_id:
				ssbot.sendPrivateMessage(rp,"InsertId: " + str(self.last_row_id))
			if self.error_msg:
				ssbot.sendPrivateMessage(rp,"Error: " + str(self.error_msg))
			else:
				ssbot.sendPrivateMessage(rp,"Query Successful: No Results")
			if self.messages:
				for m in self.messages:
					ssbot.sendPrivateMessage(rp,"Messages: " + str(m))
		else:
			if not self.description:
				ssbot.sendPrivateMessage(rp,"#### NO RESULTS ###")
			else:
				names = []
				lengths = []
				
				for dd in self.description:	# iterate over description
					names.append(dd[0])
					lengths.append(len(dd[0]))#in case name is bigger then max len of data
					
				for row in self.rows: # get the max length of each column
					for i in range(len(row)):
						lengths[i] = max(lengths[i],len(str(row[i])))
				tb = "-" * (sum(map(int,lengths))+(len(lengths) *3)+1)
				fm = "|"
				for col in lengths: #make the format string
					fm += " %" + str(col) +"s |" 		
				ssbot.sendPrivateMessage(rp,tb)
				ssbot.sendPrivateMessage(rp,(fm%tuple(names)))
				ssbot.sendPrivateMessage(rp,tb)		
				for row in self.rows: #output the rows
					ssbot.sendPrivateMessage(rp,(fm%row))
				ssbot.sendPrivateMessage(rp,tb)
	def GenericResultPrettyPrinter(self,ssbot,mtype,target):
		"""
		this function will print any result nicely on screen with proper formatting 
		"""
		ss = BotUtilities.SSmessenger(ssbot,mtype,target)
		if self.rows is None or len(self.rows) == 0:
			if self.rows_affected:
				ss.sendMessage("RowsAffected: " + str(self.rows_affected))
			if self.last_row_id:
				ss.sendMessage("InsertId: " + str(self.last_row_id))
			if self.error_msg:
				ss.sendMessage("Error: " + str(self.error_msg))
			else:
				ss.sendMessage("Query Successful: No Results")
			if self.messages:
				for m in self.messages:
					ss.sendMessage("Messages: " + str(m))
		else:
			if not self.description:
				ss.sendMessage("#### NO RESULTS ###")
			else:
				names = []
				lengths = []
				
				for dd in self.description:	# iterate over description
					names.append(dd[0])
					lengths.append(len(dd[0]))#in case name is bigger then max len of data
					
				for row in self.rows: # get the max length of each column
					for i in range(len(row)):
						lengths[i] = max(lengths[i],len(str(row[i])))
				tb = "-" * (sum(map(int,lengths))+(len(lengths) *3)+1)
				fm = "|"
				for col in lengths: #make the format string
					fm += " %" + str(col) +"s |" 		
				ss.sendMessage(tb)
				ss.sendMessage((fm%tuple(names)))
				ss.sendMessage(tb)		
				for row in self.rows: #output the rows
					ss.sendMessage((fm%row))
				ss.sendMessage(tb)


	
class Amysql(threading.Thread):
	"""Example of ussage
	   initialize:
		   db = Amysql(logger)
		   db.db.SetDbCredentialsFromFile(os.getcwd()+R"/db.conf","db")
		   db.start()
		use:
			db.Query("Select * from info",None,None)
		results:
			in event tick or timer:
			r = db.GetResults()
			check if None , check if message if not
			use....
			see mysqltest.py for working example
	""" 
	def __init__(self,logger):
		self.level = logging.DEBUG 

		self.default_file = None
		self.__Host = None
		self.__Port = None
		self.__User = None
		self.__Password = None
		self.__DB = None
		
		
		threading.Thread.__init__(self)
		
		self.__query_queue = deque()
		self.__query_cond = threading.Condition()

		self.__results_queue = deque()
		self.__results_lock = threading.Lock()
		self.do_it = 1
		
		self.conn = None
		self.cursor = None
		
		self.logger = logger;
		
		#threading.Thread.start(self)
	def setDBCredentials(self,host,port,user,password,db):
		self.__host = host
		self.__port = port
		self.__user = user
		self.__pass = password
		self.__db = db
		
	def setDbCredentialsFromFile(self,filename,section):
		config = ConfigParser.RawConfigParser()
		config.read(filename)
		self.__host = config.get(section, "host")
		self.__port = config.getint(section, "port")
		self.__user = config.get(section, "user")
		self.__pass = config.get(section, "pass")
		self.__db = config.get(section, "db")
		
	def query(self,query,query_tuple,extra_data):
		self.__enqueue_query(AQuery(query,query_tuple,extra_data))
		
	def ping(self):
		m = AMessage()
		m.id = AMessage.PING
		self.__enqueue_query(m)
		
	def __enqueue_query(self,q):
		self.__query_cond.acquire()
		self.__query_queue.append(q)
		self.__query_cond.notify()
		self.__query_cond.release()
		
	def __connect_to_db(self):
		m = AMessage()
		try:
			
			self.conn = MySQLdb.connect (host = self.__host,
										port = self.__port,
										user = self.__user,
										passwd = self.__pass,
										db = self.__db)
			self.cursor = self.conn.cursor()
			m.id = m.DB_CONNECTED
			m.message = "DBCONNECTED"
			#self.logger.info("DB CONNECTED")

		except MySQLdb.Error, e:
			m.id = m.DB_NOT_CONNECTED
			m.message = e.args[1]
			m.e = e
			self.logger.info("MysqlConnect:%d: %s" % (e.args[0], e.args[1]))
			#BotUtilities.LogException(self.logger)
		finally:
			return m
	def __execute_query(self,q):
		if(q == None):
			return None;
		if self.cursor:
			r = AResult()
			r.executeQueryAndStoreResults(self.conn,self.cursor,q)
		else:
			self.logger.ERROR("DBNotConnected cant execute:" + q.text)
		return r
	def __dequeue_query(self):
		q = None
		self.__query_cond.acquire()#this seems like it would deadlock but the wait will release the lock
		self.__query_cond.wait()#releases the lock and waits for main thread to notify it something is waiting in the queue
		if len(self.__query_queue) > 0: #might notify when i want to kill the thread with out adding stuff to the queue
			q = self.__query_queue.pop()
			#self.logger.log(self.level,"query popped")
		self.__query_cond.release()
		return q;
	def __enqueue_results(self,r):
		if r == None:
			return
		#return results to results queue
		#incase of the notify that makes this thread join main thread
		self.__results_lock.acquire()
		#self.logger.log(self.level,"result lock aquired result queued")
		self.__results_queue.append(r)
		self.__results_lock.release()
		#self.logger.log(self.level,"release lock released")

	def run(self):
		m = self.__connect_to_db()
		self.__enqueue_results(m)  
		while self.do_it:
			q = self.__dequeue_query()
			if q.getType() == q.TYPE_QUERY:
				r = self.__execute_query(q)
				self.__enqueue_results(r)
			elif q.getType() == AElement.TYPE_MESSAGE and q.id == AMessage.PING:
				if self.conn:# has connected in the past
					self.conn.ping()
				else:#never connected try again
					m = self.__connect_to_db()
					self.__enqueue_results(m) 	
			elif q.getType() == AElement.TYPE_MESSAGE and q.id == AMessage.TERMINATE:
				break
		if self.conn != None:
			self.conn.close()
		
	def queryEscape(self,string):
		if self.conn != None:
			return MySQLdb.escape_string(string)
		else:
			return None
	def requestStop(self):
		self.do_it = 0# wont iterate again
		m = AMessage()
		m.id = AMessage.TERMINATE
		m.message = "DIE"
		self.__enqueue_query(m)
		
	def cleanUp(self):
		self.requestStop()
		self.join()
		
		
	def getResults(self):
		result = None
		#self.logger.log(self.level,"mainthread:aquiring Result lock")
		self.__results_lock.acquire()
		if len(self.__results_queue) > 0:
			result = self.__results_queue.pop()
		self.__results_lock.release()
		return result		

		
