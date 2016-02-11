
from boyle.dicom.utils import DicomFile

#def test_DicomFile():

if __name__ == '__main__':
    import os
    datadir = '/home/alexandre/Projects/bcc/macuto/macuto/dicom'
    %timeit DicomFile(os.path.join(datadir, 'subj1_01.IMA'))