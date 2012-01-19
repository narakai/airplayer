import urllib2
import urllib
import time
import thread
import tempfile
import shutil
import os
import string
import xml.dom.minidom
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from enigma import eServiceReference, getDesktop, ePicLoad
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from base_media_backend import BaseMediaBackend
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService

class E2MediaBackend(BaseMediaBackend):

    def __init__(self, session):
        super(E2MediaBackend, self).__init__()
        self.session = session
        self.sref = None
        self.window = None
        self.onClose = [ ]
        self.bufferSeconds = 0
        self.bufferPercent = 0
        self.bufferSecondsLeft = 0
        self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
            {
                iPlayableService.evBuffering: self.__evUpdatedBufferInfo,
                
            })
    def __evUpdatedBufferInfo(self):
        bufferInfo = self.session.nav.getCurrentService().streamed().getBufferCharge()
        if bufferInfo[2] != 0:
            self.bufferSeconds = bufferInfo[4] / bufferInfo[2] #buffer size / avgOutRate
        else:
            self.bufferSeconds = 0
        self.bufferPercent = bufferInfo[0]
        self.bufferSecondsLeft = self.bufferSeconds * self.bufferPercent / 100
        if(self.bufferPercent > 90):
            if self.window is not None:
                self.window.bufferFull()
        if(self.bufferPercent < 3):
            if self.window is not None:
                self.window.bufferEmpty()
        print "Buffer",bufferInfo[4], "Info ",bufferInfo[0], "% filled ",bufferInfo[1],"/",bufferInfo[2]," buffered: ",self.bufferSecondsLeft, "s"
        #print "percent ",bufferInfo[0]
        #print "avgInRate ",bufferInfo[1]
        #print "avgOutRate ",bufferInfo[2]
        #print "buffering left ",bufferInfo[3]
        #print "buffer size ",bufferInfo[4]
    
    def cleanup(self):
        """
        Called when airplayer is about to shutdown.
        """
        print '[AirPlayer] cleanup'
        self.stop_playing()                    
        
    def stop_playing(self):
        """
        Stop playing media.
        """
        print '[AirPlayer] stop_playing'
        if self.window is not None:
            self.window.leavePlayer()
        self.sref = None
        self.window = None
        
    def show_picture(self, data):
        """
        Show a picture.

        Cannot do this in VLC, so we'll just pass here.

        @param data raw picture data.
        """
        print '[AirPlayer] show_picture '
        if self.window is not None:
            self.window.start_decode()
        #    self.window.leavePlayer()
        else:
            self.session.open(AirPlayPicturePlayer, self, config.plugins.airplayer.path.value + "pic.jpg")
        pass
        
    def play_movie(self, url):
        """
        Play a movie from the given location.
        @param url the address of the media file to add
        """
        print '[AirPlayer] play_movie'
        if self.window is not None:
            self.window.leavePlayer()
        sref = eServiceReference(0x1001, 0, url)
        sref.setName("AirPlay")
        self.sref = sref
        #self.session.openWithCallback(self.MoviePlayerCallback, AirPlayMoviePlayer, sref, self)
        self.session.open(AirPlayMoviePlayer, sref, self)

    def notify_started(self):
        """
        I don't believe there is a way to display a message to the user in VLC, so we are just going to print a message to the airplayer terminal instead saying that this backend has been loaded.
        """
        print '[AirPlayer] notify_started'
        print "[AirPlayer] Started connection to VLC"
        
    def pause(self):
        """
        Pause media playback.
        VLC doesn't have a seperate play and pause command so we'll
        have to check if there's currently playing any media.
        """
        print '[AirPlayer] pause'
        if self.window is not None:
            self.window.pauseService()
            
    def play(self):
        """
        Airplay sometimes sends a play command twice and since VLC
        does not offer a seperate play and pause command we'll have
        to check the current player state and choose an action
        accordingly.
        """
        print '[AirPlayer] play'
        if self.window is not None:
            self.window.unPauseService()
        
    def get_player_position(self):
        """
        Get the current videoplayer position.
        @returns int current position, int total length
        """
        print '[AirPlayer] get_play_posoition'
        time = 0
        length = 0
        service = self.session.nav.getCurrentService()
        seek = service and service.seek()
        if seek != None:
            r = seek.getLength()
            if not r[0]:
                length = r[1] / 90000
            r = seek.getPlayPosition()
            if not r[0]:
                time = r[1] / 90000
            
        return time, length, time + self.bufferSecondsLeft
        

    def set_player_position(self, position):
        """
        Set the current videoplayer position.
        @param position integer in seconds
        """
        
        time, length ,buffer = self.get_player_position()
        print '[AirPlayer] set_player_position: to:', position, " from:",time, " diff:",position - time
        if self.window is not None:
            self.window.unPauseService()
            self.window.doSeekRelative( int((position - time) * 90000) )
            
    def is_playing(self):
        if self.window is not None:
            return self.window.isPlaying()
        else:
            return False

    def set_start_position(self, percentage_position):
        """
        It can take a few seconds before VLC starts playing the movie
        and accepts seeking, so we'll wait a bit before sending this command.
        This is a bit dirty, but it's the best I could come up with. 
        @param percentage_position float
        """
        print '[AirPlayer] set_start_position: ',percentage_position
    
    def MoviePlayerCallback(self, response=None):
         print '[AirPlayer] MoviePlayerCallback: ',response
         self.sref = None
         self.window = None


class AirPlayMoviePlayer(MoviePlayer):
    def __init__(self, session, service, backend):
        MoviePlayer.__init__(self, session, service)
        self.backend = backend
        backend.window=self
        session.nav.getCurrentService().streamed().setBufferSize(config.plugins.airplayer.bufferSize.value)
        self.AutoPlay = True
        #self.skinName = "MoviePlayer"

    def bufferFull(self):
        if self.AutoPlay:
            if self.seekstate != self.SEEK_STATE_PLAY :
                self.setSeekState(self.SEEK_STATE_PLAY)
    
    def bufferEmpty(self):
        if self.AutoPlay:
            if self.seekstate != self.SEEK_STATE_PAUSE :
                self.setSeekState(self.SEEK_STATE_PAUSE)
    
    def leavePlayer(self):
        self.leavePlayerConfirmed(True)

    def leavePlayerConfirmed(self, answer):
        if answer:
            self.backend.window=None
            self.close()

    def doEofInternal(self, playing):
        self.backend.stop_playing()
            
    def isPlaying(self):
        if self.seekstate != self.SEEK_STATE_PLAY:
            return False
        else:
            return True
    
    def showMovies(self):
        pass
    

class AirPlayPicturePlayer(Screen):
    def __init__(self, session, backend, file):
        self.backend = backend
        backend.window=self
        #self.skinName = "MoviePlayer"

        self.bgcolor = "#00000000"
        space = 0 #formerly 40 we will see ;-)
        size_w = getDesktop(0).size().width()
        size_h = getDesktop(0).size().height()
        
        self.skin = "<screen position=\"0,0\" size=\"" + str(size_w) + "," + str(size_h) + "\" flags=\"wfNoBorder\" > \
            <eLabel position=\"0,0\" zPosition=\"0\" size=\""+ str(size_w) + "," + str(size_h) + "\" backgroundColor=\""+ self.bgcolor +"\" /> \
            <widget name=\"pic\" position=\"" + str(space+20) + "," + str(space) + "\" size=\"" + str(size_w-(space*2)) + "," + str(size_h-(space*2)) + "\" zPosition=\"1\" alphatest=\"on\" /> \
            </screen>"

        Screen.__init__(self, session)

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"],
        {
            "cancel": self.Exit,
        }, -1)

        self["pic"] = Pixmap()
        
        self.file = file
        
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.finish_decode)

        self.onLayoutFinish.append(self.setPicloadConf)
    
    def getScale(self):
        return AVSwitch().getFramebufferScale()
    
    def setPicloadConf(self):
        sc = self.getScale()
        self.picload.setPara([self["pic"].instance.size().width(), self["pic"].instance.size().height(), sc[0], sc[1], 0, 1, self.bgcolor])

        self.start_decode()

    def ShowPicture(self):
        if self.currPic != None:
            self["pic"].instance.setPixmap(self.currPic.__deref__())
            
    def finish_decode(self, picInfo=""):
        ptr = self.picload.getData()
        if ptr != None:
            text = ""
            try:
                text = picInfo.split('\n',1)
                text = "(" + str(self.index+1) + "/" + str(self.maxentry+1) + ") " + text[0].split('/')[-1]
            except:
                pass
            self.currPic = ptr
            self.ShowPicture()

    def start_decode(self):
        self.picload.startDecode(self.file)

    def leavePlayer(self):
        self.leavePlayerConfirmed(True)

    def leavePlayerConfirmed(self, answer):
        if answer:
            self.Exit()
        
    def Exit(self):
        del self.picload
        self.backend.window=None
        self.close()