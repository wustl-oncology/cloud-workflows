import os
import argparse

# https://stackoverflow.com/questions/56932020/search-all-files-with-same-name-in-a-directory-python

def getAlldirInDiGui(PATH, TARGET, resultList):
    filesList=os.listdir(PATH)
    for fileName in filesList:
        fileAbpath=os.path.join(PATH,fileName)
        if os.path.isdir(fileAbpath):
            getAlldirInDiGui(fileAbpath, TARGET, resultList)
        else:
            if fileName==TARGET:
                resultList.append(fileAbpath)

def relocate(resultList, OUT_DIR):
    for path in resultList:
        tmp = path[2:].replace("/", "-")
        os.rename(path, OUT_DIR + tmp)

if __name__ == "__main__":
    # read in arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--search-dir", default=".") # example: . (current dir)
    parser.add_argument("--target-name", default="monitoring.log") # example: monitoring.log    
    # Has to already exist!
    parser.add_argument("--out-dir", default="./AllMonitoringFiles/") #where the files found go to, example: "./OUTPUTHERE/"
    args = parser.parse_args()
    
    # variables
    PATH = args.search_dir
    TARGET = args.target_name
    OUT_DIR = args.out_dir
    resultList = []
    
    # generate results
    getAlldirInDiGui(PATH, TARGET, resultList)
    relocate(resultList, OUT_DIR)
    # print(resultList)
