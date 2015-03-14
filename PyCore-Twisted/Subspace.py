# Copyright (c) 2010 cycad <cycad@zetasquad.com>. All rights reserved.

# todo: bot.disconnect() and clean the interface between core disconnections and higher level disconnections
#changed import from import 1,2,3 to seperate lines as per python style guide
import socket
import sys
import struct  
import array
import os
import hashlib
import time
import types
import zlib
import platform
import random 
import traceback
import math


import SubspaceEncryption
from SubspaceFileChecksum import FileChecksum
from SubspaceSettings import * 
from logging import DEBUG,INFO,ERROR,CRITICAL

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, task

def GetTickCountHs():
    """Tick count in hundreths of a second."""
    return math.trunc(time.clock() * 100) & 0xFFFFFFFF


def TickDiff(now, base):
    """Returns the difference between two 32-bit tick counts."""
    return (now - base) & 0xFFFFFFFF



PRIORITY_HIGH = 0    # for sending a high priority packet, like position updates or ack messages
PRIORITY_NORMAL = 1    # for sending normal priority packets

MAX_PACKET = 512    # the maximum packet size

RELIABLE_RETRANSMIT_INTERVAL = 50    # in hundreths of seconds

EVENT_TICK_INTERVAL = 10 # how often EVENT_TICK happens, in hs, backed by an accumulator
EVENT_INTERNAL_CORE_PERIODIC_INTERVAL = 10 # not backed by an accumulator

NO_PACKET_RECEIVED_TIMEOUT_INTERVAL = 1500 # after 15 seconds without receiving data, disconnect


# core events
EVENT_GAME_PACKET_RECEIVED = 0



STATE_NONE = 0
STATE_CHALLENGE_RECEIVED = 1
STATE_CONNECTED = 2
EVENT_HANDLER_PRE = -1 
EVENT_HANDLER_MAIN = 0
EVENT_HANDLER_POST = 1



"""

"""
EVENT_TICK = 1
"""Occurs every 1/10th of a second.

Sets: type"""

EVENT_DISCONNECT = 2
"""Occurs when the bot disconnects from the server.

Sets: type"""

EVENT_START = 3
"""Occurs when the bot logs in to the server.

At this point, commands and messages can be sent with success.  If the bot needs
to run any commands automatically on login, this is the time to do that.

Sets: type"""
EVENT_LOGIN = 4
"""
occours when bot is added to the playerlist so u can priv it


"""


EVENT_MESSAGE = 5
"""Indicates the bot received a message.

message is the text of the message.  message_type indicates what type of message
was received, and is one of the MESSAGE_TYPE_Xxx constants.

Sets:
        event.player = player
        event.message = message
        event.message_type = message_type
        event.pname = message_name
        event.chat_no = chatnum
        event.alert_name = alert
        event.alert_arena = arena
"""

EVENT_ENTER = 6
"""Indicates a player entered the arena.

player is the player who entered.

A bot will receive an enter event for itself, so to avoid taking action on the
bot check event.player.pid against bot.pid.

Sets: type, player"""

EVENT_LEAVE = 7
"""Indicates a player left the arena.

player is the player who left.

Sets: type, player"""

EVENT_CHANGE = 8
"""Happens when a player changes ship, freq, or both.

player is the player that changed freq.  old_freq is the player's old frequency.
old_ship is the player's old ship. If {freq,ship} didn't change, old_{ship,freq}
are equal.
            event.player
            event.old_freq = player.freq
            event.old_ship = player.ship
            player.ship = new_ship
            player.freq = new_freq


"""

EVENT_COMMAND = 9
"""A command was used.

player is the player that used the command.

command is the Command object that was used.  arguments are an array, starting
at the first argument.  arguments_after is an array of an argument and everything
after it, starting at the first argument. If there are no arguments passed,
arguments and arguments_after are empty lists.

For example after the command: !command a b c
   arguments = ['a', 'b', 'c']
   arguments_after = ['a b c', 'b c', 'c']
   
This allows you to match players with spaces in their name such as:
    !lag C H E E P
by using arguments_after[0]
   
Sets: type, player, command, arguments, arguments_after.
            event = GameEvent(EVENT_COMMAND)
            event.player = event.player
            event.command = command
            event.arguments = event.arguments
            event.arguments_after = event.arguments_after
            event.pname = event.pname
            event.plvl = event.plvl
            event.chat_no = event.chat_no
            event.alert_name = event.alert_name
            event.alert_arena = event.alert_arena
            event.command_type = event.command_type


"""

EVENT_POSITION_UPDATE = 10
"""A position update was received for player.

Sets: type, player,fired_weapons,sd_updated
updates:
            player.rotation = rotation
            player.x_pos = x_pos
            player.y_pos = y_pos
            player.x_vel = x_vel
            player.y_vel = y_vel
            player._setStatus(status)
            player.Bounty = Bounty
            player.ping = latency
            player.last_pos_update_tick = GetTickCountHs()


if sd_updated == true then 
spectator data in the player class is updated

if fired_weapons is true 
event sets:
        event.weapons_type == WEAPON_XX
        event.weapons_level = 0-4
        event.shrap_level = 0-4?
        event.shrap = 0 -31
        event.alternate = 1 for mines if mines/proxMines else bomb/proxbomb
                          also indicates multifire/singlefire for bullets      



"""

EVENT_KILL = 11
"""A kill event was set.

killer is the player who did the killing, killed is the player who died.

Sets: type, killer, killed, flags_transfered,death_green_id,Bounty"""

EVENT_ARENA_LIST = 12
"""An arena list was received.  This is usually in response to sending a pub message
containing '?arena'.

arena_list is a list of (arena_name, num_players,here) tuples.

bot.arena is updated during this event.

Sets: type, arena_list"""


EVENT_GOAL = 13
"""A goal was scored.

freq is the frequency the goal was scored by.
points is the amount of points rewarded to the freq by scoring a goal.

This event has no associated PID with it.

Sets: type, freq, points"""

EVENT_FLAG_PICKUP = 14
"""Someone picked up a flag.

player is the player who picked up the flag.
flag_id is the id for the flag that was picked up.

Sets: type, player, flag_id, old_freq,new_freq,x,y"""

EVENT_FLAG_DROP = 15
"""Someone dropped a flag.

player is the player who dropped the flag.

Sets: type, player, flag_count"""

EVENT_TURRET = 16
"""A player attached to another player.

turreter is the player who attached to another player.
turreted is the player who was attached to.
old_turreted is a player if the event is a detach else it is None

Sets: type, turreter, turreted,old_turreted"""

EVENT_PERIODIC_REWARD = 17
"""Freqs are periodically given rewards for the amount of flags they own.

point_list is a list of (freq, points) tuples.

Sets: type, point_list"""

EVENT_BALL = 18
"""Ball periodically sends update packets to the server. This event records this data.

ball_id is the ID of the ball, x and y_pos hold the x and y coordinates in pixel-coordinates.
x and y_vel holds the x and y velocity in pixels per 10 seconds.
time might be the timestamp since last ball update packet? uncertain.

Sets: type, ball_id, x_pos, y_pos, x_vel, y_vel, player, time"""




EVENT_MODULE = 19
"""Custom module event 
Sets: type,event_source,event_name,event_data
this event is so a module can share information with any other module running on the same bot
example:
infobot will parse all the information from *info and pass the info class as a module event
to any other module that is running

"""

EVENT_BROADCAST = 20
"""Custom module event 
Sets: type,bsource,bmessage
this event is used for interbot communication 
think of it as equivilant to all the bots being on the 
same chat sending messages to eachother
"""

EVENT_PRIZE = 21
"""
Sets time_stamp,x,y,prize,player
happens when a player picksup a green
"""
EVENT_SCORE_UPDATE = 22
"""
Sets type,
            event.player
            old values:
            event.old_flag_points 
            event.old_kill_points
            event.old_wins 
            event.old_losses 
            new values:
            player.wins
            player.flag_points
            player.kill_points
            player.losses
            all the new values will be
player score will be updated at this time
"""
EVENT_SCORE_RESET = 23
"""
pid = 0xffff if all players reset
Sets: type,pid, player player will be None if pid is 0xffff which indicates
everyone in the arena has been reset to 0
"""
EVENT_FLAG_UPDATE = 24
"""
sets: type,freq,flag_id,x,y
this is sent periodicly, it will update the position of dropped flags
in flag drop the position of the flag wont be known until the next 
flag update
"""
EVENT_FLAG_VICTORY = 25
"""
Sets:type,freq,points 
"""
EVENT_ARENA_CHANGE = 26
"""
Sets type,old_arena
sent when a bot changes arenas
"""

EVENT_WATCH_DAMAGE = 27
"""
when the bot /*watchdamage's a player the bot will get this event everytime he takes damage
event sets:
        event.attacker
        event.attacked
        event.energy_old
        event.energy_lost
        event.weapons_type == WEAPON_XX
        event.weapons_level = 1-4
        event.shrap_level = 1-4?
        event.shrap = 0 -31
        event.alternate = 1 for mines if mines/proxMines else bomb/proxbomb 
"""
EVENT_BRICK = 28
"""sets  event.brick_list  where each brick is a brick class"""

EVENT_SPEED_GAME_OVER = 29
"""
sets bot_score,bot_rank,winners = [(rank,player,score),...]
"""

EVENT_PARSER = 30
PE_INFO = 1
PE_EINFO = 2


COMMAND_TYPE_PUBLIC = 0x02
"""A public COMMAND (blue)."""
COMMAND_TYPE_TEAM = 0x03
"""A team COMMAND (yellow)."""
COMMAND_TYPE_FREQ = 0x04
"""A freq COMMAND (green name, blue text)"""
COMMAND_TYPE_PRIVATE = 0x05
"""A private COMMAND (sourced green, in-arena)."""
COMMAND_TYPE_REMOTE = 0x07
"""A remote COMMAND (sourced green, out of arena."""
COMMAND_TYPE_CHAT = 0x09
"""A chat COMMAND (red)."""
COMMAND_TYPE_ALERT = 0x0A
"""Actually a remote message but lets pass it on as an alert"""

#convenience vars for command registration
COMMAND_LIST_PP = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_PRIVATE]
"""private and public COMMAND"""
COMMAND_LIST_PR = [COMMAND_TYPE_PRIVATE,COMMAND_TYPE_REMOTE]
"""private and public COMMAND"""
COMMAND_LIST_PPR = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_PRIVATE,
                COMMAND_TYPE_REMOTE]
"""private and public and remote COMMAND"""
COMMAND_LIST_PPRC = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_PRIVATE,
                COMMAND_TYPE_REMOTE,COMMAND_TYPE_CHAT]
"""private and public and remote and Chat COMMANDs"""
COMMAND_LIST_PPC = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_PRIVATE,
                COMMAND_TYPE_REMOTE,COMMAND_TYPE_CHAT]
"""private and public and Chat COMMANDs"""
COMMAND_LIST_ALL = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_TEAM,
                COMMAND_TYPE_FREQ,COMMAND_TYPE_PRIVATE,
                COMMAND_TYPE_REMOTE,COMMAND_TYPE_CHAT]


FREQ_NONE = 0xFFFF

PID_NONE = 0xFFFF

SOUND_NONE = 0

MESSAGE_TYPE_ARENA = 0x00
MESSAGE_TYPE_SYSTEM = MESSAGE_TYPE_ARENA
"""An arena message (unsourced green)."""
MESSAGE_TYPE_PUBLIC_MACRO = 0x01
"""A public macro message (blue)."""
MESSAGE_TYPE_PUBLIC = 0x02
"""A public message (blue)."""
MESSAGE_TYPE_TEAM = 0x03
"""A team message (yellow)."""
MESSAGE_TYPE_FREQ = 0x04
"""A freq message (green name, blue text)"""
MESSAGE_TYPE_PRIVATE = 0x05
"""A private message (sourced green, in-arena)."""
MESSAGE_TYPE_WARNING = 0x06
"""A warning message from \*warn."""
MESSAGE_TYPE_REMOTE = 0x07
"""A remote message (sourced green, out of arena."""
MESSAGE_TYPE_SYSOP = 0x08
"""A sysop message (dark red)."""
MESSAGE_TYPE_CHAT = 0x09
"""A chat message (red)."""
MESSAGE_TYPE_ALERT = 0x0A
"""Actually a parsed remote message but lets pass it on as an alert"""


SHIP_WARBIRD = 0
SHIP_JAVELIN = 1
SHIP_SPIDER = 2
SHIP_LEVIATHAN = 3
SHIP_TERRIER = 4
SHIP_WEASEL = 5
SHIP_LANCASTER = 6
SHIP_SHARK = 7
SHIP_SPECTATOR = 8
SHIP_NONE = SHIP_SPECTATOR

STATUS_STEALTH = 0x01
STATUS_CLOAK = 0x02
STATUS_XRADAR = 0x04
STATUS_ANTIWARP = 0x08
STATUS_FLASHING = 0x10
STATUS_SAFEZONE = 0x20
STATUS_UFO = 0x40

PRIZE_RECHARGE=            1     
PRIZE_ENERGY=            2
PRIZE_ROTATION=            3
PRIZE_STEALTH=            4
PRIZE_CLOAK=            5
PRIZE_XRADAR=            6
PRIZE_WARP=                7
PRIZE_GUNS=                8
PRIZE_BOMBS=            9
PRIZE_BOUNCINGBULLETS=  10
PRIZE_THRUSTER=            11
PRIZE_TOPSPEED=            12
PRIZE_FULLCHARGE=        13
PRIZE_ENGINESHUTDOWN=    14
PRIZE_MULTIFIRE=        15
PRIZE_PROXIMITY=        16
PRIZE_SUPER=            17
PRIZE_SHIELDS=            18
PRIZE_SHRAPNEL=            19
PRIZE_ANTIWARP=            20
PRIZE_REPEL=            21
PRIZE_BURST=            22
PRIZE_DECOY=            23
PRIZE_THOR=                24
PRIZE_MULTIPRIZE=        25
PRIZE_BRICK=            26
PRIZE_ROCKET=            27
PRIZE_PORTAL=            28


WEAPONS_NULL=           0
WEAPONS_BULLET=           1
WEAPONS_BOUNCEBULLET=  2
WEAPONS_BOMB=           3
WEAPONS_PROXBOMB=       4
WEAPONS_REPEL=           5
WEAPONS_DECOY=           6
WEAPONS_BURST=           7
WEAPONS_THOR=           8

#misc definitions
COORD_NONE = 0xFFFF
PID_NONE = 0xFFFF
FREQ_NONE = 0xFFFF

#botmode
BM_STANDALONE = 0
BM_SLAVE      = 2
BM_MASTER     = 3            

class CoreEvent:
    """Represents an event generated by the Core."""
    def __init__(self, type):
        self.type = type

class QueuedPacket:
    """Represents a packet that is in queue to be sent on the network."""
    def __init__(self, data, reliable=False):
        self.data = data
        self.reliable = reliable
        if self.totalPacketSize() > MAX_PACKET:
            raise Exception("Packet has a size greater than the maximum allowed: %d" % self.totalPacketSize())
    
    def totalPacketSize(self):
        """Compute the total packed size, including the size of the reliable header if necessary."""
        if self.reliable: return len(self.data) + 6
        else: return len(self.data)


class GameEvent:
    """Represents an event generated by the core."""
    
    type = None
    """Is one of EVENT_Xxx."""
    
    def __init__(self, type):
        self.type = type
        
class Player:
    """A class that represents the a Player.  All values are read-only to bots except
    for the 'player_info' variable that is reserved for bot's per-player data storage.
    
    The x_pos, y_pos, x_vel, y_vel, and status_Xxx are only as recent as the last_pos_update_tick
    timestamp.  Position updates are only received for players on the bot's radar, except
    in the case where a player first enters a safe area."""
        
    name = None
    """The player's name"""
    
    squad = None
    """The player's squad"""
    
    banner = None
    """A player's banner"""
    
    pid = None
    """The player's PID, unique for all players in the arena. Invalid after EVENT_LEAVE."""
    
    ship = None
    """The player's ship, one of SHIP_Xxx.  Use GetShipName() get the ship's name as a string."""

    freq = None
    """The player's current frequency."""
    
    x_pos = None
    """The player's X coordinate, in pixels.  This is only as recent as 'last_pos_update_tick."""
    
    y_pos = None
    """The player's Y coordinate, in pixels.  This is only as recent as 'last_pos_update_tick."""
    
    x_vel = None
    """The player's X velocity.  This is only as recent as 'last_pos_update_tick."""
    
    y_vel = None
    """The player's Y velocity.  This is only as recent as 'last_pos_update_tick."""
    
    bounty = None
    """plays Bounty is updated in position updats"""
    
    ping = None
    """also updated in event pos """
    
    last_pos_update_tick = None
    """The tickstamp, in hundreths of seconds, of when the player's last position update was received."""
    
    __extra_data = {}
    """Use This To Share Data between bot classes, look at the setExtraData,GetExtraData Function in this class
     use case example:
     Info/LagBot Has the entire parsed  data from *info and wants to share this with other bots, perhaps an alias bot need sthe ip from it,
     or another bot wants to use the lag info for something else. 
     
     so the infobot would get the  get the player p
     then do something like p.setPlayerInfo("info",info)
     or perhaps it just wants to set the ip and mid
     p.setExtraData("ip",info.identity.ip)
     p.setExtraData("mid",info.identity.mid)
     
     then if any other bot class  in the same bot needs that info it can check  
     
     ip = p.getExtraData("ip")
     if ip not None:
         #use ip
         print ip
     
    
    """
        
    status_stealth = None
    """True if the player has stealth on, otherwise False."""
    
    status_cloak = None
    """True if the player has cloak on, otherwise False."""
    
    status_xradar = None
    """True if the player has XRadar on, otherwise False."""
    
    status_antiwarp = None
    """True if the player has AntiWarp on, otherwise False."""
    
    status_flashing = None
    """I not know what this indicates."""
    
    status_safezone = None
    """True if the player is in a safe area, otherwise False."""
    
    status_ufo = None
    """True if the player has UFO toggles, otherwise False."""
    flag_points =None
    kill_points =None
    wins =None
    losses =None
    
    flag_count =None
    turreted_pid =None
    #turreter_list =None
    
    ping =None
    bounty =None
    
    #if carrying ball else 0xffff
    ball_id =None

    
    #spectator data look at sd_time to see when it was last updated
    sd_energy =None
    sd_s2c_ping =None
    sd_timer =None
    sd_shields =None
    sd_super =None
    sd_bursts =None
    sd_repels =None
    sd_thors =None
    sd_bricks =None
    sd_decoys =None
    sd_rockets =None
    sd_portals =None
    sd_time =None
    
    
    def __init__(self, name, squad, pid, ship, freq):
        """Initialize the Player object."""
        self.name = name
        self.squad = squad
        self.pid = pid
        self.ship = ship
        self.freq = freq
        

        self.rotation = 0
        self.x_pos = -1
        self.y_pos = -1
        self.x_vel = 0
        self.y_vel = 0
        self.last_pos_update_tick = None
        self.player_info = None
        self._setStatus(0x00)

        self.flag_points = 0
        self.kill_points = 0
        self.wins = 0
        self.losses = 0
        
        self.flag_count = 0
        self.turreted_pid = 0xFFFF # pid of the player this  player is turreting
    
        
        self.ping = 0
        self.bounty = 0
        
        #if carrying ball else 0xffff
        self.ball_id = 0xffff

        
        #spectator data look at sd_time to see when it was last updated
        self.sd_energy = 0
        self.sd_s2c_ping = 0
        self.sd_timer = 0
        self.sd_shields = 0
        self.sd_super = 0
        self.sd_bursts = 0
        self.sd_repels = 0
        self.sd_thors = 0
        self.sd_bricks =0
        self.sd_decoys =0
        self.sd_rockets =0
        self.sd_portals =0
        self.sd_time = 0
        
        self._extra_data = {}
        
    
    def __str__(self):
        return self.name
    
    def _setStatus(self, status_flags):
        """Updates the player's status with the status flags received in the position update packet."""
        self.status_stealth = status_flags & STATUS_STEALTH != 0
        self.status_cloak = status_flags & STATUS_CLOAK != 0
        self.status_xradar = status_flags & STATUS_XRADAR != 0
        self.status_antiwarp = status_flags & STATUS_ANTIWARP != 0
        self.status_flashing = status_flags & STATUS_FLASHING != 0
        self.status_safezone = status_flags & STATUS_SAFEZONE != 0
        self.status_ufo = status_flags & STATUS_UFO != 0
        
    def getExtraData(self,data_name):
        return self.__extra_data.get(data_name,None)
    def setExtraData(self,data_name,data):
        self.__exta_data[data_name] = data  


class Command():

    def __init__(self,id,name,alias,access_level,msg_types_list,category,args,help_short,help_long=None):
        self.id = id
        self.name= name
        self.alias= alias
        self.access_level= access_level
        self.msg_types = 0
        self.msg_types = msg_types_list
        self.category= category
        self.args= args
        self.help_short = help_short
        self.help_long= help_long
    def IsAllowed(self,ss_msg_type):
        if ss_msg_type in self.msg_types:
            return True
        else:
            return False

        
class ModuleInfo():
    def __init__(self,filename,name,author,description,version):
        self.filename=filename
        self.name=name
        self.author=author
        self.description=description
        self.version = version

class Timer:
    """Represents a timer created with setTimer in the core."""
    
    id = None
    """The ID of the timer."""
    
    duration = None
    """The the duration of the timer."""
    
    user_data = None
    """The user_data value passed in to the setTimer() call when the timer was created."""
    
    base = None
    """The tickstamp when the timer was created."""
    
    def __init__(self, id, seconds, user_data=None):
        self.id = id
        self.duration = seconds * 100 # to ticks
        self.user_data = user_data
        self.base = GetTickCountHs()

def GetShipName(ship):
    """Get the name of a ship from a SHIP_Xxx constant."""
    if ship == SHIP_WARBIRD:
        return 'Warbird'
    elif ship == SHIP_JAVELIN:
        return 'Javelin'
    elif ship == SHIP_SPIDER:
        return 'Spider'
    elif ship == SHIP_LEVIATHAN:
        return 'Leviathan'
    elif ship == SHIP_TERRIER:
        return 'Terrier'
    elif ship == SHIP_WEASEL:
        return 'Weasel'
    elif ship == SHIP_LANCASTER:
        return 'Lancaster'
    elif ship == SHIP_SHARK:
        return 'Shark'
    elif ship == SHIP_SPECTATOR:
        return 'Spectator'
    else:
        return 'Unknown'


MAX_FLAGS = 256

class Flag():
    def __init__(self,id,pid=0xFFFF,freq=0xFFFF,x=0xFFFF,y=0xFFFF):
        self.id=id
        #self.pid = pid
        self.freq=freq #if == FREQ_NONE flag neuted
        self.x=x #if == coord_none  flag is carried
        self.y=y #if == coord_none  flag is carried

MAX_BALLS = 8

class Ball():
    def __init__(self,id,pid=0xFFFF,x=0xFFFF,y=0xFFFF):
        self.id=id
        self.pid=pid
        self.x=x
        self.y=y
        self.time = 0

class Brick():
    def __init__(self,x1,y1,x2,y2,freq,id,timestamp):
        self.x1= x1
        self.y1= y1
        self.x2= x2
        self.y2= y2
        self.freq= freq
        self.id= id
        self.timestamp = timestamp
                
class Oplist:
    def __init__(self,filename='Ops.ini'):
        self.__ops_dict = {}
        self.__filename = filename
        self.Read()
    def __isValidLevel(self,lvl):
        if lvl >0 and lvl <= 9:
            return True
        else:
            return False     

    def GetAccessLevel(self, name):
        n = name.lower()
        if n in self.__ops_dict:
            return self.__ops_dict[n]
        else:
            return 0
    def AddOp(self,lvl,name):
        n = name.lower()
        if self.__isValidLevel(lvl):
            self.__ops_dict[n] = lvl
            self.Write()
            return True
        else:
            return False

    def DelOp(self,name):
        n = name.lower()
        if n in self.__ops_dict:
            del self.__ops_dict[n]
            self.Write()
            return True
        else:
            return False;
    def ListOps(self,ssbot,event):
        c = 0
        for name,lvl in self.__ops_dict.iteritems():
            if(event.plvl >= lvl):
                ssbot.sendReply(event,"OP:%25s:%i" %(name,lvl))
            c+=1
        if c == 0:
            ssbot.sendReply(event,"No Ops")
        pass
    def Read(self):        
#        self.__ops_dict = dict(((line[2:].strip().lower(),int(line[0])) for line in open(self.__filename,'r') if line.strip() != ""))
        lines = open(self.__filename,'r')
        pline = ((line[2:].strip().lower(),int(line[0])) for line in lines if line.strip() != "")
        self.__ops_dict = dict(pline)

    def Write(self):
        file = open (self.__filename, 'w' )
        for name,lvl in self.__ops_dict.iteritems():
            file.write(str(lvl)+":"+name+"\n")
            
