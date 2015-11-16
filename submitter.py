import csv
from collections import defaultdict
import yaml
import os

class LurkerLogicTable(object):
	def __init__(self, llt, prt):
		self.pipelines = []
		self.resources = defaultdict(dict)
		self.dd = defaultdict(list)

		f = open(llt, 'rb')  # opens the csv file
		lurker_file = csv.reader(f, delimiter="\t")  # creates the reader object

		for row in lurker_file: # iterates the rows of the file in orders
			print(row)
			#self.pipelines.append( PipelineLogic(row) )
			pipeline_name = row.pop(0)
			pipeline_commands = filter(None, row) #unlist
			#print(pipeline_name)
			self.dd[pipeline_name].append(pipeline_commands)

		f = open(prt, 'rb')  # opens the csv file
		resource_file = csv.DictReader(f, delimiter="\t")  # creates the reader object


		# Use the yaml config instead of this.
		# outdated:
#		for row in resource_file: # iterates the rows of the file in orders
#			print(row)
#			#self.pipelines.append( PipelineLogic(row) )
#			pipeline_name = row.pop("PIPELINE")
#			file_size = row.pop("MIN_GB")
#			print(file_size)
#			print(row)
#			pipeline_commands = row#filter(None, row)
#			#print(pipeline_name)
#			self.resources[pipeline_name][file_size] = pipeline_commands

	def getSize(filename):
		st = os.stat(filename)
		return st.st_size

	def build_pipeline(self, name):
		print("Building pipeline " + name)
		print(self.dd[name])
		for value in self.dd[name]:
			for i in range(0,len(value)):
				if i == 0:
					self.parse_parallel_jobs(value[i], None)
				else:
					self.parse_parallel_jobs(value[i], value[i-1])


	def parse_parallel_jobs(self, job, dep):
		job = job.replace("(", "")
		job = job.replace(")", "")

		split_jobs = [x.strip() for x in job.split(',')]
		if len(split_jobs) > 1:
			for s in split_jobs:
				self.submit_job(s, dep)
		else:
			self.submit_job(job, dep)

	def submit_job(self, job, dep, resources=None):
		print("Submit. Name:" + job + "\tDep:" + str(dep) + "\tRes:")
		print("\t" +  str(self.resources[job]))
		resource_profile = self.resource_lookup(82, self.resources[job])
	
		print("\t" +  str(self.resources[job][resource_profile]))




	def printme(self):
		for i in self.pipelines:
			print(i)

		print("dd:")
		print(self.dd)
		for i in self.dd:
			print(i)


class PipelineLogic(object):
	def __init__(self, lst):
		self.name = lst.pop(0)
		self.commands = filter(None, lst)
	def __str__(self):
		return("Name: " + str(self.name) + "\tCommands: " + str(self.commands))



psa = "basic_sample_table.tsv"
llt = "lurker_logic_table.tsv"
prt = "pipeline_resource_table.tsv"




f = open(psa, 'rb')  # opens the csv file
processed_samples = {}

input_file = csv.DictReader(f, delimiter="\t")  # creates the reader object


# We can use a yaml config file and then we don't have to parse as much.
pipelines_config_file =  pry
config = yaml.load(open(pipelines_config_file, 'r'))
print(config)

rtl = ResourceTableLookup(pipelines_config_file)
rtl.resource_lookup("wgbs_pipeline.py", 29)

# try:
# 	input_file = csv.DictReader(f)  # creates the reader object
# except:
#	 raise Exception("Can't read sample table.")
#
for row in input_file: # iterates the rows of the file in orders
	print(row)
	test=False


#LLT = LurkerLogicTable(llt, prt)
#LLT.printme()
#print("build:")
#LLT.build_pipeline("CORE")
#LLT.build_pipeline("WGBSNM")


#
# for row in resource_file: # iterates the rows of the file in orders
#	 print(row)
#	 test=False
