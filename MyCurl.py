import socket  ##required
import argparse ##gets argument from command line
import sys  ##system calls
import re  ## parsing string

BUFF_SIZE = 4096
TIMEOUT_SIZE = 2

neededInfo = { #contains everything that i need in my log 
    'url':None,
    'sName':None,
    'sIp':None, 
    'sPort':None,
    'Path':None, 
    'cIp':None,
    'cPort':None,
    'msg':None,
    'html_msg':None
}

def parse_url(url):
    parsed = None
    parsed = re.search(r"(?P<http>https*)://?(?P<site>(\w+\.?)+)(?P<path>/(\w*.+?(?=:)|\w*.+))?:?(?P<port>[0-9]+)?", url)
    if(parsed == None):#http does not exist
        parsed = re.search(r"(?P<site>(\w+\.?)+)(?P<path>/(\w*.+?(?=:)|(\w*.+))?:?(?P<port>[0-9]+)?", url)
    else: #http exists
        if(parsed.group('http') == "https"):#do not support https. is it http or https\
            sys.exit("HTTPS is not supported.")
    
    if(parsed == None): #still parsed doesnt match pattern, exit
        sys.exit("Parsed argument errored.")

    check_host = re.findall("[a-z]+\.[a-zA-Z0-9_]+\.[a-z]+", url) 
    check_domain = re.findall("([a-zA-Z0-9]+\.[a-z]+)", url) 
    check_ip = re.findall("([0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3})", url)
    if (len(check_host) == 0 and len(check_domain) == 0 and len(check_ip) == 0):
        sys.exit("Could not resolve host: " + url)
    return parsed

def get_port(parsed):
    port = parsed.group('port')
    if( port == None):#port doesnt e
        neededInfo['sPort'] = 80
    else:#port not empty. ensure it is 80
        neededInfo['sPort'] = int(port)
    return (port == "443") # port is 433. give error later

def multi_input(parsed, cmd_input):
    parsedin = parsed.group("site")
    if(len(cmd_input) ==2):
        parse_url(cmd_input[1])#make sure its formatted
        if (re.match("[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}", parsedin)):
            neededInfo['sName'] = cmd_input[1]
            neededInfo['sIp'] = parsedin
        else: #determine whether received string is ip or host
            neededInfo['sName'] = parsedin
            neededInfo['sIp'] = cmd_input[1]
    else:
        neededInfo['sName'] = parsedin
        neededInfo['sIp'] = socket.gethostbyname(neededInfo['sName'])

def set_path(parsed):
    path = parsed.group("path")
    if(path == None):
        neededInfo['Path'] = "/"
    else:
        neededInfo['Path'] = path

def get_msg(sock):
    neededInfo['msg'] = ""
    try:
        while True:
            pack = sock.recv(1) #getting one byte
            if("\r\n\r" in neededInfo['msg'] or pack == None): #see \r\n\r signals the end of the header file
                break
            neededInfo['msg'] += pack.decode()
    except Exception, e:
        sock.close()
        f = open("Log.csv", "a")
        log = "{}, {}, {}, {}, {}, {}, {}, {}, {}\n\n".format("Unsuccessful", "404", url,
            neededInfo['sName'], str(neededInfo['cIp']), str(neededInfo['sIp']), str(neededInfo['cPort']), 
            str(neededInfo['sPort']), "HTTP/1.1 404 Not Found")
        f.write(log)
        f.close()
        sys.exit("Could not receieve information from message.")

def stuff():
    #description on program
    parser = argparse.ArgumentParser(description='Receiving HTTP request input through command')
    parser.add_argument('input', type=str, help='User input', nargs='+')
    cmd_input = parser.parse_args().input

    url = cmd_input[0] #get host url from cmd
    #print(sys.argv)
    #print(cmd_input)

    #check if given url is valid
    parsed = parse_url(url)

    #set port above and determine if port is 443
    port_true = get_port(parsed)

    # set sName and sIp
    multi_input(parsed, cmd_input)

    # setting path
    set_path(parsed)
    
    sock =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)  

    #start connection between source and and host 
    sock.connect((neededInfo['sIp'], neededInfo['sPort']))
    sock.settimeout(TIMEOUT_SIZE)
    neededInfo['cIp'], neededInfo['cPort'] = sock.getsockname() #gets cip and cport

    request = "GET {} HTTP/1.1\r\nHost:{}\r\n\r\n".format(neededInfo['Path'], neededInfo['sName'])
    sock.send(request.encode()) #changing request (type string) need to encode to a byte 
    
    #if the port is bad, we print to our Log file with the respective parameters
    if(port_true): #such as 443
        log = "Unsuccessful, 56, {}, {}, {}, {}, {}, {}, [Errno 54] Connection reset by peer\n\n".format(url,
        neededInfo['sName'], str(neededInfo['cIp']), str(neededInfo['sIp']), str(neededInfo['cPort']), 
        str(neededInfo['sPort']))
        f = open("Log.csv", "a")
        f.write(log)
        f.close()
        sys.exit("Port not supported")

    #get the msgs from recv
    get_msg(sock)

    neededInfo['html_msg'] = ""

    msg_true = re.search(r"Content-Length: (\d+)",neededInfo['msg']) #get content length
    
    if(msg_true != None): #get the rest of the message in html format if it exists
        #msg_true = int(msg_true.group(1))-len(neededInfo['msg'].encode()) 
        try:
            while True:
                pack = sock.recv(4096)
                if (len(pack) != 4096):
                    neededInfo['html_msg'] = neededInfo['html_msg']+ pack.decode()
                    break
                neededInfo['html_msg'] = neededInfo['html_msg']+ pack.decode()
        except Exception as e:
            sock.close()
            f = open("Log.csv", "a")
            log = "{}, {}, {}, {}, {}, {}, {}, {}, {}\n\n".format("Unsuccessful", "404", url,
                neededInfo['sName'], str(neededInfo['cIp']), str(neededInfo['sIp']), str(neededInfo['cPort']), 
                str(neededInfo['sPort']), "HTTP/1.1 404 Not Found")
            f.write(log)
            f.close()
            #print("Unsuccessful " + url + " HTTP/1.1 404 Not Found")
            sys.exit("Could not receieve information from message.")

    sock.close()

    http_status = re.search(r"(HTTP/.*)?", neededInfo['msg']).group(1)

    #print the html content into my httpoutput.html file
    f = open("HTTPoutput.html", "w")
    f.write(neededInfo['html_msg'])
    f.close()

    #print to my log file with respective parameters
    log = ""
    print_message = ""

    status_code = re.search(r"HTTP/\d{1}.?\d? (\d*)? \w+", http_status).group(1)

    if(status_code == '200'):
        run_status = "Successful"
    else:
        run_status = "Unsuccessful"

    term_out = run_status + " " + url + " " + http_status
    print(term_out)
    if "chunked" in neededInfo['msg']:
        print("ERROR: Chunk encoding is not supported")

    f = open("Log.csv", "a")
    #prints column names
    # columns = "Succesful or Unsuccesful, Requested URL, Hostname, source IP, destination IP, "
    # columns += "source port, destination port, Server Resposne line\n\n"
    # f.write(columns)

    log = "{}, {}, {}, {}, {}, {}, {}, {}, {}\n\n".format(run_status, status_code, url,
        neededInfo['sName'], str(neededInfo['cIp']), str(neededInfo['sIp']), str(neededInfo['cPort']), 
        str(neededInfo['sPort']), http_status)
    f.write(log)
    f.close()

if __name__ == '__main__':
    stuff()