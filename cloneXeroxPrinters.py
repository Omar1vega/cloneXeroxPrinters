import requests
import os.path
import datetime

baseCloneTuples = (('_fun_function', 'HTTP_Set_Config_Attrib_fn'),
                   ('_fun_function', 'HTTP_Config_Cloning_fn'),
                   ('NextPage', '/properties/cloning_dl.php'))


def find_csrf(html):
    for line in html.split('\n'):
        if 'CSRF' in line:
            line = line[line.find('value=') + len('value="'):line.rfind('"')]
            return line
    return None


def find_clone_parameters(html):
    parameter_str = ''
    tuple_list = []

    for line in html.split('\n'):
        if 'directoryList' in line:
            parameter_str = line
            break
    if parameter_str is not '':
        typeOfParams = 2
        parameter_str = parameter_str.split('=')[1].strip()
        parameter_str = parameter_str.strip('"')
        parameter_str = parameter_str.strip("'")
        for entry in parameter_str.split(','):
            if entry.isnumeric():
                tuple_list.append(('clone_group', entry))
    else:
        typeOfParams = 1
        # parameter str never got assigned, parameter list is in checkboxes within html
        for line in html.split('\n'):
            if ('input type="checkbox"' in line) and ('[' not in line):
                line = line.strip()
                tuple_list.append(('clone_group', line.split('"')[-2]))
    return tuple(tuple_list), typeOfParams


def strip_tags(html_line):
    while html_line.find('<') != -1:
        start = html_line.find('<')
        end = html_line.find('>') + 1
        html_line = html_line.replace(html_line[start:end], '')
    return html_line


def get_model(printer):
    r = requests.get('http://' + printer + '/header.php')
    for line in r.text.split('\n'):
        if 'product' in line:
            model = line
            break
    return strip_tags(model).replace('&reg;', '')


def clone_printer(printer_info_list):
    dept_name = printer_info_list[0].strip()
    printer = printer_info_list[1].strip()
    printer = printer.strip('http://')
    user = printer_info_list[2]
    password = printer_info_list[3]

    print("Cloning Printer:", printer)
    with requests.Session() as s:

        # BASE SITE TO SET UP SESSION WITH COOKIES/SESSION ID
        baseURL = 'http://' + printer + '/properties/cloning.php'
        print("getting base session id and cookies")
        r = s.get(baseURL)
        csrf = find_csrf(r.text)

        # LOGGING INTO PROPERTIES PAGE
        loginURL = 'http://' + printer + '/userpost/xerox.set'
        loginData = {'_fun_function': 'HTTP_Authenticate_fn', 'NextPage': '/properties/authentication/luidLogin.php',
                     'webUsername': user, 'webPassword': password, 'frmaltDomain': 'default'}

        if csrf is not None:
            loginData['CSRFToken'] = csrf

        print("logging in...")
        r = s.post(loginURL, data=loginData, cookies=requests.utils.dict_from_cookiejar(s.cookies))

        # CHECKING IF LOGIN WAS SUCCESSFUL
        for line in r.text.split('\n'):
            if 'invalid=t' in line:
                print("Invalid Login Credential for", printer_info_list,
                      "\nUnable to access clone page\nSkipping this printer")
                return
        print("logged in!")

        # GETTING CLONE PARAMETERS FROM BASEURL HTML (ALL THE CHECKBOXES
        r = s.get(baseURL, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        cloneParameters, retrievalType = find_clone_parameters(r.text)
        cloneParameters = baseCloneTuples + cloneParameters
        if csrf is not None:
            cloneParameters = cloneParameters + (('CSRFToken', csrf),)

        # POSTING ALL CLONE PARAMETERS FOUND ON CLONE PAGE
        clonePostURL = 'http://' + printer + '/dummypost/xerox.set'
        print("asking printer to create clone file...")
        s.post(clonePostURL, data=cloneParameters, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        print("POST COMPLETE")

        if retrievalType == 1:
            cloneFileURL = 'http://' + printer + '/properties/cloneDownload.php'
        elif retrievalType == 2:
            cloneFileURL = 'http://' + printer + '/download/cloning.dlm'

        # DOWNLOADING CLONE FILE 
        print("downloading clone file")
        r = s.get(cloneFileURL, cookies=requests.utils.dict_from_cookiejar(s.cookies))
        # WRITING CLONE TO FILE
        if not (os.path.isdir(dept_name)):
            os.makedirs(dept_name)
        fileName = dept_name + '/' + datetime.datetime.today().strftime('%Y.%m.%d_') \
                   + get_model(printer).replace(' ', '') + '_' + printer + '.dlm '
        with(open(fileName, 'wb')) as clone:
            clone.write(r.content)
            print(printer + " clone file written !")


def main():
    if not (os.path.isfile('printers.txt')):
        #  no config file found
        print("""No configuration file ('printers.txt') was found in the current directory
              \nMake sure this file exists and is in the current directory with the following format separated by commas
              \n DEPT_NAME,PRINTER_IP,USERNAME,PASSWORD""")
    else:
        with(open('printers.txt', 'r')) as file:
            lines = file.readlines()
        for line in lines:
            if line[0] == '#':
                continue
            print(line[0])
            line = line.strip('\n')
            printer = line.split(',')
            clone_printer(printer)


main()
