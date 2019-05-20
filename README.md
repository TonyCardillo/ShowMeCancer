# ShowMeCancer

In this project, we establish an automated workflow for educators who wish to find single images of specific types of cancer. The educator uses a simplified frontend interface to select exactly which type of cancer they wish to view. We automate the backend process of querying and selecting single relevant slices from retrieved DICOM files. 

Presently, this project covers the “Head-Neck-PET-CT” collection of head and neck cancers. This collection was chosen because it contains supplemental reports that identify relevant anatomy, allowing our automated process to pull a relevant DICOM slice based on the anatomy desired by the educator. Even without these supplemental reports, the methodology could eventually be applied to every collection in the archive, and the educator could manually scroll through the slices to find the desired structures. 

# How to Use
Download the Head-Neck-PET-CT collection from the TCIA and place the patient folders (i.e. "HN-CHUM-001") in the directory as such:

ShowMeCancer\Collection\Head-Neck-PET-CT\*Patient Folder*

PNG files will be cached in ShowMeCancer\Completed\

It takes several minutes to process the images the first time they are queuried, pending further optimization.

This project uses Flask, so simply run the script via flask in the command line:

(while in the ShowMeCancer directory)
(use 'set' for Windows and 'export' for Mac)
set FLASK_APP=retriever.py
set FLASK_ENV=development
python -m flask run 

Then navigate to localhost:5000 or whichever port is specified in the command line.
 