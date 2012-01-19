import appletv

import lib.biplist
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet   import reactor, threads
from httputil import HTTPHeaders
from Components.config import config
from Components.Network import iNetwork

class AirplayProtocolHandler(object):
    
    def __init__(self, port, media_backend):
        self._http_server = None
        self._media_backend = media_backend
        self._port = port
    
    def start(self):
        try:
            root = Resource()
            
            #Dynamic Pages Main => WebMainActions
            root.putChild("reverse", ReverseHandler(self._media_backend))
            root.putChild("play", PlayHandler(self._media_backend))
            root.putChild("scrub", ScrubHandler(self._media_backend))
            root.putChild("rate", RateHandler(self._media_backend))
            root.putChild("photo", PhotoHandler(self._media_backend))
            root.putChild("authorize", AuthorizeHandler(self._media_backend))
            root.putChild("server-info", ServerInfoHandler(self._media_backend))
            root.putChild("slideshow-features", SlideshowFeaturesHandler(self._media_backend))
            root.putChild("playback-info", PlaybackInfoHandler(self._media_backend))
            root.putChild("stop", StopHandler(self._media_backend))
            #root.putChild("setProterpy", SetProterpyHandler(self._media_backend))
            #root.putChild("getProterpy", GetProterpyHandler(self._media_backend))
            
            site = Site(root)
            port = self._port
            reactor.listenTCP(port, site, interface="0.0.0.0")
            #reactor.run()
        except Exception, ex:
            print("Exception(Can be ignored): " + str(ex), __name__, "W")
        
        
    
class BaseHandler(Resource):
    """
    Base request handler, all other handlers should inherit from this class.

    Provides some logging and media backend assignment.
    """
    def __init__(self, media_backend):
        self._media_backend = media_backend  

    
class ReverseHandler(BaseHandler):
    """
    Handler for /reverse requests.

    The reverse command is the first command sent by Airplay,
    it's a handshake.
    """

    def render_POST(self, request):
        print "[AirPlayer] PPeverseHandler POST"
        
        request.setResponseCode(101)
        request.setHeader('Upgrade', 'PTTH/1.0')
        request.setHeader('Connection', 'Upgrade')
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

class PlayHandler(BaseHandler):
    """
    Handler for /play requests.

    Contains a header like format in the request body which should contain a
    Content-Location and optionally a Start-Position.
    """

    def render_POST(self, request):
        print "[AirPlayer] PlayHandler POST"
        """
        Immediately finish this request, no need for the client to wait for
        backend communication.
        """
        
        if request.getHeader('Content-Type') == 'application/x-apple-binary-plist':
            body = lib.biplist.readPlistFromString(request.content.getvalue())
        else:
            body = HTTPHeaders.parse(request.content.getvalue())    
        
        print "[AirPlayer] body:",body;
        if 'Content-Location' in body:
            url = body['Content-Location']
            print '[AirPlayer] Playing ', url
            
            self._media_backend.play_movie(url)

            if 'Start-Position' in body:
                """ 
                Airplay sends start-position in percentage from 0 to 1.
                Media backends expect a percentage from 0 to 100.
                """
                try:
                    str_pos = body['Start-Position']
                except ValueError:
                    print '[AirPlayer] Invalid start-position supplied: ', str_pos
                else:        
                    position_percentage = float(str_pos) * 100
                    self._media_backend.set_start_position(position_percentage)
        
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET


class ScrubHandler(BaseHandler):
    """
    Handler for /scrub requests.

    Used to perform seeking (POST request) and to retrieve current player position (GET request).
    """       

    def render_GET(self, request):
        print "[AirPlayer] ScrubHandler GET"
        """
        Will return None, None if no media is playing or an error occures.
        """
        position, duration, bufferPosition = self._media_backend.get_player_position()

        """
        Should None values be returned just default to 0 values.
        """
        if not position:
            duration = position = 0

        body = 'duration: %f\r\nposition: %f\r\n' % (duration, position)
        request.setHeader('content-length', len(body))
        request.write(body)
        request.finish()
        return 1 # NOT_DONE_YET

    def render_POST(self, request):
        print "[AirPlayer] ScrubHandler POST"
        """
        Immediately finish this request, no need for the client to wait for
        backend communication.
        """

        if 'position' in request.args:
            try:
                str_pos = request.args['position'][0]
                position = float(str_pos)
            except ValueError:
                print '[AirPlayer] Invalid scrub value supplied: ', str_pos
            else:       
                self._media_backend.set_player_position(position)
                
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

class RateHandler(BaseHandler):    
    """
    Handler for /rate requests.

    The rate command is used to play/pause media.
    A value argument should be supplied which indicates media should be played or paused.

    0.000000 => pause
    1.000000 => play
    """

    def render_POST(self, request):
        print "[AirPlayer] RateHandler POST"
        """
        Immediately finish this request, no need for the client to wait for
        backend communication.
        """

        if 'value' in request.args:
            play = bool(float(request.args['value'][0]))
            print "[AirPlayer] value ",request.args['value'][0]
            if play:
                self._media_backend.play()
            else:
                self._media_backend.pause()
        
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET    

class PhotoHandler(BaseHandler):   
    """
    Handler for /photo requests.

    RAW JPEG data is contained in the request body.
    """     

    #eigentlich put
    def render_PUT(self, request):
        print "[AirPlayer] PHOTOHandler POST"      
        """
        Immediately finish this request, no need for the client to wait for
        backend communication.
        """

        if request.content.read() is not None:
            request.content.seek(0)
            file(config.plugins.airplayer.path.value + "pic.jpg",'wb').write(request.content.read())      
            self._media_backend.show_picture(request.content.read())
        
        request.setHeader('content-length', 0)    
        request.finish()
        return 1 # NOT_DONE_YET

class AuthorizeHandler(BaseHandler):
    """
    Handler for /authorize requests.

    This is used to handle DRM authorization.
    We currently don't support DRM protected media.
    """

    def render_GET(self, request):
        print "[AirPlayer] AuthorizeHandler GET"
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

    def render_POST(self, request):
        print "[AirPlayer] AuthorizeHandler POST"
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

class StopHandler(BaseHandler):
    """
    Handler for /stop requests.

    Sent when media playback should be stopped.
    """

    def render_POST(self, request):
        print "[AirPlayer] StopHandler POST"
        self._media_backend.stop_playing()
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET
        
class ServerInfoHandler(BaseHandler):
    """
    Handler for /server-info requests.
    
    Usage currently unknown.
    Available from IOS 4.3.
    """        
    
    def render_GET(self, request):
        print "[AirPlayer] ServerInfoHandler GET"
        mac = iNetwork.getAdapterAttribute(config.plugins.airplayer.interface.value,'mac')
        if mac is None:
            mac = "01:02:03:04:05:06"
        mac=mac.upper()
        response = appletv.SERVER_INFO % (mac)
        request.setHeader('Content-Type', 'text/x-apple-plist+xml')
        request.setHeader('content-length', len(response))
        request.write(response)
        request.finish()
        return 1 # NOT_DONE_YET
        
class SlideshowFeaturesHandler(BaseHandler):
    """
    Handler for /slideshow-features requests.

    Usage currently unknown.
    Available from IOS 4.3.
    """        

    def render_GET(self, request):
        print "[AirPlayer] SlideshowHandler GET"
        """
        I think slideshow effects should be implemented by the Airplay device.
        The currently supported media backends do not support this.
        
        We'll just ignore this request, that'll enable the simple slideshow without effects.
        """
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET
        
class PlaybackInfoHandler(BaseHandler):
    """
    Handler for /playback-info requests.
    """
    
    def render_GET(self, request):
        print "[AirPlayer] PlaybackInfoHandler GET"
        playing = self._media_backend.is_playing()
        position, duration, bufferPosition = self._media_backend.get_player_position()
        
        if not position:
            position = duration = 0
        else:    
            position = float(position)
            duration = float(duration)
        print "[AirPlayer] PlaybackInfoHandler pos:",position, " duration:",duration," play:",int(playing)
        
        body = appletv.PLAYBACK_INFO % (duration, bufferPosition, position, int(playing), duration)
        
        request.setHeader('Content-Type', 'text/x-apple-plist+xml')
        request.setHeader('content-length', len(body))
        request.write(body)
        request.finish()
        return 1 # NOT_DONE_YET

class SetProterpyHandler(BaseHandler):

    def render_GET(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

    def render_POST(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET
    
class GetProterpyHandler(BaseHandler):

    def render_GET(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET

    def render_POST(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1 # NOT_DONE_YET