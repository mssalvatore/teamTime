#!/usr/bin/env python3
# File    : teamTime.py
# Author  : Joe McManus josephmc@alumni.cmu.edu
# Version : 0.6  10/17/2019 Joe McManus
# Copyright (C) 2019 Joe McManus

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from datetime import datetime
from time import time
from pytz import timezone
import pytz
from prettytable import PrettyTable
from os import path
import argparse
import csv
import re
from typing import Iterable, List


class TeamMember:
    def __init__(self, csv_row: List):
        self.name = csv_row[0]
        self.timezone = csv_row[1]
        self.time = get_current_formatted_time(self.timezone)
        self.city = csv_row[2].strip()
        self._geo_location = None

    @property
    def _location(self):
        if self._geo_location is None:
            geolocator = Nominatim(user_agent="teamTime")
            self._geo_location = geolocator.geocode(self.city)

        return self._geo_location

    @property
    def latitude(self):
        return self._location.latitude

    @property
    def longitude(self):
        return self._location.longitude

def get_current_formatted_time(staffZone, format_="%Y-%m-%d %H:%M"):
    staffTime = datetime.now(timezone(staffZone)).strftime(format_)
    return staffTime


parser = argparse.ArgumentParser(description="Time Table")
parser.add_argument("--name", help="Optional name to search for", action="store")
parser.add_argument("--comp", help="Compare times of team members.", action="store")
parser.add_argument(
    "--src",
    help="Optional src file, defaults to staff.csv",
    action="store",
    default="staff.csv",
)
parser.add_argument("--map", help="Draw map", action="store_true")
parser.add_argument(
    "--sort",
    help="Field to sort by <time|name>. Defaults to name.",
    action="store",
    default="name",
)
parser.add_argument("--rev", help="Reverse the sort order", action="store_true")
args = parser.parse_args()


def compareTime(staffZone):
    now = datetime.now()
    getHour, getMinute = args.comp.split(":")
    localTime = datetime(now.year, now.month, now.day, int(getHour), int(getMinute))
    remoteTime = localTime.astimezone(timezone(staffZone)).strftime("%Y-%m-%d %H:%M")
    return localTime, remoteTime


def getLocation(staffCity):
    geolocator = Nominatim(user_agent="teamTime")
    location = geolocator.geocode(staffCity)
    return ((location.latitude), (location.longitude))


if not path.isfile(args.src):
    print("ERROR: Unable to read {}".format(args.src))
    quit()

if args.name:
    fixedName = args.name.capitalize()

if args.comp:
    pattern = re.compile("\d{1,2}:\d{2}")
    if not pattern.match(args.comp):
        print("ERROR: Please use 24 hour time format, i.e. --comp 10:00")
        quit()

if not args.sort in ["name", "time"]:
    print("ERROR: Please specify a sort argument of 'name' or 'time'")
    quit()

if args.map:
    try:
        import pandas as pd
        from geopy.geocoders import Nominatim
        import plotly.graph_objects as go
    except:
        print("Missing mapping libs, try pip3 install pandas plotly geopy")
        quit()

table = PrettyTable()
if args.comp:
    table.field_names = ["Person", "Their Time", "Your Time"]
else:
    table.field_names = ["Person", "Local Time"]
    table.add_row(["now()", datetime.now().strftime("%Y-%m-%d %H:%M")])

table.align["Person"] = "l"

# Lists to hold data for maps
staffLat = []
staffLon = []
labels = []

def build_table_rows(team_members: Iterable[TeamMember], table: PrettyTable):
    for tm in team_members:
        if args.map:
            latitude, longitude = getLocation(tm.city)
            staffLat.append(latitude)
            staffLon.append(longitude)
            labels.append(tm.name + " " + tm.time)

        if args.comp:
            localTime, remoteTime = compareTime(tm.timezone)
            table.add_row([tm.name, remoteTime, localTime])
        else:
            table.add_row([tm.name, tm.time])

with open(args.src, mode="r", encoding="utf-8", newline="") as infile:
    reader = csv.reader(infile)
    team_members = [TeamMember(row) for row in reader]

    if args.name:
        team_members = [tm for tm in team_members if tm.name == fixedName]

    build_table_rows(team_members, table)

if args.sort == "name":
    table.sortby = "Person"
else:
    if args.comp:
        table.sortby = "Their Time"
    else:
        table.sortby = "Local Time"
if args.rev:
    table.reversesort = True

with open("/dev/stdout", "w", encoding="utf-8") as stdout:
    stdout.write(str(table) + "\n")
if not args.map:
    quit()

# Convert lists to Pandas data frames
df = pd.DataFrame(
    list(zip(staffLat, staffLon, labels)), columns=["lat", "lon", "labels"]
)

# create the map
fig = go.Figure(
    data=go.Scattergeo(
        lon=df["lon"],
        lat=df["lat"],
        text=df["labels"],
        mode="markers",
        marker_size=12,
        marker_line_width=2,
    )
)

fig.update_layout(
    title="Team Time",
)

fig.show()
