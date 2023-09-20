#!/usr/bin/python3
import os,sys, tempfile, shutil
import tarfile
import time
import subprocess
from repomanager import RepoManager as repoman
from urllib.request import urlretrieve
from lliurex import lliurexup
import gettext
_ = gettext.gettext

TMPDIR="/tmp/llx-upgrade-release"
WRKDIR="/usr/share/llx-upgrade-release/"
REPODIR="/usr/share/llx-upgrade-release/repo"
LLXUPSCRIPT="/usr/share/lliurex-up/preActions/850-remove-comited"

def i18n(raw):
	imsg=({
		"ABORT":_("Operation canceled"),
		"ACCEPT":_("Accept"),
		"ASK":_("Update?"),
		"AVAILABLE":_("There's a new LliureX release"),
		"BEGIN":_("Upgrading Lliurex..."),
		"CANCEL":_("Cancel"),
		"DEFAULT":_("Default repositores will be resetted to Lliurex defaults.") ,
		"DISABLE":_("All configured repositories will be disabled."),
		"DISABLEREPOS":_("Disabling repos.."),
		"DISCLAIMER":_("This operation may destroy your system (or not)"),
		"DISCLAIMERGUI":_("This operation may destroy the system, proceed anyway"),
		"DISMISS":_("If you don't know what are you doing abort now"),
		"DOWNGRADE":_("¡¡UPGRADE FAILED!!. Wait while trying to recovery..."),
		"EXTRACT":_("Extracting upgrade files.."),
		"IMPORTANT":_("IMPORTANT"),
		"LASTCHANCE":_("This is the last chance for aborting. Don't poweroff the computer nor interrupt this process in any way."),
		"PENDING":_("There're updates available. Install them before continue."),
		"PRAY":_("This is catastrophical.<br>Upgrader has tried to revert Lliurex-Up to original state"),
		"PRAY2":_("The upgraded failed.<br>Call a technical assistant and try to manually downgrade through Lliurex-Up"),
		"PRESS":_("Press a key for launching Lliurex-Up"),
		"READ":_("Read carefully all the info showed in the screen"),
		"REBOOT":_("System will reboot now to the new LliureX Release."), 
		"REBOOT2":_("System is under big failure. Press CANCEL to begin system rescue."),
		"REBOOT3":_("Call a technical assistant."),
		"RECOM":_("As result of this aborted upgrade may appear some problems with package management. Run lliurex-up now."),
		"REPOS":_("All repositories configured in this system will be deleted."),
		"REVERT":_("Reverting repositories to previous state"),
		"ROOT":_("Must be root"),
		"SETTINGUP":_("Setting up things. Be patient..."),
		"UNDO":_("This operation could not be reversed"),
		"UPGRADE":_("Setting info for lliurex-up")})
	return(imsg.get(raw,raw))

def processMetaRelease(meta):
	content={}
	dist={}
	for line in meta:
		if "UpgradeToolSignature" in line:
			dist["UpgradeToolSignature"]=line.strip()
		elif "UpgradeTool" in line:
			dist["UpgradeTool"]=line.strip()
		elif "ReleaseNotesHtml" in line:
			dist["ReleaseNotesHtml"]=line.strip()
		elif "ReleaseNotes" in line:
			dist["ReleaseNotes"]=line.strip()
		elif "Release-File" in line:
			dist["Release-File"]=line.strip()
		elif "Description" in line:
			dist["Description"]=line.strip()
		elif "Supported" in line:
			dist["Supported"]=line.strip()
		elif "Date" in line:
			dist["Date"]=line.strip()
		elif "Version" in line:
			dist["Version"]=line.strip()
		elif "Name" in line:
			dist["Name"]=line.strip()
		elif "Dist" in line:
			if len(dist.get("Dist",""))>0:
				content[dist["Dist"]]=dist
				dist={}
			dist["Dist"]=line.strip()
	content[dist["Dist"]]=dist
	return(content)
#def processMetaRelease

def chkReleaseAvailable(metadata):
	cmd=["lliurex-version","-n"]
	cmdOutput=subprocess.check_output(cmd,encoding="utf8").strip()
	majorCurrent=cmdOutput.split(".")[0]
	upgradeTo={}
	for release,releasedata in metadata.items():
		version=releasedata.get("Version","").split(":")[1].strip()
		majorNext=version.split(".")[0]
		upgradeTo=releasedata
		if (str(majorNext) > str(majorCurrent)):
			upgradeTo=releasedata
			break
	return(upgradeTo)
#def chkReleaseAvailable

def upgradeCurrentState():
	#check state of current release
	llxup=lliurexup.LliurexUpCore()
	update=llxup.getPackagesToUpdate()
	if len(update)>0:
		return True
	return False
#def upgradeCurrentState

def prepareFiles(metadata):
	tools=downloadFile(metadata["UpgradeTool"].replace("UpgradeTool: ",""))
	return(tools)
#def prepareFiles(metadata):

def _generateDemoteScript():
	if os.path.isfile("{}/demote.cfg".format(TMPDIR))==True:
		demote=[]
		with open("{}/demote.cfg".format(TMPDIR),"r") as f:
			for line in f.readlines():
				if len(line.strip())>0:
					demote.append(line.strip())
		if len(demote)>0:
			fcontent="#!/bin/bash\n"
			fcontent+="ACTION=\"$1\"\n"
			fcontent+="case \"$ACTION\" in\n" 
			fcontent+="preActions)\n"
			fcontent+="dpkg --force-all --purge {} || true\n".format(" ".join(demote))
			fcontent+="apt-get install -f -y\n"
			fcontent+="rm $0\n"
			fcontent+="\n;;\nesac"
		with open(LLXUPSCRIPT,"w") as f:
			f.write(fcontent)
		os.chmod(LLXUPSCRIPT,0o755)
#def _generateDemoteScript

def enableUpgradeRepos(tools):
	try:
		with tarfile.open(tools) as tar:
			tar.extractall(path=TMPDIR)
	except Exception as e:
		print(e)
	shutil.copy("{}/sources.list".format(TMPDIR),"/etc/apt/sources.list")
	_generateDemoteScript()
	return()
#def enableUpgradeRepos(tools):

#def enableUpgradeRepos(tools):

def restoreRepos():
	ftar="/tmp/data.tar"
	if os.path.isfile(ftar)==False:
		return
	try:
		with tarfile.open(ftar) as tar:
			tar.extractall(path=TMPDIR)
	except Exception as e:
		print("Untar: {}".format(e))
	wrkdir=os.path.join(TMPDIR,"etc/apt")
	shutil.copy("{}/sources.list".format(wrkdir),"/etc/apt/sources.list")
	if os.path.isdir("{}/sources.list.d".format(wrkdir)):
		for f in os.listdir("{}/sources.list.d".format(wrkdir)):
			if f.endswith(".list"):
				shutil.copy("{0}/sources.list.d/{1}".format(wrkdir,f),"/etc/apt/sources.list.d/{}".format(f))
	if os.path.isfile(LLXUPSCRIPT):
		os.unlink(LLXUPSCRIPT)
#def restoreRepos

def downgrade():
	#Update info
	cmd=["apt-get","update"]
	time.sleep(10)
	subprocess.run(cmd)
	#Get old version
	cmd=["apt-cache","policy","lliurex-up"]
	cmdOutput=subprocess.check_output(cmd,encoding="utf8").strip()
	line=""
	for out in cmdOutput.split("\n"):
		if "://" in out:
			break
		line=out
	uprelease=line.strip().split()[0]
	cmd=["apt-get","install","-y","--allow-downgrades","--reinstall","lliurex-up={}".format(uprelease), "lliurex-up-core={}".format(uprelease), "lliurex-up-cli={}".format(uprelease), "lliurex-up-indicator={}".format(uprelease),"python3-lliurexup={}".format(uprelease)]
	subprocess.run(cmd)
#def downgrade()

def _getValuesForLliurexUp():
	data={"url":"http://lliurex.net/jammy","mirror":"llx23","version":"jammy"}
	with open("/etc/apt/sources.list") as f:
		for line in f.readlines():
			l=line.strip().split()
			for item in l:
				if "://" in item:
					data["url"]=item
					data["version"]=os.path.basename(item)
					break
	return(data)
#def _getValuesForLliurexUp

def launchLliurexUp():
	#data=_getValuesForLliurexUp()
	#llxup=lliurexup.LliurexUpCore()
	#llxup.defaultUrltoCheck=data.get("url")
	#llxup.defaultVersion=data.get("version")
	#llxup.installLliurexUp()
	a=open("/var/run/disableMetaProtection.token","w")
	a.close()
	cmd=["/bin/bash","-c","/usr/sbin/lliurex-up","-s","-n"]
	out=subprocess.run(cmd)
	return(out)
#def launchLliurexUp

def launchLliurexUpgrade():
	#data=_getValuesForLliurexUp()
	#llxup=lliurexup.LliurexUpCore()
	#llxup.defaultUrltoCheck=data.get("url")
	#llxup.defaultVersion=data.get("version")
	#llxup.installLliurexUp()
	a=open("/var/run/disableMetaProtection.token","w")
	a.close()
	cmd=["/bin/bash","-c","/usr/sbin/lliurex-upgrade","-s","-n"]
	out=subprocess.run(cmd)
	return(out)
#def launchLliurexUpgrade
		
def disableRepos():
	copySystemFiles()
	manager=repoman.manager()
	for repo,data in manager.list_sources().items():
		repos={}
		repos[repo]=data
		repos[repo]['enabled']='false'
		manager.write_repo_json(repos)
		manager.write_repo(repos)
#def disableRepos

def downloadFile(url):
	meta=os.path.basename(url)
	meta=os.path.join(TMPDIR,meta)
	if os.path.isdir(TMPDIR)==False:
		os.makedirs(TMPDIR)
	if os.path.isfile(meta):
		os.unlink(meta)
	try:
		urlretrieve(url, meta)
	except Exception as e:
		print(url)
		print(e)
		sys.exit(1)
	return(meta)
#def downloadFile

def copySystemFiles():
	if os.path.isfile("/tmp/data.tar"):
		os.unlink("/tmp/data.tar")
	with tarfile.open("/tmp/data.tar","w") as tarf:
		tarf.add("/etc/apt/sources.list")
		tarf.add("/etc/apt/sources.list.d/")
#def copySystemFiles

def _modifyAptConf():
	aptconf="/etc/apt/apt.conf"
	if os.path.isfile(aptconf)==True:
		shutil.copy(aptconf,TMPDIR)
	if os.path.isdir(REPODIR)==False:
		os.makedirs(REPODIR)
	with open(aptconf,"w") as f:
		f.writelines(["Dir::Cache{Archives /usr/share/llx-upgrade-release/repo/}","Dir::Cache::Archives /usr/share/llx-upgrade-release/repo;"])
#def _modifyAptConf

def setLocalRepo():
	sources="/etc/apt/sources.list"
	with open(sources,"w") as f:
		f.write("deb file:{} ./".format(REPODIR))
#def setLocalRepo

def downloadPackages():
	_modifyAptConf()
	cmd=["apt-get","update"]
	subprocess.run(cmd)
	cmd=["apt-get","clean"]
	subprocess.run(cmd)
	cmd=["apt-get","dist-upgrade","-d","-y"]
	subprocess.run(cmd)
	if os.path.isfile(os.path.join(TMPDIR,"apt.conf")):
		shutil.copy(os.path.join(TMPDIR,"apt.conf"),"/etc/apt")
	else:
		os.unlink(os.path.join("/etc/apt/apt.conf"))
#def downloadPackages

def generateLocalRepo():
	cmd=["dpkg-scanpackages",REPODIR]
	cmdOutput=subprocess.check_output(cmd,encoding="utf8").strip()
	line=""
	with open(os.path.join(REPODIR,"Packages"),"w") as f:
		f.write(cmdOutput)
#def generateLocalRepo

def setSyemdUpgradeTarget():
	systemdpath="/usr/lib/systemd/system"
	target=os.path.join(systemdpath,"llx-upgrade.target")
	service=os.path.join(systemdpath,"llx-upgrade.service")
	targetContent=["[Unit]","Description=Upgrade Mode","Documentation=man:systemd.special(7)","Requires=llx-upgrade.service","After=llx-upgrade.service","AllowIsolate=yes"]
	with open (target,"w") as f:
		f.writelines(targetContent)
	unitContent=["[Unit]","Description=Upgrade environment","Documentation=man:sulogin(8)","DefaultDependencies=no","Conflicts=shutdown.target","Conflicts=llx-upgrade.service","Before=shutdown.target","Before=llx-upgrade.service"]
	serviceContent=["[Service]","Environment=HOME=/root","Environment=QT_QPA_PLATFORMTHEME=linuxfb","WorkingDirectory=-/root","ExecStartPre=-/bin/plymouth --wait quit","ExecStart=-/usr/share/llx-upgrade-release/upgrader.py","Type=idle","StandardInput=tty-force","StandardOutput=inherit","StandardError=inherit","KillMode=process","IgnoreSIGPIPE=no","SendSIGHUP=yes"]
	with open (service,"w") as f:
		f.writelines(unitContent)
		f.write("\n")
		f.writelines(serviceContent)
#def setSyemdUpgradeTarget

def unsetSyemdUpgradeTarget():
	systemdpath="/usr/lib/systemd/system"
	target=os.path.join(systemdpath,"llx-upgrade.target")
	service=os.path.join(systemdpath,"llx-upgrade.service")
	if os.path.isfile(target):
		os.unlink(target)
	if os.path.isfile(service):
		os.unlink(service)
#def unsetSyemdUpgradeTarget

def chkUpgradeResult():
	pass
	
#def chkUpgradeResult

