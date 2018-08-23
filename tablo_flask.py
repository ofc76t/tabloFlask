# -*- coding: utf-8 -*-
from flask import Flask
from flask import request, render_template, url_for
from flask import Response, redirect, abort
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

import os
from tablo_class import *
#from tablo_settings import *
#from datetime import datetime
from tablo_html import add_headers_http, writeOutputScheduleToFile, uploadInfoText
from tablo_func import addCounter, resetCounter, listPromoFiles
from tablo_func import getPromoContent, dirForContenet, isSupportedType, changeType
from tablo_xml import parseSheduleXML
from tablo_configparser import readEtalonCfg, fromFormToType, saveConfig, determineValType

app = Flask(__name__)
#app.secret_key = flask_secret_key
app.config.from_pyfile('tablo_settings.py', silent=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# silly user model
class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = "admin"
        self.password = ''
users = [User(0)]
users[0].password = 'admin123'


refresh = app.config['PEFRESH_TABLO']
defaultIP = app.config['DEFAULT_IP']
speedScroll = app.config['SPEED_SCROLL']
speedJumpScroll = app.config['SPEED_JUMP_SCROLL']
scrollHeight = app.config['SCROLL_HEIGHT']
scrollMode = app.config['SCROLL_MODE']
screenStrLimit = app.config['SCREEN_STR_LIMIT']
scheduleFile = app.config['SCHEDULE_FILE']
outputFile = app.config['OUTPUT_FILE']
workDir = app.config['WORK_DIR']
promoAfter = app.config['PROMO_AFTER']
onPlatform = app.config['ON_PLATFORM']



#schedule = []
style = Style()

# уже не нужна? заменена на add_headers_http()
#def myHttpHead():
#    headStr = "Content-type: text/html; charset=utf-8\nRefresh: {0}; http://{1}{2}\n\n"
#    print(headStr.format(refresh, os.environ.get('HTTP_HOST', default=defaultIP), os.environ.get('SCRIPT_NAME',default='')))
#    return str(headStr.format(refresh, os.environ.get('HTTP_HOST', default=defaultIP), os.environ.get('SCRIPT_NAME',default='')))


def readHtmlFromFile():
    with open(os.path.join(workDir, outputFile), 'r', encoding="utf8") as myfile:
        data = myfile.read()
    return data


@app.route('/settings', methods=["GET", "POST"])
@login_required
def tabloSettings():
    # print('************** begin setting ********************')
    # for a in app.config:
    #     print('{} = {}  * {}'.format(a, app.config[a], type(app.config[a])))
    if request.method == 'POST':
        # print('==================================================================================')
        # print('=begin POST=')
        # viewClass(app.config)
        arrForm = []
        for i in request.form:
            x = {}
            x['key'] = i
            x['val'] = request.form[i]
            arrForm.append(x)
        oldCfg = readEtalonCfg(app.config)
        for new in arrForm:
            for old in oldCfg:
                if new['key'] == old['key']:
                    new['val_type'] = old['val_type']
                    new['val_type'] = determineValType(new['key'], app.config)
                    old['val'] = fromFormToType(new['val'], new['val_type'])
                    new['val'] = old['val']
        # for i in oldCfg:
        #     print('{} = {} # {}'.format(i['key'], i['val'], i['comment']))
        # for i in arrForm:
        #     print('{} = {} ****************'.format(i['key'], i['val']))
        for a in app.config:
            for new in arrForm:
                if a == new['key']:
                    app.config[a] = new['val']
        # print('=POST after SAVE=')
        # viewClass(app.config)
        saveConfig(oldCfg)
        # print('************** END setting ********************')
        # for a in app.config:
        #     print('{} = {}  * {}'.format(a, app.config[a], type(app.config[a])))
        return redirect(url_for('hello_world'))
    else:
        arr = readEtalonCfg(app.config)
        userCfg = []
        # viewClass(app.config)
        # print('************** GET setting ********************')
        # for a in app.config:
        #     print('{} = {}  * {}'.format(a, app.config[a], type(app.config[a])))
        for i in arr:
            if i['key'] in app.config['USER_AVAILABLE_PARAM']:
                if i['val_type'] == 'list':
                    i['val'] = str(i['val'])[1:-1].replace("'",'').replace('"','')
                userCfg.append(i)
        return render_template('settings.html', text='Настройки....', arr=userCfg)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == users[0].password:
            user = User(0)
            login_user(user)
            return redirect(url_for('hello_world'))
        else:
            return abort(401)
    else:
        return render_template('tablo_login.html')

# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('hello_world'))

# -------------VIDEO-------------------
@app.route("/upload_video", methods=['POST','GET'])
@login_required
def uploadVideo():
    if request.method == 'POST':
        fileType = 'video'
        text = uploadInfoText(fileType, app.config)
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            if not isSupportedType(filename, fileType, app.config):
                text += '<br> <strong>Неверный тип файла!</strong>'
            else:
                fileDir = dirForContenet(fileType, app.config)
                file.save(os.path.join(fileDir, filename))
                playTime = request.form['time']
                timeFile = os.path.join(fileDir, filename + '.time')
                with open(timeFile, 'w', encoding='utf-8') as f:
                    f.write(str(playTime))
                text += "<br> Файл <strong>{}</strong> успешно загружен.".format(filename)
            return render_template('upload.html', text=text, filetype=fileType)
        return render_template('upload.html', text='Ooopss....', filetype=fileType)
    else:
        fileType = 'video'
        text = uploadInfoText(fileType, app.config)
        return render_template('upload.html', text=text, filetype=fileType)


@app.route("/delete_video")
@login_required
def deleteVideo():
    fileName = request.args.get('name',default='')
    fileType = 'video'
    if fileName == '':
        arr = listPromoFiles(fileType, app.config)
        namearr = []
        for i in arr:
            namearr.append(os.path.basename(i))
        return render_template('delete__html.html', arr=namearr, file_type=fileType)
    else:
        os.remove(os.path.join(dirForContenet(fileType, app.config), fileName))
        try:
            os.remove(os.path.join(dirForContenet(fileType, app.config), fileName + '.time'))
        except:
            pass
        return redirect(url_for('deleteVideo') + '?type=video')


# -------------IMAGE-------------------
@app.route("/upload_image", methods=['POST','GET'])
@login_required
def uploadImage():
    fileType = 'image'
    if request.method == 'POST':
        text = uploadInfoText(fileType, app.config)
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            if not isSupportedType(filename, fileType, app.config):
                text += '<br> <strong>Неверный тип файла!</strong>'
            else:
                fileDir = dirForContenet(fileType, app.config)
                file.save(os.path.join(fileDir, filename))
                text += "<br> Файл <strong>{}</strong> успешно загружен.".format(filename)
            return render_template('upload.html', text=text, filetype=fileType)
        return render_template('upload.html', text='Ooopss....', filetype=fileType)
    else:
        text = uploadInfoText(fileType, app.config)
        return render_template('upload.html', text=text, filetype=fileType)


@app.route("/delete_image")
@login_required
def deleteImage():
    fileName = request.args.get('name',default='')
    fileType = 'image'
    if fileName == '':
        arr = listPromoFiles(fileType, app.config)
        namearr = []
        for i in arr:
            namearr.append(os.path.basename(i))
        return render_template('delete__html.html', arr=namearr, file_type=fileType)
    else:
        os.remove(os.path.join(dirForContenet(fileType, app.config), fileName))
        return redirect(url_for('deleteImage') + '?type=image')


# -------------HTML-------------------
@app.route("/upload_html", methods=['POST','GET'])
@login_required
def uploadHtml():
    if request.method == 'POST':
        fileType = request.form['filetype']
        text = uploadInfoText(fileType, app.config)
        # print(fileType)
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            fileDir = dirForContenet(fileType, app.config)
            file.save(os.path.join(fileDir, filename))
            text += "<br> Файл <strong>{}</strong> успешно загружен.".format(filename)
            return render_template('upload.html', text=text, filetype=fileType)
        return render_template('upload.html', text='Ooopss....', filetype=fileType)
    else:
        fileType = request.args.get('type', default='')
        text = uploadInfoText(fileType, app.config)
        return render_template('upload.html', text=text, filetype=fileType)


@app.route("/delete_html")
@login_required
def deleteHtml():
    fileName = request.args.get('name',default='')
    fileType = request.args.get('type',default='')
    if fileType == '':
        return abort(404)
    if fileName == '':
        arr = listPromoFiles(fileType, app.config)
        namearr = []
        for i in arr:
            namearr.append(os.path.basename(i))
        return render_template('delete__html.html', arr=namearr, file_type=fileType)
    else:
        os.remove(os.path.join(dirForContenet(fileType, app.config), fileName))
        return redirect(url_for('deleteHtml') + '?type={}'.format(fileType))


@app.errorhandler(401)
def noLogin(e):
    return render_template('tablo_login.html', login_error='Login failed!')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return User(userid)

@app.route('/')
def hello_world():
#    print(db.session)
#    print(app.config)
    return render_template('base.html')


#@app.route("/login", methods=["GET", "POST"])
#def login():
#    return render_template('tablo_login.html')


@app.route('/tablo')
def webSchedule():
 #   try:
        currentRequestNum = addCounter(request.remote_addr, app.config)
        if currentRequestNum > promoAfter:
            resetCounter(request.remote_addr, app.config)
            content, promoTime = getPromoContent(app.config)
            return (content, 200, add_headers_http(promoTime, request) )
        text = parseSheduleXML(app.config)
        writeOutputScheduleToFile(text, stringColor, style, app.config)
        # print(url_for('webSchedule'))
        return (readHtmlFromFile(), 200, add_headers_http(app.config['PEFRESH_TABLO'], request))
  #  except:
  #      return abort(404)

#def add_headers_http(response):
#    response.headers.add('Content-type','text/html; charset=utf-8')
#    response.headers.add('Refresh','10; http://127.0.0.1:5000/tablo')
#    return response



@app.errorhandler(404)
def page_not_found(e):
#    return '<html><body BGCOLOR="black"></body></html>', 404, add_headers_http(app.config['PEFRESH_TABLO'], request)
    newUrl = request.url_root + url_for('webSchedule')[1:]
#    print(newUrl)
    return render_template('title.html'), 404, add_headers_http(app.config['PEFRESH_TABLO'], request, redirect=newUrl)

if __name__ == '__main__':
    app.run(debug=True)
