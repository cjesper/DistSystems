# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: G2
# Student names: Jesper Carlsson, Erik Forsström 
#------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler # Socket specifically designed to handle HTTP requests
import sys # Retrieve arguments
from urlparse import parse_qs # Parse POST data
from httplib import HTTPConnection # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode # Encode POST content into the HTTP header
from codecs import open # Open a file
from threading import  Thread # Thread Management
from byzantine_behavior import *
import traceback
import ast
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
                self.loyalNodes = 2
                self.totalNodes = 3
                self.loyalty = True 
                self.ownVote = "" 
                self.vectorList = []
                self.voteVector = {}
                self.result_vector = []
                self.compute_first = False
                self.compute_second = False
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
                self.tie = True 
		self.vessel_ip = "10.1.0."+str(vessel_id)
		# The list of other vessels
		self.vessels = vessel_list
#------------------------------------------------------------------------------------------------------
        """
            Add a vote to our vector.
        """
        def add_vote_to_vector(self, ID , vote):
            self.voteVector[ID] = vote
        
        def try_compute(self):
            if self.loyalty == False and len(self.voteVector) == self.loyalNodes and self.compute_first == False:
                self.compute_first = True
                self.compute_round_one_byzantine()
            elif self.loyalty == True and len(self.voteVector) == self.totalNodes and self.compute_second == False:
                self.compute_second = True
                self.compute_round_two()
            elif self.loyalty == False and self.compute_first == True and self.compute_second == False:
                self.compute_second= True
                self.compute_round_two_byzantine()

            if len(self.vectorList) == self.loyalNodes:
                self.compute_resulting_round()
        
        #The byzantine node sends its faulty votes to the honest nodes
        def compute_round_one_byzantine(self):
            resultVector = compute_byzantine_vote_round1(self.loyalNodes, self.totalNodes, self.tie)
            count = 0
            for vessel in self.vessels:
                if vessel != self.vessel_ip and count < self.loyalNodes:
                    vote = resultVector[count]
                    self.thread_contact_vessel(vessel, '/propagated', 'POST', self.vessel_id, vote)
                    count += 1

        #An honest node sends a list of received votes to all other nodes
        def compute_round_two(self):
            voteList = []
            for key in self.voteVector.keys():
                voteList.append(self.voteVector[key])

            self.thread_propagate_vessels('/propagatedVector', 'POST', self.vessel_id, voteList)

        #The byzantine node sends its faulty vote vectors to the honest nodes
        def compute_round_two_byzantine(self):
            result_vectors = compute_byzantine_vote_round2(self.loyalNodes, self.totalNodes, self.tie)
            count = 0
            for vessel in self.vessels:
                if vessel != self.vessel_ip and count < self.loyalNodes:
                    result_vector = result_vectors[count]
                    self.thread_contact_vessel(vessel, '/propagatedVector', 'POST', self.vessel_id, result_vector)
                    count += 1
        '''
        	Compute the final result using the list of vote vectors, comparing each index and putting the majority 
        	in each index of the result vector. Finaly count the elements in that vector and output the result.
        '''
        def compute_resulting_round(self):
            if (self.loyalty == True):
                voteList = []
                for key in self.voteVector.keys():
                    voteList.append(self.voteVector[key])
                self.vectorList.append(voteList)
                self.result_vector = []
                for i in range (0, self.totalNodes):
                    attack = 0
                    retreat = 0
                    for element in self.vectorList:
                        if element[i] == True or element[i] == 'True':
                            attack += 1
                        else:
                            retreat +=1

                    if attack > retreat:
                        self.result_vector.append(True)
                    elif retreat > attack:
                        self.result_vector.append(False)
                    else:
                        self.result_vector.append("UNKNOWN")

                attacks = 0
                retreats = 0
                for vote in self.result_vector:
                    if vote == True or vote == 'True':
                        attacks += 1
                    elif vote == False or vote == "False":
                        retreats += 1
                    else:
                        pass

                print "I am going to attack!" if attacks >= retreats else "I am going to retreat!"
                print self.result_vector
            else:
                pass

#------------------------------------------------------------------------------------------------------
# Contact a specific vessel with a set of variables to transmit to it
	def contact_vessel(self, vessel_ip, path, action, key, value):
		# the Boolean variable we will return
		success = False
		# The variables must be encoded in the URL format, through urllib.urlencode
		post_content = urlencode({'action': action, 'key': key, 'value': value})
		# the HTTP header must contain the type of data we are transmitting, here URL encoded
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		# We should try to catch errors when contacting the vessel
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
                            return success
		# We catch every possible exceptions
		except Exception as e:
			print "Error while contacting %s" % vessel_ip
			# printing the error given by Python
			print str(e)

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


        def thread_contact_vessel(self, vessel_ip, path, action, key, value):
            thread = Thread(target=self.contact_vessel, args=(vessel_ip, path, action, key, value ))
            thread.daemon = True
            thread.start()
        
        def thread_propagate_vessels(self, path, action, key, value):
            thread = Thread(target=self.propagate_value_to_vessels , args=(path, action, key, value ))
            thread.daemon = True
            thread.start()

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
		# We set the response status code to 200 (OK)
		self.set_HTTP_headers(200)
		# We should do some real HTML here
	        if self.path =="/":
                    entries = ""

                    with open('server/vote_frontpage_template.html', 'r') as template:
                        data = template.read()
                        entries += data
                        
                        self.wfile.write(entries)

                elif self.path == "/vote/result":
                    entries = ""
                    #Try to compute a result from the votes
                    self.server.try_compute()
                    with open('server/vote_result_template.html', 'r') as template:
                        data = template.read()
                        entries += data

                        self.wfile.write(entries)
		#In practice, go over the entries list, 
		#produce the boardcontents part, 
		#then construct the full page by combining all the parts ...
		
#------------------------------------------------------------------------------------------------------
	# we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
	def do_POST(self):

                self.set_HTTP_headers(200)
		print("Receiving a POST on %s" % self.path)
		# Here, we should check which path was requested and call the right logic based on it
		# We should also parse the data received
		# and set the headers for the client

		# If we want to retransmit what we received to the other vessels
		retransmit = False # Like this, we will just create infinite loops!

                if self.path == '/vote/attack':
                    self.vote_attack() 
                if self.path == '/vote/retreat':
                    self.vote_retreat()

                if self.path == '/vote/byzantine':
	            self.set_byzantine()

                if self.path == '/propagated':
                    postData = self.parse_POST_request() 
                    self.process_vote(postData) 

                if self.path == '/propagatedVector':
                    postData = self.parse_POST_request() 
                    self.process_vector(postData) 

			# do_POST send the message only when the function finishes
			# We must then create threads if we want to do some heavy computation
			# 
			# Random content
			thread = Thread(target=self.server.propagate_value_to_vessels,args=("action", "key", "value") )
			# We kill the process if we kill the server
			thread.daemon = True
			# We start the thread
			thread.start()
#------------------------------------------------------------------------------------------------------
# POST Logic
#------------------------------------------------------------------------------------------------------
	# We might want some functions here as well
#------------------------------------------------------------------------------------------------------
        #Add True to own vote vector and propagate vote
        def vote_attack(self):
            self.server.add_vote_to_vector(self.server.vessel_id, True)
            #Propagate attack order
            self.thread_propagate_vessels("/propagated", "POST", self.server.vessel_id, True)
        
        #Add False to own vote vector and propagate vote
        def vote_retreat(self):
            self.server.add_vote_to_vector(self.server.vessel_id, False)
            #Propagate attack order
            self.thread_propagate_vessels("/propagated", "POST", self.server.vessel_id, False)

        #Sets a nodes loyalty to byzantine
        def set_byzantine(self):
            print str(self.server.vessel_id) + " is now byzantine."
            self.server.loyalty = False

        #Add a propagated vote to own vote vector
        def process_vote(self, postData):
            received_vote = ast.literal_eval(postData['value'][0])
            sender = ast.literal_eval(postData['key'][0])
            self.server.add_vote_to_vector(sender, received_vote)

        #Add a propagated vote vector to own vector list
        def process_vector(self, postData):
            vector = ast.literal_eval(postData['value'][0])
            self.server.vectorList.append(vector)

        #Help method for vessel contacting
        def thread_contact_vessel(self, vessel_ip, path, action, key, value):
            thread = Thread(target=self.server.contact_vessel, args=(vessel_ip, path, action, key, value ))
            thread.daemon = True
            thread.start()

        #Help method for vessel contacting
        def thread_propagate_vessels(self, path, action, key, value):
            thread = Thread(target=self.server.propagate_value_to_vessels , args=(path, action, key, value ))
            thread.daemon = True
            thread.start()




#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

	## read the templates from the corresponding html files
	# .....

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
