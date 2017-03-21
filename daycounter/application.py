import win32api, win32gui
import win32con, winerror
import sys, os
from tkinter import *
import threading
import glob
import datetime
import daycounter

class SystemTrayIcon:
    def __init__(self):
        msg_TaskbarRestart = win32gui.RegisterWindowMessage("TaskbarCreated");#定义一个新的窗口消息
        message_map = {                         #建立函数命令字典，用于窗口回调函数的四个参数
                msg_TaskbarRestart: self.OnRestart,
                win32con.WM_DESTROY: self.OnDestroy,
                win32con.WM_COMMAND: self.OnCommand,
                win32con.WM_USER+20 : self.OnTaskbarNotify,
        }
        self.menu = win32gui.CreatePopupMenu()#产生一个菜单句柄menu
        win32gui.AppendMenu(self.menu, win32con.MF_STRING, 1023, "显示/隐藏窗口")#给菜单添加子项，1027可以一直下去
        win32gui.AppendMenu(self.menu, win32con.MF_STRING, 1024, "设置")
        win32gui.AppendMenu(self.menu, win32con.MF_STRING, 1025, "退出程序")
        #win32gui.EnableMenuItem(menu,1023,win32con.MF_GRAYED)#是用菜单句柄，对菜单进行操作

        # Register the Window class.
        self.wc = win32gui.WNDCLASS()#局部变量wc改成窗口类的实例
        hinst = self.wc.hInstance = win32api.GetModuleHandle(None)#获得程序模块句柄
        self.wc.lpszClassName = ("PythonTaskbarDemo")             #窗口类的类名
        self.wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;#窗口类的style特征，水平重画和竖直重画
        self.wc.hCursor = win32api.LoadCursor( 0, win32con.IDC_ARROW )
        self.wc.hbrBackground = win32con.COLOR_WINDOW
        self.wc.lpfnWndProc = message_map # could also specify a wndproc，给窗口回调函数赋值
        '''这里传进去的其实是函数指针，它里面保存的是我们定义的windowproc的入口地址'''
        # Don't blow up if class already registered to make testing easier
        try:
            classAtom = win32gui.RegisterClass(self.wc)#用wc将classatom注册为一个窗口类
        except win32gui.error and err_info:
            if err_info.winerror!=winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise

        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(self.wc.lpszClassName, "Taskbar Demo", style,#创建一个窗口 
            0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, 0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)#更新窗口
        self._DoCreateIcons()
        win32gui.PumpMessages()

    def _DoCreateIcons(self):
        # Try and find a custom icon
        hinst =  win32api.GetModuleHandle(None)
        
        icons = glob.glob("*.ico")
        if len(icons) > 0:
            iconPathName = os.path.abspath(os.path.join( os.getcwd(), icons[0]))
        else:
            iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "pyc.ico" ))
            #sys.executalbe为python解释程序路径
        if not os.path.isfile(iconPathName):#如果系统ico文件不存在
            # Look in DLLs dir, a-la py 2.5
            iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "DLLs", "pyc.ico" ))
        if not os.path.isfile(iconPathName):
            # Look in the source tree.
            iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "..\\PC\\pyc.ico" ))
        if os.path.isfile(iconPathName):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE#ico标识，从文件载入和默认大小
            hicon = win32gui.LoadImage(hinst, iconPathName, win32con.IMAGE_ICON, 0, 0, icon_flags)#载入.ico文件
            '''handle = LoadImage(hinst,name,type,cx,cy,fuload)'''
        else:
            print("Can't find a Python icon file - using default")
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP | win32gui.NIF_INFO#定义托盘图标的样式
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, "安全生产计时器","安全生产计时器系统托盘图标")
        #最后一个选项猪已经跑。。”是气泡提示内容
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)#增加系统托盘图标
        except win32gui.error:
            # This is common when windows is starting, and this code is hit
            # before the taskbar has been created.
            print ("Failed to add the taskbar icon - is explorer running?")
            # but keep running anyway - when explorer starts, we get the
            # TaskbarCreated message.

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self._DoCreateIcons()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # Terminate the app.

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        if lparam==win32con.WM_LBUTTONUP:
            pass
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            self.SwitchWindow()
            #win32gui.DestroyWindow(self.hwnd)
            #win32gui.UnregisterClass(self.wc.lpszClassName,None)
        elif lparam==win32con.WM_RBUTTONUP:        
            pos = win32gui.GetCursorPos()
            # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
            win32gui.SetForegroundWindow(self.hwnd)
            
            win32gui.TrackPopupMenu(self.menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None)#显示并获取选中的菜单
            win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)#忽略当前事件消息
        return 1

    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == 1023:
            self.SwitchWindow()
            #win32gui.DestroyWindow(self.hwnd)
            #win32gui.UnregisterClass(self.wc.lpszClassName,None)
            #import win32gui_dialog
            #win32api.MessageBox(0,"hello",win32con.MB_OK)
        elif id == 1024:
            config.deiconify()
        elif id == 1025:
            nid = (self.hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            root.destroy()
            win32gui.DestroyWindow(self.hwnd)
            win32gui.UnregisterClass(self.wc.lpszClassName,None)
            #win32gui.PostQuitMessage(0) # Terminate the app.
        else:
            print ("Unknown command -", id)

    def SwitchWindow(self):
        if root.state() == "normal":
            root.withdraw()
        elif root.state() == "withdrawn":
            root.deiconify()    

def StartIcon():
    thread = threading.Thread(target = createTray)
    thread.daemon = True
    thread.start()

def createTray():
    SystemTrayIcon()

def OnCloseRoot():
    root.withdraw()

def OnCloseConfig():
    config.withdraw()

def UpdateUI():
    for i in range(len(dc)):
        if dcconfig[i].GetState() is True:
            dc[i].UpdateDays(dcconfig[i].GetDate(), dcconfig[i].GetProjName())
    root.after(1000, UpdateUI)

def main():
    root.wm_protocol("WM_DELETE_WINDOW", OnCloseRoot)
    config.wm_protocol("WM_DELETE_WINDOW", OnCloseConfig)
    config.withdraw()
    for i in range(3):
        dc.append(daycounter.DayCounter(root))
        dcconfig.append(daycounter.DayCounterSetting(config, i))
    StartIcon()
    UpdateUI()
    root.mainloop()

root = Tk()
config = Toplevel(root)
dc = []
dcconfig = []

if __name__=='__main__':
    main()

