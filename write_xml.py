#!/usr/bin/env python

import StringIO
from xml.dom.minidom import Document

import thedata

def main():
    with open("static/xml/clusters.xml", 'w') as opf:
	doc = Document()
    	write_clusters(doc, opf)
    with open("static/xml/users.xml", 'w') as opf:
	doc = Document()
	write_users(doc, opf)
	opf.close

def write_clusters(doc, outputfile):
    data = thedata.CLUSTER_DATA
    tags = thedata.CLUSTER_TAGS

    # First basenode
    clusters = doc.createElement("clusters")
    doc.appendChild(clusters)

    for k, datum in enumerate(data):
	cluster = doc.createElement("cluster")
	clusters.appendChild(cluster)
	cluster.setAttribute('id', "cluster{0:02d}".format(k+1))

	# handling all properties other than hostnames
	for tag, d in zip(tags, datum[:-1]):
	    elm = doc.createElement(tag)
	    cluster.appendChild(elm)
	    text = doc.createTextNode(str(d))
	    elm.appendChild(text)
    
	# start handling hostnames from here
	hostnames = doc.createElement("hostnames")
	cluster.appendChild(hostnames)
	for hostname in datum[-1]:	
	    hn = doc.createElement("hn") # hn: hostname
	    hostnames.appendChild(hn)
	    text = doc.createTextNode(hostname)
	    hn.appendChild(text)

    # text node in xml should not contain redundant space or newlines
    # doc.writexml(outputfile, indent="  ", addindent="  ", newl="\n") 
    doc.writexml(outputfile)			# this is not pretty

def write_users(doc, outputfile):
    data = thedata.USER_DATA
    tags = thedata.USER_TAGS
    
    users = doc.createElement("users")
    doc.appendChild(users)

    data = StringIO.StringIO(data)
    k = 0
    for line in data:
	if line.strip():
	    user = doc.createElement("user")
	    users.appendChild(user)
	    user.setAttribute('id', "user{0:02d}".format(k+1))
	    
	    sl = [i.strip() for i in line.split("=")]
	    ssl = sl[1].split()
	    for username in ssl:
		un = doc.createElement(tags[0]) # un: username
		user.appendChild(un)
		text = doc.createTextNode(username)
		un.appendChild(text)
	    
		rn = doc.createElement(tags[1]) # rn: realname
		user.appendChild(rn)
		text = doc.createTextNode(sl[0])
		rn.appendChild(text)
	    k += 1
    
    print doc.toprettyxml(indent="  ")
    doc.writexml(outputfile)			# this is not pretty

if __name__ == "__main__":
    main()
