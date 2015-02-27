#!/usr/bin/env python
# requires WConio library
#http://newcenturycomputers.net/projects/wconio.html
import os
import logging
from SubspaceBot import *
from BotUtilities import *
import WConio
from Credentials import botowner, botname, botpassword,botchats

class CHAT():
	BLACK = 0
	BLUE = 1
	GREEN = 2
	CYAN = 3
	RED = 4
	MAGENTA = 5
	BROWN = 6
	LIGHTGRAY = LIGHTGREY = 7
	DARKGRAY = DARKGREY = GRAY = 8
	LIGHTBLUE = 9
	LIGHTGREEN = 10
	LIGHTCYAN = 11
	LIGHTRED = 12
	LIGHTMAGENTA = 13
	YELLOW = 14
	WHITE = 15
	RAINBOW = 16
	
	def __init__(self,logger):
		self.text = ""
		#Store current attribute settings
		self.old_setting = WConio.gettextinfo()[4] & 0x00FF
		WConio.highvideo()
		WConio.clrscr()
		self.info = WConio.gettextinfo()
		self.lg=logger
		self.target=None
	def spew(self,text,color):
		if color == CHAT.RAINBOW:
			c = 0
			for ch in text:
				WConio.textattr(c)
				WConio.putch(ch)
				c= (c +1)%16 
		else:		
			WConio.textattr(color)
			WConio.cputs(text)
		t= text.find("\r\n")
		if t:
			text=text[0:t]
		self.lg.info(text)
	def ProcessInput(self,ssbot):
		while WConio.kbhit():
			c= WConio.getch()
			if c[0] == 8 and len(self.text) > 0:
				self.text = self.text[:-1]
				
			if c[0] == 13:
				text = self.text.encode("utf-8")
				if len(text) > 0:
					if text[0] == ';':#chat
						if text[1] >= '1' and text[1] <= '9':
							ssbot.sendChatMessage(text)
							self.spew(ssbot.name+">"+text+"\r\n", CHAT.RED)
						else:
							text = ";1" + text
							ssbot.sendChatMessage(text)
							self.spew(ssbot.name+">"+text+"\r\n", CHAT.RED)

					elif text[0] == ':':#remote/priv
						text = text[1:]
						t= text.find(':')
						if t != -1:
							name = text[0:t]
							ssbot.sendPrivateMessage(name,text[t+1:])
							self.spew(ssbot.name+">"+":"+name +":"+text[t+1:]+"\r\n", CHAT.GREEN)
							
						else:
							self.text = ""
					elif text[0] == "/" and self.text[1] != "/":#priv/remote
						if self.target:
							text = text[2:] 
							ssbot.sendPrivateMessage(self.target,text[t+1:])
							self.spew("RMT->:"+self.target +":"+text[t+1:]+"\r\n", CHAT.GREEN)
						else:
							self.spew("Target:NotSet\r\n", CHAT.WHITE)
					elif text[0] == "'" or self.text[0:2] == "//":#team
						text = text[1:] if text[0] =="'" else text[2:] 
						ssbot.sendTeamMessage(text)
						self.spew(ssbot.name+">"+text+"\r\n", CHAT.YELLOW)
					elif text[0] == '?': #command
						if text.startswith("?quit"):
							self.spew("BOT:?quit -Quitting\r\n", CHAT.MAGENTA)
							ssbot.disconnectFromServer()
						elif text.startswith("?target"):
							self.target = text[8:].strip()
							self.spew("BOT:priv/remote target set to: "+self.target+"\r\n", CHAT.MAGENTA)
						elif text.startswith("?go"):
							ssbot.sendChangeArena(text[3:].strip())
							self.spew("BOT:changing arena to "+text[3:]+"\r\n", CHAT.MAGENTA)
						elif text.startswith("?team"):
							c= 0
							self.spew("----TEAM---\r\n",CHAT.MAGENTA)
							for p in ssbot.players_here:
								
								if p.freq == ssbot.freq:
									c+=1	
									self.spew(p.name,CHAT.MAGENTA)
									if c % 6 == 0:
										self.spew("\r\n",CHAT.MAGENTA)
									else:
										self.spew(", ",CHAT.MAGENTA)
							self.spew("\r\n",CHAT.MAGENTA)			
						elif text.startswith("?inarena"):
							c= 0
							self.spew("----In Arena---\r\n",CHAT.MAGENTA)
							for p in ssbot.players_here:
								c+=1
								self.spew(p.name,CHAT.MAGENTA)
								if c % 6 ==0:
									self.spew("\r\n",CHAT.MAGENTA)
								else:
									self.spew(", ",CHAT.MAGENTA)
							self.spew("\r\n",CHAT.MAGENTA)								

						else:
							ssbot.sendPublicMessage(text)

					else:
						ssbot.sendPublicMessage(text)
						self.spew(ssbot.name+">"+text+"\r\n", CHAT.GRAY)
				self.text = ""
				WConio.settitle(self.text)
					
			elif c[0] >= 32 and c[0] <= 126:
				self.text += c[1]
			#else:
			#	print c[0]
				
			WConio.settitle(self.text)
			#height = self.info[7]
			#width = self.info[8]
			#WConio.puttext(0,height-1,1,height, ssbot.MakePaddedString("Prompt> " + self.text,height))	
			
		pass		
	def Restore(self):
		WConio.textattr(self.old_setting)
					



class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"ConIO Chat Client","the junky","chat client",".01")
		self.c = CHAT(self.logger)
		ssbot.addChat(botchats)
		
		
		
	def HandleEvents(self,ssbot,event):
		if event.type == EVENT_MESSAGE:
			if event.message_type == MESSAGE_TYPE_ARENA:
				self.c.spew(event.message + "\r\n", CHAT.GREEN)
			if event.message_type == MESSAGE_TYPE_PRIVATE:
				self.c.spew(event.pname + "> " +event.message + "\r\n", CHAT.GREEN)
			if event.message_type == MESSAGE_TYPE_REMOTE:
				self.c.spew("("+ event.pname + ")> " +event.message + "\r\n", CHAT.GREEN)
			if event.message_type == MESSAGE_TYPE_PUBLIC:
				self.c.spew(event.pname + "> " +event.message + "\r\n", CHAT.LIGHTGRAY)
			if event.message_type == MESSAGE_TYPE_CHAT:
				self.c.spew(str(event.chat_no)+ ":" + event.pname + "> " +event.message + "\r\n", CHAT.RED)
			if event.message_type == MESSAGE_TYPE_TEAM:
				self.c.spew(event.pname + "> " +event.message + "\r\n", CHAT.YELLOW)
			if event.message_type == MESSAGE_TYPE_FREQ:
				self.c.spew(event.pname + "> ", CHAT.GREEN)
				self.c.spew(event.message + "\r\n", CHAT.GRAY)
		if event.type == EVENT_TICK:
			self.c.ProcessInput(ssbot)
		elif event.type == EVENT_ENTER:
			self.c.spew("Entered: " + event.player.name+ "\r\n",CHAT.GRAY)	
		elif event.type == EVENT_LEAVE:
			self.c.spew("Left: " + event.player.name+ "\r\n",CHAT.GRAY)	
		if event.type == EVENT_ARENA_LIST:
			c= 0
			self.c.spew("-------------ArenaList---------\r\n",CHAT.RAINBOW)
			for a in event.arena_list:
				self.c.spew(a[0]+":  "+str(a[1])+ ("\r\n" if a[2] == 0 else "  <--YOU ARE HERE\r\n"),CHAT.WHITE)
##				if a[2] == 0:
##					self.c.spew("\r\n",CHAT.WHITE)
##				else:
##					self.c.spew("  <--YOU ARE HERE\r\n",CHAT.WHITE)	
					
			
	def Cleanup(self):
		self.c.Restore()
		#put any cleanup code in here this is called when bot is about to die
		pass

	






if __name__ == '__main__': #bot runs in this if not run by master u can ignore this 

	try:

		logger = logging.getLogger('')
		logger.setLevel(logging.DEBUG)	
		
		
		# set a format
		formatter = logging.Formatter('[%(asctime)s]:%(message)s')
		
		
		# define a Handler which writes INFO messages or higher to the sys.stderr
		#console = logging.StreamHandler()
		#console.setLevel(logging.DEBUG)
		# tell the handler to use this format
		#console.setFormatter(formatter)
		# add the handler to the mainloop logger
		#logger.addHandler(console)
	
		
		filehandler  = logging.FileHandler(os.getcwd()+ R"/chatbot.log",mode='a')
		filehandler.setLevel(logging.INFO)
		filehandler.setFormatter(formatter)
		logger.addHandler(filehandler)
		
		ssbot = SubspaceBot(False,True,None,logging.getLogger("CHAT"+".Core"))
		ssbot.setBotInfo(__name__,"TestBoT", botowner)
		
		BotList = []
		#get the module object for the current file...	
		module = sys.modules[globals()['__name__']]
		#loads atleast the masterbot
		md = ModuleData("TesttBot",module,"None","test.ini","wtf",logging.getLogger(__name__))
		bot = Bot(ssbot,md)
		BotList.append(bot)
	
		
		ssbot.connectToServer('66.235.184.102', 7900, botname, botpassword, '#master')		   
		
		while ssbot.isConnected():
				event = ssbot.waitForEvent()
				for b in BotList:
					b.HandleEvents(ssbot,event)
	#except (KeyboardInterrupt, SystemExit):
	#	pass
	except:
		LogException(logger)
	finally:
		for b in BotList:
			b.Cleanup()
		logger.critical("Testbot shutting down")
		filehandler.close()
