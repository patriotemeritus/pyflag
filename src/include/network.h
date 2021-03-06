/******************************************************
# Copyright 2004: Commonwealth of Australia.
#
# Developed by the Computer Network Vulnerability Team,
# Information Security Group.
# Department of Defence.
#
# Michael Cohen <scudette@users.sourceforge.net>
#
# ******************************************************
#  Version: FLAG  $Version: 0.87-pre1 Date: Thu Jun 12 00:48:38 EST 2008$
# ******************************************************
#
# * This program is free software; you can redistribute it and/or
# * modify it under the terms of the GNU General Public License
# * as published by the Free Software Foundation; either version 2
# * of the License, or (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ******************************************************/
/*********************************************************************
    This file defines a number of classes for parsing network packets
    of various types.
**********************************************************************/
#ifndef __NETWORK_H
#define __NETWORK_H

#include "packet.h"
#include "misc.h"

/************************************************
    Needed packers and unpackers
*************************************************/

#define STRUCT_ETH_ADDR 0x0a
#define FORMAT_ETH_ADDR "\x0a"

/***********************************************
    The Root node.

    The Root node has placeholders for all types of possible link
    layers. This allows us to access the link layers by name like
    eth.src for example.
*************************************************/
struct root_node_struct {
  Packet eth;
  unsigned int link_type;
  unsigned int packet_id;
} __attribute__((packed));

CLASS(Root, Packet)
     struct root_node_struct packet;
END_CLASS
/***********************************************
    Linux Cooked capture (The Any device)
*************************************************/
struct cooked_struct {
  uint16_t packet_type;
  uint16_t link_layer_addr_type;
  uint16_t link_layer_addr_len;
  char link_layer_header[8];
  uint16_t type;
  Packet payload;
} __attribute__((packed));

#define cooked_Format q(STRUCT_SHORT, STRUCT_SHORT, STRUCT_SHORT, \
			STRUCT_ETH_ADDR, STRUCT_CHAR, STRUCT_CHAR, \
			STRUCT_SHORT)

CLASS(Cooked, Packet)
     struct cooked_struct packet;
END_CLASS

/***********************************************
     PPPOE headers
*************************************************/
struct pppoe_struct {
  char version;
  char session_data;
  uint16_t session_id;
  uint16_t payload_length;
  uint16_t protocol;
  Packet payload;
} __attribute__((packed));

#define pppoe_Format q(STRUCT_CHAR, STRUCT_CHAR, STRUCT_SHORT, STRUCT_SHORT, \
		       STRUCT_SHORT);

CLASS(PPPOE, Packet)
     struct pppoe_struct packet;
END_CLASS

/***********************************************
    Ethernet headers
*************************************************/
struct ethernet_2_struct {
  unsigned char destination[6];
  unsigned char source[6];
  uint16_t type;
  Packet payload;
}  __attribute__((packed));

#define ethernet_2_Format q(STRUCT_ETH_ADDR, STRUCT_ETH_ADDR, STRUCT_SHORT);

CLASS(ETH_II, Packet)
     struct ethernet_2_struct packet;
END_CLASS

/***********************************************
    Wireless IEEE 802.11 headers
*************************************************/
struct ieee_802_11_struct {
  uint16_t frame_control;
  uint16_t duration;
  unsigned char bss[6];
  unsigned char source[6];
  unsigned char dest[6];
  uint16_t seq;
  
  // Thats the LLC which we just treat the same atm:
  unsigned char dsap;
  unsigned char ssap;
  unsigned char llc_control;
  unsigned char org_code[3];
  uint16_t type;

  Packet payload;
} __attribute__((packed));

#define ieee_802_11_format FORMAT_SHORT FORMAT_SHORT FORMAT_ETH_ADDR \
  FORMAT_ETH_ADDR FORMAT_ETH_ADDR FORMAT_SHORT			     \
  FORMAT_CHAR FORMAT_CHAR FORMAT_CHAR FORMAT_CHAR FORMAT_CHAR	     \
  FORMAT_CHAR FORMAT_SHORT

CLASS(IEEE80211, Packet)
     struct ieee_802_11_struct packet;
END_CLASS
/***********************************************
    IP headers
*************************************************/
// This is a slightly modified standard header from 
struct iphdr
  {
#if __BYTE_ORDER == __LITTLE_ENDIAN
    uint32_t ihl:4;
    uint32_t version:4;
#elif __BYTE_ORDER == __BIG_ENDIAN
    uint32_t version:4;
    uint32_t ihl:4;
#else
# error	"Please fix <bits/endian.h>"
#endif
    u_int8_t tos;
    u_int16_t tot_len;
    u_int16_t id;
    u_int16_t frag_off;
    u_int8_t ttl;
    u_int8_t protocol;
    u_int16_t check;
    u_int32_t saddr;
    u_int32_t daddr;
    /*The options start here. */
  } __attribute__((packed));

struct ip_struct {
  struct iphdr header;

  /******* Everything after here will be manually filled in ****/
  uint32_t _src;
  uint32_t _dest;  

  Packet payload;

  /** The offset in the pcap file where this packet starts */
  uint32_t packet_offset;
};

#define ip_Format q(STRUCT_CHAR, STRUCT_CHAR, STRUCT_SHORT, STRUCT_SHORT, \
		    STRUCT_SHORT, STRUCT_CHAR, STRUCT_CHAR, STRUCT_SHORT, \
		    STRUCT_INT, STRUCT_INT)

CLASS(IP, Packet)
/** Each IP Packet has a unique number */
     unsigned int id;
     // This contains the packet offset from the pcap file - it just
     // gets provided to the callback
     uint64_t pcap_offset;
     struct ip_struct packet;
END_CLASS

/***********************************************
    TCP headers
*************************************************/
struct packed_tcphdr
{
  u_int16_t source;
  u_int16_t dest;
  u_int32_t seq;
  u_int32_t ack_seq;
#  if __BYTE_ORDER == __LITTLE_ENDIAN
  u_int16_t res1:4,
   doff:4,
   fin:1,
   syn:1,
   rst:1,
   psh:1,
   ack:1,
   urg:1,
   res2:2;
#  elif __BYTE_ORDER == __BIG_ENDIAN
  u_int16_t doff:4,
   res1:4,
   res2:2,
   urg:1,
   ack:1,
   psh:1,
   rst:1,
   syn:1,
   fin:1;
#  else
#   error "Adjust your <bits/endian.h> defines"
#  endif
  u_int16_t window;
  u_int16_t check;
  u_int16_t urg_ptr;
} __attribute__((packed));

struct tcp_struct {
  struct packed_tcphdr header;

  /** Private derived data */
  unsigned int len;

  /* The offset in the packet where the data portion starts */
  unsigned int data_offset;

  /** The payload data portion */
  int data_len;
  char *data;

  unsigned int tsval;
  unsigned int options_len;
  char *options;
  unsigned int tsecr;

} __attribute__((packed));

#define tcp_Format q(STRUCT_SHORT, STRUCT_SHORT, STRUCT_INT, STRUCT_INT, \
		     STRUCT_CHAR, STRUCT_CHAR, STRUCT_SHORT, STRUCT_SHORT, STRUCT_SHORT)

CLASS(TCP, Packet)
     struct tcp_struct packet;
END_CLASS

/***********************************************
    UDP headers
*************************************************/
struct udp_struct {
  uint16_t src_port;
  uint16_t dest_port;
  uint16_t length;
  uint16_t checksum;

  // This is a psuedo sequence number we may use to treat a UDP stream
  // as a stream.
  uint32_t seq;

  int data_len;
  char *data;
};

#define udp_Format q(STRUCT_SHORT, STRUCT_SHORT,	\
		     STRUCT_SHORT, STRUCT_SHORT)

CLASS(UDP, Packet)
     struct udp_struct packet;
END_CLASS

/** This must be called to initialise the network structs */
void network_structs_init(void);

#define MAX_PACKET_SIZE 64*1024

#endif
