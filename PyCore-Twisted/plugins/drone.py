'''
@author: The Junky
'''
import os
import logging
from SubspaceBot import *
from BotUtilities import *
import random
import math
import threading

class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"dronebot","The Junky","chases players around center",".01")
		#do any other initialization code here
		#...
		self.count = 0
		self.x = 8192
		self.y = 8192
		self.direction =-1
		self.rotation=0
		self.current_target_count=9999
		self.current_target_pid = 0
		self.logged_in = False
		self.last_death = GetTickCountHs()
		self.ssbot = ssbot

		
	def HandleEvents(self,ssbot,event):
		if event.type == EVENT_LOGIN:
			#ssbot.sendShipChange(SHIP_LEVIATHAN)
			me = ssbot.findPlayerByPid(ssbot.pid)
			ssbot.sendPrivateMessage(me,"*setship " + str(random.randint(1,7)))
			ssbot.sendPrivateMessage(me,"*setfreq "+ str(random.randint(100,150)))
			ssbot.setPosition()
			self.logged_in = True
			#ssbot.createPeriodicCallBack(self.veryFastTick(),0.01,False)
		elif event.type == EVENT_TICK:
			self.count+=1
			if self.logged_in:
				self.move(ssbot,True)
			self.current_target_count+=1
			if self.current_target_count >= 100:
					self.current_target_count =0

		elif event.type == EVENT_POSITION_UPDATE:
			#self.move(ssbot)
			if event.player.pid != ssbot.pid:
				if (self.current_target_count == 0 
				and event.player.freq != ssbot.freq 
				and event.player.freq < 2):
					self.current_target_pid = event.player.pid
					ssbot.sendPublicMessage("target: " + event.player.name)
				self.move(ssbot)
			if event.player.pid != ssbot.pid and event.fired_weapons == True:
				print "%s(%i)"% (event.player.name,event.player.rotation)
				print self.getallTr(ssbot,event.player)
				if (event.player.freq != ssbot.freq
				and TickDiff(GetTickCountHs(),self.last_death) > 500
				and event.player.rotation in self.getallTr(ssbot,event.player)):
					ssbot.sendPublicMessage("killed by " + event.player.name)
					#ssbot.sendDeathPacket(event.player)
					self.last_death = GetTickCountHs()
					self.x = 8192
					self.y = 8192


	def veryFastTick(self):
		self.logger.info("very Fast Tick")
		self.move(self.ssbot,False)
		self.ssbot.flushOutboundQueues()
		
	def move(self,ssbot,fire=False):
		player = ssbot.findPlayerByPid(self.current_target_pid)
		if player == None:
			return
		r = self.getRotation(self.x,self.y,player.x_pos,player.y_pos)
		
		if r > self.rotation:
			self.direction = 1
		elif r < self.rotation:
			self.direction = -1
		else:
			self.direction = 0
		self.rotation= (self.rotation+ self.direction) %40
		if self.rotation < 0:
			self.rotation=39
		dx = (player.x_pos-self.x)
		dy =(player.y_pos - self.y)

		

		rnd = random.randint(0,100)
		if rnd in [5,90] and fire:
			weapons=ssbot.makeWeapons(random.choice([1,2,3,4,5,6,7]),0,2,2,31,0)
		else:
			weapons = 0
		dx = dx if dx != 0 else 1
		m = (dy*1.0)/(dx*1.0)
		mx = math.fabs(m)
		if mx == 0:
			m=1
		while mx > 50:
			m = m/10
			mx = math.fabs(m)

		
		b= self.y -(m*self.x)
		rx = 1 #random.randint(1,3)
		nx = self.x + (rx if dx > 0 else -1*rx)
		ny = int(math.ceil(m*nx+b))
		ry = 2*rx
		if(ny - self.y) > ry:
			ny= self.y + ry
		if(self.y - ny) > ry:
			ny= self.y - ry
			
		xv = int(math.ceil((self.x-nx)))
		yv = int(math.ceil((self.y-ny)))
		#print("my position:%i,%i"%(self.x,self.y))
		#print("target position:%i,%i"%(player.x_pos,player.y_pos))
		#print("dx:%i,dy:%i,slope:%f,rotation:%i,distance:%f,angle:%i"%(dx,dy,m,r,0,angle))
		#print("y = mx+b ::%i =%f*%i+%f"%(ny,m,nx,b))
		if nx < 4000 or nx> 12000 or ny < 4000 or ny > 12000:
			self.x = 8192
			self.y = 8192
			#print ("Warped %i,%i" %(nx,ny))
			pass
		else:
			self.x = nx
			self.y = ny

		#print("%i,%i,%i,%i,%i,%i,%i,%i,%i" % (self.x,self.y,xv,yv,self.rotation,0,1000,10000,weapons))
		ssbot.sendFireWeapon(self.x,self.y,xv,yv,self.rotation,0,10,100,weapons)
	def getallTr(self,ssbot,p):
		return self.getTr(ssbot,p.x_pos,p.y_pos)
	def getTr(self,ssbot,x,y):
		t = int(self.transposedRotation(self.getRotation(ssbot.x_pos,ssbot.y_pos,x,y)))
		#print [t-1,t,t+1]
		return [t-1 if t >0 else 39,t,t+1 if t<39 else 0]		
	def transposedRotation(self,o):
		return ((o+20)%40)

	def radian_to_rotation(self,radian):
		return (round(radian*6.36619772,0)+30)%40

	def getRotation(self,x,y,x2,y2):
		return self.radian_to_rotation(math.atan2((y2-y),(x2-x))+math.pi)

	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass

	def getAngle(self, x1, y1, x2, y2):
		# Return value is 0 for right, 90 for up, 180 for left, and 270 for down (and all values between 0 and 360)
		rise = y1 - y2
		run = x1 - x2
		angle = math.atan2(run, rise) # get the angle in radians
		angle = angle * (180 / math.pi) # convert to degrees
		angle = (angle + 90) % 360 # adjust for a right-facing sprite
		return angle

if __name__ == '__main__':
	botMain(Bot)

