#------------------------------------------------------------------------------------------
#IMPORT
#------------------------------------------------------------------------------------------
import time
import os

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigList, ConfigListScreen

from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText

from mediabackends.e2_media_backend import E2MediaBackend
from protocol_handler import AirplayProtocolHandler

from Components.config import config
from Components.config import ConfigSubsection
from Components.config import ConfigSelection
from Components.config import getConfigListEntry
from Components.config import ConfigInteger
from Components.config import ConfigSubList
from Components.config import ConfigSubDict
from Components.config import ConfigText
from Components.config import configfile
from Components.config import ConfigYesNo
from Components.config import ConfigPassword

from Components.Network import iNetwork
from Screens.MessageBox import MessageBox

#------------------------------------------------------------------------------------------
#CONFIG
#------------------------------------------------------------------------------------------
config.plugins.airplayer = ConfigSubsection()

config.plugins.airplayer.startuptype  = ConfigYesNo(default = True)
#config.plugins.airplayer.interface    = ConfigSelection(default = "eth0", choices ={"eth0": _("LAN"), "wlan0": _("WLAN")})
config.plugins.airplayer.name         = ConfigText(default = "AirPlayer E2", fixed_size=False)
config.plugins.airplayer.path         = ConfigText(default = "/hdd/", fixed_size=False)
config.plugins.airplayer.bufferSize         = ConfigInteger(default = 8*1024*1024)

config.plugins.airplayer.save()

#------------------------------------------------------------------------------------------
#GLOBAL
#------------------------------------------------------------------------------------------
global_session = None
global_protocol_handler = None
global_media_backend = None
#===============================================================================
# class
# AP_MainMenu
#===============================================================================	
class AP_MainMenu(Screen, ConfigListScreen):
	
	skin = """<screen name="AP_MainMenu" title="AutoTimer Settings" position="center,center" size="565,370">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="5,50" size="555,250" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,301" zPosition="1" size="565,2" />
	</screen>"""
	
	def __init__(self, session, args = None):
		self.skin = AP_MainMenu.skin
		Screen.__init__(self, session)

		ConfigListScreen.__init__(
			self,
			[
				getConfigListEntry(_("Startup type"), config.plugins.airplayer.startuptype, _("Should the airplayer start automatically on startup?")),
				getConfigListEntry(_("Interface"), config.plugins.airplayer.interface, _("Which interface should be used for the airport service?")),
				getConfigListEntry(_("Service name"), config.plugins.airplayer.name, _("Which name should be used to identify the device with active airport service?")),
				getConfigListEntry(_("Buffer Size"), config.plugins.airplayer.bufferSize, _("How much Memmory should gstreamer allocate to buffer the Stream")),
				getConfigListEntry(_("Path"), config.plugins.airplayer.path, _("Path for the temp files.")),
			],
			session = session,
			on_change = self._changed
		)
		
		self._session = session
		self._hasChanged = False
		
		# Initialize widgets
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Start Service"))
		self["key_blue"] = StaticText(_("Stop Service"))
		
		# Define Actions
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"blue": self.keyStop,
			"yellow": self.keyStart,
			"cancel": self.keyCancel,
		}, -2)
		
		self.onLayoutFinish.append(self.setCustomTitle)
		
	def _changed(self):
		self._hasChanged = True
		
	def keyStart(self):
		print "[AirPlayer] pressed start"
		print "[AirPlayer] trying to stop if running"
		stopWebserver(global_session)
		print "[AirPlayer] trying to start"
		startWebserver(global_session)
		self.session.openWithCallback(self.close, MessageBox,_("Service successfully started"), MessageBox.TYPE_INFO, timeout = 5)
		
	def keyStop(self):
		print "[AirPlayer] pressed stop"
		stopWebserver(global_session)
		self.session.openWithCallback(self.close, MessageBox,_("Service successfully stoped"), MessageBox.TYPE_INFO, timeout = 5)
		
	def keySave(self):
		print "[AirPlayer] pressed save"
		self.saveAll()
		if self._hasChanged:
			self.session.openWithCallback(self.restartGUI, MessageBox, _("Some settings may need a GUI restart\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
		else:
			self.session.openWithCallback(self.quitPlugin, MessageBox, _("Nothing was changed. Do you want to quit?"), MessageBox.TYPE_YESNO)

	def quitPlugin(self, answer):
		if answer is True:
			self.close()
			
	def restartGUI(self, answer):
		if answer is True:
			from Screens.Standby import TryQuitMainloop
			stopWebserver(global_session)
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()
			
	def setCustomTitle(self):
		self.setTitle(_("Settings for Airplayer"))

		
#===============================================================================
# stopWebserver
# Actions to take place to stop the webserver
#===============================================================================		
def stopWebserver(session):
	os.system("killall zeroconfig &")
	print "[AirPlayer] service stopped"


#===============================================================================
# startWebserver
# Actions to take place to start the webserver
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
	
	os.system("killall zeroconfig")
	os.system("/usr/lib/enigma2/python/Plugins/Extensions/AirPlayer/zeroconfig \"" +  config.plugins.airplayer.name.value + "\" " + config.plugins.airplayer.interface.value + " &")
	
	print "[AirPlayer] starting zeroconf done"

#===============================================================================
# sessionstart
# Actions to take place on Session start 
#===============================================================================
def sessionstart(reason, session):
	global global_session
	global_session = session

		
#===============================================================================
# autostart
# Actions to take place in autostart (startup the Webserver)
#===============================================================================
def networkstart(reason, **kwargs):
	interfaces = []
	for i in iNetwork.getAdapterList():
		interfaces.append((i,i))
		print "[AirPlayer] found network dev",i
	config.plugins.airplayer.interface    = ConfigSelection(choices = interfaces)
	if reason == 1 and config.plugins.airplayer.startuptype.value:
		startWebserver(global_session)
	elif reason == 0:
		stopWebserver(global_session)
		
#===============================================================================
# main
# Actions to take place when starting the plugin over extensions
#===============================================================================
def main(session, **kwargs):
	session.open(AP_MainMenu)
	
#===============================================================================
# plugins
# Actions to take place in Plugins
#===============================================================================
def Plugins(**kwargs):
	return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_NETWORKCONFIG_READ], fnc=networkstart),
			PluginDescriptor(name = "AirPlayer", description = "AirPlayer", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
	