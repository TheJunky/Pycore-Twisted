'''
@author: The Junky
'''
#masterbot for cycad's python core written by The Junky<thejunky@gmail.com>
import re
import logging
from logging import NOTSET
import traceback
import sys
import time
import os
import math
import types
import threading
from collections import deque

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, task


from SubspaceBot import SubspaceBot
from SubspaceBot import MESSAGE_TYPE_ARENA,MESSAGE_TYPE_SYSTEM,MESSAGE_TYPE_PUBLIC_MACRO
from SubspaceBot import MESSAGE_TYPE_PUBLIC,MESSAGE_TYPE_TEAM,MESSAGE_TYPE_FREQ,MESSAGE_TYPE_PRIVATE
from SubspaceBot import MESSAGE_TYPE_WARNING,MESSAGE_TYPE_REMOTE,MESSAGE_TYPE_SYSOP,MESSAGE_TYPE_CHAT
from SubspaceBot import MESSAGE_TYPE_ALERT, SOUND_NONE, Player,BM_STANDALONE 
from SubspaceBot import EVENT_ENTER,EVENT_LEAVE,EVENT_TICK,EVENT_DISCONNECT

class Timer2(object):
	def __init__(self,id,delay,data):
		self.id = id
		self.expire_time = time.time() + delay
		self.data = data
	def hasExpired(self):
		if time.time() >= self.expire_time:
			return True
		else:
			return False
	def __repr__(self):
		return str(self.expire_time)

class TimerManager(object):
	"""
	to replace the core timer functions since they dont really work well
	with multi-module systems
	"""
	def __init__(self):
		self.id = 1
		self.tl = []
		self.sort = False
	def set(self,secs,data):
		"""same as settimer"""
		self.id+=1;
		t = Timer2(self.id,secs,data)
		self.tl.append(t)
		self.sort = True		
		return self.id
	def delete(self,id):
		"""delete a specific timer"""
		self.tl = [ t for t in self.tl if t.id != id ]
	def deleteAll(self):
		"""delete all timers"""
		del self.tl[:]
	def getExpired(self):
		"""
		use this in event_tick if it returns None no expired timers yet
		this will return a timer if expired and delete it from the list
		"""
		if self.sort:
			self.tl = sorted(self.tl,key=lambda t:t.expire_time)
			self.sort = False

			
		if self.tl and self.tl[0].hasExpired():
			return self.tl.pop(0)
		else:
			return None
			

class PlayerInfoBase:
	def __init__(self):
		self.__active = 0 
		#if here  = 0 then time stamp is when he left otherwise it is when he entered
		self.__time = time.time()
		
		self.__data = None
		 
	def IsActive(self):
		return self.__active;
	def GetTimeSinceActive(self):
		if self.__active == 0 :
			return time.time() - self.__time
		else :
			return 0;
	def SetActive(self):
		self.__active=1
		self.__time = time.time()
	def SetInactive(self):
		self.__active=0
		self.__time = time.time()
	def SetData(self,data):
		self.__data=data
	def GetData(self):
		return self.__data
	
		

class PlayerInfoManager():
	def __init__(self,initializer=None,cachetime=6*60*60,persist=1):
		self.pinfo_dict = {}
		self.cachetime = cachetime
		self.PersistBetweenEnters = persist
		self.initializer = initializer
		self.last_check = time.time()
		self.check_interval = 30*60 #30 mins time is in secs
		
	def SetOptions(self,initializer=None,cachetime=6*60*60,persist=1):
		self.cachetime = cachetime
		self.PersistBetweenEnters = persist
		self.initializer = initializer
		self.last_check = time.time()
		self.check_interval = 30*60 #30 mins time is in secs
			
	def GetPlayerInfo(self,name):
		"""
		will return a players playinfo or make a new one by default
		if the playerinfo manager is initialized with out an initializer
		it will return None when a playerinfo isnt found
		so in that case you will have to make your own and insetit using setplayerinfo
		"""
		np = None
		if(name in self.pinfo_dict):
			np =  self.pinfo_dict[name]
		else:
			np = PlayerInfoBase()
			self.pinfo_dict[name] = np;
			if self.initializer:
				np.data = self.initializer()
		return np.data
				
	def SetPlayerInfo(self,name,data):
		"""
		if you set return_new to 0 then you have manually 
		make new pinfos and insert them using this function
		Your playerinfo class must be a subclass of PlayerInfoBase
		otherwise you will get an exception
		"""
		np = None
		if(name in self.pinfo_dict):
			np = self.pinfo_dict[name]
		else:
			np = PlayerInfoBase()
			self.pinfo_dict[name] = np;
		np.data = data

	def DeleteExpired(self):#delete pinfos if a player is gone more than 6 hours
		"""use this in event timer or tick to delete all inactives after cachetime"""
		if time.time() - self.last_check>= self.check_interval:
			keys2del = []
			for k,v in self.pinfo_dict.iteritems():
				if v.GetTimeSinceActive() > self.cachetime:
					keys2del.append(k)
			for k in keys2del:
				del self.pinfo_dict[k]
			self.last_check = time.time()
	def Clear(self):
		"""tythis will empyt out the pinfo dict"""
		self.pinfo_dict.clear()
	def SetActive(self,name):
		"""
		use this in event enter: 
		if the pinfo exists it will set it back to active"""
		if(name in self.pinfo_dict):
			self.pinfo_dict[name].SetActive()
		
	def SetInactive(self,name):
		"""
		use this in event leave:
		if persists ==1 ut wukk set names pinfo (if it exists) to inactive
		"""
		if(name in self.pinfo_dict):
			if self.PersistBetweenEnters:
				self.pinfo_dict[name].SetInactive()
			else:
				del self.pinfo_dict[name]
	
	def SetAllInactive(self):
		"""use this in event disconnect
		if perisists ==1 it will set all the pinfos to inactive
		else it will clear the pinfo dict
		"""
		if self.PersistBetweenEnters:
			for p in self.pinfo_dict.values():
				p.SetInactive()
		else:
			self.pinfo_dict.clear()
			
	def HandleEvents(self,ssbot,event):
		"""
		you can manually do all of the setactive/inactive or you can use 
		this at the top of your bots handleEvents function if it is more convenient
		this will handle all of the setting/deleting etc etc
		"""
		if event.type == EVENT_ENTER:
			self.SetActive(event.player.name)
		elif event.type == EVENT_LEAVE:
			self.SetInactive(event.player.name)
		elif event.type == EVENT_TICK:
			self.DeleteExpired()
		elif event.type == EVENT_DISCONNECT:	
			self.SetAllInactive()


#added moduledata so it will be easier for me 
#to add shit to modules in the future 
#with out breaking the interface

class ModuleData():
	def __init__(self,module_name,module,param,inifile,args,logger):
		self.module_name = module_name
		self.module = module
		self.param = param
		self.inifile =inifile
		self.logger = logger
		self.module_path = os.path.dirname(self.module.__file__)
		self.args = args

class BotInterface:
	def __init__(self,bot,md):
		self.md = md
		#param defined in config, could be any string
		self.param = md.param
		self.inifile = md.inifile
		
		
		#logging module allows modules log to !log,console,and file
		self.logger = md.logger
		
		#when modules are dynamicly loaded
		#i dont think the rest of the file is easy/possible?
		#to add to the current context, even if it was possible
		# i assume it will cause some sort of name Mangling
		# i assume we can get all the variables we need if 
		#i pass the module i get from __import__ to the botclass
		#so if u need you specific Playerinfo for example u 
		#can get to it by doing module.playerinfo
		self.module_name = md.module_name
		self.module = md.module
		self.module_path = md.module_path
		self.args = md.args #any arguments passed by !sb this is a string
		self.pm = PlayerInfoManager()
		self.tm = TimerManager()
	def HandleEventsBI(self,ssbot,event):
		self.pm.HandleEvents(ssbot,event)
		
	def setPlayerInfoOptions(self,initializer=None,cachetime=6*60*60,persist=1):
		"""
		Initializer is the name of the class if you want the manager to allocate a new set of data for you instead of returning none
		cachetime is how long before the data is deleted once the player leaves the arena,
		if persist is set to 1 or true then the data is deleted as soon as the player leaves arena
		"""
		self.pm.SetOptions(initializer,cachetime,persist)	
	def getPlayerinfo(self,name):
		return self.pm.GetPlayerInfo(name)
	def setPlayerInfo(self,name,data):
		self.pm.SetPlayerInfo(name,data)
	def clearPlayerInfo(self):
		self.pm.Clear()
	
	def setTimer(self,secs,data):
		return self.tm.set(secs,data)
	def deleteTimer(self,id):
		self.tm.delete(id)
	def deleteAllTimers(self):
		self.tm.deleteall()
	def getExpiredTimer(self):
		return self.tm.getExpired()
				
	def HandleEvents(self,ssbot,event):
		self.logger.error( "BotInterface Handle Events, %s bot has not overridden this function"%(self.name))
		return None
	
	def Cleanup(self):
		pass
	

def LogException(logger):
	logger.error(sys.exc_info())
	formatted_lines = traceback.format_exc().splitlines()
	for l in formatted_lines:
		logger.error(l)


#this looks like a much cleaner way to reload modules but i dont think it works right.	  
#def LoadModule(name):
#	if name in sys.modules:
#		module = sys.modules[name]
#		reload(module)
#	else:
#		module = __import__( name,fromlist=["*"])
#	return module
#this is fugly and might cause problems when the module is loaded multiple times
# but should work for development at least

def LoadModule(name):
	#if module is already loaded
	if name in sys.modules:
		#unload module
		del sys.modules[name]
	#reload module
	module = __import__( name,globals=globals(),locals=locals(),fromlist=["*"])
	#module = importlib.import_module(name) 
	return module


def LoadBot(ssbot,modulename,param,inifile,args,logger):
	bot = None
	try:
		module= LoadModule(modulename)
		if (issubclass(module.Bot,BotInterface)):
			md = ModuleData(modulename,module,param,inifile,args,logger)
			bot =  module.Bot(ssbot,md) 
		else:
			logger.error("%s.Bot() is not a subclass of BotInterface, and cant be loaded" %(modulename))
			bot = None
	except:
			logger.error( "Trying to instantiate %s caused Exception" %(modulename))
			LogException(logger)
			bot = None
	finally:
		return bot

def Pixels_To_SS_Coords(x , y):
	try:
		ch = "ABCDEFGHIJKLMNOPQRSTU"
		x1 = int(math.floor((x*20)/16384))
		y1 = ((y*20)/16384)+1
		return ch[x1] + str(y1)
	except:
		return "InvalidCoord?"
def Tiles_To_SS_Coords(x , y):
	return Pixels_To_SS_Coords(x<<4 , y<<4)

def Pixels_To_SS_Area(x , y):
	try:
		f = 3277.6
		xc = ["FarLeft","Left","Center","Right","FarRight"]
		yc = ["FarUp-","Up-","","Down-","FarDown-"]
		xi = int(math.floor(x/f))
		yi = int(math.floor(y/f))
		return yc[yi]+xc[xi]
	except:
		return "InvalidCoord?"
def Tiles_To_SS_Area(x , y):
	return Pixels_To_SS_Area(x<<4 , y<<4)

class SSmessengerException(Exception):
	def __init__(self, value):
		self.parameter = value
	def __str__(self):
		return repr(self.parameter)	
	
class SSmessenger():
	"""
	This class is used  if you want to use differing methods to print/message 
	in Subspace. for example Database results can be printed to team/freq/pub/chat/remote
	supports 
		MESSAGE_TYPE_PUBLIC,
		MESSAGE_TYPE_PRIVATE,MESSAGE_TYPE_REMOTE (target must be a name)
		MESSAGE_TYPE_TEAM,
		MESSAGE_TYPE_FREQ (target must be an freq)
		MESSAGE_TYPE_CHAT (target must be a chat channel)
		
		for arena or zone or *bot messages use MESSAGE_TYPE_PUBLIC with thre appropriate prefix

		throws SSmessengerException on error		
	"""
	def __init__(self,ssbot,mtype,target=None,prefix=""):
		self.ssbot = ssbot
		self.func= None
		self.target = None
		self.prefix = prefix
		if mtype == MESSAGE_TYPE_PUBLIC:
			self.func = self.__pub 	
		elif mtype == MESSAGE_TYPE_PRIVATE:
			if type(target) == types.StringType:
				self.player = ssbot.findPlayerByName(target)
				if not self.player:
					raise SSmessengerException("Player NotFound")
			elif isinstance(Player,target):
				self.player = target
			else:
				raise SSmessengerException("MessageType private/remote but target is'nt a string/player")
			self.func=self.__priv
		elif mtype == MESSAGE_TYPE_REMOTE:
			if type(target) == types.StringType:
				self.func=self.__rmt
				self.playername=target
			else:
				raise SSmessengerException("MessageType remote but target is'nt a string")	
		elif mtype == MESSAGE_TYPE_TEAM:
			self.func = self.__team
		elif mtype == MESSAGE_TYPE_FREQ:
			if type(target) != types.IntType:
				raise SSmessengerException("MessageType freq but target is'nt a freq")
			self.func = self.__freq
			self.freq = target
		elif mtype == MESSAGE_TYPE_CHAT:
			if type(target) != types.IntType:
				raise SSmessengerException("MessageType chat but target is'nt a channel")
			self.func = self.__chat
			self.chat = ";"+str(target)+";"
		else:
			raise SSmessengerException("MessageType not supported")
		
	def __pub(self,message,sound=SOUND_NONE):
		self.ssbot.sendPublicMessage(message,sound)
	def __priv(self,message,sound=SOUND_NONE):
		self.ssbot.sendPrivateMessage(self.player,message,sound)
	def __rmt(self,message,sound=SOUND_NONE):
		self.ssbot.sendRemoteMessage(self.playername,message,sound)
	def __team(self,message,sound=SOUND_NONE):
		self.ssbot.sendTeamMessage(message,sound)
	def __freq(self,message,sound=SOUND_NONE):
		self.ssbot.sendFreqMessage(self.freq,message,sound)
	def __chat(self,message,sound=SOUND_NONE):
		self.ssbot.sendChatMessage(self.chat+message,sound)
	
	def sendMessage(self,message,sound=SOUND_NONE):
		self.func(self.prefix+message,sound)

class loggingChatHandler(logging.Handler):
	"""
	Logging module handler to spew entries to a specific chat
	"""
	def __init__(self,level,ssbot,chat_no):
		logging.Handler.__init__(self,level)
		self.ssbot = ssbot
		self.chat = ";"+str(chat_no)+";"
	def emit(self,record):
		self.ssbot.sendChatMessage(self.chat+self.format(record))
		
class loggingTeamHandler(logging.Handler):
	"""
	Logging module handler to spew entries to a team chat
	"""
	def __init__(self,level,ssbot):
		logging.Handler.__init__(self,level)
		self.ssbot = ssbot
	def emit(self,record):
		self.ssbot.sendTeamMessage(self.format(record))
		
class loggingPublicHandler(logging.Handler):
	"""
	Logging module handler to spew entries to pub
	"""
	def __init__(self,level,ssbot,prefix):
		logging.Handler.__init__(self,level)
		self.ssbot = ssbot
	def emit(self,record):
		self.ssbot.sendPublicMessage(self.format(record))

class loggingRemoteHandler(logging.Handler):
	"""
	Logging module handler to spew entries to pub
	"""
	def __init__(self,level,ssbot,name):
		logging.Handler.__init__(self,level)
		self.ssbot = ssbot
		self.name = name
	def emit(self,record):
		self.ssbot.sendRemoteMessage(self.name,self.format(record))			

#the logging module allows u to add handlers for log messages
#for example maybe you want certain log entries to be added
#to an offsite server using httppost
#this is simple handler that i made to copy messages to a list
#so it can be spewed to ss without reading the logfile
#you are required to overide __init__ and emit for it to work	
class ListHandler(logging.Handler):
	def __init__(self,level=NOTSET,max_recs=100):
		logging.Handler.__init__(self,level)
		self.list = []
		self.max_recs = max_recs
		self.max_slice = -1 * max_recs
	def emit(self,record):
		self.list.append(self.format(record))
	def LoadFromFile(self,filename):
		self.list = open(filename,'r').readlines()[self.max_slice:]

	def RemoveOld(self):
		if len(self.list) > self.max_recs:
			self.list = self.list[self.max_slice:]
	def GetEntries(self):
		return self.list[self.max_slice:]
	def Clear(self):
		self.list = []
				
class NullHandler(logging.Handler):
	def emit(self, record):
		pass
	
	
class MasterQue():
	def __init__(self):
		self.__queue = deque()
		self.__lock = threading.Lock()
	def queue(self,event):
		self.__lock.acquire()
		self.__queue.append(event)
		self.__lock.release()
	def dequeue(self):
		q = None
		self.__lock.acquire()
		if len(self.__queue) > 0:
			q = self.__queue.pop()
		self.__lock.release()
		return q
	def size(self):
		return len(self.__queue)	

class ShutDownException(Exception):
	def __init__(self, value):
		self.parameter = value
	def __str__(self):
		return repr(self.parameter)	



def botMain(Bot,debug=False,Mode=BM_STANDALONE,arena="#python"):
	from Credentials import botowner, botname, botpassword
	try:
		# create logger with 'spam_application'
		logger = logging.getLogger('Main')
		logger.setLevel(logging.DEBUG)
		# create file handler which logs even debug messages
		fh = logging.FileHandler('main.log')
		fh.setLevel(logging.DEBUG)
		# create console handler with a higher log level
		ch = logging.StreamHandler()
		ch.setLevel(logging.DEBUG)
		# create formatter and add it to the handlers
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fh.setFormatter(formatter)
		ch.setFormatter(formatter)
		# add the handlers to the logger
		logger.addHandler(fh)
		logger.addHandler(ch)
		
		ssbot= SubspaceBot('66.36.247.83', 7900, botname, botpassword,arena,debug,BM_STANDALONE,None,logger)
		lp = reactor.listenUDP(0, ssbot)
		ssbot.setReactorData(reactor,lp) # so clients can disconnect tghemselves when they get disconnect packet or master kills them
		module = sys.modules[globals()['__name__']]
		md = ModuleData("TesttBot",module,"None","test.ini","",logger)
		ssbot.setBotList([Bot(ssbot,md)])
		reactor.run()
	except Exception as e:
		LogException(logger)
		raise 
	finally:
		bot.Cleanup()
		logger.critical("Testbot shutting down")
		fh.close()
