
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

	MOs = et.findall("managedObject")
	for mo in MOs:
		params = []
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
		specialvalue = simpletype.find("special")
		if specialvalue is not None:
			values.append(specialvalue.attrib["value"])
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
	modict = {}
	paramdict = {}
	print(logVar.get())
	'''
	if scfVar.get() == "":
		print("SCF is not selected!!!")
		return'''

	for file in [mrbtsVar.get(), eqmVar.get(), mnlVar.get(), radioVar.get()]:
		if file != "":
			ParseNIDD(file, modict, paramdict)
	print(modict)
	print(paramdict)

	ValidateSCF(scfVar.get())

def ValidateSCF(scf):
	scf = "I:\\CUPL_BTSA_10139.xml"
	logfilename = "I:\\scfvalidation.log"

	try:
		etscf = ET.parse(scf)
		root = etscf.getroot()
		logfile = open(logfilename, "w", encoding = "utf8")
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
			if distname.find("/FTM-") != -1 or classname.find("_R") != -1:
				#print("FTM class or subclass, ignored!")
				continue
			instanceid = distname[distname.rindex("-") + 1 :]
			ValidateInstanceId(classname, int(instanceid), logfile)
			for param in mo:
				key = "{}-{}".format(classname, param.attrib["name"])
				ValidateParamValue(key, param, logfile)

		ValidateMandatoryParams(classname, mo, logfile)
	logfile.close()

def ValidateMandatoryParams(moname, mo, logfile):
	try:
		for paramname in modict[moname].params:
			if paramname == "instanceid":
				continue
			key = "{}-{}".format(moname, paramname)
			if paramdict[key].mandatory is True:
				found = False
				for param in mo:
					if param.attrib["name"] == paramname:
						found = True
						break
				if found is False:
					logfile.write("mandatory parameter {} is missing!\n".format(key))
			if paramdict[key].type == "list":
				for value in paramdict[key].values:
					if value.mandatory is True:
						for param in mo:
							if param.attrib["name"] == paramname:
								found = False
								for item in param.findall("{raml21.xsd}item"):
									for listparam in item:
										if listparam.attrib["name"] == value.name:
											found = True
											break
								if found is False:
									logfile.write("mandatory parameter {}-{} is missing!\n".format(key, value.name))
	except KeyError as err:
		#print("unknown param {}".format(err))
		logfile.write("Unknown parammeter {}\n".format(err))

def ValidateInstanceId(classname, instid, logfile):
	key = "{}-{}".format(classname, "instanceid")
	try:
		if not paramdict[key].min <= instid <= paramdict[key].max:
			#print("{} instance id {} is NOK!".format(classname, id))
			logfile.write("{} instance id {} exceeds range\n".format(classname, instid))
	except KeyError:
		print("{} does not exist".format(key))

def ValidateParamValue(key, param, logfile, islist = False):
	paramname = param.attrib["name"]
	try:
		paramtype = paramdict[key].type
	except KeyError:
		logfile.write("Unknown parameter {}\n".format(key))
		#print("{} does not exist".format(key))
		return
	
	if islist is True:
		for item in paramdict[key].values:
			if item.name == paramname:
				minval = item.min
				maxval = item.max
				special = item.values
				break
	else:
		minval = paramdict[key].min
		maxval = paramdict[key].max
		special = paramdict[key].values

	if  paramtype == "decimal":
		if not  minval <= int(param.text) <= maxval and param.text not in special:
			logfile.write("{}-{} value exceeds range\n".format(key, paramname))
	elif paramtype == "string":
		if not minval <= len(param.text) <= maxval and param.text not in special:
			logfile.write("{}-{} value length exceeds range\n".format(key, paramname))
	elif paramtype == "boolean":
		if param.text not in ("true", "false"):
			logfile.write("{}-{} value is not 'true' or 'false'\n".format(key, paramname))
	elif paramtype == "enumeration":
		if param.text not in special:
			logfile.write("{}-{} value is not in range\n".format(key, paramname))
	elif paramtype == "bit":
		if (int(param.text) & 0xFFFF) > maxval:
			logfile.write("{}-{} value is not in range\n".format(key, paramname))
	elif paramtype == "list":
		for item in param.findall("{raml21.xsd}item"):
			for listparam in item:
				ValidateParamValue(key, listparam, logfile, True)

if __name__=='__main__':
	modict = {}
	paramdict = {}

	root = tkinter.Tk()
	root.title = "SCF Validation"
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
