# -----Imports-----
import glob
import os
import sys
import pydicom  # For opening dicom files
import matplotlib.pyplot as plt
import numpy as np  # This will supercede matplotlib as our means of converting HU and saving .pngs
import openpyxl  # For opening Excel files
from flask import Flask, render_template, request

# Get our paths right from the beginning
rootpath = os.path.dirname(os.path.realpath(__file__))+"\\"
collectionpath = rootpath+"\\Collection\\Head-Neck-PET-CT\\"  # Filepath to Collection
print(rootpath)
print(collectionpath)

# -----Classes-----
class Anatomy:
    def __init__(self, anatomyPart):
        self.part = anatomyPart
        self.zpos = []  # This is a set of z-positions or planes that the anatomy exists in
        self.slice = None

    def addZPos(self, zPosAdd):
        if zPosAdd not in self.zpos:
            self.zpos.append(zPosAdd)

    def returnZPos(self):
        return self.zpos

    def clearAll(self):
        self.part = ""
        self.zpos = []

class Session:
    def __init__(self):
        self.ptID = ""
        self.posToSlice = {}
        self.rtstructDir = []
        self.dcmDir = []
        self.dcmList = []
        self.imageList = []  # A list of image filepaths to display

    def resetPt(self):
        self.ptID = ""
        self.posToSlice = {}
        self.rtstructDir = []
        self.dcmDir = []
        self.dcmList = []
        
    def resetAll(self):
        self.ptID = ""
        self.posToSlice = {}
        self.rtstructDir = []
        self.dcmDir = []
        self.dcmList = []
        self.imageList = []  # A list of image filepaths to display


# -----Functions-----

''' 
Read a patients directory and output:
rtstructDir(s)
dcmDir(s)
The index for one matches the index for the other. Contains full file paths
'''
def readPtDir(ptID):
    print("Searching pt " + ptID)
    # Base directory given above found patient
    rootDir = collectionpath + ptID + "\\"
    rtstructDir = []
    dcmDir = []

    # If the rootDir doesn't exist, return a failure
    if not os.path.exists(rootDir):
        return "Patient does not exist in collection"

    '''
    These keywords are used in the CHUM, CHUS, HMR, and HGJ sheets
    This is a major point of optimization - rather than determining 
    the directory type based on keywords, actually walk through the directory,
    see how many .dcm files are in there, if 1 file use a try/except to determine RT
    and >1 file its a dcm folder. Will include PET/CT but these could be excluded by directory name likely

    '''
    rtKeywords = ["1-RTstructCTsim", "RadOnc Structure", "REGCTsim"]
    dcmKeywords = ["Merged", "StandardFull", "CTnormal", "CT IMAGES", "2.5mm"]
    # For each study, find the "components" like rtstruct and
    studyDir = os.listdir(rootDir)  # Some pts have multiple studies, we want to see those

    for study in studyDir:
        print(" Study: " + study)
        compDir = os.listdir(rootDir + study)  # Component directory, or the components of each study

        rtFound = False
        tmpRTdir = ""
        dcmFound = False
        tmpDCMdir = ""

        # For each component in the study...
        for comp in compDir:
            # If this is an rtstruct folder...index it
            if any(x in comp for x in rtKeywords):
                rtFound = True
                tmpRTdir = comp
                # print("    "+tmpRTdir+" is an RTstruct")

            # If this is a dcm folder...index it
            if any(x in comp for x in dcmKeywords):
                dcmFound = True
                tmpDCMdir = comp
                # print("    "+tmpDCMdir+" is an dcm folder")

            # print(comp)

        # If both an RT and dcm folder have been found in a single study, index it
        if rtFound and dcmFound:
            rtstructDir.append(rootDir + study + "\\" + tmpRTdir)
            dcmDir.append(rootDir + study + "\\" + tmpDCMdir)

            #print("  Successful study.")
        else:
            print("  No suitable RTstruct + DCM folder.")

        # ds = pydicom.read_file(root_dir+ptID+study+, force=True)

    # os.chdir(collectionpath)
    return rtstructDir, dcmDir

# Read a patient's directory and get image slices (as .pngs)
# directory are full directories; see readPtDir()
def getPtTumor(rtDir, dcmDir):
    # Change directory to dicom directory
    os.chdir(dcmDir)

    # Iterate through the directory looking for any dicom files, find their position

    # Create a dictionary linking z-pos -> slice #
    session.posToSlice = {}

    for file in glob.glob("*.dcm"):
        ds = pydicom.dcmread(file)
        session.posToSlice[ds.ImagePositionPatient[2]] = file

    ds = pydicom.read_file(rtDir + "\\000000.dcm", force=True)

    # Before anything lets figure out if its a valid RTSTRUCT
    if "ROIContourSequence" not in ds:
        # This is NOT an RTstruct file
        return "This is not a valid RTstruct file"

    # Create a list that will contain Anatomy objects
    anatomyList = []

    try:
        # For all the named regions of interest (body parts) in the study...
        for anatomy in range(len(ds.ROIContourSequence)):
            bodyPart = Anatomy(ds.StructureSetROISequence[anatomy].ROIName)
    
            # For all the contours describing a single body part...
            for cont in range(len(ds.ROIContourSequence[anatomy].ContourSequence)):
                # Save the Z position of the contour
                bodyPart.addZPos(ds.ROIContourSequence[anatomy].ContourSequence[cont].ContourData[2])
            anatomyList.append(bodyPart)
    
        # For every body part identified...
        for part in range(len(anatomyList)):
            # Ignore all body parts NOT tumor
            if "GTV" in anatomyList[part].part:
                # Find the median position representing the body part
                midPos = medianNoAvg(anatomyList[part].returnZPos())
                #print(str(midPos) + " is a midPos")
    
                # Find the DICOM slice representing the median of the body part
                for pos in session.posToSlice:
                    if midPos == pos or withinRange(midPos, pos, 1):
                        session.dcmList.append(dcmDir + "\\" + session.posToSlice[pos])
                        return "Slice " + session.posToSlice[pos] + " appended."
                    else:
                        continue  # May have better luck if it can find another tumor label
    except:
        return "Not a valid RTSTRUCT"
    return "No tumor identified in this RTSTRUCT"

# Within range
def withinRange(test, value, plusMinus):
    if (test >= value - plusMinus) and (test <= (value + plusMinus)):
        return True
    else:
        return False

# Open a dcm and save its image
def saveDCM(fullDirectory, destination, winCenter, winWidth):
    # Open a slice
    ds = pydicom.dcmread(fullDirectory)

    # Make a new patient folder
    if not os.path.exists(destination):
        os.makedirs(destination)

    os.chdir(destination)

    # Lets convert to a normal grayscale space (0-255)
    img = ds.pixel_array.astype(float)
    img = np.maximum(winCenter - winWidth, img)  # Anything lower than lowerlimit is now the lowerlimit
    img = np.minimum(winCenter + winWidth, img)  # Anything higher than the higherlimit is now the higherlimit
    img = img - img.min()
    img = (img / img.max()) * 255.0

    # Convert to uint
    img = np.uint8(img)

    # Plot the image (testing) and save
    plt.figure(figsize=(16, 12))
    plt.axis('off')
    plt.imshow(img, cmap=plt.cm.gray, interpolation="bicubic")  # Colormap, need to correspond this to HU in radiology
    plt.savefig(destination + fullDirectory[-10:] + ".png", bbox_inches='tight')

    return os.path.isfile(destination + fullDirectory[-10:] + ".png")

# A custom median function that doesn't return the average if an even # of items in set
def medianNoAvg(mylist):
    sorts = sorted(mylist)
    length = len(sorts)
    return sorts[length // 2]

def getImageInFolder(folder):
    os.chdir(folder)
    
    ptName = os.path.basename(os.getcwd())

    for file in glob.glob("*.png"):
        session.imageList.append(ptName+"/"+str(file))


# Start up the webserver with Flask
app = Flask(__name__, static_folder="Completed")

# Auto-run in debug mode if running directly from Python
if __name__ == "__main__":
    app.run(debug=True)

# Flask route: home/input page
@app.route("/")
def input():
    return render_template("input.htm")

# Flask route: final render page
@app.route("/", methods=['POST'])
def images():    
    if request.method == 'POST':
        session.resetAll()
        # Import Excel spreadsheet
        desiredAnatomy = request.form['anatomy']
        #print(desiredAnatomy)
        ptWorkbook = openpyxl.load_workbook(rootpath+"Collection\\INFOclinical_HN_Version2_30may2018.xlsx")
        
        # Loop through all sheets looking for anatomy
        candidates = []
        for sheet in ptWorkbook.worksheets:
            for cell in range(sheet.max_row):
                if sheet['D' + str(cell + 2)].value == desiredAnatomy:
                    candidates.append(sheet['A' + str(cell + 2)].value)
                    print(sheet['A' + str(cell + 2)].value + " added as " + sheet['D' + str(cell + 2)].value)

        # Return nothing if the candidate list of patients is empty
        if not candidates:
            return render_template("images.htm")  # Just an empty page
            
        for candidate in candidates:
            print("-----")
            if os.path.exists(rootpath+"Completed\\"+candidate):  # If this candidate has images already
                print(str(candidate) + " already exists!")
                #print(os.listdir(rootpath+"Completed\\"+candidate))
                getImageInFolder(rootpath+"Completed\\"+candidate)
                # we done!
                # return this folder of images
            else:
                session.rtstructDir, session.dcmDir = readPtDir(candidate)
                print(str(candidate) + " is a new candidate with "+str(len(session.dcmDir))+" images")
                
                for index in range(len(session.dcmDir)):
                    getPtTumor(session.rtstructDir[index], session.dcmDir[index])
        
                for image in session.dcmList:
                    # Save with a window of 400 around a center of 1000
                    saveDCM(image,rootpath+"Completed\\"+candidate+"\\",1000,400)
                    getImageInFolder(rootpath+"Completed\\"+candidate)
            session.resetPt()  # Once you've saved files for a person, clear pt specific data
        
    # the code below is executed if the request method
    # was GET or the credentials were invalid
    #print(session.imageList)
    return render_template("images.htm", images=session.imageList)
    
# Run once
plt.ioff()
session = Session()
print("-----")
    
#sys.exit("Completed script")