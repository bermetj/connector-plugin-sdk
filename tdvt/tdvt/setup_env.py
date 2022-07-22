import re
import sys
from pathlib import Path

from .config_gen.datasource_list import print_logical_configurations
from .config_gen.test_creator import TestCreator
from .resources import *


def create_test_environment():
    """Create directories and necessary ini files."""
    create_setup_structure()
    create_tdvt_ini_file()


def create_setup_structure():
    try:
        os.mkdir('tds')
    except:
        pass
    try:
        os.makedirs('config/tdvt')
    except:
        pass


def create_tdvt_ini_file():
    try:
        ini_path = 'config/tdvt/tdvt_override.ini'
        if os.path.isfile(ini_path):
            return
        ini = open(ini_path, 'w')
        ini.write('#Add paths to tabquery executable.\n')
        ini.write('[DEFAULT]\n')
        ini.write('TAB_CLI_EXE_X64 = Full Or Relative/Path/to/tabquerytool.exe\n')
        ini.write('TAB_CLI_EXE_MAC = Full Or Relataive/Path/to/tabquerytool.exe\n')
        print("Created ini file: " + ini_path)
        print("Please set the tabquery executable file path.")
    except:
        pass


def add_datasource(name, ds_registry):
    """
        Create the datasource ini file and try to rename the connections in the tds file.
        This is a necessary step for the logical query tests.
    """
    print("Make sure you have already saved the appropriate TDS files in the tds directory.")
    print("Adding a new datasource [" + name + "] ...")

    connection_password_name = name + "_connection"
    if input(
            "Would you like to setup a password file? (y/n) This is suitable for a single connection per tds (standard).").lower() == 'y':  # noqa: E501
        password = input("Enter the datasource password:")
        create_password_file(name, connection_password_name, password)
    picked = False
    logical = None
    custom_schema_name = None
    custom_table_name = None

    # Find out if the datasource uses custom table and create test files accordingly
    if input("Would you like to run TDVT against a schema other than TestV1? (y/n) ").lower() == 'y':
        custom_schema_name = input("Enter the schema name: ")

    if input("Would you like to run TDVT against a custom table? (y/n)").lower() == 'y':
        custom_table = True
        csv_path = input("Enter the path to the custom table csv file:")

        output = input("Enter the output path for generated test files (default CWD):")
        output_dir = Path(output)
        if not output_dir.is_dir():
            print("Output directory does not exist. Please try again")
            sys.exit()

        tc = TestCreator(csv_path, name, output_dir)
        headers, formatted_results = tc.parse_csv_to_list()
        tc.write_expecteds_to_file(headers, False)  # this creates the test setup file.

    while not picked:
        logical = input(
            "Enter the logical config to use or type 'list' to see the options or 's' to skip selecting one now:")  # naqa: E501
        if logical == 'list':
            print_logical_configurations(ds_registry)
        else:
            logical = logical.replace("\"", "")
            logical = logical.replace("\'", "")
            logical = logical.strip()
            picked = True
        if logical == 's':
            logical = None

    create_ds_ini_file(name, logical, custom_schema_name, custom_test_dir)
    update_tds_files(name, connection_password_name)


def create_ds_ini_file(name, logical_config, custom_schema: bool = False, custom_test_dir=None):  # TODO: Update to be flexible depending on custom schema.
    try:
        ini_path = 'config/' + name + '.ini'
        if os.path.isfile(ini_path):
            overwrite = input("Overwrite existing ini file?(y/n)")
            if overwrite.lower() != 'y':
                return
        ini = open(ini_path, 'w')

        ini.write('[Datasource]\n')
        ini.write('Name = ' + name + '\n')
        if not logical_config:
            ini.write('LogicalQueryFormat = TODO\n')
        else:
            ini.write('LogicalQueryFormat = ' + logical_config + '\n')
        ini.write('\n')
        # TODO: the next part is taken out for custom schema
        ini.write('[StandardTests]\n')
        ini.write('\n')
        ini.write('[LODTests]\n')
        ini.write('\n')
        ini.write('[UnionTest]\n')
        ini.write('\n')
        ini.write('[ConnectionTests]\n')
        ini.write('StaplesTestEnabled = True\n')
        ini.write('CastCalcsTestEnabled = True\n')
        # TODO: custom schema block goes here
        # blah
        ini.write('\n')

        print("Created ini file: " + ini_path)
        if not logical_config:
            print("Please set the LogicalQueryFormat value to the expected format.")

    except:
        pass


def create_password_file(name, connection_name, password):
    try:
        file_path = 'tds/' + name + '.password'
        if os.path.isfile(file_path):
            overwrite = input("Overwrite existing file?(y/n): " + file_path)
            if overwrite.lower() != 'y':
                return
        ini = open(file_path, 'w')

        ini.write(connection_name + ';' + password + '\n')

        print("Created file: " + file_path)
    except IOError as e:
        print(e)
        pass


def update_tds_files(name, connection_password_name):
    # TODO: change this to get rid of calcs/staples hardcoding; handle custom table then fall back
    mangle_tds(get_tds_full_path(get_root_dir(), 'cast_calcs.' + name + '.tds'),
               connection_password_name)  # TODO: Update this to take whatever
    mangle_tds(get_tds_full_path(get_root_dir(), 'Staples.' + name + '.tds'), connection_password_name)


def mangle_tds(file_path, connection_password_name):
    print('Modifying ' + file_path)
    try:
        r1 = re.compile('(^\s*<named-connection .*? name=\').*?(\'>)')
        r2 = re.compile('(^\s*<.*relation connection=\').*?(\' .*>)')
        r3 = re.compile('(^\s*<connection .*?)(\s*/>)')

        f = open(file_path, 'r')
        new_tds = ''
        for line in f:
            new_line = line.rstrip()
            m1 = r1.match(line)
            if m1:
                new_line = m1.group(1) + 'leaf' + m1.group(2)

            m2 = r2.match(line)
            if m2:
                new_line = m2.group(1) + 'leaf' + m2.group(2)

            m3 = r3.match(line)
            if m3 and not 'tdvtconnection=\'' in line.lower():
                new_line = m3.group(1) + ' tdvtconnection=\'' + connection_password_name + '\' ' + m3.group(2)

            new_tds += new_line + '\n'

        f.close()
        f = open(file_path, 'w')
        f.write(new_tds)
        f.close()
    except IOError as e:
        print(e)
        return
