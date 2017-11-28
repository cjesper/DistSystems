# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: 2
# Student names: Jesper Carlsson & Erik Forsstrom 
#------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler # Socket specifically designed to handle HTTP requests
import sys # Retrieve arguments
import time
import ast
import random
import threading
import collections
from urlparse import parse_qs # Parse POST data
from httplib import HTTPConnection # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode # Encode POST content into the HTTP header
from codecs import open # Open a file
from threading import  Thread # Thread Management

#------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
board_frontpage_footer_template = ""
board_frontpage_header_template = ""
boardcontents_template = ""
entry_template = ""

#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 80
#------------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
#------------------------------------------------------------------------------------------------------

    def __init__(self, server_address, handler, node_id, vessel_list):
        # We call the super init
	HTTPServer.__init__(self,server_address, handler)
	# we create the dictionary of values
        self.store = {}#{1 : "First message"}
	self.vessel_id = vessel_id
        #Backing store used for eventual consistency
        self.backEndStore = []#{(1, vessel_id) : "First message"}
        #Links keys in frontend to backend (frontkey, backkey)
        self.frontKeyToBackKey = []
	# We keep a variable of the next id to insert
	self.current_key = 1
        self.sequence_number = 1
	# The list of other vessels
	self.vessels = vessel_list
        self.deleteQueue = []
        #Leader Election Info
        self.timesFailed = 0 #Used to determine which neighbor we should try to contact next
        self.initialize_delayed_update()

#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
    def add_value_to_store(self, value):
        self.store[self.current_key] = value
        self.current_key = self.current_key + 1
#------------------------------------------------------------------------------------------------------
    def add_value_to_backend_store(self, key, value):
        self.backEndStore.append((key,value))
        
    #Check if a value exists in store - used for delete and modify
    def is_in_store(self, key):
        return key in self.store

    def is_in_backend_store(self, key):
        for val in self.backEndStore:
            if str(val[0]) == str(key):
                return True
        
        return False

	# We modify a value received in the store
    def modify_value_in_store(self,key,value):
        # we modify a value in the store if it exists
        if self.is_in_store:
            self.store[key] = value
#------------------------------------------------------------------------------------------------------
	# We delete a value received from the store
    def delete_value_in_store(self,key):
        # we delete a value in the store if it exists
        if self.is_in_store(key):
            del self.store[key]

    def delete_value_in_backendStore(self,key):
        # we delete a value in the store if it exists
        print "Trying to delete " + str(key)
        for val in self.backEndStore:
            print val
            if str(val[0]) == str(key):
                print "found! " + str(val[0])
                toDel = self.backEndStore.index(val)
                del self.backEndStore[toDel]

    #Sort the backend store, first on sequence number then on vessel id
    def sort_backend_store(self):
        sortedList = sorted(self.backEndStore, key=lambda x: x[0])
        print sortedList 
        self.reorder_frontend_list(sortedList)
        self.frontKeyToBackKey = []
        key = 1
        for value in sortedList:
            self.frontKeyToBackKey.append((key , value[0]))
            key += 1
        print "Front to back: "
        print self.frontKeyToBackKey

    #Construct frontend-list
    def reorder_frontend_list(self, sortedList):
        tempDict = {}
        key = 1
        for value in sortedList:
            tempDict[key] = value[1] 
            key += 1
        self.store.clear()
        self.store = tempDict
        print self.store

    #Find corresponding backend key from frontend
    def convert_frontend_to_backend_key (self, key):
        print ("From key " + str(key)  + " i found:")
        for value in self.frontKeyToBackKey:
            if value[0] == key:
                print "Frontkey " + str(key) + " had back " + str(value[1])
                return value[1] 

    def initialize_delayed_update(self):
        thread = Thread(target=self.delayedUpdate)
        thread.daemon = True
        thread.start()

    def delayedUpdate (self):
        time.sleep(10);
        self.sort_backend_store()
        for element in self.deleteQueue:
            self.delete_value_in_backendStore(element)
            print "Deleted " + str(element)
        self.deleteQueue = []
        thread = Thread(target=self.delayedUpdate)
        thread.daemon = True
        thread.start()

           
#------------------------------------------------------------------------------------------------------
# Contact a specific vessel with a set of variables to transmit to it
    def contact_vessel(self, vessel_ip, path, action, key, value):
        # the Boolean variable we will return
        success = False
        print "Contacting vessel " + vessel_ip
        # The variables must be encoded in the URL format, through urllib.urlencode
        post_content = urlencode({'action': action, 'key': key, 'value': value})
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        # We should try to catch errors when contacting the vessel
        try:
            # We contact vessel:PORT_NUMBER since we all use the same port

            # We can set a timeout, after which the connection fails if nothing happened
                connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 25)
                # We only use POST to send data (PUT and DELETE not supported)
                action_type = "POST"
                # We send the HTTP request
                connection.request(action_type, path, post_content, headers)
                # We retrieve the response
                response = connection.getresponse()
                # We want to check the status, the body should be empty
                status = response.status
                # If we receive a HTTP 200 - OK
                if status == 200:
                    success = True
        # We catch every possible exceptions
        except Exception as e:
            print "Error while contacting %s" % vessel_ip
            # printing the error given by Python
            print(e)

            return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
    def propagate_value_to_vessels(self, path, action, key, value):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                self.contact_vessel(vessel, path, action, key, value)		
#------------------------------------------------------------------------------------------------------


#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
#------------------------------------------------------------------------------------------------------
	# We fill the HTTP headers
    def set_HTTP_headers(self, status_code = 200):
         # We set the response status code (200 if OK, something else otherwise)
        self.send_response(status_code)
        # We set the content type to HTML
        self.send_header("Content-type","text/html")
        # No more important headers, we can close them
        self.end_headers()
#------------------------------------------------------------------------------------------------------
	# a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
    def parse_POST_request(self):
        post_data = ""
        # We need to parse the response, so we must know the length of the content
        length = int(self.headers['Content-Length'])
        # we can now parse the content using parse_qs
        post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
        # we return the data
        return post_data
#------------------------------------------------------------------------------------------------------	
#------------------------------------------------------------------------------------------------------
# Request handling - GET
#------------------------------------------------------------------------------------------------------
    # This function contains the logic executed when this server receives a GET request
    # This function is called AUTOMATICALLY upon reception and is executed as a thread!
    def do_GET(self):
        print("Receiving a GET on path %s" % self.path)
        # Here, we should check which path was requested and call the right logic based on it
        self.do_GET_Index()
#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------
    def do_GET_Index(self):
        self.set_HTTP_headers(200)
        '''
        If the user is on / (index), we simply construct the page,
        using the html-templates initiating the list of entries 
        to contain one item
        '''
        if self.path == "/":
            entries = ""
            with open('server/board_frontpage_header_template.html', 'r') as template:
                data = template.read() 
                entries += data

            with open('server/boardcontents_template.html', 'r') as template:
                firstThing = ""
                for k,v in sorted(self.server.store.items()):
                    with open('server/entry_template.html', 'r') as template1:
                        firstThing += template1.read() % ("entries/"+str(k), k, v)
                data = template.read() % ('OurBoard', firstThing) 
                entries += data

            with open('server/board_frontpage_footer_template.html', 'r') as template:
                data = template.read()# % ("erifor@student.chalmers.se, cjesper@student.chalmers.se")  
                entries += data
                
            self.wfile.write(entries)
            '''
            If the user wants to display a board, we:
                - Construct html-elements using the values we have in our store-dictionary
                - Append these to the html-string
                - Write the to our html-file
            '''
        elif self.path == "/board":
            entries = ""
            
            with open('server/boardcontents_template.html', 'r') as template:
                 data = template.read() % ('OurBoardTitle', "") 
                 entries += data
           
            with open('server/entry_template.html', 'r') as template:
                #Sort the dictionary so items appear in the correct order    
                for k,v in sorted(self.server.store.items()):
                    with open('server/entry_template.html', 'r') as template1:
                        data = template1.read() % ("entries/"+str(k), k, v)
                        entries += data
            
            self.wfile.write(entries)
#-----------------------------------------------------------------------------------------------------
# we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
    def do_POST(self):
        self.set_HTTP_headers(200)	
        '''
        When we get a POST on /board, the user wants to add a new entry.
        This entry is parsed and then sent to the leader so that the 
        leader can sort add requests from all vessels and propagate them
        in the same order for everyone
        '''
        if self.path == '/board':   
            self.add_to_store(True) 
        '''
        A POST containing /entries indicate that the user wants to remove
        or modify that element of the list. We find out which action is to
        be taken and call the appropriate function. A request is then sent 
        to the leader so that the leader can sort delete or modify requests 
        from all vessels and propagate them in the same order for everyone.
        '''
        if '/entries' in self.path:
            print "Del or mod" 
            self.delete_from_store(True)

        '''
        These paths are used for when values are propagated from the leader 
        to a vessel that is not the leader. Depending on which of the paths
        receive a POST, the appropriate function will be called.
        '''
        if self.path == '/propagateAdd':
            self.add_to_store(False)
        
        if self.path == '/propagateDel':
            self.delete_from_store(False)
            
        if self.path == '/propagateMod':
            self.modify_in_store()

    #A vessel adds the value parsed from the POST request to store
    def add_to_store(self, propagate):
        postData = self.parse_POST_request()
        if propagate:
            key = str(self.server.sequence_number) + str(self.server.vessel_id)
            key = int(key)
            #key = (self.server.sequence_number, self.server.vessel_id)
            value = postData['entry'][0]
            self.thread_propagate_vessels('/propagateAdd', 'POST', key, value)
            self.server.sequence_number += 1
        else:
            key = int(postData['key'][0])
            value = postData['value'][0]
        self.server.add_value_to_backend_store(key, value)
        self.server.add_value_to_store(value)
        self.server.frontKeyToBackKey.append((len(self.server.frontKeyToBackKey)+1 , key))

    #A vessel deletes the value corresponding to the key parsed from the POST request to store
    def delete_from_store(self, propagate) :
        postData = self.parse_POST_request()
        print postData
        if propagate:
            key = int(self.path[9:])
            backendKey = self.server.convert_frontend_to_backend_key(int(key))
            self.thread_propagate_vessels('/propagateDel', 'POST', backendKey, 0)
            self.server.delete_value_in_store(int(key)) 
            self.server.delete_value_in_backendStore(backendKey)
        else:
            key = int(postData['key'][0])
            #self.server.delete_value_in_store(int(key))
            print "Got propagated key " + str(key)
            if self.server.is_in_backend_store(int(key)):
                print "Trying to del prop.."
                print "Backend key for me: "
                self.server.delete_value_in_backendStore(key)
            else:
                self.server.deleteQueue.append(key)
                print "Could not find " + str(key) + " in my store. Added to deletequeue."

    #A vessel sets the value parsed from the POST request corresponding to the key parsed from the POST request to store
    def modify_in_store(self):
        postData = self.parse_POST_request()
        key = postData['key'][0]
        value = postData['value'][0]
        self.server.modify_value_in_store(int(key), value) 

    #This function creates a thread that contacts a specific vessel with the appropriate arguments
    def thread_contact_vessel(self, vessel_ip, path, action, key, value):
        thread = Thread(target=self.server.contact_vessel ,args=(vessel_ip , path, action, key, value))
        thread.daemon = True
        thread.start()

    #This function creates a thread that contacts all other vessel with the appropriate arguments
    def thread_propagate_vessels(self, path, action, key, value):
        thread = Thread(target=self.server.propagate_value_to_vessels,args=(path, action, key, value))
        thread.daemon = True
        thread.start()

  
#------------------------------------------------------------------------------------------------------
# POST Logic
#------------------------------------------------------------------------------------------------------
	# We might want some functions here as well
#------------------------------------------------------------------------------------------------------


#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':
	vessel_list = []
	vessel_id = 0
	# Checking the arguments
	if len(sys.argv) != 3: # 2 args, the script and the vessel name
		print("Arguments: vessel_ID number_of_vessels")
	else:
		# We need to know the vessel IP
		vessel_id = int(sys.argv[1])
		# We need to write the other vessels IP, based on the knowledge of their number
		for i in range(1, int(sys.argv[2])+1):
			vessel_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation
	# We launch a server
	server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
	print("Starting the server on port %d" % PORT_NUMBER)

	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()
		print("Stopping Server")
#------------------------------------------------------------------------------------------------------


