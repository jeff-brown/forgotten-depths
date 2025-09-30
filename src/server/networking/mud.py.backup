#!/usr/bin/env python
"""
 File Name : mud.py

Basic MUD server module for creating text-based Multi-User Dungeon
(MUD) games.

Contains one class, MudServer, which can be instantiated to start a
server running then used to send and receive messages from players.

 Creation date : Thu Feb  3 20:43:03 PST 2022
 Last update : Thu Feb  3 20:43:03 PST 2022

 author: Mark Frimston - mfrimston@gmail.com
 Updated By : Jeff Brown <jeffbr@gmail.com>

"""
import logging
import socket
import time
import select
import sys
from logging.handlers import SysLogHandler

DEBUG = False

LOGFILE_FORMAT = logging.Formatter(
    '%(module)s: [%(levelname)s] %(message)s '
    '[%(pathname)s:%(funcName)s:%(lineno)d]'
)

LOGFILE_HANDLER = SysLogHandler(
    address='/var/run/syslog',
    facility='local1'
)
LOGFILE_HANDLER.setFormatter(LOGFILE_FORMAT)

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(LOGFILE_HANDLER)

if DEBUG:
    LOGGER.setLevel(logging.DEBUG)
else:
    LOGGER.setLevel(logging.INFO)


class Mud():
    """A basic server for text-based Multi-User Dungeon (MUD) games.

    Once created, the server will listen for players connecting using
    Telnet. Messages can then be sent to and from multiple connected
    players.

    The 'update' method should be called in a loop to keep the server
    running.
    """

    # An inner class which is instantiated for each connected client to store
    # info about them

    class _Client():
        """Holds information about a connected player"""

        # the socket object used to communicate with this client
        sock = None
        # the ip address of this client
        address = ""
        # holds data send from the client until a full message is received
        buffer = ""
        # the last time we checked if the client was still connected
        lastcheck = 0

        def __init__(self, sock, address, buffer, lastcheck):
            self.sock = sock
            self.address = address
            self.buffer = buffer
            self.lastcheck = lastcheck

    # Used to store different types of occurences
    _EVENT_NEW_PLAYER = 1
    _EVENT_PLAYER_LEFT = 2
    _EVENT_COMMAND = 3

    # Different states we can be in while reading data from client
    # See _process_sent_data function
    _READ_STATE_NORMAL = 1
    _READ_STATE_COMMAND = 2
    _READ_STATE_SUBNEG = 3

    # Command codes used by Telnet protocol
    # See _process_sent_data function
    _TN_INTERPRET_AS_COMMAND = 255
    _TN_ARE_YOU_THERE = 246
    _TN_WILL = 251
    _TN_WONT = 252
    _TN_DO = 253
    _TN_DONT = 254
    _TN_SUBNEGOTIATION_START = 250
    _TN_SUBNEGOTIATION_END = 240

    # socket used to listen for new clients
    _listen_socket = None
    # holds info on clients. Maps client id to _Client object
    _clients = {}
    # counter for assigning each client a new id
    _nextid = 0
    # list of occurences waiting to be handled by the code
    _events = []
    # list of newly-added occurences
    _new_events = []

    def __init__(self):
        """Constructs the MudServer object and starts listening for
        new players.
        """

        self._clients = {}
        self._nextid = 0
        self._events = []
        self._new_events = []

        # create a new tcp socket which will be used to listen for new clients
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # set a special option on the socket which allows the port to be
        # immediately without having to wait
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                                       1)

        # bind the socket to an ip address and port. Port 23 is the standard
        # telnet port which telnet clients will use, however on some platforms
        # this requires root permissions, so we use a higher arbitrary port
        # number instead: 1234. Address 0.0.0.0 means that we will bind to all
        # of the available network interfaces
        self._listen_socket.bind(("0.0.0.0", 1234))

        # set to non-blocking mode. This means that when we call 'accept', it
        # will return immediately without waiting for a connection
        self._listen_socket.setblocking(False)

        # start listening for connections on the socket
        self._listen_socket.listen(1)

    def update(self):
        """Checks for new players, disconnected players, and new
        messages sent from players. This method must be called before
        up-to-date info can be obtained from the 'get_new_players',
        'get_disconnected_players' and 'get_commands' methods.
        It should be called in a loop to keep the game running.
        """

        # check for new stuff
        self._check_for_new_connections()
        self._check_for_disconnected()
        self._check_for_messages()
        # self._move_monsters()

        # move the new events into the main events list so that they can be
        # obtained with 'get_new_players', 'get_disconnected_players' and
        # 'get_commands'. The previous events are discarded
        self._events = list(self._new_events)
        self._new_events = []

    def _check_for_new_connections(self):
        # print("_check_for_new_connections")
        # 'select' is used to check whether there is data waiting to be read
        # from the socket. We pass in 3 lists of sockets, the first being those
        # to check for readability. It returns 3 lists, the first being
        # the sockets that are readable. The last parameter is how long to wait
        # - we pass in 0 so that it returns immediately without waiting
        rlist, _, _ = select.select([self._listen_socket], [], [], 0)

        # if the socket wasn't in the readable list, there's no data available,
        # meaning no clients waiting to connect, and so we can exit the method
        # here
        if self._listen_socket not in rlist:
            return

        # 'accept' returns a new socket and address info which can be used to
        # communicate with the new client
        joined_socket, addr = self._listen_socket.accept()

        # set non-blocking mode on the new socket. This means that 'send' and
        # 'recv' will return immediately without waiting
        joined_socket.setblocking(False)

        # construct a new _Client object to hold info about the newly connected
        # client. Use 'nextid' as the new client's id number
        self._clients[self._nextid] = Mud._Client(joined_socket, addr[0],
                                                  "", time.time())

        # add a new player occurence to the new events list with the player's
        # id number
        self._new_events.append((self._EVENT_NEW_PLAYER, self._nextid))

        # add 1 to 'nextid' so that the next client to connect will get a
        # unique id number
        print("got new socket")
        self._nextid += 1

    def _check_for_disconnected(self):
        # go through all the clients
        for cid, clnt in list(self._clients.items()):

            # send the client an invisible character. It doesn't actually
            # matter what we send, we're really just checking that data can
            # still be written to the socket. If it can't, an error will be
            # raised and we'll know that the client has disconnected.
            self._attempt_send(cid, "\x00")

            # update the last check time
            clnt.lastcheck = time.time()

    def _check_for_messages(self):
        # print("_check_for_messages")
        # go through all the clients
        for pid, clnt in list(self._clients.items()):

            # we use 'select' to test whether there is data waiting to be read
            # from the client socket. The function takes 3 lists of sockets,
            # the first being those to test for readability. It returns 3 list
            # of sockets, the first being those that are actually readable.
            rlist, _, _ = select.select([clnt.sock], [], [], 0)

            # if the client socket wasn't in the readable list, there is no
            # new data from the client - we can skip it and move on to the next
            # one
            if clnt.sock not in rlist:
                continue

            try:
                # read data from the socket, using a max length of 4096
                data = clnt.sock.recv(4096).decode("latin1")

                # process the data, stripping out any special Telnet commands
                message = self._process_sent_data(clnt, data)

                # if there was a message in the data
                if message:
                    print("got message")
                    # remove any spaces, tabs etc from the start and end of
                    # the message
                    message = message.strip()

                    # separate the message into the command (the first word)
                    # and its parameters (the rest of the message)
                    command, params = (message.split(" ", 1) + ["", ""])[:2]

                    # add a command occurence to the new events list with the
                    # player's id number, the command and its parameters
                    self._new_events.append((self._EVENT_COMMAND, pid,
                                             command.lower(), params))

            # if there is a problem reading from the socket (e.g. the client
            # has disconnected) a socket error will be raised
            except socket.error:
                print("socket error in _check_for_messages")
                self._handle_disconnect(pid)

    def _attempt_send(self, clid, data):
        # python 2/3 compatability fix - convert non-unicode string to unicode
        if sys.version < '3' and not isinstance(data, str):
            data = str(data, "latin1")

        try:
            # look up the client in the client map and use 'sendall' to send
            # the message string on the socket. 'sendall' ensures that all of
            # the data is sent in one go
            self._clients[clid].sock.sendall(bytearray(data, "latin1"))
        # KeyError will be raised if there is no client with the given id in
        # the map
        except KeyError:
            pass
        # If there is a connection problem with the client (e.g. they have
        # disconnected) a socket error will be raised
        except socket.error:
            print("got disconnect")
            self._handle_disconnect(clid)

    def _handle_disconnect(self, clid):

        # remove the client from the clients map
        print("handle disconnect")
        del self._clients[clid]

        # add a 'player left' occurence to the new events list, with the
        # player's id number
        self._new_events.append((self._EVENT_PLAYER_LEFT, clid))

    def _process_sent_data(self, client, data):

        # the Telnet protocol allows special command codes to be inserted into
        # messages. For our very simple server we don't need to response to
        # any of these codes, but we must at least detect and skip over them
        # so that we don't interpret them as text data.
        # More info on the Telnet protocol can be found here:
        # http://pcmicro.com/netfoss/telnet.html

        # start with no message and in the normal state
        message = None
        state = self._READ_STATE_NORMAL

        # go through the data a character at a time
        for char in data:

            # handle the character differently depending on the state we're in:

            # normal state
            if state == self._READ_STATE_NORMAL:

                # if we received the special 'interpret as command' code,
                # switch to 'command' state so that we handle the next
                # character as a command code and not as regular text data
                if ord(char) == self._TN_INTERPRET_AS_COMMAND:
                    state = self._READ_STATE_COMMAND

                # if we get a newline character, this is the end of the
                # message. Set 'message' to the contents of the buffer and
                # clear the buffer
                elif char == "\n":
                    message = client.buffer
                    client.buffer = ""

                # some telnet clients send the characters as soon as the user
                # types them. So if we get a backspace character, this is where
                # the user has deleted a character and we should delete the
                # last character from the buffer.
                elif char == "\x08":
                    client.buffer = client.buffer[:-1]

                # otherwise it's just a regular character - add it to the
                # buffer where we're building up the received message
                else:
                    client.buffer += char

            # command state
            elif state == self._READ_STATE_COMMAND:

                # the special 'start of subnegotiation' command code indicates
                # that the following characters are a list of options until
                # we're told otherwise. We switch into 'subnegotiation' state
                # to handle this
                if ord(char) == self._TN_SUBNEGOTIATION_START:
                    state = self._READ_STATE_SUBNEG

                # if the command code is one of the 'will', 'wont', 'do' or
                # 'dont' commands, the following character will be an option
                # code so we must remain in the 'command' state
                elif ord(char) in (self._TN_WILL, self._TN_WONT, self._TN_DO,
                                   self._TN_DONT):
                    state = self._READ_STATE_COMMAND

                # for all other command codes, there is no accompanying data so
                # we can return to 'normal' state.
                else:
                    state = self._READ_STATE_NORMAL

            # subnegotiation state
            elif state == self._READ_STATE_SUBNEG:

                # if we reach an 'end of subnegotiation' command, this ends the
                # list of options and we can return to 'normal' state.
                # Otherwise we must remain in this state
                if ord(char) == self._TN_SUBNEGOTIATION_END:
                    state = self._READ_STATE_NORMAL

        # return the contents of 'message' which is either a string or None
        return message

    def get_new_players(self):
        """Returns a list containing info on any new players that have
        entered the game since the last call to 'update'. Each item in
        the list is a player id number.
        """
        retval = []
        # go through all the events in the main list
        # print("get_new_players events: {}".format(self._events))
        for event in self._events:
            # if the event is a new player occurence, add the info to the list
            if event[0] == self._EVENT_NEW_PLAYER:
                retval.append(event[1])
        # return the info list
        return retval

    def get_disconnected_players(self):
        """Returns a list containing info on any players that have left
        the game since the last call to 'update'. Each item in the list
        is a player id number.
        """
        retval = []
        # go through all the events in the main list
        for event in self._events:
            # if the event is a player disconnect occurence, add the info to
            # the list
            if event[0] == self._EVENT_PLAYER_LEFT:
                retval.append(event[1])
        # return the info list
        return retval

    def get_commands(self):
        """Returns a list containing any commands sent from players
        since the last call to 'update'. Each item in the list is a
        3-tuple containing the id number of the sending player, a
        string containing the command (i.e. the first word of what
        they typed), and another string containing the text after the
        command
        """
        retval = []
        # go through all the events in the main list
        # print(self._events)
        for event in self._events:
            # if the event is a command occurence, add the info to the list
            if event[0] == self._EVENT_COMMAND:
                retval.append((event[1], event[2], event[3]))
        # return the info list
        return retval

    def send_message(self, to_player, message):
        """Sends the text in the 'message' parameter to the player with
        the id number given in the 'to' parameter. The text will be
        printed out in the player's terminal.
        """
        # we make sure to put a newline on the end so the client receives the
        # message on its own line
        self._attempt_send(to_player, message+"\n\r")

    def get_disconnect(self, clid):
        """non-protected method for gracefully allowing a player to disconnect
        """
        self._handle_disconnect(clid)

    def shutdown(self):
        """Closes down the server, disconnecting all clients and
        closing the listen socket.
        """
        # for each client
        for clnt in self._clients.values():
            # close the socket, disconnecting the client
            clnt.sock.shutdown(socket.SHUT_RDWR)
            clnt.sock.close()
        # stop listening for new clients
        self._listen_socket.close()
