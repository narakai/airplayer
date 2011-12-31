from Plugins.Plugin import PluginDescriptor

import os
from mediabackends.e2_media_backend import E2MediaBackend
from protocol_handler import AirplayProtocolHandler
import time
#===============================================================================
# start the Webinterface for all configured Interfaces
#===============================================================================
def startWebserver(session):
	global global_protocol_handler
	global global_media_backend
	print "[AirPlayer] starting webserver"
	print "[AirPlayer] init Backend"
	media_backend = E2MediaBackend(session)
	print "[AirPlayer] init protocol handler"
	protocol_handler = AirplayProtocolHandler(6002, media_backend)
	
	global_protocol_handler = protocol_handler
	global_media_backend = media_backend
	print "[AirPlayer] starting protocol hadler"
	protocol_handler.start()												
	print "[AirPlayer] starting webserver done"
	print "[AirPlayer] starting zeroconf"
	os.system("/usr/lib/enigma2/python/Plugins/Extensions/AirPlayer/sh4-zero duckbox &")
	print "[AirPlayer] starting zeroconf done"
	

def stopWebserver(session):
	print "[AirPlayer] stopping zeroconf"
	os.system("killall sh4-zero &")
	print "[AirPlayer] stopping zeroconf done"
	
global_session = None
global_protocol_handler = None
global_media_backend = None
#===============================================================================
# sessionstart
# Actions to take place on Session start 
#===============================================================================
def sessionstart(reason, session):
	global global_session
	global_session = session

		
#===============================================================================
# networkstart
# Actions to take place after Network is up (startup the Webserver)
#===============================================================================
def networkstart(reason, **kwargs):
	if reason is True:
		startWebserver(global_session)
		
	elif reason is False:
		stopWebserver(global_session)

def Plugins(**kwargs):
	return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_NETWORKCONFIG_READ], fnc=networkstart)]
	
#if __name__ == '__main__':
#    startWebserver(None)
#    while True:
#    	time.sleep(10)
