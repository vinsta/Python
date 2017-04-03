
import xml.etree.ElementTree as ET
import collections
import tkinter
import tkinter.ttk
import tkinter.filedialog

Param = collections.namedtuple("Param", "name mandatory type min max values")
Mo = collections.namedtuple("Mo", "minoccurs maxoccurs params")

def ParseNIDD(filename, modict, paramdict):
	print(filename)
	try:
		et = ET.parse(filename)
	except FileNotFoundError as err:
		print(err)
		return

	params = []

	MOs = et.findall("managedObject")
	for mo in MOs:
		moname = mo.attrib["class"]

		minoccursfound = False
		maxoccursfound = False
		for param in mo:
			if param.tag != "p":
				continue

			if not minoccursfound or not maxoccursfound:
				for productData in param.iter("productData"):
					for data in productData:
						if data.attrib["name"] == "MO MaxOccurs":
							maxoccurs = data.attrib["value"]
							param.set("name", "instanceid")
							maxoccursfound = True
						elif data.attrib["name"] == "MO MinOccurs":
							minoccurs = data.attrib["value"]
							param.set("name", "instanceid")
							minoccursfound = True
						if minoccursfound and maxoccursfound:
							break
			paramname = param.attrib["name"]
			params.append(paramname)

			paramdict["{}-{}".format(moname, paramname)] = GetParamDetail(param)

		modict[moname] = Mo(minoccurs, maxoccurs, params)

def GetParamDetail(param):
	mandatory = False
	paramtype = ""
	minoccurs = 0
	maxoccurs = 0
	minval = 0
	maxval = 0
	values = []

	paramname = param.attrib["name"]

	creation = param.find("creation")
	if creation.attrib["priority"] == "mandatory":
		mandatory = True

	simpletype = param.find("simpleType")
	if simpletype is not None:
		paramtype = simpletype.attrib["base"]
		if paramtype == "decimal":
			editing = simpletype.find("editing")
			if "divisor" in editing.attrib:
				divisor = int(editing.attrib["divisor"])
			else:
				divisor = 1
			if "multiplicand" in editing.attrib:
				multiplicand = int(editing.attrib["multiplicand"])
			else:
				multiplicand = 1
			if "shift" in editing.attrib:
				shift = float(editing.attrib["shift"])
			else:
				shift = 0
			paramrange = editing.find("range")
			minval = (float(paramrange.attrib["minIncl"]) - shift) * divisor / multiplicand
			maxval = (float(paramrange.attrib["maxIncl"]) - shift) * divisor / multiplicand
		elif paramtype == "string":
			for child in simpletype:
				if child.tag == "minLength":
					minval = int(child.attrib["value"])
				elif child.tag == "maxLength":
					maxval = int(child.attrib["value"])
		elif paramtype == "boolean":
			minval = False
			maxval = True
		elif paramtype == "integer":
			enums = simpletype.findall("enumeration")
			if len(enums) > 0:
				paramtype = "enumeration"
				for enum in enums:
					values.append(enum.attrib["text"])
			bits = simpletype.findall("bit")
			if len(bits) > 0:
				paramtype = "bit"
				for bit in bits:
					maxval |= (1 << int(bit.attrib["number"]))
	else:
		complextype = param.find("complexType")
		if complextype is not None:
			paramtype = "list"
			for child in complextype:
				values.append(GetParamDetail(child))

	return Param(paramname, mandatory, paramtype, minval, maxval, values)

def OpenFile(var, isDirectory = False):
	if isDirectory is False:
		filename = tkinter.filedialog.askopenfilename(filetypes=[("xml file", "*.xml")])
	else:
		filename = tkinter.filedialog.asksaveasfilename()
		#filename = tkinter.filedialog.askdirectory()
		#filename = "{}{}".format(filename, "/log.txt")
	var.set(filename)

def OnValidate():
	print(logVar.get())
	'''
	if scfVar.get() == "":
		print("SCF is not selected!!!")
		return'''

	for file in [mrbtsVar.get(), eqmVar.get(), mnlVar.get(), radioVar.get()]:
		if file != "":
			ParseNIDD(file, modict, paramdict)
	#print(modict)
	#print(paramdict)

	ValidateSCF(scfVar.get())

def ValidateSCF(scf):
	scf = "I:\\CUPL_BTSA_10139.xml"
	print(scf)
	try:
		etscf = ET.parse(scf)
		root = etscf.getroot()
	except FileNotFoundError as err:
		print(err)
		return

	cmdata = root.findall("{raml21.xsd}cmData")
	for data in cmdata:
		MOs = data.findall("{raml21.xsd}managedObject")
		for mo in MOs:
			classname =  mo.attrib["class"]
			classname = classname[classname.rindex(":") + 1 :]
			distname = mo.attrib["distName"]
			if distname.find("/FTM-") != -1:
				print("FTM class or subclass, ignored!")
				continue
			instanceid = distname[distname.rindex("-") + 1 :]
			print("class = {}, instance = {}".format(classname, instanceid))
			ValidateInstanceId(classname, instanceid)
			for param in mo:
				print(param.attrib)
				ValidateParamValue(classname, param)

def ValidateInstanceId(classname, id):
	key = "{}-{}".format(classname, "instanceid")
	try:
		if not paramdict[key].min <= id <= paramdict[key].max:
			print("{} instance id {} is NOK!".format(classname, id))
		else:
			print("{} instance id {} is OK!".format(classname, id))
	except KeyError:
		print("{} does not exist".format(key))

def ValidateParamValue(classname, param):
	key = "{}-{}".format(classname, param.attrib["name"])
	try:
		paramtype = paramdict[key].type
	except KeyError:
		print("{} does not exist".format(key))
		return
	
	if  paramtype == "decimal":
		pass
	elif paramtype == "string":
		pass
	elif paramtype == "boolean":
		pass
	elif paramtype == "enumeration":
		pass
	elif paramtype == "bit":
		pass
	elif paramtype == "list":
		pass

if __name__=='__main__':
	modict = {}
	paramdict = {}

	root = tkinter.Tk()
	mrbtsVar= tkinter.StringVar()
	tkinter.ttk.Button(root, text = "MRBTS", command = lambda:OpenFile(mrbtsVar)).grid(row = 0, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = mrbtsVar, width = 30).grid(row = 0, column  = 1, padx = 4, pady = 4)

	eqmVar = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "EQM", command = lambda:OpenFile(eqmVar)).grid(row = 1, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = eqmVar, width = 30).grid(row = 1, column = 1, padx = 4, pady = 4)

	mnlVar = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "MNL", command = lambda:OpenFile(mnlVar)).grid(row = 2, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = mnlVar, width = 30).grid(row = 2, column = 1, padx = 4, pady = 4)

	radioVar = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "RADIO", command = lambda:OpenFile(radioVar)).grid(row = 3, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = radioVar, width = 30).grid(row = 3, column = 1, padx = 4, pady = 4)

	scfVar = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "SCF", command = lambda:OpenFile(scfVar)).grid(row = 4, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = scfVar, width = 30).grid(row = 4, column = 1, padx = 4, pady = 4)

	logVar = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "LOG", command = lambda:OpenFile(logVar, True)).grid(row = 5, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = logVar, width = 30).grid(row = 5, column = 1, padx = 4, pady = 4)

	tkinter.ttk.Button(root, text = "Validate", command = OnValidate).grid(row = 6, column = 0,  columnspan = 2, padx = 4, pady = 4)

	root.mainloop()
