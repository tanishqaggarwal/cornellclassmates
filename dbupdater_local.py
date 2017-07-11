import requests, json

#url = "http://cornellclassmates.appspot.com/new/class"
url = "http://localhost:11080/new/class"

datafile = open("sections_data.json", "r")
data = json.load(datafile)
datafile.close()

print "The total number of sections is " + str(len(data))

sectioncounter = 0
for section in data:
	payload = {
		"class_id" 		: section["class_id"],
		"class_title" 	: section["class_title"],
		"course_number" : section["course_number"],
		"class_times" 	: section["class_times"],
		"class_type" 	: section["class_type"],
	}
	r = requests.post(url, data=payload)
	sectioncounter += 1
	print "Currently processing section #" + str(sectioncounter)