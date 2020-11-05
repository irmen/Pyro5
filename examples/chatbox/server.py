from Pyro5.api import expose, behavior, serve
import Pyro5.errors


# Chat box administration server.
# Handles logins, logouts, channels and nicknames, and the chatting.
@expose
@behavior(instance_mode="single")
class ChatBox(object):
    def __init__(self):
        """
        Initialize the channel.

        Args:
            self: (todo): write your description
        """
        self.channels = {}  # registered channels { channel --> (nick, client callback) list }
        self.nicks = []  # all registered nicks on this server

    def getChannels(self):
        """
        Return a list of channels.

        Args:
            self: (todo): write your description
        """
        return list(self.channels.keys())

    def getNicks(self):
        """
        Return the number of ticks.

        Args:
            self: (todo): write your description
        """
        return self.nicks

    def join(self, channel, nick, callback):
        """
        Join a channel.

        Args:
            self: (todo): write your description
            channel: (int): write your description
            nick: (todo): write your description
            callback: (callable): write your description
        """
        if not channel or not nick:
            raise ValueError("invalid channel or nick name")
        if nick in self.nicks:
            raise ValueError('this nick is already in use')
        if channel not in self.channels:
            print('CREATING NEW CHANNEL %s' % channel)
            self.channels[channel] = []
        self.channels[channel].append((nick, callback))
        self.nicks.append(nick)
        print("%s JOINED %s" % (nick, channel))
        self.publish(channel, 'SERVER', '** ' + nick + ' joined **')
        return [nick for (nick, c) in self.channels[channel]]  # return all nicks in this channel

    def leave(self, channel, nick):
        """
        Leave a channel.

        Args:
            self: (todo): write your description
            channel: (int): write your description
            nick: (todo): write your description
        """
        if channel not in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n, c) in self.channels[channel]:
            if n == nick:
                self.channels[channel].remove((n, c))
                break
        self.publish(channel, 'SERVER', '** ' + nick + ' left **')
        if len(self.channels[channel]) < 1:
            del self.channels[channel]
            print('REMOVED CHANNEL %s' % channel)
        self.nicks.remove(nick)
        print("%s LEFT %s" % (nick, channel))

    def publish(self, channel, nick, msg):
        """
        Publish a message.

        Args:
            self: (todo): write your description
            channel: (todo): write your description
            nick: (str): write your description
            msg: (str): write your description
        """
        if channel not in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n, c) in self.channels[channel][:]:  # use a copy of the list
            c._pyroClaimOwnership()
            try:
                c.message(nick, msg)  # oneway call
            except Pyro5.errors.ConnectionClosedError:
                # connection dropped, remove the listener if it's still there
                # check for existence because other thread may have killed it already
                if (n, c) in self.channels[channel]:
                    self.channels[channel].remove((n, c))
                    print('Removed dead listener %s %s' % (n, c))


serve({
    ChatBox: "example.chatbox.server"
})
