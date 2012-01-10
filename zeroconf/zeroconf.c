/*
 * zeroconf.c
 *
 *  Created on: 08.10.2011
 *      Author: matthias
 */
#include <stdio.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <signal.h>
#include <stdio.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/time.h>
#include <stdlib.h>
#include <memory.h>
#include <string.h>
#include <sys/ioctl.h>
#include <net/if.h>

void sendPacket(int s,unsigned char* msg, int len){
        struct sockaddr_in sin;
        sin.sin_family = AF_INET;
        sin.sin_port = htons(5353); // htons for network byte order
        sin.sin_addr.s_addr = inet_addr("224.0.0.251");
        int i=sendto(s, msg, len, 0, (struct sockaddr *)&sin, sizeof(sin));
        //printf("sending %d bytes %d - %s %d\n",len,i,strerror(errno),s);
}

int createSocket(char* ip){
		printf("createSocket ->\n");
        struct sockaddr_in sin;
        int s;
        s = socket(AF_INET, SOCK_DGRAM, 0);
        if(s < 0){
        	perror("create socket failed\n");
        }
        int on = 1;
        setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));

        sin.sin_family = AF_INET;
        sin.sin_port = htons(5353);
        sin.sin_addr.s_addr = inet_addr(ip);
        if(bind(s, (struct sockaddr *)&sin, sizeof(sin))<0){
        	perror("bind failed\n");
        }

        unsigned char msg[512];
        int sin_length;
        sin_length = sizeof(sin);
        printf("createSocket <-\n");
        return s;

}

int createRequestPacket(unsigned char* msg, char* name, unsigned short port, char* host, char* mac){
	printf("createRequestPacket ->\n");
	unsigned char head[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00};
	
	memset(msg, 0, 512);
	int i=0;
	memcpy(msg,head,sizeof(head));
	i+=sizeof(head);
	i+=writeString(msg + i, name);
	i+=writeString(msg + i, "_airplay");
	i+=writeString(msg + i, "_tcp");
	i+=writeString(msg + i, "local");
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0xff;
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0xc0;
	msg[i++] = 0x0c;
	msg[i++] = 0x00;
	msg[i++] = 0x21;
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x78;
	msg[i++] = 0x00;
	msg[i++] = strlen(host)+9;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = port>>8 & 0xff;
	msg[i++] = port & 0xff;
	i+=writeString(msg + i, host);
	msg[i++] = 0xc0;
	msg[i++] = 27+strlen(name);

	msg[i++] = 0xc0;
	msg[i++] = 0x0c;
	msg[i++] = 0x00;
	msg[i++] = 0x10;
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x11;
	msg[i++] = 0x94;
	msg[i++] = 0x00;
	msg[i++] = 0x49;
	i+=writeString(msg + i, "model=AppleTV2,1");
	i+=writeString(msg + i, "srcvers=101.10");
	char macstr[32];
	sprintf (macstr, "deviceid=%s", mac);
	i+=writeString(msg + i, macstr);
	i+=writeString(msg + i, "features=0x77");
	printf("createRequestPacket <-\n");
	return i;
}

int createResponsePacket(unsigned char* msg, char* name, unsigned short port, char* host,char* ipaddr, char* mac){
	printf("createResponsePacket ->\n");
	unsigned char head[] = {0x00, 0x00, 0x84, 0x00, 0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00};

	memset(msg, 0, 512);
	int i=0;
	memcpy(msg,head,sizeof(head));
	i+=sizeof(head);
	i+=writeString(msg + i, name);
	i+=writeString(msg + i, "_airplay");
	i+=writeString(msg + i, "_tcp");
	i+=writeString(msg + i, "local");
	msg[i++] = 0x00; //00 00 10 80 01 00 00 11 94 #zeugs
	msg[i++] = 0x00;
	msg[i++] = 0x10;
	msg[i++] = 0x80;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x11;
	msg[i++] = 0x94;

	msg[i++] = 0x00;
	msg[i++] = 0x49;
	i+=writeString(msg + i, "model=AppleTV2,1");
	i+=writeString(msg + i, "srcvers=101.10");
	char macstr[32];
	sprintf (macstr, "deviceid=%s", mac);
	i+=writeString(msg + i, macstr);
	i+=writeString(msg + i, "features=0x77");
	msg[i++] = 0xc0;
	msg[i++] = 13 + strlen(name);

	//00 0c 00 01 00 00 11 94 00 02 c0 0c c0 0c 00 21
	//  80 01 00 00 00 78
	msg[i++] = 0x00;
	msg[i++] = 0x0c;
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x11;
	msg[i++] = 0x94;
	msg[i++] = 0x00;
	msg[i++] = 0x02;
	msg[i++] = 0xc0;
	msg[i++] = 0x0c;
	msg[i++] = 0xc0;
	msg[i++] = 0x0c;
	msg[i++] = 0x00;
	msg[i++] = 0x21;
	msg[i++] = 0x80;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x78;

	msg[i++] = 0x00;
	msg[i++] = 9 + strlen(host);
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;

	msg[i++] = port>>8 & 0xff;
	msg[i++] = port & 0xff;
	i+=writeString(msg + i, host);

	msg[i++] = 0xc0;
	msg[i++] = 27+strlen(name);

	msg[i++] = 0xc0;
	msg[i++] = 149+strlen(name);
	//00 01 80 01 00 00 00 78 00 04
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0x80;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x78;
	msg[i++] = 0x00;
	msg[i++] = 0x04;

	//c0 a8 00 67 #ipaddr
	int ip=inet_addr(ipaddr);

	msg[i++] = ip &0xff;
	msg[i++] = ip>>8 &0xff;
	msg[i++] = ip>>16 &0xff;
	msg[i++] = ip>>24 &0xff;

	i+=writeString(msg + i, "_services");
	i+=writeString(msg + i, "_dns-sd");
	i+=writeString(msg + i, "_udp");

	msg[i++] = 0xc0;
	msg[i++] = 27+strlen(name);

	//00 0c 00 01 00 00 11 94 00 02
	msg[i++] = 0x00;
	msg[i++] = 0x0c;
	msg[i++] = 0x00;
	msg[i++] = 0x01;
	msg[i++] = 0x00;
	msg[i++] = 0x00;
	msg[i++] = 0x11;
	msg[i++] = 0x94;
	msg[i++] = 0x00;
	msg[i++] = 0x02;

	msg[i++] = 0xc0;
	msg[i++] = 13+strlen(name);

	printf("createResponsePacket <-\n");
	return i;
}

int writeString(unsigned char* msg, unsigned char* str){
	msg[0]=(unsigned char)strlen(str);
	memcpy(msg+1,str,strlen(str));
	return strlen(str)+1;
}

char* getIP(const char *interface)
{
	struct ifreq ifr;
	struct sockaddr_in *addr_ptr;
	int sock_fd;

	if((sock_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0)
		return -1;

	memset(&ifr, 0, sizeof(ifr));
	strcpy(ifr.ifr_name, interface);
	if(ioctl(sock_fd, SIOCGIFADDR, &ifr) == 0)
	{
		addr_ptr = (struct sockaddr_in *) &ifr.ifr_addr;
		addr_ptr->sin_family = AF_INET;

		return inet_ntoa(addr_ptr->sin_addr);
	}

	return NULL;
}

char * hwaddr (char * s)
{
  static char buf[30];
  sprintf (buf, "%02X:%02X:%02X:%02X:%02X:%02X", s[0]&0xff, s[1]&0xff, s[2]&0xff, s[3]&0xff, s[4]&0xff, s[5]&0xff);
  return buf;
}

char* getMAC(const char *interface)
{
	struct ifreq ifr;
	struct sockaddr_in *addr_ptr;
	char myMAC[6];
	int sock_fd;

	if((sock_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0)
		return -1;

	memset(&ifr, 0, sizeof(ifr));
	strcpy(ifr.ifr_name, interface);
	if(ioctl(sock_fd, SIOCGIFHWADDR, &ifr) == 0)
	{
		memcpy (myMAC, ifr.ifr_hwaddr.sa_data, 6);
  		return hwaddr (myMAC);
	}

	return NULL;
}

int main (int argc,char* argv[]){
	unsigned char request[512];
	unsigned char response[512];
	unsigned short port = 6002;
	char default_name[]="duck";
	char default_device[]="eth0";
	char* name = NULL;
	char* device = NULL;
	if(argc > 1){
		name=argv[1];
	}else{
		name=default_name;
	}
	if(argc > 2){
			device=argv[2];
	}else{
			device=default_device;
	}

	char* ip=getIP(device);
	char* mac=getMAC(device);

	char host[128];
	gethostname(host,128);

	printf("Setting up airplay service %s for host %s IP: %s Mac: %s Device: %s\n",name,host,ip,mac,device);

	int s = createSocket(ip);
	int len_request = createRequestPacket(request,name,port,host,mac);

	int len_response = createResponsePacket(response,name,port,host,ip,mac);

	do{
		sendPacket(s,request,len_request);
		usleep(20000);
		sendPacket(s,response,len_response);
		sleep(15);
	}while(1);
}
