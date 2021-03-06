#!/usr/bin/env python
"""
Dan 2008-10-29: copied this from
CRAB_2_3_1/external/ProdCommon/FwkJobRep/ModifyJobReport.py and
updated for use with farmout jobs.

_ModifyJobReport.py

Example of how to use the FwkJobRep package to update a job report post processing


"""
import os, string
import sys
import popen2
import getopt

from ProdCommon.FwkJobRep.ReportParser import readJobReport

tmp_file_path = "/tmp"
if os.access("/scratch",os.W_OK):
	tmp_file_path = "/scratch"



def readCksum(filename):
	"""
	_readCksum_

	Run a cksum command on a file an return the checksum value

	"""
	pop = popen2.Popen4("cksum %s" % filename)
	while pop.poll() == -1:
		exitStatus = pop.poll()
	exitStatus = pop.poll()
	if exitStatus:
		return None
	content = pop.fromchild.read()
	value = content.strip()
	value = content.split()[0]
	return value


def fileSize(filename):
	"""
	_fileSize_

	Get size of file

	"""
	return os.stat(filename)[6]	

def addFileStats(file):
	"""
	_addFileStats_

	Add checksum and size info to each size

	"""

	pfn = file['PFN']

	file['Size'] = fileSize(pfn)
	checkSum = readCksum(pfn)
	file.addChecksum('cksum',checkSum)

	return

def ShowUsage():
	msg = """
USAGE: ModifyJobReport.py OPTIONS

OPTIONS:
--input-fjr
--output-fjr
--PrimaryDataset
--DataTier
--ProcessedDataset
--ApplicationFamily
--ApplicationName
--ApplicationVersion
--PSetHash
--SEName
--pfn-path
--lfn-path
--strip-input-file-info   (do not publish info about input files)
"""
	sys.stderr.write(msg)


if __name__ == '__main__':

	# Example:  Load the report, update the file stats, pretend to do a stage out
	# and update the information for the stage out

	long_options = [
		"help",
		"input-fjr=",
		"output-fjr=",
		"PrimaryDataset=",
		"DataTier=",
		"ProcessedDataset=",
		"ApplicationFamily=",
		"ApplicationName=",
		"ApplicationVersion=",
		"PSetHash=",
		"SEName=",
		"pfn-path=",
		"lfn-path=",
		"strip-input-file-info"
	]
	options,args = getopt.getopt(sys.argv[1:],"h",long_options)

	strip_input_file_info = 0

	for option,value in options:
		if option == "--help" or option == "-h":
			ShowUsage()
			sys.exit(0)
		elif option == "--input-fjr":
			inputReport = value
		elif option == "--output-fjr":
			outputReport = value
		elif option == "--PrimaryDataset":
			PrimaryDataset = value
		elif option == "--DataTier":
			DataTier = value
		elif option == "--ProcessedDataset":
			ProcessedDataset = value
		elif option == "--ApplicationFamily":
			ApplicationFamily = value
		elif option == "--ApplicationName":
			ApplicationName = value
		elif option == "--ApplicationVersion":
			ApplicationVersion = value
		elif option == "--PSetHash":
			PSetHash = value
		elif option == "--SEName":
			SEName = value
		elif option == "--pfn-path":
			pfn_path = value
		elif option == "--lfn-path":
			lfn_path = value
		elif option == "--strip-input-file-info":
			strip_input_file_info = 1
		else:
			sys.stderr.write("Unexpected option: " + str(option) + "\n")
			sys.exit(2)

	reports = readJobReport(inputReport)
	
	# report is an instance of FwkJobRep.FwkJobReport class
	# can be N in a file, so a list is always returned
	# here I am assuming just one report per file for simplicity
	if len(reports) <> 1:
		sys.stderr.write("ERROR: Found %d reports in " + inputReport + "\n" % len(reports))
		sys.exit(1)

	report = reports[-1]

	if (len(report.files) == 0):
		print "no output file to modify"
		sys.exit(1)

	# CRAB requires this status == "Success"
	# would be nice to know if the job _really_ succeeded
	report.status = "Success"

	# NOTE, ExitCode in the job report is 50117, which means
	# "could not update exit code in job report"
	# I think this is the default set by cmssw and it is
	# supposed to be overridden by the job wrapper.
	# Currently we are not setting it.  Perhaps we
	# should save the exit code and file cksum in
	# a log file (or poke it into the FJR) at runtime
	# and then fix it up here if necessary.  That way,
	# the worker node does not need access to the python
	# code for parsing FJRs.

	for f in report.files:
		fname = f['PFN']
		if not os.path.exists(os.path.join(pfn_path,fname)):
			for i in range(1,100):
				if os.path.exists(os.path.join(pfn_path,str(i),fname)):
					fname = os.path.join(str(i),fname)
					break
		f['PFN'] = os.path.join(pfn_path,fname)
		f['LFN'] = os.path.join(lfn_path,fname)
		f['SEName'] = SEName

		#Generate per file stats
		addFileStats(f)

		if strip_input_file_info:
			f.inputFiles = []

		datasetinfo=f.newDataset()
		datasetinfo['PrimaryDataset'] = PrimaryDataset 
		datasetinfo['DataTier'] = DataTier 
		datasetinfo['ProcessedDataset'] = ProcessedDataset 
		datasetinfo['ApplicationFamily'] = ApplicationFamily 
		datasetinfo['ApplicationName'] = ApplicationName 
		datasetinfo['ApplicationVersion'] = ApplicationVersion
		datasetinfo['PSetHash'] = PSetHash

	if strip_input_file_info:
		report.inputFiles = []

	# After modifying the report, save it to a file.
	report.write(outputReport)
	print "Wrote modified report to " + outputReport
