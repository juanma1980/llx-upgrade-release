#!/usr/bin/python3

import os,subprocess,shutil,time
from http.server import BaseHTTPRequestHandler, HTTPServer
from PySide2.QtWidgets import QApplication, QWidget,QLabel,QGridLayout
from PySide2 import QtGui
from PySide2.QtCore import Qt,QThread,QObject,Signal
import llxupgrader
from lliurex import lliurexup

class Watchdog(QThread):
	def __init__(self,parent=None):
		super (Watchdog,self).__init__(parent)
		self.file="/var/run/lliurex-up/sourceslist/default"

	def run(self):
		while os.path.isfile(self.file)==False:
			time.sleep(0.1)
		shutil.copy("/etc/apt/sources.list",self.file)
#class Watchdog

class Launcher(QThread):
	processEnd=Signal(str,subprocess.CompletedProcess)
	def __init__(self,parent=None):
		super (Launcher,self).__init__(parent)
		self.cmd=[]
		self.check_output=False
		self.universal_newlines=True
		self.encoding="utf8"
	#def __init__

	def setCmd(self,cmd):
		if isinstance(cmd,str):
			self.cmd=cmd.split()
		elif isinstance(cmd,[]):
			self.cmd=cmd
	#def setCmd

	def run(self):
		print("Launching {}".format(self.cmd))
		prc=subprocess.run(self.cmd,universal_newlines=self.universal_newlines,encoding=self.encoding,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		self.processEnd.emit(" ".join(self.cmd),prc)
	#def run
#class Launcher

class Server(BaseHTTPRequestHandler):
	def do_GET(self):
		self.send_response(200)
		self.send_header("Content-type","text/ascii")
		self.end_headers()
		wrkfile="/usr/share/llx-upgrade-release/files/Release"
		if os.path.isfile(wrkfile)==True:
			if os.path.basename(self.path)=="Release":
			#	if "jammy-updates" in self.path:
			#		with open("{}_up".format(wrkfile),"rb") as file:
			#			self.wfile.write(file.read())
			#	if "jammy-security" in self.path:
			#		with open("{}_se".format(wrkfile),"rb") as file:
			#			self.wfile.write(file.read())
			#	else:
				with open(wrkfile,"rb") as file:
					self.wfile.write(file.read())
	#def do_GET
#class Server

class QServer(QThread):
	def __init__(self,parent=None):
		super (QServer,self).__init__(parent)
		self.hostname="localhost"
	#def __init__

	def run(self):
		serverport=80
		try:
			print("SERVER READY")
			web=HTTPServer((self.hostname,serverport),Server)
			web.serve_forever()
		except Exception as e:
			print("***********")
			print(e)
			print("***********")
		finally:
			print("server closed")
	#def run(self):
#class QServer

class qupgrader(QWidget):
	def __init__(self,parent=None):
		super (qupgrader,self).__init__(parent)
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.setWindowFlags(Qt.X11BypassWindowManagerHint)
		self.setWindowState(Qt.WindowFullScreen)
		self.setWindowFlags(Qt.WindowStaysOnBottomHint)
		#self.setWindowModality(Qt.WindowModal)
		self.img="/usr/share/llx-upgrade-release/rsrc/1024x768.jpg"
		self.wrkdir="/usr/share/llx-upgrade-release"
		self.tmpdir=os.path.join(self.wrkdir,"tmp")
		if os.path.isdir(self.tmpdir)==False:
			os.makedirs(self.tmpdir)
		self.lbl=QLabel()
		self.qserver=QServer()
		self.processDict={}
		self.noreturn=1
	#def __init__

	def renderBkg(self):
		lay=QGridLayout()
		self.setLayout(lay)
		self.lbl.setPixmap(self.img)
		self.lbl.setScaledContents(True)
		lay.addWidget(self.lbl)
		self.show()
	#def renderBkg

	def closeEvent(self,event):
		if self.noreturn==1:
			event.ignore()
	#def closeEvent

	def doFixes(self):
		llxupgrader.fixAptSources()
		ln=Launcher()
		cmd="/usr/bin/kwin --replace"
		ln.setCmd(cmd)
		ln.processEnd.connect(self._processEnd)
		ln.start()
		self.processDict[cmd]=ln
		self.fakeLliurexNet()
		self.launchLlxUp()

		wd=Watchdog()
		wd.start()
		self.processDict["wd"]=wd
		llxupgrader.disableSystemdServices()
	#def doFixes

	def launchLlxUp(self):
		cmd='/sbin/lliurex-up -u -s -n'
		ln=Launcher()
		ln.setCmd(cmd)
		ln.processEnd.connect(self._processEnd)
		with open("/etc/hosts","a") as f:
			f.write("\n")
		ln.start()
		self.processDict[cmd]=ln
	#def launchLlxUp

	def fakeLliurexNet(self):
		llxupgrader._enableIpRedirect()
		llxupgrader._modHosts()
		llxupgrader._modHttpd()
		llxupgrader._disableMirror()
		print("LAUNCH")
		self.qserver.start()
	#def fakeLliurexNet

	def _processEnd(self,prc,prcdata):
		err=True
		if "lliurex-up" in prc.lower():
			#self.processDict[prc].wait()
			print("ENDED: {}".format(prcdata))
			if prcdata.returncode==0:
				if len(llxupgrader.getPkgsToUpdate())==0:
					err=False
			if err==True:
				if prcdata.returncode!=0:
					self._relaunchLlxUp()
				else:
					self._errorMode()
			else:
				self._undoFixes()
				self.showEnd()
		print("END")
	#def _processEnd

	def _relaunchLlxUp(self):
		a=lliurexup.LliurexUpCore()
		a.cleanEnvironment()
		a.cleanLliurexUpLock()
		cmd='/sbin/lliurex-up -u -s -n'
		ln=Launcher()
		ln.setCmd(cmd)
		ln.processEnd.connect(self._processEnd)
		ln.start()
		self.processDict[cmd]=ln
	#def _relaunchLlxUp

	def showEnd(self):
		cmd=["kdialog","--title","Lliurex Release Upgrade","--msgbox","Upgrade ended. Press to reboot".format(llxupgrader.i18n("UPGRADEEND"))]
		subprocess.run(cmd)
		cmd=["systemctl","reboot"]
		subprocess.run(cmd)
	#def showEnd

	def _undoFixes(self):
		llxupgrader.unfixAptSources()
		llxupgrader.removeAptConf()
		llxupgrader.undoHostsMod()
		llxupgrader.clean()
		llxupgrader.unsetSystemdUpgradeTarget()
		llxupgrader.cleanLlxUpActions()
	#def _undoFixes()

	def _errorMode(self):
		ln=Launcher()
		cmd=os.path.join(self.wrkdir,"qrescuer.py")
		ln.setCmd(cmd)
		ln.start()
		ln.processEnd.connect(self._endErrorMode)
		self.processDict[cmd]=ln
	#def _errorMode

	def _endErrorMode(self,prc,prcdata):
		if prcdata.returncode!=0:
			cmd=["/usr/bin/konsole"]
			subprocess.run(cmd)
		self._undoFixes()
		self.showEnd()
	#def _endErrorMode
#def qupgrader(self):
		
app=QApplication(["Llx-Upgrader"])
if __name__=="__main__":
	qup=qupgrader()
	qup.renderBkg()
	qup.doFixes()
app.exec_()

