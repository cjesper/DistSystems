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

                all_candidates_received = False
                leader_elected = False
		HTTPServer.__init__(self,server_address, handler)
		# we create the dictionary of values
                self.store = {1 : "First message"}
		# We keep a variable of the next id to insert
		self.current_key = 2
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
                self.known_IPs = []
                self.known_IPs.append("10.1.0."+str(self.vessel_id))
		# The list of other vessels
		self.vessels = vessel_list
                #List of received IP
		#while not all_candidates_received:
                self.send_known_IPs()
#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store(self, value):
		# We add the value to the store
                self.store[self.current_key] = value
                self.current_key = self.current_key + 1
                print("Added value to store")
#------------------------------------------------------------------------------------------------------
	# We modify a value received in the store
	def modify_value_in_store(self,key,value):
		# we modify a value in the store if it exists
                self.store[key] = value
#------------------------------------------------------------------------------------------------------
	# We delete a value received from the store
	def delete_value_in_store(self,key):
		# we delete a value in the store if it exists
                del self.store[key]

        def add_ip(self, IPs):
            print "Adding IPs"
            if not "10.1.0."+str(self.vessel_id)in IPs:
                for value in IPs:
                    print type(value)
                    self.known_IPs.append(value)
            print self.known_IPs

        def send_known_IPs(self):
            nr_of_vessels = len(self.vessels)
            neighborId = ((self.vessel_id) % nr_of_vessels) + 1
            neighbor = "10.1.0."+str(neighborId)
            thread = Thread(target=self.contact_vessel , args = (neighbor, "/propagateIP", 'POST', "key", self.known_IPs))
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
                print vessel_ip + " " + key
		try:
			# We contact vessel:PORT_NUMBER since we all use the same port
			# We can set a timeout, after which the connection fails if nothing happened
			connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 30)
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

		# we return if we succeeded or not
		return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
	def propagate_value_to_vessels(self, path, action, key, value):
                print ("Propagating " + path + " " + action + " " + value)
		# We iterate through the vessel list
		for vessel in self.vessels:
			# We should not send it to our own IP, or we would create an infinite loop of updates
			if vessel != ("10.1.0.%s" % self.vessel_id):
				# A good practice would be to try again if the request failed
				# Here, we do it only once
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
                            data = template.read() % ('OurBoardTitle', firstThing) 
                            entries += data

                    with open('server/board_frontpage_footer_template.html', 'r') as template:
                        data = template.read() % ("erifor@student.chalmers.se/cjesper@student.chalmers.se") 
                        entries += data
                        
                    self.wfile.write(entries)
                    '''
                    If the user wants to display a board, we:
                        Construct html-elements using the values we have in our store-dictionary
                        Append these to the html-string
                        Write the to our html-file
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
                    We parse the request to get the new value, then add it to our
                    store.
                    Then, we propagate the value to the other vessels, passing 0 as
                    the key since each vessel knows it's own current_key.
                '''
                if self.path == '/board':
                    postData = self.parse_POST_request()
                    value = postData['entry'][0]
                    self.server.add_value_to_store(value) 
		# If we want to retransmit what we received to the other vessels
                    retransmit = True# Like this, we will just create infinite loops!
                    if retransmit:
                        thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagate", 'POST', 0, value) )
                        thread.daemon = True
                        thread.start()
                '''
                    A POST containing /entries indicate that the user wants to remove
                    or modify that element of the list. We find out which action is to
                    be taken and call the appropriate function.
                    A propagation is then made, which uses the propagation-paths
                    mentioned below.
                '''
                if '/entries' in self.path:
                    whichEntry = self.path[9:]
                    postData = self.parse_POST_request()
                    value = postData['entry'][0]
                    delOrModify = postData['delete'][0]
                    #If we want to delete : Delete the entry in our store, then propagate to other vessels
                    if delOrModify == '1':
                        self.server.delete_value_in_store(int(whichEntry))
                        retransmit = True
                        if retransmit:
                            thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagateDelete", 'POST', whichEntry, value) )
                            thread.daemon = True
                            thread.start()
                    #If we want to modify
                    else:
                        self.server.modify_value_in_store(int(whichEntry), value)
                        retransmit = True
                        if retransmit:
                            thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagateModify", 'POST', whichEntry, value) )
                            thread.daemon = True
                            thread.start()
                '''
                    These paths are used for when values are propagated from one vessel to another.
                    Depending on which of the paths receive a POST, the appropriate function will be called.
                '''
                if self.path == '/propagate':
                    postData = self.parse_POST_request()
                    value = postData['value'][0]
                    self.server.add_value_to_store(value) 
                
                if self.path == '/propagateDelete':
                    postData = self.parse_POST_request()
                    key = postData['key'][0]
                    self.server.delete_value_in_store(int(key)) 
                    
                if self.path == '/propagateModify':
                    postData = self.parse_POST_request()
                    key = postData['key'][0]
                    value = postData['value'][0]
                    self.server.modify_value_in_store(int(key), value) 
                '''
                    List of IP's received from previous node
                '''
                if self.path == '/propagateIP':
                    postData = self.parse_POST_request()
                    value = postData['value'][0]
                    print "Value is " + value[2:len(value)-2]
                    self.server.add_ip(["10.1.4.5", "10.1.4.6"])

                    
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


