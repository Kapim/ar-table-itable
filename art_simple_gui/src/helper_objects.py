import rospy
from PyQt4 import QtGui, QtCore
from geometry_msgs.msg import PoseStamped
import numpy as np

def dist(pt1,  pt2):
    
    a = np.array(pt1)
    b= np.array(pt2)
    return np.linalg.norm(a-b)

class scene_place():
    
    def __init__(self,  scene, pos,  pub=None, wsize=None, calib=None):
        
        self.scene = scene
        self.pos = pos
        self.pub = pub
        self.viz = self.scene.addEllipse(0, 0, 100, 100, QtCore.Qt.cyan, QtCore.Qt.cyan)
        self.viz.setPos(self.pos[0] - 100/2, self.pos[1] - 100/2)
        self.wsize = wsize
        self.calib = calib
        
        if self.pub is not None:
            ps = self.get_pose(self.pos[0],  self.pos[1])
            self.pub.publish(ps)
     
    def remove(self):
        
        if self.viz is not None:
            self.scene.removeItem(self.viz)
            self.viz = None
  
    def get_pose(self, px=None, py=None):

        if px is None or py is None:
            px = self.pos[0]
            py = self.pos[1]

        return self.calib.get_pose(px,  py)
        
class scene_polygon():
    
    def __init__(self,  scene,  calib=None,  points = []):
        
        self.scene = scene
        self.calib = calib
        self.closed = False
        self.points = points
        self.lines = []
        self.active_line = None
        self.pen = QtGui.QPen(QtCore.Qt.white, 5, QtCore.Qt.DotLine)
        self.apen = QtGui.QPen(QtCore.Qt.white, 5, QtCore.Qt.SolidLine)
        
        if len(self.points) > 0:
            
            for i in range(0,  len(points)-1):

                self.lines.append(self.scene.addLine(self.points[i][0],  self.points[i][1],  self.points[i+1][0],  self.points[i+1][1]))
                self.lines[-1].setPen(self.apen)
                
            self.lines.append(self.scene.addLine(self.points[-1][0],  self.points[-1][1],  self.points[0][0],  self.points[0][1]))
            self.lines[-1].setPen(self.apen)
            
            self.closed = True
        
    def remove(self):
        
        for l in self.lines:
            self.scene.removeItem(l)
        self.lines = []
        
    def get_point_array(self):
        
        if not self.closed: return None
        
        arr = []
        
        for pt in self.points:
            
            arr.append(self.calib.get_point(pt[0],  pt[1]))
            
        return arr
        
    def set_pos(self,  pt):
        
        if len(self.points) > 0 and not self.closed:
            
            if self.active_line is None:
                
                self.active_line = self.scene.addLine(self.points[-1][0],  self.points[-1][1],  pt[0],  pt[1])
                self.active_line.setPen(self.pen)
                
            else:    
                
                if dist(pt, self.points[0]) < 30:
                    self.active_line.setPen(self.apen)
                    self.active_line.setLine(self.points[-1][0],  self.points[-1][1],  self.points[0][0],  self.points[0][1])
                else:
                    self.active_line.setLine(self.points[-1][0],  self.points[-1][1],  pt[0],  pt[1])
                    self.active_line.setPen(self.pen)
        
    def add_point(self,  pt):
        
        if len(self.points) == 0:
            self.points.append(pt)
            return False
            
        else:
            
            d = dist(pt, self.points[0])
            
            if d < 30:
                
                self.lines.append(self.scene.addLine(self.points[-1][0],  self.points[-1][1],  self.points[0][0],  self.points[0][1]))
                self.lines[-1].setPen(self.apen)
                
                self.closed = True
                self.scene.removeItem(self.active_line)
                self.active_line = None
                return True
                
            else:
                
                self.lines.append(self.scene.addLine(self.points[-1][0],  self.points[-1][1],  pt[0],  pt[1]))
                self.lines[-1].setPen(self.apen)
                self.points.append(pt)
                
                return False
        
class scene_object():

    def __init__(self,  scene,  id, obj_type,  pos,  pub):
        
        self.scene = scene
        self.id = id
        self.obj_type = obj_type
        self.pub = pub
        
        self.viz = self.scene.addEllipse(0, 0, 150, 150, QtCore.Qt.white, QtCore.Qt.white)
        
        self.label = self.scene.addText(id + '\n(' + obj_type + ')', QtGui.QFont('Arial', 16))
        self.label.setParentItem(self.viz)
        self.label.rotate(180)
        self.label.setDefaultTextColor(QtCore.Qt.white)
        
        self.set_pos(pos)
        
        self.pointed_at = None
        
        self.preselected = False
        self.preselected_at = None
        
        self.selected = False
        self.selected_at = None
        
        self.viz_preselect = None
        
        self.viz_selected = None
        
        self.timer = QtCore.QTimer()
        self.timer.start(500)
        self.timer.timeout.connect(self.timer_evt)
    
    def set_pos(self,  pos):
        
        self.pos = pos
        self.viz.setPos(self.pos[0] - 150/2, self.pos[1] - 150/2)
        #self.viz.setPos(self.pos[0] + 150/2, self.pos[1] + 150/2)
        #self.viz.setPos(self.pos[0], self.pos[1])
        self.label.setPos(120,  -10)
    
    def timer_evt(self):
        
        # cancel preselect after some time - object was not pointed at
        if not self.selected:
           
          if self.preselected and rospy.Time.now() - self.pointed_at  > rospy.Duration(0.5):
              
              rospy.loginfo("object " + self.id + ": preselect cancelled")
              self.preselected = False
              self.scene.removeItem(self.viz_preselect)
              self.viz_preselect = None
    
    def remove(self):
        
        self.scene.removeItem(self.viz)
        self.viz = None
        self.label = None
        
    def unselect(self):
        
         if self.preselected:
             
            self.preselected = False
            if self.viz_preselect is not None:
                self.scene.removeItem(self.viz_preselect)
                self.viz_preselect = None
            
         if self.selected:
            
            self.selected = False
            self.scene.removeItem(self.viz_selected)
            self.viz_selected = None
    
    def set_selected(self):
        
        if self.selected is False:
            
            rospy.loginfo("object " + self.id + ": selected")
            self.pub.publish(self.id)
            
            self.selected = True
            self.viz_selected = self.scene.addEllipse(0, 0, 180, 180, QtCore.Qt.green, QtCore.Qt.green)
            self.viz_selected.setParentItem(self.viz)
            self.viz_selected.setPos(150/2 - 180/2, 150/2 - 180/2)
            self.viz_selected.setFlag(QtGui.QGraphicsItem.ItemStacksBehindParent)
            
            if self.viz_preselect is not None:
                self.scene.removeItem(self.viz_preselect)
                self.viz_preselect = None

    def pointing(self,  pointing_obj,  click = False):
        
        if self.viz not in pointing_obj.collidingItems(): return False
        
        self.pointed_at = rospy.Time.now()
        
        if not self.preselected:
            
            rospy.loginfo("object " + self.id + ": preselected")
            
            self.preselected = True
            self.preselected_at = rospy.Time.now()
        
            self.viz_preselect = self.scene.addEllipse(0, 0, 180, 180, QtCore.Qt.gray, QtCore.Qt.gray)
            self.viz_preselect.setParentItem(self.viz)
            self.viz_preselect.setPos(150/2 - 180/2, 150/2 - 180/2)
            self.viz_preselect.setFlag(QtGui.QGraphicsItem.ItemStacksBehindParent)
            
            return False
        
        if not self.selected:
           
          if (rospy.Time.now() - self.preselected_at > rospy.Duration(1)) or click:
              self.set_selected()
              return True
          
          return False

class pointing_point():
    
    def __init__(self,  id,  scene,  mouse = False):
        
        self.id = id
        self.scene = scene
        
        self.pos = (0,  0)
        
        self.viz = None
        self.timestamp = None
        self.mouse = mouse
        
        self.xyt = []
        self.pointed_pos = None
        
        self.timer = QtCore.QTimer()
        self.timer.start(100)
        self.timer.timeout.connect(self.timer_evt)

    def get_pointed_place(self):
        
        return self.pointed_pos
    
    def disable(self):
        
        if self.is_active():
            #rospy.loginfo("Disabling pointing-point: " + self.id)
            self.pointed_pos = None
            self.scene.removeItem(self.viz)
            self.viz = None
            self.timestamp = None
    
    def set_pos(self,  pos,  click = False):
        
        self.timestamp = rospy.Time.now()
        self.pos = pos
        
        # TODO what to do if pos differs much? like from 1280 to 0 or so
        
        if self.mouse:
            if click: self.pointed_pos = pos
        else:
            self.xyt.append([self.pos, rospy.Time.now()])
        
        if self.viz is None:
        
            #rospy.loginfo("Enabling pointing-point: " + self.id)
            self.viz = self.scene.addEllipse(0, 0, 50, 50, QtCore.Qt.blue, QtCore.Qt.blue)
            self.viz.setZValue(100)
            
        self.viz.setPos(self.pos[0] - 25, self.pos[1] - 25)

    def is_active(self):
        
        if self.timestamp is None: return False
        else: return True

    def timer_evt(self):
        
        if self.timestamp is None: return
        
        now = rospy.Time.now()
        
        if not self.mouse:
        
            # throw away older data
            while len(self.xyt) > 0 and now - self.xyt[0][1] > rospy.Duration(2):
                
                self.xyt.pop(0)
            
            # wait until we have some data
            if len(self.xyt) > 10 and now - self.xyt[0][1] > rospy.Duration(1.5):
                
                x = []
                y = []
                
                for it in self.xyt:
                    
                    x.append(it[0][0])
                    y.append(it[0][1])
            
                xm = np.mean(x)
                ym = np.mean(y)
                
                xs = np.std(x)
                ys = np.std(y)
                
                # if "cursor" position move a bit (noise) but doesn't move too much - the user is pointing somewhere
                if xs > 0.01 and xs < 15.0 and ys > 0.01 and ys < 15.0:
                #if xs < 10.0 and ys < 10.0: # -> this is only for testing
                    
                    # TODO zezelenat
                    self.pointed_pos = (int(xm),  int(ym))
                    # self.viz.setPen(QtCore.Qt.green)
                    
                else:
                    
                    self.pointed_pos = None
        
        if (not self.mouse and len(self.xyt) == 0) or (self.mouse and (now - self.timestamp > rospy.Duration(2))):
            
            self.disable()
