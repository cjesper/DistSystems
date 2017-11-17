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
                self.store = {1 : "First message"}
		# We keep a variable of the next id to insert
		self.current_key = 2
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
		# The list of other vessels
		self.vessels = vessel_list
                # Random number used to order the leaders
                self.random_vessel_nr = random.randint(0,15000)
                #Leader Election Info
                self.leaderElected = False #Used to determine what we should do in case of a timeout
                self.leader = "No leader."
                self.timesFailed = 0 #Used to determine which neighbor we should try to contact next
                self.sortedCandidates = []
                self.leaderCandidates = []
                self.sendDicts = {} #The dictionary we send during the leader election, containing {random_vessel_nr : vessel_ip}
                self.neighborNumber = self.vessel_id % len(self.vessels) + 1 #See nextNeighbor
                self.nextNeighbor = "10.1.0." + str(self.neighborNumber) #The neighbor we are currently trying to contact
                self.elect() #Start the election

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
       
        '''
            Initiate the leader election by:
            Sleeping (to avoid problems with other nodes booting slower)
            Adding our own random number and vessel_ip to the dictionary that we send
            Sending a POST-request to the /elect-endpoint to our neighbor
            Initially, the dictionary we send will only contain our own info
        '''
        def elect(self):
            time.sleep(1)
            thread = Thread(target=self.contact_vessel , args=(self.nextNeighbor, "/elect", 'POST', self.addSelf(), self.sendDicts))
            thread.daemon = True
            thread.start()

        '''
            Helper method to add our info to the dictionary
        '''
        def addSelf(self):
            self.sendDicts[self.random_vessel_nr] = "10.1.0." + str(self.vessel_id)
            return self.random_vessel_nr 

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
                        if not self.leaderElected:
                            self.neighborNumber = self.neighborNumber % len(self.vessels) +  1
                            self.nextNeighbor = "10.1.0." + str(self.neighborNumber)
                            print "NextNeighbor changed to " + self.nextNeighbor

                        '''
                            A leader crash is handled as follows:
                            1) The node trying to contact the leader will be unable to reach it
                            2) We keep all leader candidates - {rndNr :  }
                        '''
                        if vessel_ip == self.leader:
                            #Choose new leader, based on the random value we store in the sortedCandidates-list
                            self.timesFailed = self.timesFailed + 1
                            self.leader = self.sendDicts[self.sortedCandidates[self.timesFailed % len(self.vessels)]]
                            self.propagate_value_to_vessels('/newLeader', 'POST', 0, self.leader)
                            print "New leader: " + self.leader
                            #Send the request again
                            self.contact_vessel(self.leader, path, action, key, value)

		# we return if we succeeded or not
		return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
	def propagate_value_to_vessels(self, path, action, key, value):
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
                            data = template.read() % ('OurBoard', firstThing) 
                            entries += data

                    with open('server/board_frontpage_footer_template.html', 'r') as template:
                        data = template.read() % ("erifor@student.chalmers.se, cjesper@student.chalmers.se", "LEADER " + self.server.leader + " with number " + str(self.server.random_vessel_nr)) 
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

                    thread = Thread(target=self.server.contact_vessel ,args=(self.server.leader , "/leaderReceiveAdd", 'POST', 0, value) )
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
                        retransmit = False 
                        thread = Thread(target=self.server.contact_vessel , args=(self.server.leader, "/leaderReceiveDelete", 'POST', whichEntry, value) )
                        thread.daemon = True
                        thread.start()
                        
                        retransmit = False 
                        if retransmit:
                            thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagateDelete", 'POST', whichEntry, value) )
                            thread.daemon = True
                            thread.start()
                    #If we want to modify
                    else:
                        thread = Thread(target=self.server.contact_vessel , args=(self.server.leader, "/leaderReceiveMod", 'POST', whichEntry, value) )
                        thread.daemon = True
                        thread.start()

                        retransmit = False 
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
                
                if self.path == '/elect':
                    postData = self.parse_POST_request()
                    value = postData['value'][0]
                    #Parses the dict-like string to a dict
                    valueDict = ast.literal_eval(value)
                    self.server.sendDicts = valueDict

                    #Check if we have received our own IP
                    found = False
                    vesselIP = "10.1.0."+str(self.server.vessel_id)
                    for key in valueDict.keys():
                        if valueDict[key] == vesselIP:
                            found = True
                            break
                    
                    if found:
                        for key in self.server.sendDicts.keys():
                            if not key in self.server.leaderCandidates:
                                self.server.leaderCandidates.append(key)
                        
                        #Now, sort the candidates based on their key (the random value they generate)
                        #At first we select the first value in the list
                        self.server.sortedCandidates= sorted(self.server.leaderCandidates, reverse=True)
                        self.server.leader = self.server.sendDicts[self.server.sortedCandidates[0]]
                        self.server.leaderElected = True
                        print "Leader elected " + self.server.leader
                    else:
                        print "Did not find myself in " + str(valueDict)
                        self.server.addSelf()

                        thread = Thread(target=self.server.contact_vessel , args=(self.server.nextNeighbor , "/elect", 'POST', "key", self.server.sendDicts) )
                        thread.daemon = True
                        thread.start()
                   
                if self.path == '/leaderReceiveAdd': 
                    postData = self.parse_POST_request()
                    value = postData['value'][0]
                    self.server.add_value_to_store(value) 
                        
                    thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagate", 'POST', 0, value) )
                    thread.daemon = True
                    thread.start()

                if self.path == '/leaderReceiveMod': 
                    postData = self.parse_POST_request()
                    key = postData['key'][0]
                    value = postData['value'][0]
                    self.server.modify_value_in_store(int(key), value)

                    thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagateModify", 'POST', key, value) )
                    thread.daemon = True
                    thread.start()
                
                if self.path == '/leaderReceiveDelete': 
                    postData = self.parse_POST_request()
                    key = postData['key'][0]
                    self.server.delete_value_in_store(int(key))
                        
                    thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagateDelete", 'POST', key, '0') )
                    thread.daemon = True
                    thread.start()

                if self.path == '/newLeader':
                    postData = self.parse_POST_request()
                    value = postData['value'][0]
                    self.server.leader = value
                    print "New leader: " + self.server.leader

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


