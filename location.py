import urllib
from xml.dom.minidom import parse

def get_woeid(location):
    f = open('conf.ini')
    lines = f.readlines()
    f.close()

    for line in lines:
        name,value = line.split('=')

        if name == 'yahoo_appid':
            url_location = urllib.quote(location)
            url = "http://where.yahooapis.com/v1/places.q('%s')?appid=%s" % (url_location, value)

            try:
                dom = parse(urllib.urlopen(url))
            except:
                return None

            woeid = dom.getElementsByTagName('woeid')[0]
            data = woeid.childNodes[0].data

            return data

if __name__ == '__main__':
    woeid = get_woeid('32571')
    print woeid

