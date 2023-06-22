# FSync1w
 One-way folder synchronizer
 
 
This script synchronizes one-way two folders (SRC -> DST) at specified interval logging info at both console and output file.
The CLI inputs are
 -src SRC = source folder
 -dst DST = destination folder
 -t interval = seconds after which synchronization is re-started
 -log logfile = file where the log is kept
Example:
python fsync1w.py -src .\Tests\FA -dst .\Tests\FB -log .\Tests\log.log -t 15

The script is taking the following steps:
  - scans the content of both folders and keeps path of every found file or folder as strings in a list
  - analyzes the two resulted lists in the following steps:
       - entities in list SRC not in DST are NEW files and folders
       - entities in list DST not in SRC are OLD files and folders
       - files in both lists are further compared with filecmp to decide if files have been MODIFIED or not
  -  makes the required changes in the following order:
       - deletes OLD folders and everything in them
       - deletes OLD files
       - creates NEW folders
       - copies NEW files
       - copies MODIFIED files

 Operations are logged to the console and LOG file recording:
   - date and time of the operation
   - user running the operation
   - step number of the synchronization
   - stage of the synchronization step:
        - INITIALIZING
        - SCANNING / ANALYZING
        - DELETING / CREATING / COPYING
        - SUMMARY / FINALIZING
   - description of the operation

 The SUMMARY stage provides a rough count of files and folders copied or deleted, including the number of OSError occured.
 
