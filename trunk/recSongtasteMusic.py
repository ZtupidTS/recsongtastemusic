#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------
【版本信息】
版本：     v1.0
作者：     crifan

【详细信息】
推荐Songtaste歌曲
recSongtasteMusic.py

【使用说明】
recSongtasteMusic.py -t 20120901-20121001

【TODO】

【版本历史】
[v1.0]
1. 完成基本功能，可以输出需要的html了。

-------------------------------------------------------------------------------
"""

#---------------------------------import---------------------------------------
import os;
import re;
import sys;
sys.path.append("libs/crifan");
sys.path.append("libs/thirdparty");
import math;
import time;
import codecs;
import logging;
import urllib;
from datetime import datetime,timedelta;
from optparse import OptionParser;
from string import Template,replace;
#import xml;
#from xml.sax import saxutils;
from BeautifulSoup import BeautifulSoup,Tag,CData;

import crifanLib;

#--------------------------------const values-----------------------------------
__VERSION__ = "v0.1";

gConst = {
    # songtaste html encode is GB2312
    'stHtmlEnc'    : "GB18030",
    # in allrec url, total 100 song per page
    'songNumPerPage'    : 100,
    
};

#----------------------------------global values--------------------------------
gVal = {
    # the main entry url of user's allrec in songtaste
    # eg: http://www.songtaste.com/user/351979/allrec
    # generated by input userId
    'allrecUrl'   : "",
    
    # songtaste user main url
    # eg: http://www.songtaste.com/user/351979/
    'userMainUrl'     : "",
    
    #songtaste user name
    'username'      : "",
    
    #all recommand song number
    'allrec'        : {
        'num'       : 0,
        'totalPage' : 0,
    },
    
    'timeSpan'      :{
        'start'         : "",
        'end'           : "",
        'startDateStr'  : "",
        'endDateStr'    : "",
    },
};

#--------------------------configurable values---------------------------------
gCfg ={
    # the user id in songtaste, default is crifan's songtaste user id
    'userId'      : "351979",
    # output file settings
    'outputFile'    : {
        'name'      : "",
        'encode'    : "UTF-8",
    },
    # if none, should use code to calc to latest one month
    'timeSpanStr'      : "",
};

#--------------------------functions--------------------------------------------

#------------------------------------------------------------------------------
# just print whole line
def printDelimiterLine() :
    logging.info("%s", '-'*80);
    return ;

#------------------------------------------------------------------------------
# output unicode string to file
def outputToFile(outpuStr):
    global gCfg;
    # 'a+': read,write,append
    # 'w' : clear before, then write
    outputFile = codecs.open(gCfg['outputFile']['name'], 'w', gCfg['outputFile']['encode']);
    if outputFile:
        logging.info('Created output file: %s', gCfg['outputFile']['name']);
        outputFile.write(outpuStr);
        outputFile.close();
    else:
        logging.error("Can not open writable output file: %s", gCfg['outputFile']['name']);
        sys.exit(2);
    return;

#------------------------------------------------------------------------------
# convert date time string into datetime delta value
def convertStrToDatetimeDelta(datetimeStr):
    logging.debug("datetimeStr=%s", datetimeStr);
    datetimeDelta = None;
    
    daysBefore = 0;
    hoursBefore = 0;
    minutesBefore = 0;
    secondsBefore = 0;

    #一个月0天前
    #一个月1天前
    #一个月26天前
    foundOneMonthDaysBefore = re.search(u"一个月(?P<oneMonthDaysBeforeNum>\d+)天前", datetimeStr);
    #<span class=date>7</span>天前
    foundDaysBefore = re.search(u"<span class=.?date.?>(?P<daysBeforeNum>\d+)</span>天前", datetimeStr);
    #<span class="date">1</span>小时前
    foundHourssBefore = re.search(u'<span class=.?date.?>(?P<hoursBeforeNum>\d+)</span>小时前', datetimeStr);
    #<span class=date>28</span>分钟前
    foundMinutesBefore = re.search(u"<span class=.?date.?>(?P<minutesBeforeNum>\d+)</span>分钟前", datetimeStr);
    #<span class=date>59</span>秒前
    foundSecondsBefore = re.search(u"<span class=.?date.?>(?P<secondsBeforeNum>\d+)</span>秒前", datetimeStr);
    
    if(foundOneMonthDaysBefore):
        oneMonthDaysBeforeNum = foundOneMonthDaysBefore.group("oneMonthDaysBeforeNum");
        oneMonthDaysBeforeNum = int(oneMonthDaysBeforeNum);
        oneMonthDaysBeforeNum = oneMonthDaysBeforeNum + 30;
        logging.debug("oneMonthDaysBeforeNum=%d", oneMonthDaysBeforeNum);
        daysBefore = oneMonthDaysBeforeNum;
    elif(foundDaysBefore):
        daysBeforeNum = foundDaysBefore.group("daysBeforeNum");
        daysBeforeNum = int(daysBeforeNum);
        logging.debug("daysBeforeNum=%d", daysBeforeNum);
        daysBefore = daysBeforeNum;
    elif(foundHourssBefore):
        hoursBeforeNum = foundHourssBefore.group("hoursBeforeNum");
        hoursBeforeNum = int(hoursBeforeNum);
        logging.debug("hoursBeforeNum=%d", hoursBeforeNum);
        hoursBefore = hoursBeforeNum;
    elif(foundMinutesBefore):
        minutesBeforeNum = foundMinutesBefore.group("minutesBeforeNum");
        minutesBeforeNum = int(minutesBeforeNum);
        logging.debug("minutesBeforeNum=%d", minutesBeforeNum);
        minutesBefore = minutesBeforeNum;
    elif(foundSecondsBefore):
        secondsBeforeNum = foundSecondsBefore.group("secondsBeforeNum");
        secondsBeforeNum = int(secondsBeforeNum);
        logging.debug("secondsBeforeNum=%d", secondsBeforeNum);
        secondsBefore = secondsBeforeNum;
    else:
        logging.error("Can not recognize datatime string: %s", datetimeStr);
        sys.exit(0);

    datetimeDelta = timedelta(days=daysBefore, hours=hoursBefore, minutes=minutesBefore, seconds=secondsBefore);
    logging.debug("datetimeDelta=%s", datetimeDelta);
    return datetimeDelta;
    
#------------------------------------------------------------------------------
# fetch and extract all song info from single allrec url
def extractSongInfoDictList(singleAllrecUrl):
    songInfoDictList = [];

    logging.debug("singleAllrecUrl=%s", singleAllrecUrl);
    respHtml = crifanLib.getUrlRespHtml(singleAllrecUrl);
    #logging.debug("respHtml=\n%s", respHtml);
    soup = BeautifulSoup(respHtml, fromEncoding=gConst['stHtmlEnc']);

    # findAllsong = soup.find(attrs={"class":"u_song_tab u_song_all"});
    # logging.debug("findAllsong=%s", findAllsong);
    #pretifiedHtml = soup.prettify(encoding=gCfg['outputFile']['encode']);
    #pretifiedHtml = soup.prettify();
    #pretifiedHtml = soup;
    pretifiedHtml = unicode(soup);
    #logging.info("type(pretifiedHtml)=%s", type(pretifiedHtml));
    #logging.debug("pretifiedHtml=%s", pretifiedHtml);
    
    #<table cellpadding="0" cellspacing="0" border="0" width="420" class="u_song_tab u_song_all">
    #...
    # <script>
    # ...
    # WL("1", "3055432","E.R‖＜拯救听觉 前奏一起就注定是极品＞丨 -- 忆の蓝色 ","<span class=date>6</span>天前");
    #...
    # </script>
    # </table>
    #foundAllWl = re.findall(r'WL\("\d+",\s*?"\d+",\s*?".+? -- .+? ",\s*?".+?"\);', pretifiedHtml);
    #foundAllWl = re.findall(r'WL\("\d+", "\d+",".+? -- .+? ",".+?"\);', pretifiedHtml);
    #foundAllWl = re.findall(r'WL\("\d+", "\d+",".+ -- .+ ",".+?"\);', pretifiedHtml);
    #foundAllWl = re.findall(r'WL\("\d+", "\d+",".+ -- .+ ",".+?"\);', pretifiedHtml);
    
    #WL("133", "255907","10.Two Moon Butterflies ","2012-01-02 16:21:18");
    foundAllWl = re.findall(r'WL\("\d+",\s*?"\d+",\s*?".+",\s*?".+?"\);', pretifiedHtml);
    foundAllWlNum = len(foundAllWl);
    #logging.info("foundAllWl=%s", foundAllWl);
    logging.info("foundAllWlNum=%d", foundAllWlNum);
    for singleWl in foundAllWl:
        #logging.info("singleWl=%s", singleWl);

        #extract all song info
        songInfoDict = {
            'number'        : "",
            'id'            : "",
            'title'         : "",
            'singer'        : "",
            'time'          : None, # finally will store datetime type value
        };

        # WL("26", "3080141","Lone Wanderer -- Rameses B ","<span class=date>24</span>天前");
        # WL("31", "3155354","泰语 我不会要求 -- Da Endorphine ","一个月0天前");
        # WL("35", "3154813","北京北京（中国好声音） -- 梁博 ft 黄勇 ","一个月1天前");
        # WL("73", "3048771","＜ 小漠 迟来生日快乐 ＞ 超赞大气的节奏 Ｓexy的嗓音 -- 羊氏 Ｃlub° ","一个月26天前");
        # WL("80", "3084927","Not Inveted Love -- Stan Crown ","2012-08-08 11:27:03");
        #foundSongInfo = re.search(r'WL\("(?P<number>\d+)",\s*?"(?P<id>\d+)",\s*?"(?P<title>.+?) -- (?P<singer>.+?) ",\s*?"(?P<time>.+?)"\);', singleWl);
        #WL("133", "255907","10.Two Moon Butterflies ","2012-01-02 16:21:18");
        foundSongInfo = re.search(r'WL\("(?P<number>\d+)",\s*?"(?P<id>\d+)",\s*?"(?P<title>.+?)( -- (?P<singer>.+?))? ",\s*?"(?P<time>.+?)"\);', singleWl);
        logging.debug("foundSongInfo=%s", foundSongInfo);
        if(foundSongInfo):
            songInfoDict['number']    = foundSongInfo.group("number");
            songInfoDict['id']        = foundSongInfo.group("id");
            songInfoDict['title']     = foundSongInfo.group("title");
            songInfoDict['singer']    = foundSongInfo.group("singer");
            
            if(not songInfoDict['singer']):
                logging.debug("singer is empty for %s", singleWl);
                #WL("254", "226169","妞子 - 郝爽 ","2009-01-09 15:33:13");
                #WL("255", "161306","Kate Havnevik-Solo ","2009-01-09 15:32:59");
                #WL("256", "341131","when you say nothing at all - Alison Krauss ","2009-01-09 15:32:34");
                
                #try parse the title into title and singer
                foundHyphen = re.search(r"(?P<subTitle>.+)\s*\-\s*(?P<subSinger>.+)", songInfoDict['title']);
                logging.debug("foundHyphen=%s", foundHyphen);
                if(foundHyphen):
                    subTitle = foundHyphen.group("subTitle");
                    subSinger = foundHyphen.group("subSinger");
                    subTitle = subTitle.strip();
                    subSinger = subSinger.strip();
                    if(subTitle and subSinger):
                        songInfoDict['title'] = subTitle;
                        songInfoDict['singer'] = subSinger;
                        logging.info("Extrat sub title and singer OK. subTitle=%s, subSinger=%s", subTitle, subSinger);
            
            datetimeStr = foundSongInfo.group("time");
            #logging.info("type(datetimeStr)=%s", type(datetimeStr)); # <type 'unicode'>
            convertedDatetime = None;
            
            #parse time to YYYY-MM-DD hh:mm:ss
            foundDatetime = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", datetimeStr);
            if(foundDatetime):
                convertedDatetime = datetime.strptime(datetimeStr, "%Y-%m-%d %H:%M:%S");
                logging.debug("type(convertedDatetime)=%s", type(convertedDatetime));
            else:
                curDatetime = datetime.now();
                logging.debug("curDatetime=%s", curDatetime);
                
                convertedDatetime = curDatetime - convertStrToDatetimeDelta(datetimeStr);
                logging.debug("convertedDatetime=%s", convertedDatetime);

            songInfoDict['time'] = convertedDatetime;
            logging.debug("songInfoDict=%s", songInfoDict);
            songInfoDictList.append(songInfoDict);
        else:
            logging.warning("Can not parse single song info string %s !", singleWl);
    return songInfoDictList;

#------------------------------------------------------------------------------
# generate songtaste user main url
def generateUserMainUrl(userId):
    userMainUrl = "http://www.songtaste.com/user/" + str(userId) + "/"; 
    return userMainUrl;

#------------------------------------------------------------------------------
# generate songtaste user allrec url
def generateAllrecUrl(userId, pageNum=1):
    if(pageNum > 1):
        allrecUrl = "http://www.songtaste.com/user/" + str(userId) + "/allrec/" + str(pageNum);
    else:
        allrecUrl = "http://www.songtaste.com/user/" + str(userId) + "/allrec";
    return allrecUrl;

#------------------------------------------------------------------------------
# generate output header
def generateOutputHeader(startDatetime, endDatetime):
    headerT = Template(u"""
<p>【歌曲批量推荐】${startDatetime} – ${endDatetime}</p>
<p>
  <table border="1" cellspacing="0" cellpadding="0" boarder="1">
    <tbody>
      <tr align="center">
        <td>
          <p><strong>歌曲名</strong></p>
        </td>

        <td>
          <p><strong>歌手</strong></p>
        </td>

        <td>
          <p><strong>Songtaste在线试听地址</strong></p>
        </td>

        <td>
          <p><strong>推荐感言</strong></p>
        </td>
      </tr>
""");#need startDatetime, endDatetime
    
    headerUni = headerT.substitute(startDatetime = startDatetime, endDatetime = endDatetime);
    logging.debug("headerUni=%s", headerUni);
    return headerUni;

#------------------------------------------------------------------------------
# generate output string for each song 
def generateSingleSongStr(songInfoDict):
    singleSongT = Template(u"""
      <tr>
        <td>
          <p>${title}</p>
        </td>

        <td>
          <p>${singer}</p>
        </td>

        <td>
          <p><a href="http://www.songtaste.com/song/${id}/" target="_blank">${title} - ${singer}</a></p>
        </td>

        <td>
          <p>Good</p>
        </td>
      </tr>
"""); # need title, singer, id
    
    singleSongUni = singleSongT.substitute(title = songInfoDict['title'], singer = songInfoDict['singer'], id=songInfoDict['id']);
    logging.debug("singleSongUni=%s", singleSongUni);
    return singleSongUni;

#------------------------------------------------------------------------------
def main():
    global gVal
    global gCfg

    # 0. main procedure begin
    parser = OptionParser();
    parser.add_option("-t","--timeSpanStr",action="store", type="string",dest="timeSpanStr",help=u"Time span/duration. eg:20120901-20121001");
    parser.add_option("-o","--outputFilename",action="store", type="string",dest="outputFilename",help=u"Output file name. default is recMusicHtml.txt");
    parser.add_option("-u","--userId",action="store", type="string",dest="userId",help=u"User's songtaste ID. default is crifan's user id: 351979");
    
    logging.info(u"版本信息：%s", __VERSION__);
    printDelimiterLine();
    
    (options, args) = parser.parse_args();
    for i in dir(options):
        exec(i + " = options." + i);
        
    if(userId):
        gCfg['userId'] = userId;
        
    gCfg['timeSpanStr'] = timeSpanStr;
    if(not gCfg['timeSpanStr']):
        # set default time span
        curDatetime = datetime.now();
        logging.info("curDatetime=%s", curDatetime);
        
        gVal['timeSpan']['start']   = curDatetime.replace(day=1);
        gVal['timeSpan']['end']     = curDatetime;
        
        gVal['timeSpan']['startDateStr']= datetime.strftime(gVal['timeSpan']['end'],    "%Y%m%d");
        gVal['timeSpan']['endDateStr']  = datetime.strftime(gVal['timeSpan']['start'],  "%Y%m%d");

        gCfg['timeSpanStr'] = gVal['timeSpan']['startDateStr'] + "-" + gVal['timeSpan']['endDateStr'];
        
        logging.info("Set defalt gVal['timeSpan']=%s", gVal['timeSpan']);
    else:
        #parse input time span string
        foundTimeSpanStr = re.search("(?P<startDateStr>(?P<startYear>\d{4})(?P<startMonth>\d{2})(?P<startDay>\d{2}))-(?P<endDateStr>(?P<endYear>\d{4})(?P<endMonth>\d{2})(?P<endDay>\d{2}))", gCfg['timeSpanStr']);
        logging.info("foundTimeSpanStr=%s", foundTimeSpanStr);
        if(foundTimeSpanStr):
             gVal['timeSpan']['startDateStr'] = foundTimeSpanStr.group("startDateStr");
             gVal['timeSpan']['endDateStr'] = foundTimeSpanStr.group("endDateStr");
             
             startYear  = int(foundTimeSpanStr.group("startYear"));
             startMonth = int(foundTimeSpanStr.group("startMonth"));
             startDay   = int(foundTimeSpanStr.group("startDay"));

             endYear    = int(foundTimeSpanStr.group("endYear"));
             endMonth   = int(foundTimeSpanStr.group("endMonth"));
             endDay     = int(foundTimeSpanStr.group("endDay"));
             
             gVal['timeSpan']['start']  = datetime(year=startYear,  month=startMonth,   day=startDay);
             gVal['timeSpan']['end']    = datetime(year=endYear,    month=endMonth,     day=endDay);
             logging.info("parsed gVal['timeSpan']=%s", gVal['timeSpan']);
        else:
            logging.error("Fail to parse the input time span str %s", gCfg['timeSpanStr']);
            sys.exit(2);
            
    if(outputFilename):
        gCfg['outputFile']['name'] = outputFilename;
    else:
        defaultFilename = str(gCfg['userId']) + u" 【歌曲批量推荐】" + gCfg['timeSpanStr'] + ".html";
        gCfg['outputFile']['name'] = defaultFilename;


    gVal['userMainUrl']   = generateUserMainUrl(gCfg['userId']);
    
    logging.info("Time span         = %s", gCfg['timeSpanStr']);
    logging.info("Output file name  = %s", gCfg['outputFile']['name']);
    logging.info("Songtaste user id = %s", gCfg['userId']);
    logging.info("User main url     = %s", gVal['userMainUrl']);
    
    respHtml = crifanLib.getUrlRespHtml(gVal['userMainUrl']);
    soup = BeautifulSoup(respHtml, fromEncoding=gConst['stHtmlEnc']);
    #extract user name
    #<h1 class="h1user">crifan</h1>
    foundH1user = soup.find(attrs={"class":"h1user"});
    logging.debug("foundH1user=%s", foundH1user);
    if(foundH1user):
        gVal['username'] = foundH1user.string;
        logging.info("Extracted songtaste username is %s", gVal['username']);
    else:
        logging.error("Cannot extract user name for songtaste main user url %s !", gVal['userMainUrl']);
        sys.exit(2);
    
    #extract total rec music number
    #<p class="more"><a href="/user/351979/allrec" class="underline">全部 306 首推荐</a></p>
    soupUni = unicode(soup);
    foundAllrecNum = re.search(u"全部 (?P<allrecNum>\d+) 首推荐", soupUni);
    logging.info("foundAllrecNum=%s", foundAllrecNum);
    if(foundAllrecNum):
        gVal['allrec']['num'] = foundAllrecNum.group("allrecNum");
        gVal['allrec']['num'] = int(gVal['allrec']['num']);
        logging.info("gVal['allrec']['num']=%d", gVal['allrec']['num']);
        gVal['allrec']['totalPage'] = gVal['allrec']['num']/gConst['songNumPerPage'];
        if((gVal['allrec']['num'] - gConst['songNumPerPage'] * gVal['allrec']['totalPage']) > 0):
            gVal['allrec']['totalPage'] += 1;
        logging.info("gVal['allrec']=%s", gVal['allrec']);

    # extract all song info dict list
    totalSongInfoDictList = [];
    for pageIdx in range(gVal['allrec']['totalPage']):
        pageNum = pageIdx + 1;
        singleAllrecUrl = generateAllrecUrl(gCfg['userId'], pageNum);
        logging.info("pageIdx=%d, pageNum=%d, singleAllrecUrl=%s", pageIdx, pageNum, singleAllrecUrl);
        singlePageSongInfoDictList = extractSongInfoDictList(singleAllrecUrl);
        logging.info("Current allrec page extracted %d songs info", len(singlePageSongInfoDictList));
        totalSongInfoDictList.extend(singlePageSongInfoDictList);
    
    logging.info("Total extracted song info number: %d", len(totalSongInfoDictList));
    
    #filter out the song within desiginated time span
    withinTimeSpanSongList = [];
    for singleSongDict in totalSongInfoDictList:
        if((singleSongDict['time'] >= gVal['timeSpan']['start']) and (singleSongDict['time'] <= gVal['timeSpan']['end'])):
            logging.info("found within time span time=%s", singleSongDict['time']);
            withinTimeSpanSongList.append(singleSongDict);
    
    #generate output
    outputUni = "";
    # generate header
    outputUni += generateOutputHeader(gVal['timeSpan']['startDateStr'], gVal['timeSpan']['endDateStr']);
    
    # generate each song info
    for singSongInfoDict in withinTimeSpanSongList:
        outputUni += generateSingleSongStr(singSongInfoDict);
    
    # generate tail
    
    outputToFile(outputUni);


###############################################################################
if __name__=="__main__":
    # for : python xxx.py -s yyy    # -> sys.argv[0]=xxx.py
    # for : xxx.py -s yyy           # -> sys.argv[0]=D:\yyy\zzz\xxx.py
    scriptSelfName = crifanLib.extractFilename(sys.argv[0]);

    logging.basicConfig(
                    level    = logging.DEBUG,
                    format   = 'LINE %(lineno)-4d  %(levelname)-8s %(message)s',
                    datefmt  = '%m-%d %H:%M',
                    filename = scriptSelfName + ".log",
                    filemode = 'w');
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler();
    console.setLevel(logging.INFO);
    # set a format which is simpler for console use
    formatter = logging.Formatter('LINE %(lineno)-4d : %(levelname)-8s %(message)s');
    # tell the handler to use this format
    console.setFormatter(formatter);
    logging.getLogger('').addHandler(console);
    try:
        main();
    except:
        logging.exception("Unknown Error !");
        raise;