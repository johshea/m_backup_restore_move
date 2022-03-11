# This is a script to migrate the switchport configuration of one organization to another.
# Forked from the Meraki Automation Hub - modernized and enhanced
# The script can be used to export switchport configuration of a source org to a file and 
#  import it to a destination org. The script will look for the exact same network names and
#  device serial numbers, as they were in the source org. Use copynetworks.py and movedevices.py
#  to migrate networks and devices if needed. The recommended migration workflow is:
#   * Copy networks with copynetworks.py
#   * Export device info with movedevices.py -m export
#   * Export switchport configuration with copyswitchcfg.py -m export
#   * Run additional export scripts
#   * Remove devices from networks with movedevices.py -m remove
#   * Unclaim devices manually and wait for them to become claimable again
#   * Import device info with movedevices.py -m import
#   * Import switchport configuration with copyswitchcfg.py -m import
#   * Run additional import scripts
#
# The script will only process devices that are part of a network.
# It has 2 modes of operation:
#  * python copyswitchcfg.py -k <key> -o <org> -m export -f <file>
#     This mode will export switchport configuration of all swithces in the org to a file.
#	  This is the default mode.
#  * python copyswitchcfg.py -k <key> -o <org> -m import -f <file>
#     Import all switchport configuration in <file> to the specified organization. 
#
# You need to have Python 3 and the Meraki SDK module installed. You
#
#  or install it using pip (pip(3) install meraki).
#
# To run the script, enter:
#  python copyswitchcfg.py -k <key> -o <org> [-m export/import] -f <file>
#
# If option -m is not defined, export mode will be assumed. The 2 valid forms of this parameter are:
#  -m export
#  -m import
#
# To make script chaining easier, all lines containing informational messages to the user
#  start with the character @

import sys, getopt, meraki, json, datetime


def printusertext(p_message):
	#prints a line of text that is meant for the user to read
	#do not process these lines when chaining scripts
	print('@ %s' % p_message)

def printhelp():
	#prints help text

	printusertext('# This is a script to migrate the switchport configuration of one organization to another.')
	printusertext('')
	printusertext('Usage:')
	printusertext('python copyswitchcfg.py -k <key> -o <org> [-m export/import] -f <file>')
	printusertext('')
	printusertext('If option -m is not defined, export mode will be assumed.')
	printusertext('The 2 valid forms of this parameter are:')
	printusertext(' -m export')
	printusertext(' -m import')
	printusertext('')
	printusertext(' # python copyswitchcfg.py -k <key> -o <org> -m export -f <file>')
	printusertext('    This mode will export switchport configuration of all swithces in the org to a file.')
	printusertext('	   This is the default mode.')
	printusertext(' # python copyswitchcfg.py -k <key> -o <org> -m import -f <file>')
	printusertext('    Import all switchport configuration in <file> to the specified organization.')
	printusertext('')
	printusertext('The script will only process devices that are part of a network.')
	printusertext('')
	printusertext('Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.')


		
def main(argv):
	#set default values for command line arguments
	arg_apikey = 'null'
	arg_orgname = 'null'
	arg_mode = 'export'
	arg_filepath = 'null'
		
	#get command line arguments
	try:
		opts, args = getopt.getopt(argv, 'hk:o:m:f:')
	except getopt.GetoptError:
		printhelp()
		sys.exit(2)
	
	for opt, arg in opts:
		if opt == '-h':
			printhelp()
			sys.exit()
		elif opt == '-k':
			arg_apikey = arg
		elif opt == '-o':
			arg_orgname = arg
		elif opt == '-m':
			arg_mode = arg
		elif opt == '-f':
			arg_filepath = arg
			
	#check if parameter -m has one a valid value. blank is also OK, as export is default
	mode_export = True
	modenotvalid = True
	if arg_mode == 'import':
		modenotvalid = False
		mode_export = False
	elif arg_mode == 'export':
		modenotvalid = False
	
	#check if all parameters are required parameters have been given
	if arg_apikey == 'null' or arg_orgname == 'null' or arg_filepath == 'null' or modenotvalid:
		printhelp()
		sys.exit(2)

	dashboard = meraki.DashboardAPI(arg_apikey, suppress_logging=True)

	#get organization id corresponding to org name provided by user
	org = dashboard.organizations.getOrganizations()

	for record in org:
		if record['name'] == arg_orgname:
			orgid = record['id']
		elif record['name'] == 'null':
			printusertext('ERROR: Fetching organization failed')
			sys.exit(2)

	
	#get network list for fetched org id
	nwlist = dashboard.organizations.getOrganizationNetworks(
    orgid, total_pages='all')

	if nwlist[0]['id'] == 'null':
		printusertext('ERROR: Fetching network list failed')
		sys.exit(2)
	
	#if export mode, open file for writing. if import mode, open file for reading
	if mode_export:
		#if parameter -m export, open file for writing
		try:
			f = open(arg_filepath, 'w')
		except:
			printusertext('ERROR: Unable to open file for writing')
			sys.exit(2)
	else:
		#if parameter -m import, open file for reading
		try:
			f = open(arg_filepath, 'r')
		except:
			printusertext('ERROR: Unable to open file for reading')
			sys.exit(2)
		
	#define list for all switchports for source org
	orgswitchports = []
		
	if mode_export:
		#devices in network
		devicelist = []
		#switchports in a single device
		devswitchports = []
		
		for nwrecord in nwlist:
			#all switchports in a single network
			nwswitchports = []
			devicelist = dashboard.networks.getNetworkDevices(nwrecord['id'])
			#print(devicelist)
			for devrecord in devicelist:
				#print(devrecord)
				if devrecord['model'][:2] == 'MS':
					print(devrecord)
					#get switchports in device
					devswitchports = dashboard.switch.getDeviceSwitchPorts(devrecord['serial'])
					#devswitchports [0]['portId'] will be 'null' if anything went wrong (device not an MS switch, etc)
					#print(devswitchports)
					if devswitchports[0]['portId'] != 'null':
						#app end dev switchports to network list
						nwswitchports.append( {'serial': devrecord['serial'], 'devports' : devswitchports} )
			if len(nwswitchports) > 0:
				orgswitchports.append( {'network': nwrecord['name'], 'nwports': nwswitchports} )
			else:
				printusertext('WARNING: Skipping network "%s": No switchports' % nwrecord['name'])

		#write org switchports' list to file
		try:
			json.dump(orgswitchports, f)
		except:
			printusertext('ERROR: Writing to output file failed')
			sys.exit(2)		
	else:
		#import mode
		
		#read org switchports' list from file
		try:
			orgswitchports = json.load(f)
			#print(orgswitchports)
		except:
			printusertext('ERROR: Reading from file failed')
			sys.exit(2)	
				
		#upload switchport configuration to Dashboard
		for nwrecord in orgswitchports:
			print("nwrecord marker")
			for devrecord in nwrecord['nwports']:
				print("devrecord marker")
				#print(devrecord)
				printusertext('INFO: Configuring device %s' % devrecord['serial'])
				for swport in devrecord['devports']:
					print("swport marker")
					if swport['accessPolicyType'] != 'Open':
						importsw = dashboard.switch.updateDeviceSwitchPort(devrecord['serial'], swport['portId'],
										isolationEnabled = swport['isolationEnabled'],
										rstpEnabled = swport['rstpEnabled'],
										enabled = swport['enabled'],
										stpGuard = swport['stpGuard'],
										accessPolicyType = swport['accessPolicyType'],
										accessPolicyNumber = swport['accessPolicyNumber'],
										type = swport['type'],
										allowedVlans = swport['allowedVlans'],
										poeEnabled = swport['poeEnabled'],
										name = swport['name'],
										tags = swport['tags'],
										vlan = swport['vlan'],
										voiceVlan = swport['voiceVlan'])
						#print(importsw)
					else:
						importsw = dashboard.switch.updateDeviceSwitchPort(devrecord['serial'], swport['portId'],
										isolationEnabled=swport['isolationEnabled'],
										rstpEnabled=swport['rstpEnabled'],
										enabled=swport['enabled'],
										stpGuard=swport['stpGuard'],
										accessPolicyType=swport['accessPolicyType'],
										type=swport['type'],
										allowedVlans=swport['allowedVlans'],
										poeEnabled=swport['poeEnabled'],
										name=swport['name'],
										tags=swport['tags'], vlan=swport['vlan'],
										voiceVlan=swport['voiceVlan'])

						#print(importsw)

		printusertext('End of script.')
			
if __name__ == '__main__':
	main(sys.argv[1:])