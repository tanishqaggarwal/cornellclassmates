#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import json
from google.appengine.ext import ndb
import logging
import urllib
import traceback
from datetime import datetime, timezone

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), 
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)

##DATABASE
class Cornellian(ndb.Model):
    first_name = ndb.StringProperty(required = True)
    last_name  = ndb.StringProperty(required = True)
    classof       = ndb.StringProperty(required = True)
    email_address = ndb.StringProperty(required = True) #Has to be a Cornell email address
    passcode      = ndb.StringProperty(required = True) #Passcode used by the Cornellian to delete themselves from the class, if necessary
    enrolled_classes = ndb.StringProperty(repeated = True)

CLASS_TYPES = ['Lecture', 'Laboratory', 'Discussion', 'Seminar', 'Independent Study', 'Field Studies', 'Research', 'TA/Tutor Group', 'Studio', 'Clinical']
class Course(ndb.Model):
    class_id  = ndb.StringProperty(required = True)
    course_number = ndb.StringProperty(required = True)
    class_title   = ndb.StringProperty(required = True)
    class_type    = ndb.StringProperty(required = True, choices = CLASS_TYPES)
    class_times   = ndb.StringProperty(required = True)
    class_members = ndb.StringProperty(repeated = True) #email addresses of Cornellians

#Programmatically inserts all of the courses that were scraped from the Cornell Roster API
class DBUpdate(webapp2.RequestHandler):
    def get(self):
        #To ensure this script cannot fuck shit up, it cannot run past a certain datetime
        if datetime.now() > datetime(2017, 7, 10, 22, 30, 0, 0): # Jul 10 2017 6:30 PM EST (10:30 PM UTC)
            course_data_path = os.path.join(os.path.dirname(__file__), 'sections_data.json')
            with open(course_data_path, 'r') as course_data_file:
                course_data = json.loads(course_data_file.read())

                course_list = []
                for section in course_data:
                    course = Course()
                    course.class_id      = section["class_id"]
                    course.course_number = section["course_number"]
                    course.class_title   = section["class_title"]
                    course.class_type    = section["class_type"]
                    course.class_times   = section["class_times"]
                    course_list.append(course)
                ndb.put_multi(course_list)

            self.response.out.write(JINJA_ENVIRONMENT.get_template("dbupdate.html").render())

##HANDLERS
class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(JINJA_ENVIRONMENT.get_template("index.html").render())
    def post(self):
        class_id = self.request.get("class_id")
        found_class = Course.query(Course.class_id == class_id).get()
        if not found_class:
            self.response.out.write("not found")
        else:
            self.response.out.write("found")

class NewClass(webapp2.RequestHandler):
    def get(self):
        class_id = self.request.get("class_id")
        self.response.out.write(JINJA_ENVIRONMENT.get_template("new_class.html").render({"class_id" : class_id, "class_types" : CLASS_TYPES}))
    def post(self):
        try: 
            class_id = self.request.get("class_id")
            course_number = self.request.get("course_number")
            class_title = self.request.get("class_title")
            class_times = self.request.get("class_times")
            class_type = self.request.get("class_type")

            course = Course()
            course.class_id = class_id
            course.course_number = course_number
            course.class_title = class_title
            course.class_times = class_times
            course.class_type = class_type
            course.put()

            self.response.out.write("added class")
        except:
            self.response.out.write("could not add class")

class NewCornellian(webapp2.RequestHandler):
    def get(self):
        class_id = self.request.get("class_id")
        self.response.out.write(JINJA_ENVIRONMENT.get_template("new_cornellian.html").render({"class_id" : class_id}))
    def post(self):
        try:
            class_id      = self.request.get("class_id")
            first_name    = self.request.get("first_name")
            last_name     = self.request.get("last_name")
            classof       = self.request.get("classof")
            email_address = self.request.get("email_address")
            passcode      = self.request.get("passcode")

            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()
            else:
                course.class_members.append(email_address)
                course.put()

            cornellian = Cornellian.query(Cornellian.email_address == email_address).get()
            if cornellian:
                cornellian.enrolled_classes.append(class_id)
                cornellian.put()
                return webapp2.Response("added cornellian")

            cornellian = Cornellian()
            cornellian.first_name       = first_name
            cornellian.last_name        = last_name
            cornellian.classof          = classof
            cornellian.email_address    = email_address
            cornellian.passcode         = passcode
            cornellian.enrolled_classes.append(class_id)
            cornellian.put()

            self.response.out.write("added cornellian")
        except Exception as e:
            logging.error(e)
            self.response.out.write("could not add cornellian")

class ViewClass(webapp2.RequestHandler):
    def get(self):
        try:
            class_id = self.request.get("class_id")
            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()
            else:
                course_info = {
                    "class_id"      : course.class_id,
                    "course_number" : course.course_number,
                    "class_title"   : course.class_title,
                    "class_type"    : course.class_type,
                    "class_times"   : course.class_times,
                }
                members = course.class_members
                class_members = []
                if members:
                    cornellians = Cornellian.query(Cornellian.email_address.IN(members)).fetch()
                    for cornellian in cornellians:
                        class_members.append({
                            "first_name"    : cornellian.first_name,
                            "last_name"     : cornellian.last_name,
                            "classof"       : cornellian.classof,
                            "email_address" : cornellian.email_address,
                            "email_address_urlencoded" : urllib.quote(cornellian.email_address),
                        })
                self.response.out.write(JINJA_ENVIRONMENT.get_template("view_class.html").render({"class_members" : class_members, "course_info" : course_info}))
        except Exception as e:
            logging.error(e)
            self.response.out.write(JINJA_ENVIRONMENT.get_template("view_class_error.html").render())

class ViewCornellian(webapp2.RequestHandler):
    def get(self):
        try:
            email_address = self.request.get("email_address")
            cornellian = Cornellian.query(Cornellian.email_address == email_address).get()
            if not cornellian:
                raise Exception()
            else:
                cornellian_info = {
                    "first_name"               : cornellian.first_name,
                    "last_name"                : cornellian.last_name,
                    "email_address"            : cornellian.email_address,
                    "classof"                  : cornellian.classof,
                }

                list_of_courses = cornellian.enrolled_classes
                enrolled_courses = []
                if list_of_courses:
                    courses = Course.query(Course.class_id.IN(list_of_courses)).fetch()
                    for course in courses:
                        enrolled_courses.append({
                            "class_id"       : course.class_id,
                            "course_number"  : course.course_number,
                            "class_title"    : course.class_title,
                            "class_type"     : course.class_type,
                            "class_times"    : course.class_times,
                        })
                self.response.out.write(JINJA_ENVIRONMENT.get_template("view_cornellian.html").render({"enrolled_courses" : enrolled_courses, "cornellian_info" : cornellian_info}))
        except Exception as e:
            logging.error(traceback.print_exc(e))
            self.response.out.write(JINJA_ENVIRONMENT.get_template("view_cornellian_error.html").render())

class DeleteCornellian(webapp2.RequestHandler):
    def get(self):
        try:
            email_address = self.request.get("email_address")
            class_id = self.request.get("class_id")
            cornellian = Cornellian.query(Cornellian.email_address == email_address).get()
            if not cornellian:
                raise Exception()

            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()

            cornellian_info = {
                "first_name"               : cornellian.first_name,
                "last_name"                : cornellian.last_name,
                "email_address"            : cornellian.email_address,
                "classof"                  : cornellian.classof,
            }

            course_info = {
                "class_id"      : course.class_id,
                "course_number" : course.course_number,
                "class_title"   : course.class_title,
                "class_type"    : course.class_type,
                "class_times"   : course.class_times,
            }
                
            self.response.out.write(JINJA_ENVIRONMENT.get_template("delete_cornellian.html").render({"course_info" : course_info, "cornellian_info" : cornellian_info}))
        except Exception as e:
            logging.error(traceback.print_exc(e))
            self.response.out.write(JINJA_ENVIRONMENT.get_template("delete_cornellian_error.html").render())
    
    def post(self):
        try:
            email_address = self.request.get("email_address")
            class_id = self.request.get("class_id")
            passcode = self.request.get("passcode")
            cornellian = Cornellian.query(ndb.AND(Cornellian.email_address == email_address, Cornellian.passcode == passcode)).get()
            if not cornellian:
                raise Exception()

            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()

            cornellian.enrolled_classes.remove(class_id)
            cornellian.put()
            course.class_members.remove(email_address)
            course.put()
                
            self.response.out.write("removed cornellian from class")
        except Exception as e:
            logging.error(traceback.print_exc(e))
            self.response.out.write("error")

class DeleteClass(webapp2.RequestHandler):
    def get(self):
        try:
            email_address = self.request.get("email_address")
            class_id = self.request.get("class_id")
            cornellian = Cornellian.query(Cornellian.email_address == email_address).get()
            if not cornellian:
                raise Exception()

            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()

            cornellian_info = {
                "first_name"               : cornellian.first_name,
                "last_name"                : cornellian.last_name,
                "email_address"            : cornellian.email_address,
                "classof"                  : cornellian.classof,
            }

            course_info = {
                "class_id"      : course.class_id,
                "course_number" : course.course_number,
                "class_title"   : course.class_title,
                "class_type"    : course.class_type,
                "class_times"   : course.class_times,
            }
                
            self.response.out.write(JINJA_ENVIRONMENT.get_template("delete_class.html").render({"course_info" : course_info, "cornellian_info" : cornellian_info}))
        except Exception as e:
            logging.error(traceback.print_exc(e))
            self.response.out.write(JINJA_ENVIRONMENT.get_template("delete_class_error.html").render())

    def post(self):
        try:
            email_address = self.request.get("email_address")
            class_id = self.request.get("class_id")
            passcode = self.request.get("passcode")
            cornellian = Cornellian.query(Cornellian.email_address == email_address, Cornellian.passcode == passcode).get()
            if not cornellian:
                raise Exception()

            course = Course.query(Course.class_id == class_id).get()
            if not course:
                raise Exception()

            cornellian.enrolled_classes.remove(class_id)
            cornellian.put()
            course.class_members.remove(email_address)
            course.put()
                
            self.response.out.write("removed class from cornellian")
        except Exception as e:
            logging.error(traceback.print_exc(e))
            self.response.out.write("error")

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/dbupdate', DBUpdate),
    ('/new/class', NewClass),
    ('/new/cornellian', NewCornellian),
    ('/view/class', ViewClass),
    ('/view/cornellian', ViewCornellian),
    ('/delete/cornellian', DeleteCornellian),
    ('/delete/class', DeleteClass),
], debug=True)