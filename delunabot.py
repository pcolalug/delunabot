#!/usr/bin/env python
"""
The IRC bot for #pensacola_linux on irc.freenode.net
"""


# twisted imports
from twisted.words.protocols import irc

from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
import re

class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message))
        self.file.flush()

    def close(self):
        self.file.close()


class DelunaBot(irc.IRCClient):
    """ The DelunaBot """
    messages = {}

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" % 
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.logger.close()


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        
        # Check to see if they're sending me a private message
        if channel == self.factory.nickname:
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return
        # Otherwise check to see if it is a message directed at me
        else:
            command = msg.lower().strip()
            if command == 'ping':
                self.pong(channel, user)
            elif command == '.fortune':
                self.fortune(channel, user)
            elif command == '.nextmeeting':
                self.nextmeeting(channel, user)
            elif command == '.mailinglist':
                self.mailinglist(channel, user)
            elif command == '.website':
                self.website(channel, user)
            elif command.startswith('.weather'):
                self.weather(channel, user, command)
            elif command == '.help':
                self.help(channel, user)
            else:
                self.check_for_search_replace(channel, user, msg)

        self.messages[user] = msg


    def check_for_search_replace(self, channel, user, msg):
        if user in self.messages.keys():
            last_message = self.messages[user]

            match = re.match('^s\/(.+)\/(.+)\/$', msg, flags=re.DOTALL | re.MULTILINE)

            if match:
                to_replace = match.group(1)
                if to_replace in last_message:
                    msg = last_message.replace(to_replace, match.group(2))

                    self.msg(channel, '%s meant: %s'  % (user, msg))

    def weather(self, channel, user, command):
        from weather import get_weather

        class WeatherOptions(object):
            def __init__(self, metric=False, forecast=1):
                self.metric = metric
                self.forecast = forecast
        try:
            postal_code = command.split('.weather')[1].strip()
            results = get_weather(postal_code, WeatherOptions())

            msg = 'It is %(current_condition)s in %(city)s with a high of %(high)s and low of %(low)s, the current temperature is %(current_temp)s %(units)s' % dict(
                current_condition=str(results['current_condition']).lower(),
                city=str(results['city']),
                current_temp=str(results['current_temp']),
                units=str(results['units']),
                high=str(results['forecasts'][0]['high']),
                low=str(results['forecasts'][0]['low']),
            )
        except:
            msg = 'Please provide a valid postal code'

        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))


    def website(self, channel, user):
        msg = "%s: http://pcolalug.com" % user
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def help(self, channel, user):
        msg = "%s: .website, .fortune, .nextmeeting, .mailinglist, .weather <postal code>" % user
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def pong(self, channel, user):
        msg = "%s: pong!" % user
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def mailinglist(self, channel, user):
        msg = "%s: http://groups.google.com/group/pcolalug" % user
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def nextmeeting(self, channel, user):
        import urllib
        from icalendar import Calendar
        from dateutil import tz
        import datetime
        DATE_FORMAT = "%B %d, %Y @ %-I:%M %p"
        DATE_FORMAT_NO_TIME = "%B %d, %Y @ All Day"

        ics = urllib.urlopen("https://www.google.com/calendar/ical/pcolalug%40gmail.com/public/basic.ics").read()
        events = []

        cal = Calendar.from_ical(ics)

        for event in cal.walk('vevent'):
            to_zone = tz.gettz('America/Chicago')

            date = event.get('dtstart').dt
            format = DATE_FORMAT
            if hasattr(date, 'astimezone'):
                date = event.get('dtstart').dt.astimezone(to_zone)
            else:
                format = DATE_FORMAT_NO_TIME

            description = event.get('description', '')
            summary = event.get('summary', '')
            location = event.get('location', '')
            if not location:
                location = 'TBA'

            events.append({
                        'real_date': date,
                        'start': date.strftime(format),
                        'description': description if description else 'No Description',
                        'summary': summary,
                        'location': location
                        })

        sorted_list = sorted(events, key=lambda k: k['real_date'], reverse=True)
        next_meeting = None
        for x in sorted_list:
            if x['real_date'].date() >= datetime.date.today():
                next_meeting = x
        if next_meeting:
            msg = "%(user)s: Next Meeting is: %(topic)s on %(start)s: %(description)s, meeting at: %(location)s" % { 
                    'user': user,
                    'topic': str(next_meeting['summary']),
                    'start': str(next_meeting['start']),
                    'description': str(next_meeting['description'].title()),
                    'location': str(next_meeting['location'].title()),
            }
        else:
            msg = "Meetings are held the 3rd Tuesday of each month at Ozone's at 7pm."
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def fortune(self, channel, user):
        from random import choice

        f = open('linux')
        data = f.readlines()
        f.close()

        fortunes = []

        fortune = ''

        for line in data:
            if line.strip() == "%":
                fortunes.append(fortune)
                fortune = ''
            else:
                fortune += line

        fortune = choice(fortunes)

        msg = "%s: %s" % (user, fortune)
        self.msg(channel, msg)
        self.logger.log("<%s> %s" % (self.factory.nickname, msg))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'



class LogBotFactory(protocol.ClientFactory):
    """A factory for DelunaBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, filename, nickname):
        self.channel = channel
        self.filename = filename
        self.nickname = nickname

    def buildProtocol(self, addr):
        p = DelunaBot()
        p.nickname = self.nickname
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)
    
    # create factory protocol and application
    nickname = 'DelunaBot'

    if len(sys.argv) == 4:
        nickname = sys.argv[3]

    f = LogBotFactory(sys.argv[1], sys.argv[2], nickname)

    # connect factory to this host and port
    reactor.connectTCP("irc.freenode.net", 6667, f)

    # run bot
    reactor.run()
