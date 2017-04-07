
import xml.etree.ElementTree as ET
import collections
import re
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox

Param = collections.namedtuple("Param", "name mandatory type min max values")
Mo = collections.namedtuple("Mo", "minoccurs maxoccurs params")
modict = {}
paramdict = {}
logfile = None

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
		fullname = moname
		if moname == "EQM":
			fullname = "MRBTS/EQM"
		elif moname == "MNL":
			fullname = "MRBTS/MNL"
		elif moname == "LNBTS":
			fullname = "MRBTS/LNBTS"
		for name in modict:
			pos = name.rfind("/")
			if pos != -1 and name[pos + 1 :] == moname:
				fullname = name
				break
		minoccursfound = False
		maxoccursfound = False
		keystoremove = {}
		for param in mo:
			if param.tag == "childManagedObject":
				mofound = None
				simplechildmoname = param.attrib["class"]
				complexchildmoname = "{}/{}".format(fullname, simplechildmoname)
				keystoremove.clear()
				found = False
				for item in modict:
					if item == simplechildmoname:
						found = True
						keystoremove[item] = complexchildmoname
					else:
						pos = item.find("/")
						if pos != -1 and item[: pos] == simplechildmoname:
							newname = item.replace("{}/".format(simplechildmoname), "{}/".format(complexchildmoname))
							keystoremove[item] = newname
						else:
							pos = item.rfind(complexchildmoname)
							if pos != -1 and item[pos :] == complexchildmoname:
								found = True
							pos = item.rfind(simplechildmoname)
							if pos != -1 and item[pos :] == simplechildmoname:
								mofound = modict[item]
				for key in keystoremove:
					try:
						modict[keystoremove[key]] = modict[key]
						modict.pop(key)
					except KeyError as err:
						print(err)
				if found is False:
					modict[complexchildmoname] = mofound
				continue
			elif param.tag != "p":
				continue

			if not minoccursfound or not maxoccursfound:
				for productData in param.iter("productData"):
					for data in productData:
						if data.attrib["name"] == "MO MaxOccurs":
							maxoccurs = int(data.attrib["value"])
							param.set("name", "instanceid")
							maxoccursfound = True
						elif data.attrib["name"] == "MO MinOccurs":
							minoccurs = int(data.attrib["value"])
							param.set("name", "instanceid")
							minoccursfound = True
						if minoccursfound and maxoccursfound:
							break
			paramname = param.attrib["name"]
			params.append(paramname)

			paramdict["{}-{}".format(moname, paramname)] = GetParamDetail(param)

		fullnamefound = False
		for item in modict:
			pos = item.rfind(fullname)
			if pos != -1 and item[pos :] == fullname:
				fullnamefound = True
				modict[item] = Mo(minoccurs, maxoccurs, params)
				break
		if fullnamefound is False:
				modict[fullname] = Mo(minoccurs, maxoccurs, params)

		#for mo in modict:
			#print("{}:{}".format(mo, modict[mo]))


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
				shift = int(editing.attrib["shift"])
			else:
				shift = 0
			paramrange = editing.find("range")
			minval = int((float(paramrange.attrib["minIncl"]) - shift) * divisor / multiplicand)
			maxval = int((float(paramrange.attrib["maxIncl"]) - shift) * divisor // multiplicand)
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
					values.append(bit.attrib["number"])
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
	modict.clear()
	paramdict.clear()
	
	if scfVar.get() == "" or logVar.get() == "":
		print("SCF or log file is not selected!!!")
		return

	for file in [mrbtsVar.get(), eqmVar.get(), mnlVar.get(), radioVar.get()]:
		if file != "":
			ParseNIDD(file, modict, paramdict)
	
	#for mo in modict:
		#print("{}:{}".format(mo, modict[mo]))
	#for param in paramdict:
		#print("{}:{}".format(param, paramdict[param]))
	
	ValidateSCF(scfVar.get())
	tkinter.messagebox.showinfo(title = "Information", message = "SCF validation complete!")

def ValidateSCF(scf):
	logfilename = logVar.get()

	try:
		etscf = ET.parse(scf)
		root = etscf.getroot()
		logfile = open(logfilename, "w", encoding = "utf8")
		logfile.write("{} validattion begin\n".format(scf))
	except FileNotFoundError as err:
		print(err)
		return

	ns = re.match("\{.*\}", root.tag)
	if ns is not None:
		ns = ns.group(0)
	else:
		ns = None
	cmdata = root.findall("{}cmData".format(ns))
	for data in cmdata:
		MOs = data.findall("{}managedObject".format(ns))
		for mo in MOs:
			classname =  mo.attrib["class"]
			classname = classname[classname.rindex(":") + 1 :]
			distname = mo.attrib["distName"]
			if distname.find("/FTM-") != -1 or classname.find("_R") != -1:
				continue
			result = ValidateInstanceId(classname, distname, logfile)
			if result is True:
				for param in mo:
					ValidateParamValue(classname, distname, param.attrib["name"], param, logfile)

			ValidateMandatoryParams(classname, distname, mo, logfile)
		ValidateMandatoryClass(MOs, logfile)
	logfile.write("{} validation end\n".format(scf))
	logfile.close()

def ValidateMandatoryParams(clsname, distname, mo, logfile):
	try:
		fullclsname, number = re.subn("-[0-9]*", "", distname)
		for paramname in modict[fullclsname].params:
			if paramname == "instanceid":
				continue
			key = "{}-{}".format(clsname, paramname)
			try:
				if paramdict[key].mandatory is True:
					found = False
					for param in mo:
						if param.attrib["name"] == paramname:
							found = True
							break
					if found is False:
						logfile.write("Mandatory parameter {}-{} is missing!\n".format(distname, paramname))
				if paramdict[key].type != "list":
					continue
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
									logfile.write("Mandatory parameter {}-{}-{} is missing!\n".format(distname, paramname, value.name))
			except KeyError:
				logfile.write("Unknown parammeter {}!\n".format(err))
	except KeyError as err:
		print("Unknown object {}!".format(err))

def ValidateMandatoryClass(objlist, logfile):
	for key in modict:
		if key.find("/FTM") != -1:
			continue
		name = ""
		parentname = None
		pos1 = key.rfind("/")
		if pos1 == -1:
			name = key
		else:
			name = key[pos1 + 1 :]
			pos2 = key.rfind("/", 0, pos1)
			if pos2 == -1:
				parentname = key[: pos1]
			else:
				parentname = key[pos2 + 1 : pos1]
		if parentname is None:
			parentcount = 1
		else:
			parentcounts = GetCounts(parentname, objlist, True)
		counts = GetCounts(name, objlist)

		for parentdn in parentcounts:
			for dn in counts:
				if dn[: dn.rfind("/")] == parentdn:
					count = counts[dn]
					if not modict[key].minoccurs <= count <= modict[key].maxoccurs:
						logfile.write("{} object nubmer {} not in range [{}-{}]\n".format(dn, count, modict[key].minoccurs, modict[key].maxoccurs))
					counts.pop(dn)
					break
		for dn in counts:
			fullname, num = re.subn("-[0-9]*", "", dn)
			if fullname == key and parentname is not None:
				logfile.write("{} parent object is missing!\n".format(dn))

def GetCounts(name, objs, isparent = False):
	counts = {}
	for obj in objs:
		classname = obj.attrib["class"]
		classname = classname[classname.rfind(":") + 1 :]
		if classname == name:
			distname = obj.attrib["distName"]
			if isparent is False:
				distname = distname[: distname.rfind("-")]
			if distname in counts:
				counts[distname] += 1
			else:
				counts[distname] = 1
	return counts

def ValidateInstanceId(clsname, distname, logfile):
	result = True
	instid = int(distname[distname.rindex("-") + 1 :])
	key = "{}-{}".format(clsname, "instanceid")
	try:
		if not paramdict[key].min <= instid <= paramdict[key].max:
			logfile.write("{} instance id {} not in range [{}-{}]!\n".format(distname, instid, paramdict[key].min, paramdict[key].max))
			result = False
	except KeyError:
		logfile.write("Unknown object {}!\n".format(distname))
		result = False
	return result

def ValidateParamValue(classname, distname, name, param, logfile, islist = False):
	paramname = param.attrib["name"]
	key = "{}-{}".format(classname, name)
	try:
		if islist is True:
			for item in paramdict[key].values:
				if item.name == paramname:
					paramdn = "{}-{}-{}".format(distname, name, paramname)
					paramtype = item.type
					minval = item.min
					maxval = item.max
					special = item.values
					break
		else:
			paramdn = "{}-{}".format(distname, name)
			paramtype = paramdict[key].type
			minval = paramdict[key].min
			maxval = paramdict[key].max
			special = paramdict[key].values

		if  paramtype == "decimal":
			if not  minval <= int(param.text) <= maxval and param.text not in special:
				logfile.write("{} value {} exceeds range [{}-{}]!\n".format(paramdn, param.text, minval, maxval))
		elif paramtype == "string":
			if not minval <= len(param.text) <= maxval and param.text not in special:
				logfile.write("{} value length {} exceeds range [{}-{}]!\n".format(paramdn, len(param.text), minval, maxval))
		elif paramtype == "boolean":
			if param.text not in ("true", "false"):
				logfile.write("{} value {} is not 'true' or 'false'!\n".format(paramdn, param.text))
		elif paramtype == "enumeration":
			if param.text not in special:
				logfile.write("{} value {} is not in range {}!\n".format(paramdn, param.text, special))
		elif paramtype == "bit":
			if (int(param.text) & 0xFFFF) > maxval:
				logfile.write("{} value {} is not in bit range {}(0-{})!\n".format(paramdn, param.text, special, maxval))
		elif paramtype == "list":
			for item in param.findall("{raml21.xsd}item"):
				for listparam in item:
					ValidateParamValue(classname, distname, paramname, listparam, logfile, True)
	except KeyError:
		logfile.write("Unknown parameter {}-{}\n".format(distname, name))
		#print("{} does not exist".format(key))
		return

if __name__=='__main__':

	root = tkinter.Tk()
	root.title("SCF Validation")
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
