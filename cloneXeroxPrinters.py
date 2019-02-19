import requests
import os.path
import datetime

baseCloneTuples = (('_fun_function', 'HTTP_Set_Config_Attrib_fn'),
                   ('_fun_function', 'HTTP_Config_Cloning_fn'),
                   ('NextPage', '/properties/cloning_dl.php'))


def findCSRF(html):
    for line in html.split('\n'):
        if ('CSRF' in line):
            line = line[line.find('value=') + len('value="'):line.rfind('"')]
            return line
    return None


def findCloneParameters(html):
    typeOfParams = 0
    paramList = []
    parameterStr = ''
    tupleList = []

    for line in html.split('\n'):
        if ('directoryList' in line):
            parameterStr = line
            break
    if (parameterStr is not ''):
        typeOfParams = 2
        parameterStr = parameterStr.split('=')[1].strip()
        parameterStr = parameterStr.strip('"')
        parameterStr = parameterStr.strip("'")
        for entry in parameterStr.split(','):
            if (entry.isnumeric()):
                tupleList.append(('clone_group', entry))
    else:
        typeOfParams = 1
        ##par str never got assigned, parameter list is in checkboxes within html
        for line in html.split('\n'):
            if (('input type="checkbox"' in line) and ('[' not in line)):
                line = line.strip()
                tupleList.append(('clone_group', line.split('"')[-2]))
    return (tuple(tupleList), typeOfParams)


def stripTags(htmlLine):
    while htmlLine.find('<') != -1:
        start = htmlLine.find('<')
        end = htmlLine.find('>') + 1
        htmlLine = htmlLine.replace(htmlLine[start:end], '')
    return htmlLine


def getModel(printer):
    r = requests.get('http://' + printer + '/header.php')
    for line in r.text.split('\n'):
        if 'product' in line:
            model = line
            break
    return stripTags(model).replace('&reg;', '')


def clonePrinter(printerInfoList):
    deptName = printerInfoList[0].strip()
    printer = printerInfoList[1].strip()
    printer = printer.strip('http://')
    user = printerInfoList[2]
    password = printerInfoList[3]

    print(
        "***************************************************************************************************************************************")
    print("Cloning Printer:", printer)
    with requests.Session() as s:

        retrievalType = 0

        ##BASE SITE TO SET UP SESSION WITH COOKIES/SESSION ID
        baseURL = 'http://' + printer + '/properties/cloning.php'
        print("getting base session id and cookies")
        r = s.get(baseURL)
        csrf = findCSRF(r.text)

        ##LOGING INTO PROPERTIES PAGE
        loginURL = 'http://' + printer + '/userpost/xerox.set'
        loginData = {'_fun_function': 'HTTP_Authenticate_fn', 'NextPage': '/properties/authentication/luidLogin.php',
                     'webUsername': user, 'webPassword': password, 'frmaltDomain': 'default'}

        if csrf is not None:
            loginData['CSRFToken'] = csrf

        print("logging in...")
        r = s.post(loginURL, data=loginData, cookies=requests.utils.dict_from_cookiejar(s.cookies))

        ##CHEKING IF LOGIN WAS SUCCESSFUL 
        for line in r.text.split('\n'):
            if ('invalid=t' in line):
                print("Invalid Login Credential for", printerInfoList,
                      "\nUnable to access clone page\nSkipping this printer")
                return
        print("logged in!")

        ##GETTING CLONE PARAMETERS FROM BASEURL HTML (ALL THE CHECKBOXES
        r = s.get(baseURL, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        cloneParameters, retrievalType = findCloneParameters(r.text)
        cloneParameters = baseCloneTuples + cloneParameters
        if csrf is not None:
            cloneParameters = cloneParameters + (('CSRFToken', csrf),)

        ##POSTING ALL CLONE PARAMETERS FOUND ON CLONE PAGE
        clonePostURL = 'http://' + printer + '/dummypost/xerox.set'
        print("asking printer to create clone file...")
        r = s.post(clonePostURL, data=cloneParameters, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        print("POST COMPLETE")

        if (retrievalType == 1):
            cloneFileURL = 'http://' + printer + '/properties/cloneDownload.php'
        elif (retrievalType == 2):
            cloneFileURL = 'http://' + printer + '/download/cloning.dlm'

        ##DOWNLOADING CLONE FILE 
        print("downloading clone file")
        r = s.get(cloneFileURL, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        ##WRITING CLONE TO FILE
        if not (os.path.isdir(deptName)):
            os.makedirs(deptName)
        fileName = deptName + '/' + datetime.datetime.today().strftime('%Y.%m.%d_') + getModel(printer).replace(' ',
                                                                                                                '') + '_' + printer + '.dlm'
        with(open(fileName, 'wb')) as clone:
            clone.write(r.content)
            print(printer + " clone file written !")
        print(
            "***************************************************************************************************************************************\n\n\n")


def main():
    if not (os.path.isfile('printers.txt')):
        ## no config file found
        print("""No configuration file ('printers.txt') was found in the current dirrectory
              \nMake sure this file exists and is in the current directory with the following format seperated by commas
              \n DEPT_NAME,PRINTER_IP,USERNAME,PASSWORD""")
    else:
        with(open('printers.txt', 'r')) as file:
            lines = file.readlines()
        for line in lines:
            if (line[0] == '#'):
                continue
            print(line[0])
            line = line.strip('\n')
            printer = line.split(',')
            clonePrinter(printer)


main()
