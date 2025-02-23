# coding=utf-8

import datetime
import json
import locale
import os
import re
import sqlite3
import string
import time
import urllib.parse

import xbmc
import xbmcvfs 

OS_WINDOWS = "windows"
OS_ANDROID = "android"
OS_LINUX = "linux"
OS_XBOX = "xbox"
OS_IOS = "ios"
OS_DARWIN = "darwin"

REMOTE_SHARE_PATTERN = re.compile(r"^(smb|ftp|ftps|http|https|nfs):.+", re.IGNORECASE)

ENCODING = locale.getpreferredencoding()
if (ENCODING == None):
    ENCODING = 'UTF-8'


def getpreferredencoding():
    return ENCODING


def getOS():
    """
    Determines current operations system (OS) on which Kode is running. 

    return values are: "linux", "android", "windows", "xbox", "ios", "darwin"
    """

    if xbmc.getCondVisibility("system.platform.android"):

        return OS_ANDROID

    elif xbmc.getCondVisibility("system.platform.linux"):

        return OS_LINUX

    elif xbmc.getCondVisibility("system.platform.xbox"):

        return OS_XBOX

    elif xbmc.getCondVisibility("system.platform.windows"):

        return OS_WINDOWS

    elif xbmc.getCondVisibility("system.platform.ios"):

        return OS_IOS
    else:
        try:
            if platform.system() == "Darwin":

                return OS_DARWIN

        except:
            pass

        try:
            if "AppleTV" in platform.platform():

                return OS_IOS

        except:
            pass

    return None


def _lookup_db(dbName):

    database_dir = xbmc.translatePath("special://database")
    entries = os.listdir(database_dir)
    entries.sort()
    entries.reverse()
    for entry in entries:
        if entry.startswith(dbName) and entry.endswith(".db"):
            return "%s%s" % (database_dir, entry)

    return None


def _connect_db(db_file):

    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        xbmc.log(e, xbmc.LOGERROR)

    return conn


def select_bookmarks(strFilename):
    """
    Selects bookmarks from video database for the given filename

    Returns array with objects with following fields
    - idBookmark : int
    - timeInSeconds : int
    - timeInStr : str
    - totalTimeInSeconds : int
    - totalTimeInStr : int
    - thumbNailImage : str
    - strPath : str
    - strFilename : str
    """

    bookmarks = []

    dbFile = _lookup_db("MyVideos")
    if dbFile is None:
        return bookmarks

    conn = _connect_db(dbFile)
    if conn is None:
        return bookmarks

    cur = conn.cursor()
    cur.execute("""
        SELECT b.idBookmark, b.timeInSeconds, b.totalTimeInSeconds, b.thumbNailImage, p.strPath, f.strFilename
        FROM bookmark b
        INNER JOIN files f ON (f.idFile=b.idFile)
        INNER JOIN path p ON (f.idPath=p.idPath)
        WHERE p.strPath || f.strFilename = ?
        AND b.thumbNailImage <> ''
        ORDER BY b.timeInSeconds;
        """, (strFilename,))

    rows = cur.fetchall()
    for row in rows:
        bookmarks += [
            {
                "idBookmark": row[0],
                "timeInSeconds": int(row[1]),
                "timeInStr": seconds_to_time_str(row[1]),
                "totalTimeInSeconds": int(row[2]),
                "totalTimeInStr": seconds_to_time_str(row[2]),
                "thumbNailImage": row[3],
                "strPath": row[4],
                "strFilename": row[5]
            }
        ]

    return bookmarks


def delete_bookmarks(bookmarks):
    """
    Deletes bookmarks

    bookmarks parameter is an object with the following fields:
    - idBookmark : int
    - ...
    """

    dbFile = _lookup_db("MyVideos")
    if dbFile is None:
        return bookmarks

    conn = _connect_db(dbFile)
    if conn is None:
        return bookmarks

    cur = conn.cursor()
    for bookmark in bookmarks:
        cur.execute("DELETE FROM bookmark WHERE idBookmark = ?;",
                    (bookmark["idBookmark"],))
        thumbnail = xbmc.translatePath(bookmark["thumbNailImage"])
        if os.path.isfile(thumbnail):
            os.remove(thumbnail)

    conn.commit()


def parse_recording_from_pvr_url(pvrFilename):
    """
    Tries to parse kodi's internal url for recodings and returns
    - title
    - channelname
    - start time
    """

    pvrFilename = urllib.parse.unquote(pvrFilename)

    pattern = re.compile(
        "^pvr://recordings/tv/active/(.*/)*(.+), TV \((.+)\), (19[0-9][0-9]|20[0-9][0-9])([0-9][0-9])([0-9][0-9])_([0-9][0-9])([0-9][0-9])([0-9][0-9]), (.+)\.pvr$", flags=re.S)
    m = pattern.match(pvrFilename)

    record_datetime = datetime.datetime(int(m.group(4)), int(m.group(5)), int(
        m.group(6)), int(m.group(7)), int(m.group(8)), int(m.group(9)))
    epoche = (record_datetime - datetime.datetime(1970, 1, 1)).total_seconds()

    return m.group(2), m.group(3), epoche


def is_pvr_recording(url):
    """
    Checks if url belongs to pvr recording
    """

    pattern = re.compile("^pvr://recordings/.+\\.pvr$")
    return pattern.match(url) is not None


def seconds_to_time_str(secs):

    return time.strftime('%H:%M:%S', time.gmtime(secs))


def json_rpc(jsonmethod, params=None):

    kodi_json = {}
    kodi_json["jsonrpc"] = "2.0"
    kodi_json["method"] = jsonmethod

    if not params:
        params = {}

    kodi_json["params"] = params
    kodi_json["id"] = 1

    json_response = xbmc.executeJSONRPC(json.dumps(kodi_json))
    json_object = json.loads(json_response)

    result = None
    if "result" in json_object:
        return json_object['result']
    else:
        return None


def makeLegalFilename(filename):

    filename = xbmcvfs.makeLegalFilename(filename)
    if filename[-1:] == os.path.sep or filename[-1:] == "/":
        filename = filename[:-1]

    return filename


def is_remote_share(path):

    return REMOTE_SHARE_PATTERN.match(path) is not None


def make_path_for_smb_share_on_windows(path):

    if getOS() in [OS_WINDOWS, OS_XBOX]:
        path = path.replace("smb://", os.path.sep * 2).replace("/", os.path.sep)

    return path