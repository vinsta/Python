
import xml.etree.ElementTree as ET
import collections
import re
import os
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox
import tkinter.scrolledtext

Param = collections.namedtuple("Param", "name mandatory type min max values")
Mo = collections.namedtuple("Mo", "minoccurs maxoccurs params")
modict = {}
paramdict = {}
global textview

def ParseNIDD(niddpath):
	modict.clear()
	paramdict.clear()
	filelist = []
	for filename in os.listdir(niddpath):
		filename = os.path.join(niddpath, filename)
		if not filename.endswith(".xml"):
			continue
		et = ET.parse(filename)
		header = et.find("header")
		if header is None:
			continue
		try:
			product = header.attrib["product"]
			if product == "MRBTS":
				print("MRBTS file is found: {}".format(filename))
				filelist.append(filename)
			elif product == "EQM":
				print("EQM file is found: {}".format(filename))
				filelist.append(filename)
			elif product == "MNL":
				print("MNL file is found: {}".format(filename))
				filelist.append(filename)
			elif product == "LTE BTS":
				print("RADIO file is found: {}".format(filename))
				filelist.append(filename)
		except KeyError:
			continue

	if len(filelist) == 0:
		print("No NIDD file is found!")
		return False

	for filename in filelist:
		ParseNIDDFile(filename)

	return True

def ParseNIDDFile(file):
	tempmodict = {}
	tempparamdict = {}
	et = ET.parse(file)
	MOs = et.findall("managedObject")
	for mo in MOs:
		params = []
		moname = mo.attrib["class"]
		if moname == "FTM":
			continue
		fullname = moname
		if moname == "EQM":
			fullname = "MRBTS/EQM"
		elif moname == "MNL":
			fullname = "MRBTS/MNL"
		elif moname == "LNBTS":
			fullname = "MRBTS/LNBTS"
		for name in tempmodict:
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
				if simplechildmoname == "FTM":
					continue
				complexchildmoname = "{}/{}".format(fullname, simplechildmoname)
				keystoremove.clear()
				found = False
				for item in tempmodict:
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
								mofound = tempmodict[item]
				for key in keystoremove:
					try:
						tempmodict[keystoremove[key]] = tempmodict[key]
						tempmodict.pop(key)
					except KeyError as err:
						print(err)
				if found is False:
					tempmodict[complexchildmoname] = mofound
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
		for item in tempmodict:
			pos = item.rfind(fullname)
			#if pos != -1 and item[pos :] == fullname and :
			if item == fullname or (pos != -1 and item[pos :] == fullname and item[pos - 1] == "/"):
				fullnamefound = True
				if tempmodict[item] is None:
					tempmodict[item] = Mo(minoccurs, maxoccurs, params)
				break
		if fullnamefound is False:
				tempmodict[fullname] = Mo(minoccurs, maxoccurs, params)

	keystoremove = []
	for x in tempmodict:
		if not x.startswith("MRBTS"):
			keystoremove.append(x)
	for x in keystoremove:
		tempmodict.pop(x)
	modict.update(tempmodict)


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

def ValidateSCF(scfpath):
	for filename in os.listdir(scfpath):
		filename = os.path.join(scfpath, filename)
		if not filename.endswith(".xml"):
			continue
		try:
			etscf = ET.parse(filename)
			root = etscf.getroot()
			WriteLog("{}\n".format("#" * 50))
			WriteLog("{} validattion begin\n".format(filename))
			WriteLog("{}\n".format("#" * 50))
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
				pos = classname.rfind(":")
				if pos != -1:
					classname = classname[pos + 1 :]
				distname = mo.attrib["distName"]
				if distname.find("/FTM-") != -1 or classname.find("_R") != -1:
					continue
				result = ValidateInstanceId(classname, distname)
				if result is True:
					for param in mo:
						ValidateParamValue(classname, distname, param.attrib["name"], param)

				ValidateMandatoryParams(classname, distname, mo)
		ValidateMandatoryClass(MOs)
	WriteLog("{} validation end\n".format(filename))

def ValidateMandatoryParams(clsname, distname, mo):
	try:
		fullclsname, number = re.subn("-[0-9]*", "", distname)
		for paramname in modict[fullclsname].params:
			if paramname == "instanceid":
				continue
			key = "{}-{}".format(clsname, paramname)
			if paramdict[key].mandatory is True:
				found = False
				for param in mo:
					if param.attrib["name"] == paramname:
						found = True
						break
				if found is False:
					WriteLog("Mandatory parameter {}-{} is missing!\n".format(distname, paramname))
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
								WriteLog("Mandatory parameter {}-{}-{} is missing!\n".format(distname, paramname, value.name))
	except (KeyError, AttributeError) as err:
		print(err)

def ValidateMandatoryClass(objlist):
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

		try:
			for parentdn in parentcounts:
				for dn in counts:
					if dn[: dn.rfind("/")] == parentdn:
						count = counts[dn]
						if not modict[key].minoccurs <= count <= modict[key].maxoccurs:
							WriteLog("{} object nubmer {} not in range [{}-{}]\n".format(dn, count, modict[key].minoccurs, modict[key].maxoccurs))
						counts.pop(dn)
						break
			for dn in counts:
				fullname, num = re.subn("-[0-9]*", "", dn)
				if fullname == key and parentname is not None:
					WriteLog("{} parent object is missing!\n".format(dn))
		except AttributeError as err:
			print(err)
			print(dn, parentdn)

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

def ValidateInstanceId(clsname, distname):
	result = True
	instid = int(distname[distname.rindex("-") + 1 :])
	key = "{}-{}".format(clsname, "instanceid")
	try:
		if not paramdict[key].min <= instid <= paramdict[key].max:
			WriteLog("{} instance id {} not in range [{}-{}]!\n".format(distname, instid, paramdict[key].min, paramdict[key].max))
			result = False
	except KeyError:
		WriteLog("Unknown object {}!\n".format(distname))
		result = False
	return result

def ValidateParamValue(classname, distname, name, param, islist = False):
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

		if  paramtype == "decimal" or paramtype == "string":
			values = []
			if param.tag.endswith("list"):
				tagname = param.tag.replace("list", "p")
				for tag in param.findall(tagname):
					values.append(tag.text)
			else:
				values.append(param.text)
			for value in values:
				if paramtype == "decimal":
					if not  minval <= int(value) <= maxval and value not in special:
						WriteLog("{} value {} exceeds range [{}-{}]!\n".format(paramdn, value, minval, maxval))
				elif paramtype == "string":
					if not minval <= len(value) <= maxval and len(value) not in special:
						WriteLog("{} value length {} exceeds range [{}-{}]!\n".format(paramdn, len(param.text), minval, maxval))
		elif paramtype == "boolean":
			if param.text not in ("true", "false"):
				WriteLog("{} value {} is not 'true' or 'false'!\n".format(paramdn, param.text))
		elif paramtype == "enumeration":
			if param.text not in special:
				WriteLog("{} value {} is not in range {}!\n".format(paramdn, param.text, special))
		elif paramtype == "bit":
			if (int(param.text) & 0xFFFF) > maxval:
				WriteLog("{} value {} is not in bit range {}(0-{})!\n".format(paramdn, param.text, special, maxval))
		elif paramtype == "list":
			for item in param.findall("{raml21.xsd}item"):
				for listparam in item:
					ValidateParamValue(classname, distname, paramname, listparam, True)
	except KeyError:
		WriteLog("Unknown parameter {}-{}\n".format(distname, name))
		#print("{} does not exist".format(key))
		return

def SelectDir(var):
	#filename = tkinter.filedialog.askopenfilename(filetypes=[("xml file", "*.xml")])
	dirname = tkinter.filedialog.askdirectory()
	#filename = "{}{}".format(filename, "/log.txt")
	var.set(dirname)

def OnValidate():
	global textview
	textview.delete(1.0, "end")

	if niddpath.get() == "" or scfpath.get() == "":
		print("SCF or file is not selected!!!")
		tkinter.messagebox.showinfo(title = "Information", message = "NIDD or SCF directory is not specified!")
		return

	result = ParseNIDD(niddpath.get())
	
	#for mo in modict:
		#print("{}:{}".format(mo, modict[mo]))
	#for param in paramdict:
		#print("{}:{}".format(param, paramdict[param]))
	
	if result is True:
		ValidateSCF(scfpath.get())

	if result is True:
		message = "SCF validation complete!"
	else:
		message = "SCF validation failure!"
	tkinter.messagebox.showinfo(title = "Information", message = message)

def WriteLog(text):
	global textview
	textview.insert("current", text)
	textview.insert("current", "-" * 50 + "\n")

def ExportLog():
	global textview
	filename = 	tkinter.filedialog.asksaveasfilename()
	logfile = open(filename, "w", encoding = "utf8")
	logfile.write(textview.get(0.0, "end"))
	logfile.close()

if __name__=='__main__':
	global textview

	root = tkinter.Tk()
	root.title("SCF Validator")
	root.columnconfigure(1, weight = 1)

	niddpath = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "NIDD", command = lambda:SelectDir(niddpath)).grid(row = 0, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = niddpath, width = 30).grid(row = 0, column  = 1, padx = 4, pady = 4, sticky = "wesn")
	
	scfpath = tkinter.StringVar()
	tkinter.ttk.Button(root, text = "SCF", command = lambda:SelectDir(scfpath)).grid(row = 1, column = 0, padx = 4, pady = 4)
	tkinter.ttk.Entry(root, textvariable = scfpath, width = 30).grid(row = 1, column  = 1, padx = 4, pady = 4, sticky = "wesn")
	
	#mrbtsVar= tkinter.StringVar()
	#tkinter.ttk.Button(root, text = "MRBTS", command = lambda:OpenFile(mrbtsVar)).grid(row = 0, column = 0, padx = 4, pady = 4)
	#tkinter.ttk.Entry(root, textvariable = mrbtsVar, width = 30).grid(row = 0, column  = 1, padx = 4, pady = 4, sticky = "wesn")

	#eqmVar = tkinter.StringVar()
	#tkinter.ttk.Button(root, text = "EQM", command = lambda:OpenFile(eqmVar)).grid(row = 1, column = 0, padx = 4, pady = 4)
	#tkinter.ttk.Entry(root, textvariable = eqmVar, width = 30).grid(row = 1, column = 1, padx = 4, pady = 4, sticky = "wesn")

	#mnlVar = tkinter.StringVar()
	#tkinter.ttk.Button(root, text = "MNL", command = lambda:OpenFile(mnlVar)).grid(row = 2, column = 0, padx = 4, pady = 4)
	#tkinter.ttk.Entry(root, textvariable = mnlVar, width = 30).grid(row = 2, column = 1, padx = 4, pady = 4, sticky = "wesn")

	#radioVar = tkinter.StringVar()
	#tkinter.ttk.Button(root, text = "RADIO", command = lambda:OpenFile(radioVar)).grid(row = 3, column = 0, padx = 4, pady = 4)
	#tkinter.ttk.Entry(root, textvariable = radioVar, width = 30).grid(row = 3, column = 1, padx = 4, pady = 4, sticky = "wesn")

	#scfVar = tkinter.StringVar()
	#tkinter.ttk.Button(root, text = "SCF", command = lambda:OpenFile(scfVar)).grid(row = 4, column = 0, padx = 4, pady = 4)
	#tkinter.ttk.Entry(root, textvariable = scfVar, width = 30).grid(row = 4, column = 1, padx = 4, pady = 4, sticky = "wesn")

	tkinter.ttk.Button(root, text = "Validate", command = OnValidate).grid(row = 5, column = 0,  columnspan = 1, padx = 4, pady = 4)
	#tkinter.ttk.Button(root, text = "Export LOG", command = ExportLog).grid(row = 6, column = 0, padx = 4, pady = 4)

	textview = tkinter.scrolledtext.ScrolledText(root, font = ('Arial', '12', 'normal'), wrap = "word")
	textview.grid(row = 6, column = 0, columnspan = 2, sticky = "wesn")
	
	root.mainloop()
