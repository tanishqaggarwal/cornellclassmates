#Python script to scrape all roster data from the Cornell API.
import requests
import json
import re

def translate_days(original_list): #To translate the pattern into something human-readable
	translation_key = {
		"M" : "Monday",
		"T" : "Tuesday",
		"W" : "Wednesday",
		"R" : "Thursday",
		"F" : "Friday",
		"S" : "Saturday",
		"Su" : "Sunday",
	}
	new_list = []
	for item in original_list:
		new_list.append(translation_key[item])
	return new_list

component_types = ["Lecture", "Lab", "Discussion"]
class_ids = []
duplicated_ids = []

url = 'https://classes.cornell.edu/api/2.0/config/subjects.json'
payload = {'roster': 'FA17'}

# GET with params in URL
r = requests.get(url, params=payload)


filtered = json.loads(r.text)

subjectkeys = []
for subject in filtered["data"]["subjects"]:
	subjectkeys.append(subject["value"])

print "The total number of subjects is " + str(len(subjectkeys))

subjectcounter = 0
for subject in subjectkeys:
	url = 'https://classes.cornell.edu/api/2.0/search/classes.json'
	payload = {'roster': 'FA17', 'subject':subject}
	r = requests.get(url, params=payload)
	filtered = json.loads(r.text)

	print "The total number of classes in " + subject + " is " + str(len(filtered["data"]["classes"]))
	for course in filtered["data"]["classes"]:
		course_number = subject + course["catalogNbr"]
		class_title = course["titleLong"]

		course_sections_data = []
		for enroll_group in course["enrollGroups"]:
			for section in enroll_group["classSections"]:
				section_data = {}

				if section["ssrComponentLong"] not in component_types:
					component_types.append(section["ssrComponentLong"])

				section_data["class_type"] = section["ssrComponentLong"]
				section_data["class_id"] = str(section["classNbr"])

				meeting_strings = []
				for meeting in section["meetings"]:
					time_start   = meeting["timeStart"]
					time_end     = meeting["timeEnd"]
					meeting_days = ", ".join(translate_days(re.findall('[A-Z][^A-Z]*', meeting["pattern"]))) #Converts "MWF" to "Monday, Wednesday, Friday"
					meeting_string = meeting_days + " " + time_start + " to " + time_end
					meeting_strings.append(meeting_string)
				
				section_data["class_times"] = "; ".join(meeting_strings)
				course_sections_data.append(section_data)

		for section in course_sections_data:
			section["course_number"] = course_number
			section["class_title"]   = class_title

			while section_data["class_id"] in class_ids:
				section_data["class_id"] += "-0"
			class_ids.append(section_data["class_id"])

			#Now write this data to a file
			jsonfile = open("scraped_data/" + section["class_id"] + ".json", "w")
			jsonfile.write(json.dumps(section))
			jsonfile.close()

	subjectcounter += 1
	print "Subject #" + str(subjectcounter) + " (" + subject + ") completed (of " + str(len(subjectkeys)) + ")"

print "Types of classes: " + str(component_types)
