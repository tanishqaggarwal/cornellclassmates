#Python script to scrape all roster data from the Cornell API that is relevant to the CornellClassmates app.
import requests
import json
import re

#Auxiliary function: to translate the time patterns (MWF) into their full forms
def translate_days(original_list):
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

#Scrape the subject data
r = requests.get('https://classes.cornell.edu/api/2.0/config/subjects.json', {'roster': 'FA17'})

filtered = json.loads(r.text)

subjectkeys = []
for subject in filtered["data"]["subjects"]:
	subjectkeys.append(subject["value"])

print "The total number of subjects is " + str(len(subjectkeys))

sections_data = []
##Now that you've got subject data, scrape each and every class per subject
subjectcounter = 0
for subject in subjectkeys:
	r = requests.get('https://classes.cornell.edu/api/2.0/search/classes.json', {'roster': 'FA17', 'subject':subject})
	filtered = json.loads(r.text)

	subject_sections_data = []
	#From each class, scrape the sections
	print "The total number of classes in " + subject + " is " + str(len(filtered["data"]["classes"]))
	for course in filtered["data"]["classes"]:
		course_number = subject + course["catalogNbr"]
		class_title = course["titleLong"]

		#Scrape the relevant fields from each section: class ID, class type, meeting times
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

					if meeting_string == " to ":
						meeting_string = "Time: TBA or Non-Periodic"
					meeting_strings.append(meeting_string)
				
				section_data["class_times"] = "; ".join(meeting_strings)
				course_sections_data.append(section_data)

		#Modify the section entries to include the course number and class title
		for idx, section in enumerate(course_sections_data):
			section["course_number"] = course_number
			section["class_title"]   = class_title

			subject_sections_data.append(section)

	for section in subject_sections_data:
		sections_data.append(section)

	subjectcounter += 1
	print "Subject #" + str(subjectcounter) + " (" + subject + ") completed (of " + str(len(subjectkeys)) + ")"

#print "Component Types: " + str(component_types)

jsonfile = open("sections_data.json", "w")
jsonfile.write(json.dumps(sections_data))
jsonfile.close()