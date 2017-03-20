import tkinter
import tkinter.ttk
#import calendar
import datetime
#import objgraph

class DayCounter(tkinter.Frame):
	#num = 0
	
	def __init__ (self, master=None, cnf={}, **kw):
		self.master = master
		#self.master.size = (100,150)
		self.master.resizable(False, False)
		self.master.title('安全生产计时器')
		#self.master.rowconfigure(0, weight = 1)
		#self.master.columnconfigure(0, weight = 1)
		#self.pack()
		self.InitUI()

	def InitUI (self):
		nameframe = tkinter.Frame(self.master)
		nameframe.pack(pady = 4)
		self.project = tkinter.StringVar(value = "项目名称")
		tkinter.Label(nameframe, width = 10, textvariable = self.project, font = ('仿宋', '20', 'bold')).pack()

		dataframe = tkinter.Frame(self.master)
		dataframe.pack()
		tkinter.Label(dataframe, text = "第").pack(side = "left", padx = 8)
		self.lbDays = tkinter.Label(dataframe, text = "0", fg = "red", font = ('Arial', '36', 'bold'))
		self.lbDays.pack(side = "left")
		tkinter.Label(dataframe, text = "天").pack(side = "left", padx = 8)

	def UpdateDays(self, date, text):
		today = datetime.date.today()
		self.lbDays.configure(text = (today - date).days)
		self.project.set(text)
		#self.lbDays.configure(text = str(self.num+1))
		#self.num += 1

class DayCounterSetting(tkinter.Toplevel):
	isStart = False

	def __init__ (self, master=None, cnf={}, **kw):
		self.master = master
		self.master.resizable(False, False)
		self.master.title('安全生产计时器设置')
		self.InitUI()

	def InitUI (self):
		infoframe = tkinter.Frame(self.master)
		infoframe.pack(pady = 8, fill = "x")
		self.project = tkinter.StringVar()
		tkinter.Entry(infoframe, textvariable = self.project).pack()

		dateframe = tkinter.Frame(self.master)
		dateframe.pack()
		tkinter.Label(dateframe, text = "开始时间:").pack(side = "left", anchor = "e")
		self.yearChosen = tkinter.ttk.Combobox(dateframe, width = 4, state = "readonly")
		self.yearChosen.pack(side = "left")
		self.InitYearCombobox()
		tkinter.Label(dateframe, text = "年").pack(side = "left")
		self.monthChosen = tkinter.ttk.Combobox(dateframe, width = 2, state = "readonly")
		self.monthChosen.pack(side = "left")
		self.InitMonthCombobox()
		tkinter.Label(dateframe, text = "月").pack(side = "left")
		self.dayChosen = tkinter.ttk.Combobox(dateframe, width = 2, state = "readonly")
		self.dayChosen.pack(side = "left")
		self.InitDayCombobox()
		tkinter.Label(dateframe, text = "日").pack(side = "left")

		btnframe = tkinter.Frame(self.master)
		btnframe.pack(pady = 8)
		self.btnStart = tkinter.Button(btnframe, text = "开始计数", command = lambda:self.StartCount(), relief = "groove")
		self.btnStart.pack(side = "left")
		tkinter.Button(btnframe, width = 6, relief = "flat").pack(side = "left")
		self.btnStop = tkinter.Button(btnframe, text = "停止计数", command = lambda:self.StopCount(), relief = "groove", state = "disabled")
		self.btnStop.pack(side = "left")

	def InitYearCombobox(self):
		year = datetime.date.today().year
		yearList = list(range(year-100, year+1))
		yearList.reverse()
		self.yearChosen['values'] = yearList
		self.yearChosen.current(0)

	def InitMonthCombobox(self):
		self.monthChosen['values'] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
		self.monthChosen.current(datetime.date.today().month - 1)

	def InitDayCombobox(self):
		date = datetime.date.today()
		daysList = []
		i = 1
		while i <= 31:
			if (i == 29):
				if (date.month == 2 and date.year%4 != 0):
					break
			if (i == 30):
				if (date.month == 2):
					break
			if (i == 31):
				if date.month not in (1, 3, 5, 7, 8, 10, 12):
					break
			daysList.append(i)
			i += 1
		self.dayChosen['values'] = daysList
		self.dayChosen.current(date.day-1)

	def StartCount(self):
		self.btnStart.configure(state = "disabled")
		self.btnStop.configure(state = "normal")
		self.yearChosen.configure(state = "disabled")
		self.monthChosen.configure(state = "disabled")
		self.dayChosen.configure(state = "disabled")
		self.isStart = True

	def StopCount(self):
		self.btnStart.configure(state = "normal")
		self.btnStop.configure(state = "disabled")
		self.yearChosen.configure(state = "normal")
		self.monthChosen.configure(state = "normal")
		self.dayChosen.configure(state = "normal")
		self.isStart = False

	def isStart(self):
		return self.isStart
