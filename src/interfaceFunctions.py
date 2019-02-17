"""
***********************************************************
File: interfaceFunctions.py
Author: Luke Burks
Date: April 2018

Provides primary accessible functions for the backend of 
interface.py

***********************************************************
"""


__author__ = "Luke Burks"
__copyright__ = "Copyright 2018"
__credits__ = ["Luke Burks"]
__license__ = "GPL"
__version__ = "0.2.0"
__maintainer__ = "Luke Burks"
__email__ = "luke.burks@colorado.edu"
__status__ = "Development"

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import *; 
from PyQt5.QtGui import *;
from PyQt5.QtCore import *;

import sys
import numpy as np
from scipy.spatial import ConvexHull
import time

from planeFunctions import *;
from helpers import Timer

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure, SubplotParams
import matplotlib.pyplot as plt
from shapely.geometry import Polygon,Point
import shapely
from copy import copy,deepcopy


#Converts a gaussian mixture belief to an image in the belief tab
def makeBeliefMap(wind):

	[x,y,c] = wind.assumedModel.belief.plot2D(low=[0,0],high=[wind.imgWidth,wind.imgHeight],vis=False);
	sp = SubplotParams(left=0.,bottom=0.,right=1.,top=1.); 
	fig = Figure(subplotpars=sp); 
	canvas = FigureCanvas(fig); 
	ax = fig.add_subplot(111); 
	ax.contourf(np.transpose(c),cmap='viridis',alpha=1); 
	ax.invert_yaxis(); 
	ax.set_axis_off(); 

	canvas.draw(); 

	#canvas = makeBeliefMap(wind); 
	size = canvas.size(); 
	width,height = size.width(),size.height(); 
	im = QImage(canvas.buffer_rgba(),width,height,QtGui.QImage.Format_ARGB32); 
	im = im.rgbSwapped(); 
	pm = QPixmap(im); 
	pm = pm.scaled(wind.imgWidth,wind.imgHeight);
	paintPixToPix(wind.beliefLayer,pm,wind.beliefOpacitySlider.sliderPosition()/100);   


	#return canvas; 

#Converts a transition or cost model to an image
def makeModelMap(wind,layer):
	sp = SubplotParams(left=0.,bottom=0.,right=1.,top=1.); 
	fig = Figure(subplotpars=sp); 
	canvas = FigureCanvas(fig); 
	ax = fig.add_subplot(111); 
	ax.contourf(np.transpose(layer),cmap='seismic',vmin=-10,vmax=10);
	ax.set_axis_off(); 

	canvas.draw(); 
	size=canvas.size(); 
	width,height = size.width(),size.height(); 
	im = QImage(canvas.buffer_rgba(),width,height,QtGui.QImage.Format_ARGB32); 
	im = im.mirrored(vertical=True);

	pm = QPixmap(im); 
	pm = pm.scaled(wind.imgWidth,wind.imgHeight); 
	return pm; 

def convertPixmapToGrayArray(pm):
	channels_count = 4
	image = pm.toImage()
	s = image.bits().asstring(437 * 754 * channels_count)
	arr = np.fromstring(s, dtype=np.uint8).reshape((754, 437, channels_count))

	r,g,b = arr[:,:,0],arr[:,:,1],arr[:,:,2]; 
	gray = 0.2989*r+0.5870*g+0.1140*b; 

	return np.amax(gray)-gray.T; 


def moveRobot(wind,eventKey=None): 

	#place the breadcrumbs
	wind.trueModel.prevPoses.append(copy(wind.trueModel.copPose)); 



	nomSpeed = wind.trueModel.ROBOT_NOMINAL_SPEED; 
	if(eventKey is not None):
		if(eventKey == QtCore.Qt.Key_Up):
			delta = int(wind.trueModel.transitionEval([wind.trueModel.copPose[0],wind.trueModel.copPose[1]-nomSpeed])); 
			if(nomSpeed+delta < 0):
				speed = 0; 
			else:
				speed = nomSpeed + delta; 
			wind.trueModel.copPose[1] = wind.trueModel.copPose[1] - speed; 
		elif(eventKey == QtCore.Qt.Key_Left):
			delta = int(wind.trueModel.transitionEval([wind.trueModel.copPose[0]-nomSpeed,wind.trueModel.copPose[1]])); 
			if(nomSpeed+delta < 0):
				speed = 0; 
			else:
				speed = nomSpeed + delta;
			wind.trueModel.copPose[0] = wind.trueModel.copPose[0] - speed;
		elif(eventKey == QtCore.Qt.Key_Down):
			delta = int(wind.trueModel.transitionEval([wind.trueModel.copPose[0],wind.trueModel.copPose[1]+nomSpeed]));
			if(nomSpeed+delta < 0):
				speed = 0; 
			else:
				speed = nomSpeed + delta; 
			wind.trueModel.copPose[1] = wind.trueModel.copPose[1] + speed; 
		elif(eventKey == QtCore.Qt.Key_Right):
			delta = int(wind.trueModel.transitionEval([wind.trueModel.copPose[0]+nomSpeed,wind.trueModel.copPose[1]])); 
			if(nomSpeed+delta < 0):
				speed = 0; 
			else:
				speed = nomSpeed + delta; 
			wind.trueModel.copPose[0] = wind.trueModel.copPose[0] + speed;

	# if(wind.REPLAY_FILE != 'None'):
	# 	print(wind.trueModel.copPose,wind.replayData['CopPoses'][wind.timeStamp])
	# 	wind.trueModel.copPose = wind.replayData['CopPoses'][wind.timeStamp]; 
		

	wind.assumedModel.copPose = wind.trueModel.copPose;
	wind.assumedModel.prevPoses = wind.trueModel.prevPoses; 

	wind.trueModel.stateDynamicsUpdate(); 
	wind.assumedModel.stateDynamicsUpdate(); 


	if(wind.REPLAY_FILE != 'None' and wind.timeStamp < wind.replayTime):
		#Fix Robber Pose
		wind.trueModel.robPose = wind.replayData['RobPoses'][wind.timeStamp]; 

		#Introduce Sketches
		if(wind.replayData['Sketches'][wind.timeStamp] is not None):
			wind.allSketchPaths.append(wind.replayData['Sketches'][wind.timeStamp][1]); 
			name = wind.replayData['Sketches'][wind.timeStamp][0]; 
			if(name not in wind.allSketchPlanes.keys()):
				wind.allSketchPlanes[name] = wind.imageScene.addPixmap(makeTransparentPlane(wind));
				wind.objectsDrop.addItem(name);
				wind.allSketchNames.append(name); 
			else:
				planeFlushPaint(wind.allSketchPlanes[name],[]);

			wind.currentSketch = [name,wind.allSketchPaths[-1]]; 
			wind.allSketches[name] = wind.allSketchPaths[-1]; 
			wind.sketchListen = False; 
			wind.sketchingInProgress = False; 
			makeModel(wind,name);

		#Give Push Obs
		if(wind.replayData['PushObservations'][wind.timeStamp] is not None):
			[name,rel,pos] = wind.replayData['PushObservations'][wind.timeStamp];
			wind.assumedModel.stateObsUpdate(name,rel,pos); 

		wind.timeStamp += 1; 


	# if(not wind.sketchingInProgress):
	movementViewChanges(wind);
	if(len(wind.trueModel.prevPoses) > wind.trueModel.BREADCRUMB_TRAIL_LENGTH):
		wind.trueModel.prevPoses = wind.trueModel.prevPoses[1:];  
	planeFlushColors(wind.trailLayer,wind.trueModel.prevPoses,wind.breadColors); 

	if(len(wind.assumedModel.prevPoses) > 1):
		change = False

		change = wind.assumedModel.stateLWISUpdate(); 
		if(change):
			a = 0; 
			#wind.tabs.removeTab(0); 
			#a = 0; 
			#makeBeliefMap(wind); 
			#print(wind.beliefOpacitySlider.sliderPosition()); 
			# canvas = makeBeliefMap(wind); 
			# size = canvas.size(); 
			# width,height = size.width(),size.height(); 
			# im = QImage(canvas.buffer_rgba(),width,height,QtGui.QImage.Format_ARGB32); 
			# pm = QPixmap(im); 
			# pm = pm.scaled(wind.imgWidth,wind.imgHeight);
			# paintPixToPix(wind.beliefLayer,pm);   


			#wind.beliefMapWidget = pm; 
			#wind.tabs.insertTab(0,wind.beliefMapWidget,'Belief');
			#wind.tabs.setCurrentIndex(0);   
	if(wind.TARGET_STATUS=='loose'):
		checkEndCondition(wind); 

	# if(wind.SAVE_FILE is not None):
	# 	updateSavedModel(wind); 


# def updateSavedModel(wind):
# 	mod = wind.assumedModel; 

# 	mod.history['beliefs'].append(deepcopy(mod.belief));
# 	mod.history['positions'].append(deepcopy(mod.copPose)); 
# 	mod.history['sketches'] = mod.sketches; 

# 	if(len(wind.lastPush) > 0):
# 		mod.history['humanObs'].append(wind.lastPush); 
# 		wind.lastPush = [];
# 	else:
# 		mod.history['humanObs'].append([]); 

# 	np.save(wind.SAVE_FILE,[mod.history]); 



def paintTargetEnd(wind):
	points = []; 
	rad = wind.trueModel.TARGET_SIZE_RADIUS; 
	for i in range(-int(rad/2)+wind.trueModel.robPose[0],int(rad/2)+wind.trueModel.robPose[0]):
		for j in range(-int(rad/2) + wind.trueModel.robPose[1],int(rad/2)+wind.trueModel.robPose[1]):
			#if(i>0 and j>0 and i<wind.imgHeight and j<wind.imgWidth):
			tmp1 = min(wind.imgWidth-1,max(0,i)); 
			tmp2 = min(wind.imgHeight-1,max(0,j)); 
			points.append([tmp1,tmp2]); 
	planeAddPaint(wind.fogPlane,points,QColor(255,0,255,255)); 


def checkEndCondition(wind):
	if(distance(wind.trueModel.copPose,wind.trueModel.robPose) < wind.trueModel.ROBOT_CATCH_RADIUS):
		wind.collectAndSaveData(); 
		np.save(wind.DATA_SAVE,wind.runData); 
		wind.TARGET_STATUS = 'captured'
		print('End Condition Reached'); 
		paintTargetEnd(wind); 
		dialog = QMessageBox(); 
		dialog.setText('Target Captured!'); 
		dialog.exec_(); 

def movementViewChanges(wind):

	rad = wind.trueModel.ROBOT_VIEW_RADIUS;

	points = []; 

	for i in range(-int(rad/2)+wind.trueModel.copPose[0],int(rad/2)+wind.trueModel.copPose[0]):
		for j in range(-int(rad/2) + wind.trueModel.copPose[1],int(rad/2)+wind.trueModel.copPose[1]):
			tmp1 = min(wind.imgWidth-1,max(0,i)); 
			tmp2 = min(wind.imgHeight-1,max(0,j)); 
			if(distance([tmp1,tmp2],wind.trueModel.copPose) < rad/2):
				points.append([tmp1,tmp2]); 

	if(wind.REFOG_COP):
		refog(wind,wind.prevFogPoints); 

	defog(wind,points); 

	wind.prevFogPoints = points; 


	#Cop
	points = []; 
	rad = wind.trueModel.ROBOT_SIZE_RADIUS; 
	for i in range(-int(rad/2)+wind.trueModel.copPose[0],int(rad/2)+wind.trueModel.copPose[0]):
		for j in range(-int(rad/2) + wind.trueModel.copPose[1],int(rad/2)+wind.trueModel.copPose[1]):
			tmp1 = min(wind.imgWidth-1,max(0,i)); 
			tmp2 = min(wind.imgHeight-1,max(0,j)); 
			points.append([tmp1,tmp2]); 
			wind.assumedModel.transitionLayer[tmp1,tmp2] = wind.trueModel.transitionLayer[tmp1,tmp2];

	planeFlushPaint(wind.robotPlane,points,QColor(0,255,0,255)); 

	#Robber
	points = []; 
	rad = wind.trueModel.TARGET_SIZE_RADIUS; 
	for i in range(-int(rad/2)+wind.trueModel.robPose[0],int(rad/2)+wind.trueModel.robPose[0]):
		for j in range(-int(rad/2) + wind.trueModel.robPose[1],int(rad/2)+wind.trueModel.robPose[1]):
			#if(i>0 and j>0 and i<wind.imgHeight and j<wind.imgWidth):
			tmp1 = min(wind.imgWidth-1,max(0,i)); 
			tmp2 = min(wind.imgHeight-1,max(0,j)); 
			points.append([tmp1,tmp2]); 
	planeFlushPaint(wind.targetPlane,points,QColor(255,0,255,255)); 
	
	if(wind.CHEAT_TARGET):
		planeAddPaint(wind.fogPlane,points,QColor(255,0,255,255)); 

	makeBeliefMap(wind); 



def startSketch(wind):
	wind.sketchListen=True;
	wind.allSketchPaths.append([]); 


def imageMousePress(QMouseEvent,wind):
	if(wind.droneClickListen):
		wind.droneClickListen = False; 
		tmp = [QMouseEvent.scenePos().x(),QMouseEvent.scenePos().y()]; 
		wind.timeLeft = wind.DRONE_WAIT_TIME;
		revealMapDrone(wind,tmp);
		updateDroneTimer(wind);  
		wind.refogDroneTimer = QTimer();
		wind.refogDroneTimer.timeout.connect(lambda: refogTimerTimeout(wind)); 
		wind.refogDroneTimer.start(1000);  
		wind.refogTimeLeft = wind.DRONE_WAIT_TIME; 

	elif(wind.sketchListen):
		wind.sketchingInProgress = True; 
		name = wind.sketchName.text(); 
		if(name not in wind.allSketchPlanes.keys()):
			wind.allSketchPlanes[name] = wind.imageScene.addPixmap(makeTransparentPlane(wind));
			wind.objectsDrop.addItem(name);
			wind.allSketchNames.append(name); 
		else:
			planeFlushPaint(wind.allSketchPlanes[name],[]);



def imageMouseMove(QMouseEvent,wind):


	if(wind.sketchingInProgress):

		tmp = [int(QMouseEvent.scenePos().x()),int(QMouseEvent.scenePos().y())]; 
		#tmp = [int(QMouseEvent.x()),int(QMouseEvent.y())]; 
		wind.allSketchPaths[-1].append(tmp); 
		#add points to be sketched
		# points = []; 
		# si = wind.sketchDensity;
		# for i in range(-si,si+1):
		# 	for j in range(-si,si+1):
		# 		points.append([tmp[0]+i,tmp[1]+j]); 
		pen = QPen(QColor(0,0,0,255)); 
		pen.setWidth(wind.sketchDensity*2); 
		name = wind.sketchName.text(); 


		planeAddPaint(wind.allSketchPlanes[name],[tmp],pen=pen); 

		#print(""); 



def imageMouseRelease(QMouseEvent,wind):

	if(wind.sketchingInProgress):
		tmp = wind.sketchName.text(); 
		wind.sketchName.clear();
		wind.sketchName.setPlaceholderText("Sketch Name");

		# cost = wind.costRadioGroup.checkedId(); 
		# speed = wind.speedRadioGroup.checkedId(); 
		# wind.safeRadio.setChecked(True); 
		# wind.nomRadio.setChecked(True); 

		wind.currentSketch = [tmp,wind.allSketchPaths[-1]]; 
		wind.allSketches[tmp] = wind.allSketchPaths[-1]; 
		wind.sketchListen = False; 
		wind.sketchingInProgress = False; 
		makeModel(wind,tmp);






def redrawSketches(wind):
	#print("Redrawing"); 
	for name in wind.sketchLabels.keys():
		updateModel(wind,name); 


def updateModel(wind,name):

	centx,centy = wind.sketchLabels[name]; 
	planeFlushPaint(wind.allSketchPlanes[name]); 

	pm = wind.allSketchPlanes[name].pixmap(); 
	paintBlack = QPainter(pm); 
	pen = QPen(QColor(255,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(10); 
	paintBlack.setPen(pen); 
	paintBlack.setFont(QtGui.QFont('Decorative',25)); 
	paintBlack.drawText(QPointF(centx,centy),name); 
	pen = QPen(QColor(0,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(wind.sketchDensity*2);
	paintBlack.setPen(pen); 
	

	for l in wind.sketchLines[name]['Black']:
		paintBlack.drawLine(l); 

	paintBlack.end(); 


	paintRed = QPainter(pm); 
	pen = QPen(QColor(255,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(np.floor(wind.sketchDensity));
	paintRed.setPen(pen); 
	
	for l in wind.sketchLines[name]['Red']:
		paintRed.drawLine(l); 

	paintRed.end(); 


	wind.allSketchPlanes[name].setPixmap(pm); 


def makeModel(wind,name):
	pairedPoints = np.array(wind.allSketches[name]); 
	cHull = ConvexHull(pairedPoints); 
	xFudge = len(name)*10/2; 

	#print(cHull.vertices.tolist()); 
	#print(wind.allSketches[name]); 
	vertices = fitSimplePolyToHull(cHull,pairedPoints,N=wind.NUM_SKETCH_POINTS); 
	#print(len(vertices)); 
	#print(vertices); 

	centx = np.mean([vertices[i][0] for i in range(0,len(vertices))])-xFudge; 
	centy = np.mean([vertices[i][1] for i in range(0,len(vertices))]) 
	wind.sketchLabels[name] = [centx,centy]; 


	planeFlushPaint(wind.allSketchPlanes[name]); 

	pm = wind.allSketchPlanes[name].pixmap(); 
	paintBlack = QPainter(pm); 
	pen = QPen(QColor(255,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(10); 
	paintBlack.setPen(pen); 
	paintBlack.setFont(QtGui.QFont('Decorative',25)); 
	paintBlack.drawText(QPointF(centx,centy),name); 
	pen = QPen(QColor(0,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(wind.sketchDensity*2);
	paintBlack.setPen(pen); 
	
	vpaint = pairedPoints[cHull.vertices.tolist()]; 
	wind.sketchLines[name] = {'Red':[],'Black':[]}; 
	for i in range(0,len(vpaint)):
		tmp = QLineF(vpaint[i-1][0],vpaint[i-1][1],vpaint[i][0],vpaint[i][1]); 
		wind.sketchLines[name]['Black'].append(tmp); 
		paintBlack.drawLine(tmp); 

	paintBlack.end(); 


	paintRed = QPainter(pm); 
	pen = QPen(QColor(255,0,0,255*wind.sketchOpacitySlider.sliderPosition()/100)); 
	pen.setWidth(np.floor(wind.sketchDensity));
	paintRed.setPen(pen); 
	
	for i in range(0,len(vertices)):
		tmp = QLineF(vertices[i-1][0],vertices[i-1][1],vertices[i][0],vertices[i][1]);
		wind.sketchLines[name]['Red'].append(tmp); 
		paintRed.drawLine(tmp); 

	paintRed.end(); 


	wind.allSketchPlanes[name].setPixmap(pm); 

	wind.assumedModel.makeSketch(vertices,name);

	loadQuestions(wind); 

	# #Update Cost Map
	# poly = Polygon(vertices); 
	# poly = poly.convex_hull; 
	# mina = min([v[0] for v in vertices]);
	# minb = min([v[1] for v in vertices]); 
	# maxa = max([v[0] for v in vertices]); 
	# maxb = max([v[1] for v in vertices]); 


	# if(speed != 0 or cost != 0):

	# 	for i in range(mina,maxa):
	# 		for j in range(minb,maxb):
	# 			if(poly.contains(Point(i,j))):
	# 				if(speed!=0):
	# 					wind.assumedModel.transitionLayer[i,j] = 5*speed; 
	# 				if(cost!=0):
	# 					wind.assumedModel.costLayer[i,j] = cost*10; 
	# 	if(cost!=0):		
	# 		cm = makeModelMap(wind,wind.assumedModel.costLayer); 
	# 		wind.costMapWidget.setPixmap(cm); 
	# 	if(speed!=0):
	# 		tm = makeModelMap(wind,wind.assumedModel.transitionLayer); 
	# 		wind.transMapWidget_assumed.setPixmap(tm); 



def fitSimplePolyToHull(cHull,pairedPoints,N = 4):
	vertices = [];  

	for i in range(0,len(cHull.vertices)):
		vertices.append([pairedPoints[cHull.vertices[i],0],pairedPoints[cHull.vertices[i],1]]);

	
	while(len(vertices) > N):
		allAngles = []; 
		#for each point, find the angle it forces between the two points on either side
		#find first point
		a = vertices[-1]; 
		b = vertices[0]; 
		c = vertices[1]; 
		allAngles.append(abs(angleOfThreePoints(a,b,c))); 
		for i in range(1,len(vertices)-1):
			#find others
			a = vertices[i-1];
			b = vertices[i]; 
			c = vertices[i+1]; 
			allAngles.append(abs(angleOfThreePoints(a,b,c)));
		#find last point
		a = vertices[-2]; 
		b = vertices[-1]; 
		c = vertices[0]; 
		allAngles.append(abs(angleOfThreePoints(a,b,c))); 


		#remove the point with the smallest angle change
		smallest = min(allAngles); 
		vertices.remove(vertices[allAngles.index(smallest)]); 

		#repeat until number is equal to N

	return vertices;

def distance(p1,p2):
	return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2);

def mahalanobisDistance(point,mean,var):
	S = np.matrix(var); 
	R = np.matrix(point).T; 
	mu = np.matrix(mean).T; 

	return np.sqrt((R-mu).T * S.I * (R-mu)); 
	



def angleOfThreePoints(a,b,c):
	ab = [b[0]-a[0],b[1]-a[1]]; 
	bc = [c[0]-b[0],c[1]-b[1]]; 
	num = ab[0]*bc[0] + ab[1]*bc[1]; 
	dem = distance([0,0],ab)*distance([0,0],bc); 
	theta = np.arccos(num/dem); 
	return theta; 


def controlTimerStart(wind):
	wind.controlTimer = QtCore.QTimer(wind); 
	wind.controlTimer.timeout.connect(lambda: controlTimerTimeout(wind)); 
	wind.controlTimer.start((1/wind.CONTROL_FREQUENCY)*1000); 


def questionTimerStart(wind):
	wind.questionTimer = QtCore.QTimer(wind); 
	wind.questionTimer.timeout.connect(lambda: questionTimerTimeout(wind)); 
	wind.questionTimer.start((1/wind.QUESTION_FREQUENCY)*1000); 

#TODO: Change this behavior to call control  behavior of specific controllers
def controlTimerTimeout(wind):
	arrowEvents = [QtCore.Qt.Key_Up,QtCore.Qt.Key_Down,QtCore.Qt.Key_Left,QtCore.Qt.Key_Right]; 
	if(wind.TARGET_STATUS == 'loose'):
		if(not wind.sketchingInProgress):
			wind.collectAndSaveData(); 
			moveRobot(wind,arrowEvents[wind.control.getActionKey()]);


def questionTimerTimeout(wind):
	wind.questionIndex = wind.control.getQuestionIndex(); 
	setRobotPullQuestion(wind); 


def findMixtureParams(mixture):

	#mean is a weighted average of means
	mixMean = np.zeros(2);
	for g in mixture:
		mixMean += np.array(g.mean)*g.weight; 

	#Variance is the weighted sum of variances plus the weighted sum of outer products of the difference of the mean and mixture mean
	mixVar = np.zeros(shape=(2,2)); 
	for g in mixture:
		mixVar += np.matrix(g.var)*g.weight; 
		mixVar += (np.matrix(g.mean)-np.matrix(mixMean)).T*(np.matrix(g.mean)-np.matrix(mixMean))*g.weight; 

	return mixMean,mixVar;



def droneTimerStart(wind):
	wind.droneTimer = QtCore.QTimer(wind); 
	wind.timeLeft = wind.DRONE_WAIT_TIME; 

	wind.droneTimer.timeout.connect(lambda: droneTimerTimeout(wind)); 
	wind.droneTimer.start(1000); 

	updateDroneTimer(wind); 

def droneTimerTimeout(wind):
	if(wind.timeLeft > 0):	
		wind.timeLeft -= 1; 
	updateDroneTimer(wind); 

def refogTimerTimeout(wind):
	if(wind.refogTimeLeft > 0):
		wind.refogTimeLeft -= 1; 
	else:
		wind.refogDroneTimer.stop(); 
	updateRefogTimer(wind); 


def updateRefogTimer(wind):
	
	R = wind.DRONE_VIEW_RADIUS; 
	T = wind.DRONE_WAIT_TIME; 
	t = wind.refogTimeLeft; 

	points = wind.refogPoints; 
	cent = wind.refogCent; 

	setOfPoints = []; 
	for p in points:
		if(distance(cent,p) >= (t-1)*R/T and distance(cent,p) <= t*R/T):
			setOfPoints.append(p); 

	#print("Refogging: {}".format(len(setOfPoints))); 
	if(wind.REFOG_SCOUT):
		refog(wind,setOfPoints); 




def launchDrone(wind):
	if(wind.timeLeft==0):
		wind.droneClickListen = True; 


def revealMapDrone(wind,point):

	rad = wind.DRONE_VIEW_RADIUS;
	points=[]; 


	#print()
	for i in range(-int(rad/2)+int(point[0]),int(rad/2)+int(point[0])):
		for j in range(-int(rad/2) + int(point[1]),int(rad/2)+int(point[1])):

			tmp1 = min(wind.imgWidth-1,max(0,i)); 
			tmp2 = min(wind.imgHeight-1,max(0,j)); 
			if(distance([tmp1,tmp2],point) < rad/2):
				points.append([tmp1,tmp2]); 

	defog(wind,points); 

	wind.refogPoints = points;
	wind.refogCent = point; 

def updateDroneTimer(wind):
	rcol = 255*wind.timeLeft/wind.DRONE_WAIT_TIME; 
	gcol = 255*(wind.DRONE_WAIT_TIME-wind.timeLeft)/wind.DRONE_WAIT_TIME; 

	wind.updateTimerLCD.setStyleSheet("background-color:rgb({},{},0)".format(rcol,gcol)); 
	wind.updateTimerLCD.display(wind.timeLeft); 

	if(wind.timeLeft == 0):
		wind.droneButton.show(); 
	else:
		wind.droneButton.hide(); 


def setRobotPullQuestion(wind):
	if(wind.questionIndex > -1):
		wind.pullQuestion.setText(wind.questions[wind.questionIndex]); 
		#Make background not boring
		wind.pullQuestion.setStyleSheet("border: 3px solid cyan; color: white; background-color: black");
		wind.questionTimer.stop(); 
	else:
		wind.pullQuestion.setText("Awaiting Query");
		wind.questionTimer.start();
		#Make background boring
		wind.pullQuestion.setStyleSheet("border: 1px solid black; color: black; background-color: slategray");


def answerRobotPullQuestion(wind,pos):
	if(wind.questionIndex > -1):

		relations = ["South of","North of","East of", "West of","Near"]; 
		name = "You"
		rel = None


		for r in relations:
			if(r in wind.pullQuestion.text()):
				rel = r; 
		for o in wind.allSketchNames:
			if(o in wind.pullQuestion.text()):
				name = o; 

		wind.currentPull = [name,rel,pos]; 
		wind.assumedModel.stateObsUpdate(name,rel,pos); 

		wind.questionIndex = -1;
		setRobotPullQuestion(wind);  






#TODO: Map in actual robot questions
def loadQuestions(wind):
	#f = open('../data/Questions.txt','r'); 
	#lines = f.read().split("\n"); 
	#wind.questions = lines; 

	preample = "Is the Target "
	relations = ["South of ","North of ","East of ", "West of ","Near "]; 
	objects = deepcopy(wind.allSketchNames);
	objects.insert(0,"Me");  
	questionMark = "?"; 

	wind.questions = []; 
	for o in objects:
		for r in relations:
			wind.questions.append(preample+r+o+questionMark);
	



def pushButtonPressed(wind):
	rel = str(wind.relationsDrop.currentText()) 
	name = str(wind.objectsDrop.currentText());
	pos = str(wind.positivityDrop.currentText());

	wind.currentPush = [name,rel,pos]; 
	wind.assumedModel.stateObsUpdate(name,rel,pos); 

	#makeBeliefMap(wind); 
	# wind.tabs.removeTab(0); 
	# pm = makeBeliefMap(wind); 
	# wind.beliefMapWidget = pm; 
	# wind.tabs.insertTab(0,wind.beliefMapWidget,'Belief');
	# wind.tabs.setCurrentIndex(0); 
	# wind.lastPush = [pos,rel,name]; 


