############################
# **** IMPORT SECTION **** #
############################

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from qtvcp.widgets.origin_offsetview import OriginOffsetView as OFFVIEW_WIDGET
from qtvcp.widgets.tool_offsetview import ToolOffsetView as TOOLVIEW_WIDGET
from qtvcp.widgets.dialog_widget import CamViewDialog as CAMVIEW
from qtvcp.widgets.dialog_widget import MacroTabDialog as LATHEMACRO
from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
from qtvcp.widgets.gcode_widget import GcodeEditor as GCODE
from qtvcp.lib.keybindings import Keylookup
from qtvcp.lib.notify import Notify

from qtvcp.core import Status, Action

# Set up logging
from qtvcp import logger

import linuxcnc
import sys
import os

###########################################
# **** instantiate libraries section **** #
###########################################

KEYBIND = Keylookup()
STATUS = Status()
ACTION = Action()
LOG = logger.getLogger(__name__)
# Set the log level for this module
#LOG.setLevel(logger.INFO) # One of DEBUG, INFO, WARNING, ERROR, CRITICAL

###################################
# **** HANDLER CLASS SECTION **** #
###################################

class HandlerClass:

    ########################
    # **** INITIALIZE **** #
    ########################
    # widgets allows access to  widgets from the qtvcp files
    # at this point the widgets and hal pins are not instantiated
    def __init__(self, halcomp,widgets,paths):
        self.hal = halcomp
        self.w = widgets
        self.stat = linuxcnc.stat()
        self.cmnd = linuxcnc.command()
        self.error = linuxcnc.error_channel()
        self.PATH = paths.CONFIGPATH
        self.IMAGE_PATH = paths.IMAGEDIR
    ##########################################
    # Special Functions called from QTVCP
    ##########################################

    # at this point:
    # the widgets are instantiated.
    # the HAL pins are built but HAL is not set ready
    def initialized__(self):
        if self.w.PREFS_:
            print 'Using preference file:',self.w.PREFS_.fn
        STATUS.emit('play-alert','SPEAK This is a test screen for Qt V C P')
        KEYBIND.add_call('Key_F3','on_keycall_F3')
        KEYBIND.add_call('Key_F4','on_keycall_F4')
        KEYBIND.add_call('Key_F5','on_keycall_F5')
        KEYBIND.add_call('Key_F6','on_keycall_F6')

    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        # when typing in MDI, we don't want keybinding to call functions
        # so we catch and process the events directly.
        # We do want ESC, F1 and F2 to call keybinding functions though
        if code not in(QtCore.Qt.Key_Escape,QtCore.Qt.Key_F1 ,QtCore.Qt.Key_F2,
                    QtCore.Qt.Key_F3,QtCore.Qt.Key_F5,QtCore.Qt.Key_F5):
            if isinstance(receiver, OFFVIEW_WIDGET) or \
                isinstance(receiver, MDI_WIDGET) or isinstance(receiver, TOOLVIEW_WIDGET):
                if is_pressed:
                    receiver.keyPressEvent(event)
                    event.accept()
                return True
            elif isinstance(receiver, GCODE) and STATUS.is_man_mode() == False:
                if is_pressed:
                    receiver.keyPressEvent(event)
                    event.accept()
                return True
            elif isinstance(receiver,QtWidgets.QDialog):
                print 'dialog'
                return True

        try:
            return KEYBIND.call(self,event,is_pressed,shift,cntrl)
        except NameError as e:
            LOG.debug('Exception in KEYBINDING: {}'.format (e))
        except Exception as e:
            LOG.debug('Exception in KEYBINDING:', exc_info=e)
            print 'Error in, or no function for: %s in handler file for-%s'%(KEYBIND.convert(event),key)
            return False

    ########################
    # callbacks from STATUS #
    ########################

    #######################
    # callbacks from form #
    #######################

    #####################
    # general functions #
    #####################

    def kb_jog(self, state, joint, direction, fast = False, linear = True):
        if linear:
            distance = STATUS.get_jog_increment()
            rate = STATUS.get_jograte()/60
        else:
            distance = STATUS.get_jog_increment_angular()
            rate = STATUS.get_jograte_angular()/60
        if state:
            if fast:
                rate = rate * 2
            ACTION.JOG(joint, direction, rate, distance)
        else:
            ACTION.JOG(joint, 0, 0, 0)

    #####################
    # KEY BINDING CALLS #
    #####################

    # Machine control
    def on_keycall_ESTOP(self,event,state,shift,cntrl):
        if state:
            ACTION.SET_ESTOP_STATE(STATUS.estop_is_clear())
    def on_keycall_POWER(self,event,state,shift,cntrl):
        if state:
            ACTION.SET_MACHINE_STATE(not STATUS.machine_is_on())
    def on_keycall_HOME(self,event,state,shift,cntrl):
        if state:
            if STATUS.is_all_homed():
                ACTION.SET_MACHINE_UNHOMED(-1)
            else:
                ACTION.SET_MACHINE_HOMING(-1)
    def on_keycall_ABORT(self,event,state,shift,cntrl):
        if state:
            if STATUS.stat.interp_state == linuxcnc.INTERP_IDLE:
                self.w.close()
            else:
                self.cmnd.abort()

    # dialogs
    def on_keycall_F3(self,event,state,shift,cntrl):
        if state:
            self.w.originoffsetdialog.load_dialog()
    def on_keycall_F4(self,event,state,shift,cntrl):
        if state:
            self.w.camviewdialog.load_dialog()
    def on_keycall_F5(self,event,state,shift,cntrl):
        if state:
            self.w.macrotabdialog.load_dialog()
    def on_keycall_F6(self,event,state,shift,cntrl):
        if state:
            self.w.tooloffsetdialog.load_dialog()

    # Linear Jogging
    def on_keycall_XPOS(self,event,state,shift,cntrl):
        self.kb_jog(state, 0, 1, shift)

    def on_keycall_XNEG(self,event,state,shift,cntrl):
        self.kb_jog(state, 0, -1, shift)

    def on_keycall_YPOS(self,event,state,shift,cntrl):
        self.kb_jog(state, 1, 1, shift)

    def on_keycall_YNEG(self,event,state,shift,cntrl):
        self.kb_jog(state, 1, -1, shift)

    def on_keycall_ZPOS(self,event,state,shift,cntrl):
        self.kb_jog(state, 2, 1, shift)

    def on_keycall_ZNEG(self,event,state,shift,cntrl):
        self.kb_jog(state, 2, -1, shift)

    def on_keycall_APOS(self,event,state,shift,cntrl):
        pass
        #self.kb_jog(state, 3, 1, shift, False)

    def on_keycall_ANEG(self,event,state,shift,cntrl):
        pass
        #self.kb_jog(state, 3, -1, shift, linear=False)

    ###########################
    # **** closing event **** #
    ###########################
    def closing_cleanup__(self):
        pass

    ##############################
    # required class boiler code #
    ##############################

    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)

################################
# required handler boiler code #
################################

def get_handlers(halcomp,widgets,paths):
     return [HandlerClass(halcomp,widgets,paths)]
