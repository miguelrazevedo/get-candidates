import csv
import subprocess
import argparse
import os
import time
import fnmatch

PIPE = subprocess.PIPE

def check_out_dirs(project, bug, dir_format):
  buggy_dir = dir_format.format(project=project, bug=bug, bf='b')
  fixed_dir = dir_format.format(project=project, bug=bug, bf='f')
  subprocess.call(
    'defects4j checkout -p {} -v {}b -w {}'.format(
      project, bug, buggy_dir),
    shell=True)
  subprocess.call(
    'defects4j checkout -p {} -v {}f -w {}'.format(
      project, bug, fixed_dir),
    shell=True)

def remove_check_out_dirs(project, bug, dir_format):
  buggy_dir = dir_format.format(project=project, bug=bug, bf='b')
  subprocess.call('rm -rf {}'.format(buggy_dir), shell=True)
  fixed_dir = dir_format.format(project=project, bug=bug, bf='f')
  subprocess.call('rm -rf {}'.format(fixed_dir), shell=True)

def get_buggy_lines(project, bug, dir_format, project_dir, absent_path):
  buggy_dir = dir_format.format(project=project, bug=bug, bf='b')
  fixed_dir = dir_format.format(project=project, bug=bug, bf='f')
  
  # Get directory
  print_source_dir_command = 'cd {} && defects4j export -p dir.src.classes'.format(buggy_dir)
  p = subprocess.Popen(print_source_dir_command, shell=True, stdout=PIPE, stderr=PIPE)
  project_source = p.communicate()[0].decode().strip()

  # Get changed classes
  print_source_folder = 'cd {} && defects4j export -p classes.modified'.format(buggy_dir)
  p = subprocess.Popen(print_source_folder, shell=True, stdout=PIPE, stderr=PIPE)
  source_dir = p.communicate()[0].decode().strip().replace(".", "/").split("\n")

  # Get each .buggy.lines and .candidates for each
  current_dir = os.getcwd()
  for i in range(len(source_dir)):
    subprocess.call([current_dir + '/get_buggy_lines.sh'] + [
      f"{source_dir[i]}.java",
      f"{buggy_dir}/{project_source}/{source_dir[i]}.java",
      f"{fixed_dir}/{project_source}/{source_dir[i]}.java",
      f"{project}-{bug}-{i}"
    ])

    subprocess.call(f"mv /tmp/{project}-{bug}-{i}.buggy.lines {project_dir}/{bug}-{i}.buggy.lines", shell=True)

  try:
    subprocess.call(f"java -jar {absent_path} collectCandidates --inputFile {project_dir}/{bug}-{i}.buggy.lines --outputFile {project_dir}/{project}-{bug}-{i}.candidates --srcBug {buggy_dir}/{project_source} --srcFix {fixed_dir}/{project_source}/{source_dir[i]}.java", shell=True, timeout=30)
  except subprocess.TimeoutExpired:
    print(f"Timeout for {project}-{bug}-{i}.candidates")

  # Get all .buggy.lines files and combine them into one
  buggy_lines_files = [filename for filename in os.listdir(project_dir) if fnmatch.fnmatch(filename, f"{bug}-*.buggy.lines")]
  with open(f"{project_dir}/{project}-{bug}.buggy.lines", "w") as new_buggy_file:
    for file in buggy_lines_files:
      filename = project_dir + "/" + file
      with open(filename, "r") as buggy_file:
        content = buggy_file.readlines()
        new_buggy_file.writelines(content)
      
      # Remove the file after being used
      if os.path.exists(filename):
        os.remove(filename)
    

  # Get all .candidates files and combine them into one
  candidates_files = [filename for filename in os.listdir(project_dir) if fnmatch.fnmatch(filename, f"{project}-{bug}-*.candidates")]
  with open(f"{project_dir}/{project}-{bug}.candidates", "w") as new_candidate_file:
    for file in candidates_files:
      filename = project_dir + "/" + file
      with open(project_dir + "/" + file, "r") as candidate_file:
        content = candidate_file.readlines()
        new_candidate_file.writelines(content)
      
      # Remove the file after being used
      if os.path.exists(filename):
        os.remove(filename)

  

if subprocess.call('which defects4j', shell=True, stdout=PIPE) != 0:
  raise RuntimeError('defects4j command not found (try adding defects4j/framework/bin to your path)')

parser = argparse.ArgumentParser()
parser.add_argument('versions_file', help='CSV file with "project,bugId" pairs to ask about')
parser.add_argument('--absent-dir', required=True)
parser.add_argument('--skip-until', help='e.g. "Lang,8" will skip all bugs listed in the CSV until Lang 8')
parser.add_argument('--checkout-dir-format', default='/tmp/ask_for_candidates_{project}_{bug}{bf}', help="path to check projects out into, e.g. `--checkout-dir-format '/tmp/{project}_{bug}{bf}'` will check things out into /tmp/Lang_1b, /tmp/Chart_2f, etc.")

args = parser.parse_args()

with open(args.versions_file) as f:
  versions = list(csv.reader(f))

if args.skip_until is not None:
  project, bug = args.skip_until.split(',')
  versions = versions[versions.index([project, bug]):]

absent_path = args.absent_dir
if not os.path.exists(absent_path):
  raise RuntimeError("ABSENT .jar file not found!")

start_time = time.time()
for i, (project, bug, num_buggy_lines, num_faults_omission) in enumerate(versions[1:], start=1):

  if int(num_faults_omission) < 1:
    continue
  
  project_dir = os.getcwd() + f"/{project}" 
  print(project_dir)
  try:
    os.makedirs(project_dir)
  except FileExistsError:
    pass

  check_out_dirs(project, bug, args.checkout_dir_format)

  # Get the buggy lines and candidates (from ABSENT) files
  get_buggy_lines(project, bug, args.checkout_dir_format, project_dir, absent_path)

  remove_check_out_dirs(project, bug, args.checkout_dir_format)

end_time = time.time()
elapsed_time = end_time - start_time

start_time_local = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
print(f"Starting time: {start_time_local}")


end_time_local = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
print(f"Ending time: {end_time_local}")

execution_time_seconds = end_time - start_time
execution_time_minutes = execution_time_seconds / 60

print(f"Execution time (s): {execution_time_seconds:.2f}")
print(f"Execution time (min): {execution_time_minutes:.2f} minutes")


